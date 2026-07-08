"""In-memory task store and background execution for long-running analyses.

Design notes for productionizing beyond this skeleton:

- **Multi-process / multi-node deployments**: replace the in-memory `dict`
  with a shared store (Redis, Postgres) so any API instance can serve a
  status request regardless of which instance created the task.
- **Durability**: an in-memory store loses all in-flight tasks on restart.
  A real task queue (Celery, arq, Dramatiq, or a simple DB-backed queue)
  survives restarts and gives you retries for free.
- **Scaling**: `asyncio.create_task` runs the agent in the same event loop
  as the web server. That's fine for I/O-bound agent work (network calls to
  Anthropic + search APIs) at moderate concurrency, but a dedicated worker
  pool is the right move once throughput matters.

The `TaskManager` interface below is intentionally narrow so that swap is
localized to this one file.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Set

from app.agent.agent import MarketAnalysisAgent
from app.core.exceptions import AgentError, TaskNotFoundError
from app.core.logging import get_logger
from app.models.schemas import AnalyzeRequest, FinalReport, TaskStatus, TaskStatusResponse

logger = get_logger(__name__)

# Sentinel pushed to SSE subscriber queues once a task reaches a terminal state.
STREAM_DONE_SENTINEL = "__DONE__"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskRecord:
    task_id: str
    request: AnalyzeRequest
    status: TaskStatus = TaskStatus.PENDING
    progress: Optional[str] = None
    result: Optional[FinalReport] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    subscribers: Set[asyncio.Queue] = field(default_factory=set)

    def to_response(self) -> TaskStatusResponse:
        return TaskStatusResponse(
            task_id=self.task_id,
            status=self.status,
            progress=self.progress,
            created_at=self.created_at,
            updated_at=self.updated_at,
            result=self.result,
            error=self.error,
        )


class TaskManager:
    """Owns the lifecycle of analysis tasks: creation, background execution,
    progress tracking, and status retrieval.
    """

    def __init__(self, agent_factory: Callable[[], MarketAnalysisAgent]) -> None:
        # A factory (rather than a shared instance) so each task gets its own
        # Anthropic client, and so tests can inject a fake agent.
        self._agent_factory = agent_factory
        self._tasks: Dict[str, TaskRecord] = {}
        self._background_tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock()

    async def create_task(self, task_id: str, request: AnalyzeRequest) -> TaskRecord:
        record = TaskRecord(task_id=task_id, request=request)
        async with self._lock:
            self._tasks[task_id] = record

        # Keep a strong reference to the background task — asyncio only holds
        # a weak reference internally, so an unreferenced task can be garbage
        # collected mid-execution.
        task = asyncio.create_task(self._run(task_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return record

    async def get_task(self, task_id: str) -> TaskRecord:
        async with self._lock:
            record = self._tasks.get(task_id)
        if record is None:
            raise TaskNotFoundError(f"No task found with id '{task_id}'")
        return record

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Register a queue that receives progress-message strings for a
        task, used by the SSE streaming endpoint.
        """
        record = self._tasks.get(task_id)
        if record is None:
            raise TaskNotFoundError(f"No task found with id '{task_id}'")
        queue: asyncio.Queue = asyncio.Queue()
        record.subscribers.add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        record = self._tasks.get(task_id)
        if record is not None:
            record.subscribers.discard(queue)

    async def _update(self, task_id: str, *, notify: bool = False, **fields) -> None:
        async with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                return
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = _utcnow()
            subscribers = list(record.subscribers)
            progress_message = record.progress

        if notify and progress_message:
            for queue in subscribers:
                queue.put_nowait(progress_message)

    async def _run(self, task_id: str) -> None:
        await self._update(
            task_id, status=TaskStatus.IN_PROGRESS, progress="Starting analysis...", notify=True
        )
        record = await self.get_task(task_id)

        async def on_progress(message: str) -> None:
            await self._update(task_id, progress=message, notify=True)

        try:
            agent = self._agent_factory()
            report = await agent.run(record.request, on_progress=on_progress)
            await self._update(
                task_id, status=TaskStatus.COMPLETED, result=report, progress="Done", notify=True
            )
        except AgentError as exc:
            logger.warning("Task %s failed: %s", task_id, exc)
            await self._update(task_id, status=TaskStatus.FAILED, error=str(exc))
        except Exception as exc:  # noqa: BLE001 — never leave a task hung on an unexpected bug
            logger.exception("Task %s failed with an unexpected error", task_id)
            await self._update(task_id, status=TaskStatus.FAILED, error=f"Unexpected error: {exc}")
        finally:
            final_record = self._tasks.get(task_id)
            if final_record is not None:
                for queue in list(final_record.subscribers):
                    queue.put_nowait(STREAM_DONE_SENTINEL)
