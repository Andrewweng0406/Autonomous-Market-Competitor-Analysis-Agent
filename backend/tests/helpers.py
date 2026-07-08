"""Lightweight stand-ins for Anthropic SDK objects, used to drive
`MarketAnalysisAgent` through scripted conversations without any network
access. `agent.py` only reads `.content`, `.stop_reason`, and per-block
`.type` / `.name` / `.input` / `.id` — these fakes implement exactly that
surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: Dict[str, Any]
    type: str = "tool_use"


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: List[Any]
    stop_reason: str


class FakeMessagesAPI:
    """Stand-in for `client.messages` — returns one scripted `FakeMessage`
    per call to `.create()`, in order. Records every call's kwargs so tests
    can assert on what was sent (e.g. that tool_results were appended).
    """

    def __init__(self, responses: List[FakeMessage]) -> None:
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> FakeMessage:
        # `agent.py` mutates the same `messages` list in place across turns
        # (it's passed by reference), so snapshot it now — otherwise every
        # recorded call would end up reflecting the *final* conversation
        # state instead of what was actually sent on that turn.
        snapshot = dict(kwargs)
        if "messages" in snapshot:
            snapshot["messages"] = list(snapshot["messages"])
        self.calls.append(snapshot)
        if not self._responses:
            raise AssertionError(
                "FakeMessagesAPI ran out of scripted responses — the agent "
                "made more turns than the test expected."
            )
        return self._responses.pop(0)


class FakeAnthropicClient:
    """Drop-in replacement for `anthropic.AsyncAnthropic` — only implements
    the `.messages.create(...)` surface `MarketAnalysisAgent` uses.
    """

    def __init__(self, responses: List[FakeMessage]) -> None:
        self.messages = FakeMessagesAPI(responses)
