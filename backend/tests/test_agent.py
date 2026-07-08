import pytest

from app.agent.agent import MarketAnalysisAgent
from app.core.exceptions import (
    AgentMaxIterationsError,
    AgentRefusalError,
    AgentTruncatedResponseError,
)
from app.models.schemas import AnalyzeRequest, FinalReport
from tests.helpers import FakeAnthropicClient, FakeMessage, FakeTextBlock, FakeToolUseBlock

VALID_REPORT_INPUT = {
    "subject": "Test subject",
    "executive_summary": "A promising opportunity with moderate risk.",
    "swot": {
        "strengths": ["strong founding team"],
        "weaknesses": ["unproven market"],
        "opportunities": ["growing demand"],
        "threats": ["well-funded incumbents"],
    },
    "competitors": [],
    "market_trends": [],
    "sources": [],
    "markdown_report": "# Report\n\nDetails here.",
}


def make_agent(max_iterations: int = 10) -> MarketAnalysisAgent:
    return MarketAnalysisAgent(
        api_key="test-key",
        model="claude-sonnet-5",
        max_iterations=max_iterations,
        tavily_api_key=None,
    )


async def test_agent_searches_then_submits_final_report():
    agent = make_agent()
    agent._client = FakeAnthropicClient(
        [
            FakeMessage(
                content=[FakeToolUseBlock(id="t1", name="web_search", input={"query": "test market size"})],
                stop_reason="tool_use",
            ),
            FakeMessage(
                content=[FakeToolUseBlock(id="t2", name="submit_final_report", input=VALID_REPORT_INPUT)],
                stop_reason="tool_use",
            ),
        ]
    )

    progress_messages = []

    async def on_progress(message: str) -> None:
        progress_messages.append(message)

    report = await agent.run(AnalyzeRequest(subject="Test subject"), on_progress=on_progress)

    assert isinstance(report, FinalReport)
    assert report.subject == "Test subject"
    assert any("Searching" in m for m in progress_messages)

    # Two model turns should have happened, with the search's tool_result fed
    # back in between.
    assert len(agent._client.messages.calls) == 2
    second_turn_messages = agent._client.messages.calls[1]["messages"]
    last_user_turn = second_turn_messages[-1]
    assert last_user_turn["role"] == "user"
    assert last_user_turn["content"][0]["type"] == "tool_result"
    assert last_user_turn["content"][0]["tool_use_id"] == "t1"


async def test_agent_retries_after_invalid_report_schema():
    agent = make_agent()
    invalid_input = {"subject": "Missing required fields"}
    agent._client = FakeAnthropicClient(
        [
            FakeMessage(
                content=[FakeToolUseBlock(id="t1", name="submit_final_report", input=invalid_input)],
                stop_reason="tool_use",
            ),
            FakeMessage(
                content=[FakeToolUseBlock(id="t2", name="submit_final_report", input=VALID_REPORT_INPUT)],
                stop_reason="tool_use",
            ),
        ]
    )

    report = await agent.run(AnalyzeRequest(subject="Test subject"))

    assert isinstance(report, FinalReport)
    second_turn_messages = agent._client.messages.calls[1]["messages"]
    tool_result = second_turn_messages[-1]["content"][0]
    assert tool_result["is_error"] is True
    assert tool_result["tool_use_id"] == "t1"


async def test_agent_raises_agent_refusal_error_on_refusal():
    agent = make_agent()
    agent._client = FakeAnthropicClient([FakeMessage(content=[], stop_reason="refusal")])

    with pytest.raises(AgentRefusalError):
        await agent.run(AnalyzeRequest(subject="Test subject"))


async def test_agent_raises_truncated_response_error_on_max_tokens():
    agent = make_agent()
    agent._client = FakeAnthropicClient(
        [FakeMessage(content=[FakeTextBlock(text="partial reasoning...")], stop_reason="max_tokens")]
    )

    with pytest.raises(AgentTruncatedResponseError):
        await agent.run(AnalyzeRequest(subject="Test subject"))


async def test_agent_nudges_plain_text_response_then_succeeds():
    agent = make_agent()
    agent._client = FakeAnthropicClient(
        [
            FakeMessage(content=[FakeTextBlock(text="Let me think about this...")], stop_reason="end_turn"),
            FakeMessage(
                content=[FakeToolUseBlock(id="t1", name="submit_final_report", input=VALID_REPORT_INPUT)],
                stop_reason="tool_use",
            ),
        ]
    )

    report = await agent.run(AnalyzeRequest(subject="Test subject"))

    assert isinstance(report, FinalReport)
    second_turn_messages = agent._client.messages.calls[1]["messages"]
    nudge = second_turn_messages[-1]
    assert nudge["role"] == "user"
    assert "submit_final_report" in nudge["content"]


async def test_agent_raises_max_iterations_when_it_never_submits():
    agent = make_agent(max_iterations=2)
    agent._client = FakeAnthropicClient(
        [
            FakeMessage(content=[FakeTextBlock(text="thinking...")], stop_reason="end_turn"),
            FakeMessage(content=[FakeTextBlock(text="still thinking...")], stop_reason="end_turn"),
        ]
    )

    with pytest.raises(AgentMaxIterationsError):
        await agent.run(AnalyzeRequest(subject="Test subject"))
