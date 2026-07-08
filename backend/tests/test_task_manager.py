import asyncio

import pytest

from app.core.exceptions import AgentError, TaskNotFoundError
from app.models.schemas import AnalyzeRequest, FinalReport, SWOTAnalysis, TaskStatus
from app.services.task_manager import STREAM_DONE_SENTINEL, TaskManager


def make_report(subject: str) -> FinalReport:
    return FinalReport(
        subject=subject,
        executive_summary="Summary.",
        swot=SWOTAnalysis(),
        markdown_report="# Report",
    )


class FakeAgent:
    """Stand-in for MarketAnalysisAgent — runs instantly and reports whatever
    result/error/progress messages the test configures."""

    def __init__(self, *, result=None, error=None, progress_messages=None):
        self._result = result
        self._error = error
        self._progress_messages = progress_messages or []

    async def run(self, request, on_progress=None):
        for message in self._progress_messages:
            if on_progress is not None:
                await on_progress(message)
        if self._error is not None:
            raise self._error
        return self._result


async def _wait_for_terminal(manager: TaskManager, task_id: str, timeout: float = 2.0):
    async def _poll():
        while True:
            record = await manager.get_task(task_id)
            if record.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return record
            await asyncio.sleep(0.01)

    return await asyncio.wait_for(_poll(), timeout=timeout)


async def test_task_lifecycle_success():
    report = make_report("Idea A")
    manager = TaskManager(
        agent_factory=lambda: FakeAgent(result=report, progress_messages=["step 1", "step 2"])
    )

    record = await manager.create_task("task-1", AnalyzeRequest(subject="Idea A"))
    assert record.status == TaskStatus.PENDING

    final = await _wait_for_terminal(manager, "task-1")
    assert final.status == TaskStatus.COMPLETED
    assert final.error is None
    assert final.result.subject == "Idea A"


async def test_task_lifecycle_failure_marks_task_failed():
    manager = TaskManager(agent_factory=lambda: FakeAgent(error=AgentError("boom")))
    await manager.create_task("task-2", AnalyzeRequest(subject="Idea B"))

    final = await _wait_for_terminal(manager, "task-2")
    assert final.status == TaskStatus.FAILED
    assert "boom" in final.error


async def test_unexpected_exception_is_caught_and_marks_task_failed():
    manager = TaskManager(agent_factory=lambda: FakeAgent(error=RuntimeError("unexpected bug")))
    await manager.create_task("task-2b", AnalyzeRequest(subject="Idea B"))

    final = await _wait_for_terminal(manager, "task-2b")
    assert final.status == TaskStatus.FAILED
    assert "unexpected bug" in final.error


async def test_get_task_raises_not_found_for_unknown_id():
    manager = TaskManager(agent_factory=lambda: FakeAgent(result=None))
    with pytest.raises(TaskNotFoundError):
        await manager.get_task("does-not-exist")


async def test_subscriber_receives_progress_and_terminal_sentinel():
    report = make_report("Idea C")
    manager = TaskManager(
        agent_factory=lambda: FakeAgent(result=report, progress_messages=["searching..."])
    )
    await manager.create_task("task-3", AnalyzeRequest(subject="Idea C"))
    queue = manager.subscribe("task-3")

    seen = []
    try:
        for _ in range(50):
            message = await asyncio.wait_for(queue.get(), timeout=1.0)
            seen.append(message)
            if message == STREAM_DONE_SENTINEL:
                break
    finally:
        manager.unsubscribe("task-3", queue)

    assert STREAM_DONE_SENTINEL in seen
    assert "searching..." in seen


async def test_subscribe_raises_not_found_for_unknown_task():
    manager = TaskManager(agent_factory=lambda: FakeAgent(result=None))
    with pytest.raises(TaskNotFoundError):
        manager.subscribe("does-not-exist")


async def test_cleanup_expired_removes_old_terminal_tasks():
    report = make_report("Idea D")
    manager = TaskManager(agent_factory=lambda: FakeAgent(result=report))
    await manager.create_task("task-4", AnalyzeRequest(subject="Idea D"))
    await _wait_for_terminal(manager, "task-4")

    # ttl_seconds=0 means "anything already completed counts as expired".
    removed = await manager.cleanup_expired(ttl_seconds=0)

    assert removed == 1
    with pytest.raises(TaskNotFoundError):
        await manager.get_task("task-4")


async def test_cleanup_expired_never_evicts_in_progress_tasks():
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowAgent:
        async def run(self, request, on_progress=None):
            started.set()
            await release.wait()
            return make_report(request.subject)

    manager = TaskManager(agent_factory=lambda: SlowAgent())
    await manager.create_task("task-5", AnalyzeRequest(subject="Idea E"))
    await asyncio.wait_for(started.wait(), timeout=1.0)

    removed = await manager.cleanup_expired(ttl_seconds=0)
    assert removed == 0

    record = await manager.get_task("task-5")
    assert record.status == TaskStatus.IN_PROGRESS

    release.set()
    await _wait_for_terminal(manager, "task-5")
