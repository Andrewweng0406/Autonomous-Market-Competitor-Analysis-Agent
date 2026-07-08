"""Core agent orchestration logic.

Implements a manual tool-use loop against the Anthropic Messages API (native
tool calling / function calling). The loop:

  1. Sends the task + system prompt to Claude with the `web_search` and
     `submit_final_report` tools available.
  2. Executes any `web_search` tool calls the model makes and feeds the
     results back.
  3. Repeats until the model calls `submit_final_report`, at which point the
     tool input is validated against `FinalReport` and returned.

We use a manual loop (rather than the SDK's beta tool runner) so this
skeleton has zero beta dependencies and full control over progress reporting
back to the task manager / API layer.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional

import anthropic
from pydantic import ValidationError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import AGENT_TOOLS, execute_tool
from app.core.exceptions import (
    AgentAPIError,
    AgentMaxIterationsError,
    AgentRefusalError,
    AgentTruncatedResponseError,
    SearchToolError,
)
from app.core.logging import get_logger
from app.models.schemas import AnalyzeRequest, FinalReport

logger = get_logger(__name__)

ProgressCallback = Callable[[str], Awaitable[None]]


class MarketAnalysisAgent:
    """Autonomous research agent that turns a business subject into a
    structured market & competitor analysis report.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        effort: str = "high",
        max_iterations: int = 10,
        max_output_tokens: int = 8000,
        tavily_api_key: Optional[str] = None,
        search_results_per_query: int = 5,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._effort = effort
        self._max_iterations = max_iterations
        self._max_output_tokens = max_output_tokens
        self._tavily_api_key = tavily_api_key
        self._search_results_per_query = search_results_per_query

    async def run(
        self,
        request: AnalyzeRequest,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> FinalReport:
        """Run the full research -> synthesis -> report loop.

        Returns a validated FinalReport. Raises an AgentError subclass if the
        agent cannot complete the task (refusal, truncation, max iterations).
        """
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": self._build_task_prompt(request)}
        ]

        async def progress(message: str) -> None:
            logger.info(message)
            if on_progress is not None:
                await on_progress(message)

        await progress("Planning research strategy...")

        for iteration in range(1, self._max_iterations + 1):
            logger.debug("Agent iteration %d/%d", iteration, self._max_iterations)

            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_output_tokens,
                    system=SYSTEM_PROMPT,
                    thinking={"type": "adaptive", "display": "summarized"},
                    output_config={"effort": self._effort},
                    tools=AGENT_TOOLS,
                    messages=messages,
                )
            except anthropic.APIError as exc:
                raise AgentAPIError(f"Anthropic API call failed: {exc}") from exc

            if response.stop_reason == "refusal":
                raise AgentRefusalError(
                    "The model declined to complete this analysis for safety reasons."
                )

            # Always preserve the full assistant turn — including thinking and
            # tool_use blocks — before doing anything else with it.
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "max_tokens":
                raise AgentTruncatedResponseError(
                    "The model's response was truncated before it could finish "
                    "(max_tokens reached). Increase max_output_tokens and retry."
                )

            final_report = await self._handle_tool_use(response, messages, progress)
            if final_report is not None:
                await progress("Analysis complete.")
                return final_report

            if response.stop_reason == "end_turn":
                # Model responded with plain text instead of calling a tool —
                # steer it back toward completing the task.
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Please continue. Use web_search to gather any "
                            "remaining evidence, then call submit_final_report "
                            "with your complete findings. Do not respond with "
                            "plain text only."
                        ),
                    }
                )

        raise AgentMaxIterationsError(
            f"Agent did not produce a final report within {self._max_iterations} iterations."
        )

    async def _handle_tool_use(
        self,
        response: Any,
        messages: List[Dict[str, Any]],
        progress: ProgressCallback,
    ) -> Optional[FinalReport]:
        """Execute any tool_use blocks in `response`.

        Returns a validated FinalReport if `submit_final_report` was called
        successfully. Otherwise appends a user turn with tool_result blocks
        (including error results for failed searches / invalid submissions)
        and returns None so the loop continues.
        """
        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
        if not tool_use_blocks:
            return None

        tool_results: List[Dict[str, Any]] = []

        for block in tool_use_blocks:
            if block.name == "submit_final_report":
                try:
                    return FinalReport.model_validate(block.input)
                except ValidationError as exc:
                    logger.warning("submit_final_report failed schema validation: %s", exc)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                f"Your submission did not match the required schema: {exc}. "
                                "Please correct the fields and call submit_final_report again."
                            ),
                            "is_error": True,
                        }
                    )
                    continue

            if block.name == "web_search":
                await progress(f"Searching: {block.input.get('query', '')}")
            else:
                await progress(f"Calling tool: {block.name}")

            try:
                result_text = await execute_tool(
                    block.name,
                    block.input,
                    tavily_api_key=self._tavily_api_key,
                    search_results_per_query=self._search_results_per_query,
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                )
            except SearchToolError as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    }
                )

        messages.append({"role": "user", "content": tool_results})
        return None

    @staticmethod
    def _build_task_prompt(request: AnalyzeRequest) -> str:
        parts = [
            f"Subject to analyze: {request.subject}",
            f"Subject type: {request.subject_type.value}",
            f"Requested analysis depth: {request.depth.value}",
        ]
        if request.additional_context:
            parts.append(f"Additional context from the user: {request.additional_context}")
        parts.append(
            "Research this subject thoroughly using web_search, then submit your "
            "findings via submit_final_report."
        )
        return "\n".join(parts)
