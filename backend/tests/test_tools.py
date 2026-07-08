import httpx
import pytest

from app.agent.tools import AGENT_TOOLS, _tavily_search, execute_tool, web_search
from app.core.exceptions import SearchToolError

# Captured before any test monkeypatches `httpx.AsyncClient` — the fakes below
# construct a real client (pointed at a mock transport) using this reference,
# never the module attribute, so patching it doesn't cause infinite recursion.
_RealAsyncClient = httpx.AsyncClient


def test_agent_tools_expose_exactly_web_search_and_submit_final_report():
    names = {tool["name"] for tool in AGENT_TOOLS}
    assert names == {"web_search", "submit_final_report"}


@pytest.mark.parametrize("tool", AGENT_TOOLS)
def test_each_tool_has_a_valid_object_schema(tool):
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert "properties" in schema
    assert isinstance(tool["description"], str) and tool["description"]


def test_submit_final_report_schema_requires_core_fields():
    schema = next(t for t in AGENT_TOOLS if t["name"] == "submit_final_report")["input_schema"]
    required = set(schema["required"])
    assert {"subject", "executive_summary", "swot", "markdown_report"} <= required


@pytest.mark.asyncio
async def test_web_search_falls_back_to_mock_when_no_api_key():
    result = await web_search("artisanal coffee subscription market size", api_key=None, max_results=3)
    assert "artisanal coffee subscription market size" in result
    assert "MOCK DATA" in result


@pytest.mark.asyncio
async def test_execute_tool_dispatches_web_search():
    result = await execute_tool(
        "web_search",
        {"query": "Notion vs Coda pricing 2026"},
        tavily_api_key=None,
        search_results_per_query=2,
    )
    assert "Notion vs Coda pricing 2026" in result


@pytest.mark.asyncio
async def test_execute_tool_rejects_unknown_tool_name():
    with pytest.raises(SearchToolError):
        await execute_tool(
            "delete_database",
            {},
            tavily_api_key=None,
            search_results_per_query=2,
        )


@pytest.mark.asyncio
async def test_tavily_search_parses_the_expected_fields(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.tavily.com"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Notion Pricing",
                        "url": "https://notion.so/pricing",
                        "content": "Notion offers a free plan and paid plans starting at $8/user/month.",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    def fake_async_client(**kwargs):
        return _RealAsyncClient(transport=transport, timeout=kwargs.get("timeout"))

    monkeypatch.setattr("app.agent.tools.httpx.AsyncClient", fake_async_client)

    results = await _tavily_search("Notion pricing", api_key="fake-key", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Notion Pricing"
    assert results[0]["url"] == "https://notion.so/pricing"
    assert "paid plans" in results[0]["snippet"]


@pytest.mark.asyncio
async def test_tavily_search_raises_search_tool_error_on_http_failure(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    transport = httpx.MockTransport(handler)

    def fake_async_client(**kwargs):
        return _RealAsyncClient(transport=transport, timeout=kwargs.get("timeout"))

    monkeypatch.setattr("app.agent.tools.httpx.AsyncClient", fake_async_client)

    with pytest.raises(SearchToolError):
        await web_search("anything", api_key="fake-key", max_results=3)
