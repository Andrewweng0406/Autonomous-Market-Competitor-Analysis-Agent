"""Shared pytest setup.

Sets a dummy `ANTHROPIC_API_KEY` before any `app.*` module is imported, since
`app.config.Settings` requires a non-empty key at construction time (and
`app/main.py` builds a `Settings` instance at import time). No real Anthropic
API calls are made anywhere in this suite — wherever the agent loop is
exercised, `MarketAnalysisAgent._client` is replaced with a fake (see
`tests/helpers.py`).
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key")
os.environ.setdefault("TAVILY_API_KEY", "")
