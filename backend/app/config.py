"""Application configuration, loaded from environment variables / .env file."""
from functools import lru_cache
from typing import List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object. Values are sourced from the environment
    (or a local .env file) and validated once at process startup.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Anthropic / Agent configuration -----------------------------------
    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-8"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    max_agent_iterations: int = 10
    max_output_tokens: int = 8000

    # --- Search tool ---------------------------------------------------------
    tavily_api_key: str | None = None
    search_results_per_query: int = 5

    # --- FastAPI / server ------------------------------------------------------
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    cors_allow_origins_raw: str = "http://localhost:3000"

    # --- Task execution --------------------------------------------------------
    task_ttl_seconds: int = 3600

    @property
    def cors_allow_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]

    @field_validator("anthropic_api_key")
    @classmethod
    def _validate_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Set it in your environment or .env file."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — avoids re-parsing the environment on every call."""
    return Settings()
