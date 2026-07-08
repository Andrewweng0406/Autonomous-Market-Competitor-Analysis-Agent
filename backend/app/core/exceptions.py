"""Domain-specific exceptions used across the agent and API layers."""


class AgentError(Exception):
    """Base class for all agent-execution related failures."""


class AgentMaxIterationsError(AgentError):
    """Raised when the agent exceeds its allotted tool-use iterations without
    producing a final report."""


class AgentRefusalError(AgentError):
    """Raised when the model declines to complete the analysis (safety refusal)."""


class AgentTruncatedResponseError(AgentError):
    """Raised when a response hits max_tokens before the model could finish
    (a configuration issue — max_output_tokens is too low for the task)."""


class AgentAPIError(AgentError):
    """Raised when the underlying Anthropic API call fails unrecoverably."""


class ReportValidationError(AgentError):
    """Raised when the model's final report tool call does not match the
    expected schema."""


class SearchToolError(AgentError):
    """Raised when the web search tool fails to retrieve results."""


class TaskNotFoundError(Exception):
    """Raised when a requested task_id does not exist in the task store."""
