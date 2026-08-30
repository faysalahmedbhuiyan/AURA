"""
AURA Backend — Planning Schemas.

Module: app.schemas.planning
Purpose: Pydantic models for the Self Improvement Planner (Phase 9).
"""

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """Request to create an improvement plan."""

    description: str = Field(
        ..., min_length=5, max_length=2000,
        description="Free-text description of the desired improvement.",
    )
    project_root: str = Field(default="D:/AURA")


class RequestAnalysisResponse(BaseModel):
    """Parsed signals from the improvement request."""

    raw_text: str
    mentioned_files: list[str]
    keywords: list[str]
    likely_scope: str


class AffectedFileResponse(BaseModel):
    """A single candidate affected file."""

    path: str
    relevance: float
    reason: str


class RiskResponse(BaseModel):
    """Risk assessment for the proposed change."""

    level: str
    explanation: str
    factors: list[str]


class PlanResponse(BaseModel):
    """
    Full improvement plan. NEVER implies any file was changed —
    status is always 'pending_approval' since applying plans is a
    future capability (Phase 10) that does not exist yet.
    """

    request: str
    analysis: RequestAnalysisResponse
    affected_files: list[AffectedFileResponse]
    risk: RiskResponse
    status: str
    approval_note: str