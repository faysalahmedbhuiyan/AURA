"""
AURA Backend — Review Schemas.

Module: app.schemas.review
Purpose: Pydantic models for the Self Review Engine (Phase 8).
"""

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """Request to review a file or directory."""

    path: str = Field(..., description="Absolute path to file or directory")
    max_files: int = Field(default=200, ge=1, le=1000)


class DebtSummary(BaseModel):
    total_score: int
    average_score: float
    files_analyzed: int
    total_issues: int
    worst_files: list[dict]
    by_category: dict[str, int]
    by_severity: dict[str, int]


class Suggestion(BaseModel):
    title: str
    description: str
    affected_files: list[str]
    priority: str
    issue_count: int


class Issue(BaseModel):
    file_path: str
    line: int
    category: str
    severity: str
    message: str


class ReviewResponse(BaseModel):
    """
    Full review report. READ-ONLY — no changes were made to any file.
    """

    target: str
    files_analyzed: int
    debt_summary: DebtSummary
    suggestions: list[Suggestion]
    issues: list[Issue]