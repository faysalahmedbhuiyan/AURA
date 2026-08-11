"""
AURA Backend — Research Schemas.

Module: app.schemas.research
Purpose: Pydantic models for the Knowledge System research pipeline
         (Search → Collect → Verify → Summarize).
"""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Request to research a topic from the web."""

    query: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="en")
    max_sources: int = Field(default=4, ge=1, le=8)


class SourceInfo(BaseModel):
    """A single source used in a research candidate."""

    url: str
    name: str
    snippet: str


class ResearchCandidateResponse(BaseModel):
    """
    A research result awaiting user review.

    This is NEVER saved automatically. The frontend should show this
    to the user, let them edit title/summary/confidence if needed,
    then POST to /api/v1/memory/knowledge to save as pending,
    followed by /api/v1/memory/knowledge/{id}/confirm to activate it.
    """

    title: str
    summary: str
    sources: list[SourceInfo]
    suggested_confidence: float
    language: str