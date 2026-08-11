"""
AURA Backend — Journal Schemas.

Module: app.schemas.journal
Purpose: Pydantic models for the Development Journal (Phase 12).
"""

from pydantic import BaseModel, Field


class JournalEntryCreate(BaseModel):
    """Request schema for creating a journal entry."""

    category: str = Field(
        ..., description="session_log | decision | change"
    )
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    tags: str | None = None
    files_created: str | None = None
    files_modified: str | None = None
    files_deleted: str | None = None
    related_phase: str | None = None


class JournalEntryResponse(BaseModel):
    """Response schema for a journal entry."""

    id: str
    category: str
    title: str
    content: str
    tags: str | None
    files_created: str | None
    files_modified: str | None
    files_deleted: str | None
    related_phase: str | None
    created_at: str


class JournalSummaryResponse(BaseModel):
    """Response schema for a generated summary."""

    period_days: int
    total_entries: int
    by_category: dict[str, int]
    groups: dict[str, list[dict]]
    files_touched: list[str]