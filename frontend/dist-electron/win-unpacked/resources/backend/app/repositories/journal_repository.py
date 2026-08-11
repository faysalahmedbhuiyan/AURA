"""
AURA Backend — Journal Repository.

Module: app.repositories.journal_repository
Purpose: Database operations for JournalEntry. Journal entries are
         write-once records — there is no update/delete endpoint by
         design, keeping the development history tamper-evident.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntry

logger = logging.getLogger(__name__)


class JournalRepository:
    """
    Repository for JournalEntry database operations.

    Methods:
        create_entry: Add a new journal entry.
        list_entries: List entries with optional filters.
        get_recent: Get entries from the last N days.
    """

    async def create_entry(
        self,
        db: AsyncSession,
        category: str,
        title: str,
        content: str,
        tags: str | None = None,
        files_created: str | None = None,
        files_modified: str | None = None,
        files_deleted: str | None = None,
        related_phase: str | None = None,
    ) -> JournalEntry:
        """
        Create a new journal entry.

        Args:
            db: Async database session.
            category: 'session_log' | 'decision' | 'change'.
            title: Short entry title.
            content: Full entry text.
            tags: Comma-separated tags.
            files_created: Comma-separated file paths.
            files_modified: Comma-separated file paths.
            files_deleted: Comma-separated file paths.
            related_phase: Optional phase label.

        Returns:
            JournalEntry: The newly created entry.
        """
        entry = JournalEntry(
            category=category,
            title=title,
            content=content,
            tags=tags,
            files_created=files_created,
            files_modified=files_modified,
            files_deleted=files_deleted,
            related_phase=related_phase,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        logger.info("Journal entry created: [%s] %s", category, title)
        return entry

    async def list_entries(
        self,
        db: AsyncSession,
        category: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JournalEntry]:
        """
        List journal entries, newest first, with optional filters.

        Args:
            db: Async database session.
            category: Filter by category if provided.
            search: Case-insensitive substring search on title/content.
            limit: Max entries to return.
            offset: Pagination offset.

        Returns:
            list[JournalEntry]: Matching entries, newest first.
        """
        query = select(JournalEntry)

        if category:
            query = query.where(JournalEntry.category == category)

        if search:
            like = f"%{search}%"
            query = query.where(
                or_(
                    JournalEntry.title.ilike(like),
                    JournalEntry.content.ilike(like),
                )
            )

        query = query.order_by(JournalEntry.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recent(self, db: AsyncSession, days: int = 7) -> list[JournalEntry]:
        """
        Get all entries created within the last N days.

        Args:
            db: Async database session.
            days: Lookback window in days.

        Returns:
            list[JournalEntry]: Entries newest first.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = await db.execute(
            select(JournalEntry)
            .where(JournalEntry.created_at >= cutoff)
            .order_by(JournalEntry.created_at.desc())
        )
        return list(result.scalars().all())


# ── Singleton instance ────────────────────────────────────────────────────────
journal_repository = JournalRepository()