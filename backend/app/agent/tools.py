"""Tool definitions (Anthropic tool-use schemas) and their client-side
implementations.

Two tools are exposed to the model:

1. ``web_search`` — a client-executed tool that fetches real-time market data.
   Backed by the Tavily Search API when ``TAVILY_API_KEY`` is configured;
   otherwise it falls back to a clearly-labeled mock provider so the backend
   remains runnable out of the box.
2. ``submit_final_report`` — a "structured answer" tool. Rather than parsing
   free-form text at the end of the conversation, we force the model to call
   this tool exactly once with a payload matching ``FinalReport``. This is a
   simple, reliable pattern for getting valid structured JSON out of an
   otherwise free-form agentic loop.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.exceptions import SearchToolError
from app.core.logging import get_logger

logger = get_logger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WEB_SEARCH_TOOL: Dict[str, Any] = {
    "name": "web_search",
    "description": (
        "Search the public web for real-time information — news, funding rounds, "
        "pricing pages, product launches, market-size reports, competitor sites. "
        "Use this whenever you need current information that is not already in "
        "the conversation. Call it multiple times with focused, specific queries "
        "rather than one broad query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A focused search query, e.g. 'Notion pricing plans 2026' or 'AI note-taking startups funding 2026'.",
            },
        },
        "required": ["query"],
    },
}

# Hand-written JSON schema mirroring `app.models.schemas.FinalReport`.
SUBMIT_FINAL_REPORT_TOOL: Dict[str, Any] = {
    "name": "submit_final_report",
    "description": (
        "Submit the completed market & competitor analysis. Call this exactly "
        "once, only after you have gathered enough information via web_search "
        "to support every section. This is the final action of the research task."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "The subject that was analyzed."},
            "executive_summary": {
                "type": "string",
                "description": "2-4 sentence high-level summary of the findings and recommendation.",
            },
            "swot": {
                "type": "object",
                "properties": {
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "opportunities": {"type": "array", "items": {"type": "string"}},
                    "threats": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["strengths", "weaknesses", "opportunities", "threats"],
            },
            "competitors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "estimated_market_position": {"type": "string"},
                        "website": {"type": "string"},
                    },
                    "required": ["name", "description"],
                },
            },
            "market_trends": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "impact": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                    "required": ["title", "description"],
                },
            },
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                    "required": ["title", "url"],
                },
            },
            "markdown_report": {
                "type": "string",
                "description": (
                    "The complete report formatted as Markdown, with headers for "
                    "Executive Summary, Market Overview, Competitor Analysis, SWOT "
                    "Analysis, Trends, and Sources. This is rendered directly to the user."
                ),
            },
        },
        "required": ["subject", "executive_summary", "swot", "markdown_report"],
    },
}

AGENT_TOOLS: List[Dict[str, Any]] = [WEB_SEARCH_TOOL, SUBMIT_FINAL_REPORT_TOOL]


# ---------------------------------------------------------------------------
# web_search implementation
# ---------------------------------------------------------------------------

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
)
async def _tavily_search(query: str, api_key: str, max_results: int) -> List[Dict[str, str]]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "title": item.get("title", "Untitled"),
            "url": item.get("url", ""),
            "snippet": (item.get("content") or "")[:600],
        }
        for item in data.get("results", [])
    ]


def _mock_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """Deterministic offline fallback so the agent is runnable without a
    Tavily API key. Clearly labeled as mock data — never presented as real.
    """
    return [
        {
            "title": f"[MOCK DATA — no TAVILY_API_KEY configured] Result {i + 1} for '{query}'",
            "url": f"https://example.com/mock-result-{i + 1}",
            "snippet": (
                "This is placeholder content because no live search provider is configured. "
                "Set TAVILY_API_KEY in your environment to enable real-time web search."
            ),
        }
        for i in range(min(max_results, 3))
    ]


async def web_search(query: str, *, api_key: Optional[str], max_results: int = 5) -> str:
    """Execute a web search and return a formatted string block suitable for
    a tool_result content field.
    """
    logger.info("web_search: query=%r", query)
    try:
        if api_key:
            results = await _tavily_search(query, api_key, max_results)
        else:
            results = await asyncio.get_event_loop().run_in_executor(
                None, _mock_search, query, max_results
            )
    except Exception as exc:  # noqa: BLE001 — surfaced to the model as a tool error
        logger.exception("web_search failed for query=%r", query)
        raise SearchToolError(f"Search failed for query '{query}': {exc}") from exc

    if not results:
        return f"No results found for query: '{query}'"

    formatted = [f"Search results for: '{query}'\n"]
    for idx, item in enumerate(results, start=1):
        formatted.append(
            f"{idx}. {item['title']}\n   URL: {item['url']}\n   {item['snippet']}\n"
        )
    return "\n".join(formatted)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

async def execute_tool(
    name: str,
    tool_input: Dict[str, Any],
    *,
    tavily_api_key: Optional[str],
    search_results_per_query: int,
) -> str:
    """Execute a client-side tool by name and return its result as a string.

    ``submit_final_report`` is intentionally NOT handled here — it terminates
    the agent loop and is parsed directly by the agent orchestrator.
    """
    if name == "web_search":
        query = tool_input.get("query", "")
        return await web_search(
            query, api_key=tavily_api_key, max_results=search_results_per_query
        )

    raise SearchToolError(f"Unknown tool requested by model: '{name}'")
