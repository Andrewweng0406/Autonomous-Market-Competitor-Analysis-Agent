"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Or via the provided Dockerfile / docker-compose for a containerized run.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.agent import MarketAnalysisAgent
from app.api.routes import router as api_router
from app.config import Settings, get_settings
from app.core.exceptions import AgentError, TaskNotFoundError
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import RateLimiter
from app.services.task_manager import TaskManager

settings: Settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def _make_agent_factory(settings: Settings):
    """Returns a zero-arg factory that builds a fresh MarketAnalysisAgent.

    A factory (rather than one shared instance) keeps each background task's
    Anthropic client isolated, which is the simplest safe option for a
    single-process deployment.
    """

    def factory() -> MarketAnalysisAgent:
        return MarketAnalysisAgent(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            effort=settings.anthropic_effort,
            max_iterations=settings.max_agent_iterations,
            max_output_tokens=settings.max_output_tokens,
            tavily_api_key=settings.tavily_api_key,
            search_results_per_query=settings.search_results_per_query,
        )

    return factory


async def _cleanup_loop(task_manager: TaskManager, settings: Settings) -> None:
    """Periodically evicts expired completed/failed tasks from the in-memory
    store. Runs for the lifetime of the app; cancelled on shutdown.
    """
    while True:
        await asyncio.sleep(settings.task_cleanup_interval_seconds)
        try:
            removed = await task_manager.cleanup_expired(settings.task_ttl_seconds)
            if removed:
                logger.info("Task cleanup: evicted %d expired task(s).", removed)
        except Exception:  # noqa: BLE001 — a sweep failure should never crash the app
            logger.exception("Task cleanup loop encountered an error.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting Autonomous Market & Competitor Analysis Agent (model=%s, env=%s)",
        settings.anthropic_model,
        settings.app_env,
    )
    if not settings.tavily_api_key:
        logger.warning(
            "TAVILY_API_KEY is not set — web_search will return mock/placeholder "
            "results instead of live data. See .env.example."
        )
    app.state.task_manager = TaskManager(agent_factory=_make_agent_factory(settings))
    app.state.rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_per_minute, window_seconds=60
    )
    cleanup_task = asyncio.create_task(_cleanup_loop(app.state.task_manager, settings))

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutting down.")


app = FastAPI(
    title="Autonomous Market & Competitor Analysis Agent",
    description=(
        "Give the agent a business idea, product concept, or company name and it "
        "will plan a research strategy, search the web for real-time market data, "
        "and return a structured SWOT + competitor analysis report."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
    logger.error("Unhandled AgentError: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": f"Agent execution failed: {exc}"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        # Raw 422 rather than the status.* constant — Starlette renamed
        # HTTP_422_UNPROCESSABLE_ENTITY to HTTP_422_UNPROCESSABLE_CONTENT in
        # recent releases; the plain int is stable across both.
        status_code=422,
        content={"detail": "Invalid request payload.", "errors": exc.errors()},
    )


app.include_router(api_router, prefix="/api")


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "Autonomous Market & Competitor Analysis Agent",
        "status": "running",
        "docs": "/docs",
    }
