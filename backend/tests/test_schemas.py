import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalysisDepth,
    AnalyzeRequest,
    FinalReport,
    SubjectType,
    SWOTAnalysis,
)


def test_analyze_request_applies_defaults():
    req = AnalyzeRequest(subject="A subscription box for artisanal coffee")
    assert req.subject_type == SubjectType.IDEA
    assert req.depth == AnalysisDepth.STANDARD
    assert req.additional_context is None


def test_analyze_request_rejects_too_short_subject():
    with pytest.raises(ValidationError):
        AnalyzeRequest(subject="a")


def test_analyze_request_rejects_too_long_subject():
    with pytest.raises(ValidationError):
        AnalyzeRequest(subject="x" * 501)


def test_analyze_request_accepts_explicit_fields():
    req = AnalyzeRequest(
        subject="Notion competitor",
        subject_type="company",
        depth="deep",
        additional_context="Focus on the European market.",
    )
    assert req.subject_type == SubjectType.COMPANY
    assert req.depth == AnalysisDepth.DEEP


def test_final_report_requires_core_fields():
    with pytest.raises(ValidationError):
        FinalReport(subject="x")  # missing executive_summary, swot, markdown_report


def test_final_report_minimal_valid_payload():
    report = FinalReport(
        subject="x",
        executive_summary="A promising but crowded market.",
        swot=SWOTAnalysis(strengths=["first-mover advantage"]),
        markdown_report="# Report\n\nDetails.",
    )
    # Optional list fields default to empty rather than None/missing.
    assert report.competitors == []
    assert report.market_trends == []
    assert report.sources == []
    assert report.swot.weaknesses == []
