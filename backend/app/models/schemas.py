"""Pydantic models shared across the API layer and the agent."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request / task lifecycle
# ---------------------------------------------------------------------------

class SubjectType(str, Enum):
    IDEA = "idea"
    PRODUCT = "product"
    COMPANY = "company"


class AnalysisDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class AnalyzeRequest(BaseModel):
    subject: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="The business idea, product concept, or company name to analyze.",
    )
    subject_type: SubjectType = Field(
        default=SubjectType.IDEA,
        description="What kind of subject this is — shapes the research strategy.",
    )
    additional_context: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Any extra context the user wants the agent to consider (target market, geography, etc.).",
    )
    depth: AnalysisDepth = Field(
        default=AnalysisDepth.STANDARD,
        description="Controls how many search iterations the agent performs.",
    )


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


# ---------------------------------------------------------------------------
# Agent output — SWOT / competitor analysis
# ---------------------------------------------------------------------------

class SWOTAnalysis(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)


class Competitor(BaseModel):
    name: str
    description: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    estimated_market_position: Optional[str] = Field(
        default=None, description="e.g. 'market leader', 'niche challenger', 'emerging entrant'"
    )
    website: Optional[str] = None


class MarketTrend(BaseModel):
    title: str
    description: str
    impact: Literal["high", "medium", "low"] = "medium"


class SourceCitation(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None


class FinalReport(BaseModel):
    """The structured deliverable produced by the agent's `submit_final_report`
    tool call. This is the single source of truth for both the JSON API
    response and the rendered Markdown report.
    """

    subject: str
    executive_summary: str = Field(..., description="2-4 sentence high-level summary of the findings.")
    swot: SWOTAnalysis
    competitors: List[Competitor] = Field(default_factory=list)
    market_trends: List[MarketTrend] = Field(default_factory=list)
    sources: List[SourceCitation] = Field(default_factory=list)
    markdown_report: str = Field(
        ..., description="The complete, well-structured Markdown report ready to render to the user."
    )


# ---------------------------------------------------------------------------
# Task status polling
# ---------------------------------------------------------------------------

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: Optional[str] = Field(default=None, description="Human-readable description of the current step.")
    created_at: datetime
    updated_at: datetime
    result: Optional[FinalReport] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
