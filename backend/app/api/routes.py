"""HTTP API routes for the market analysis agent."""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.core.exceptions import TaskNotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import RateLimiter
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    TaskStatus,
    TaskStatusResponse,
)
from app.services.task_manager import STREAM_DONE_SENTINEL, TaskManager

logger = get_logger(__name__)
router = APIRouter()


def get_task_manager(request: Request) -> TaskManager:
    """Dependency accessor for the singleton TaskManager created at app startup."""
    return request.app.state.task_manager


def _client_key(request: Request) -> str:
    """Best-effort client identifier for rate limiting. Honors X-Forwarded-For
    (first hop) since this service is typically deployed behind a proxy/LB;
    falls back to the direct connection address.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    """Dependency that 429s once a client exceeds the configured per-minute
    limit on expensive endpoints. Disabled entirely when
    RATE_LIMIT_PER_MINUTE=0.
    """
    limiter: Optional[RateLimiter] = getattr(request.app.state, "rate_limiter", None)
    if limiter is None or limiter.max_requests <= 0:
        return
    key = _client_key(request)
    if not limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before starting another analysis.",
            headers={"Retry-After": str(limiter.retry_after_seconds(key))},
        )


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(model=settings.anthropic_model)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=202,
    tags=["analysis"],
    summary="Start an asynchronous market & competitor analysis",
    dependencies=[Depends(enforce_rate_limit)],
    responses={429: {"description": "Rate limit exceeded"}},
)
async def analyze(
    payload: AnalyzeRequest,
    task_manager: TaskManager = Depends(get_task_manager),
) -> AnalyzeResponse:
    """Kick off an autonomous research task for the given subject.

    This returns immediately (HTTP 202) with a `task_id` — the agent runs in
    the background and typically takes anywhere from 30 seconds to a few
    minutes depending on `depth`. Track progress via:

    - `GET /api/status/{task_id}` — poll for current status + final result
    - `GET /api/stream/{task_id}` — Server-Sent Events stream of live progress

    Rate limited per client IP (see `RATE_LIMIT_PER_MINUTE`) since each call
    fans out into several Claude + search-provider requests.
    """
    task_id = str(uuid.uuid4())
    await task_manager.create_task(task_id, payload)
    return AnalyzeResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Analysis started. Poll GET /api/status/{task_id} for updates.",
    )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    tags=["analysis"],
    responses={404: {"description": "Task not found"}},
)
async def get_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> TaskStatusResponse:
    try:
        record = await task_manager.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.to_response()


@router.get(
    "/stream/{task_id}",
    tags=["analysis"],
    responses={404: {"description": "Task not found"}},
    summary="Server-Sent Events stream of live task progress",
)
async def stream_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> StreamingResponse:
    """Stream progress updates as Server-Sent Events.

    Recommended for interactive frontends — avoids polling latency and lets
    the UI show live steps ("Searching: ...") as the agent works. See
    docs/ARCHITECTURE.md for the polling-vs-streaming tradeoffs.
    """
    # Validate the task exists before opening the stream.
    try:
        await task_manager.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    queue = task_manager.subscribe(task_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Emit current state immediately so late subscribers see where
            # things stand rather than waiting for the next transition.
            current = await task_manager.get_task(task_id)
            yield _sse_event(current.to_response().model_dump(mode="json"))
            if current.status.value in ("completed", "failed"):
                return

            while True:
                message = await queue.get()
                latest = await task_manager.get_task(task_id)
                yield _sse_event(latest.to_response().model_dump(mode="json"))
                if message == STREAM_DONE_SENTINEL:
                    break
        finally:
            task_manager.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
