import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import FinalReport, SWOTAnalysis
from app.services.task_manager import TaskManager


def make_report(subject: str) -> FinalReport:
    return FinalReport(
        subject=subject,
        executive_summary="Summary.",
        swot=SWOTAnalysis(),
        markdown_report="# Report",
    )


class InstantAgent:
    """Fake agent used in place of MarketAnalysisAgent for API-level tests —
    completes immediately with no network calls."""

    async def run(self, request, on_progress=None):
        if on_progress is not None:
            await on_progress("Searching: mock query")
        return make_report(request.subject)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        # The real lifespan wires up a TaskManager backed by MarketAnalysisAgent
        # (which would try to call the real Anthropic API). Swap in a fast,
        # deterministic fake so these tests never hit the network.
        test_client.app.state.task_manager = TaskManager(agent_factory=lambda: InstantAgent())
        yield test_client


def _wait_for_terminal_status(client: TestClient, task_id: str, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/status/{task_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"Task {task_id} did not reach a terminal state within {timeout}s")


def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_analyze_then_poll_status_to_completion(client: TestClient):
    response = client.post(
        "/api/analyze",
        json={
            "subject": "AI-powered pet food subscription",
            "subject_type": "idea",
            "depth": "standard",
        },
    )
    assert response.status_code == 202
    task_id = response.json()["task_id"]

    final_status = _wait_for_terminal_status(client, task_id)
    assert final_status["status"] == "completed"
    assert final_status["result"]["subject"] == "AI-powered pet food subscription"
    assert final_status["error"] is None


def test_status_returns_404_for_unknown_task(client: TestClient):
    response = client.get("/api/status/does-not-exist")
    assert response.status_code == 404


def test_analyze_rejects_subject_that_is_too_short(client: TestClient):
    response = client.post("/api/analyze", json={"subject": "a"})
    assert response.status_code == 422


def test_analyze_rejects_missing_subject(client: TestClient):
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422


def test_rate_limit_returns_429_once_exceeded(client: TestClient):
    # The real rate limiter was created during startup from Settings; tighten
    # it here for a fast, deterministic test rather than issuing 6+ requests.
    client.app.state.rate_limiter.max_requests = 2

    payload = {"subject": "A subscription box for something"}
    first = client.post("/api/analyze", json=payload)
    second = client.post("/api/analyze", json=payload)
    third = client.post("/api/analyze", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    assert "Retry-After" in third.headers


def test_stream_endpoint_delivers_final_completed_state(client: TestClient):
    response = client.post("/api/analyze", json={"subject": "A meal-kit delivery startup"})
    task_id = response.json()["task_id"]

    final_payload = None
    with client.stream("GET", f"/api/stream/{task_id}") as stream_response:
        assert stream_response.status_code == 200
        assert stream_response.headers["content-type"].startswith("text/event-stream")
        for line in stream_response.iter_lines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line[len("data:"):].strip())
            if payload["status"] in ("completed", "failed"):
                final_payload = payload
                break

    assert final_payload is not None
    assert final_payload["status"] == "completed"
    assert final_payload["result"]["subject"] == "A meal-kit delivery startup"


def test_stream_endpoint_404s_for_unknown_task(client: TestClient):
    response = client.get("/api/stream/does-not-exist")
    assert response.status_code == 404
