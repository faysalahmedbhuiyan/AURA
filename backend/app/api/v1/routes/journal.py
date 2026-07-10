"""
AURA Backend — Journal Routes.

Module: app.api.v1.routes.journal
Purpose: API endpoints for AURA's Development Journal (Phase 12).

Endpoints:
    POST /api/v1/journal/entries  — Create a journal entry
    GET  /api/v1/journal/entries  — List entries (with filters)
    GET  /api/v1/journal/summary  — Generate a summary for a time window
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.journal.summary_generator import summary_generator
from app.repositories.journal_repository import journal_repository
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(entry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        category=entry.category,
        title=entry.title,
        content=entry.content,
        tags=entry.tags,
        files_created=entry.files_created,
        files_modified=entry.files_modified,
        files_deleted=entry.files_deleted,
        related_phase=entry.related_phase,
        created_at=entry.created_at,
    )


@router.post(
    "/journal/entries",
    response_model=JournalEntryResponse,
    summary="Create a Journal Entry",
    description="Add a session log, architecture decision, or change record.",
    tags=["Journal"],
    status_code=201,
)
async def create_entry(
    request: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> JournalEntryResponse:
    """
    Create a new journal entry.

    Args:
        request: Entry data.
        db: Injected database session.

    Returns:
        JournalEntryResponse: The created entry.
    """
    entry = await journal_repository.create_entry(
        db,
        category=request.category,
        title=request.title,
        content=request.content,
        tags=request.tags,
        files_created=request.files_created,
        files_modified=request.files_modified,
        files_deleted=request.files_deleted,
        related_phase=request.related_phase,
    )
    return _to_response(entry)


@router.get(
    "/journal/entries",
    response_model=list[JournalEntryResponse],
    summary="List Journal Entries",
    description="List journal entries, newest first, with optional filters.",
    tags=["Journal"],
)
async def list_entries(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[JournalEntryResponse]:
    """
    List journal entries with optional category/search filters.

    Args:
        category: Filter by 'session_log' | 'decision' | 'change'.
        search: Substring search on title/content.
        limit: Max results.
        offset: Pagination offset.
        db: Injected database session.

    Returns:
        list[JournalEntryResponse]: Matching entries.
    """
    entries = await journal_repository.list_entries(
        db, category=category, search=search, limit=limit, offset=offset
    )
    return [_to_response(e) for e in entries]


@router.get(
    "/journal/summary",
    response_model=JournalSummaryResponse,
    summary="Generate a Journal Summary",
    description="Summarizes journal entries from the last N days, grouped by category.",
    tags=["Journal"],
)
async def get_summary(
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> JournalSummaryResponse:
    """
    Generate a summary of recent journal activity.

    Args:
        days: Lookback window in days.
        db: Injected database session.

    Returns:
        JournalSummaryResponse: Grouped summary of recent entries.
    """
    entries = await journal_repository.get_recent(db, days=days)
    summary = summary_generator.generate(entries, days)
    return JournalSummaryResponse(**summary)