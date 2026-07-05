"""
AURA Backend — Knowledge Repository.

Module: app.repositories.knowledge_repository
Purpose: Database operations for KnowledgeEntry model.
         Enforces confirm-before-save rule — unconfirmed entries
         are stored but never indexed or used in responses.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """
    Repository for KnowledgeEntry database operations.

    Enforces AURA's core principle: never blindly learn from internet.
    All entries start as unconfirmed and require explicit user approval.

    Methods:
        create_entry: Create a new unconfirmed knowledge entry.
        confirm_entry: Mark an entry as user-confirmed.
        get_entry: Get a single entry by ID.
        get_pending: Get all unconfirmed entries.
        get_confirmed: Get all confirmed entries.
        mark_indexed: Mark entry as ChromaDB indexed.
    """

    async def create_entry(
        self,
        db: AsyncSession,
        title: str,
        summary: str,
        source_url: str | None = None,
        source_name: str | None = None,
        category: str | None = None,
        tags: str | None = None,
        confidence: float = 0.0,
        language: str = "en",
    ) -> KnowledgeEntry:
        """
        Create a new unconfirmed knowledge entry.

        Entry starts with is_confirmed=False and is_indexed=False.
        Must be confirmed by user before being used by AURA.

        Args:
            db: Async database session.
            title: Short descriptive title.
            summary: Full knowledge summary.
            source_url: Original source URL.
            source_name: Human-readable source name.
            category: Topic category.
            tags: Comma-separated tags.
            confidence: Source reliability (0.0-1.0).
            language: Language code.

        Returns:
            KnowledgeEntry: Newly created unconfirmed entry.
        """
        entry = KnowledgeEntry(
            title=title,
            summary=summary,
            source_url=source_url,
            source_name=source_name,
            category=category,
            tags=tags,
            confidence=confidence,
            language=language,
            is_confirmed=False,
            is_indexed=False,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        logger.info("Created knowledge entry (pending): %s", entry.id)
        return entry

    async def confirm_entry(
        self,
        db: AsyncSession,
        entry_id: str,
    ) -> KnowledgeEntry | None:
        """
        Mark a knowledge entry as user-confirmed.

        After confirmation, entry will be indexed in ChromaDB
        and used in AURA's responses via RAG.

        Args:
            db: Async database session.
            entry_id: UUID of the entry to confirm.

        Returns:
            KnowledgeEntry | None: Updated entry or None if not found.
        """
        entry = await self.get_entry(db, entry_id)
        if not entry:
            return None

        entry.is_confirmed = True
        entry.confirmed_at = datetime.now(timezone.utc).isoformat()
        await db.flush()
        await db.refresh(entry)
        logger.info("Knowledge entry confirmed: %s", entry_id)
        return entry

    async def get_entry(
        self,
        db: AsyncSession,
        entry_id: str,
    ) -> KnowledgeEntry | None:
        """
        Get a knowledge entry by ID.

        Args:
            db: Async database session.
            entry_id: UUID of the entry.

        Returns:
            KnowledgeEntry | None: Entry or None if not found.
        """
        result = await db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_pending(
        self,
        db: AsyncSession,
    ) -> list[KnowledgeEntry]:
        """
        Get all unconfirmed knowledge entries awaiting user review.

        Returns:
            list[KnowledgeEntry]: Unconfirmed entries.
        """
        result = await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.is_confirmed == False)  # noqa: E712
            .order_by(KnowledgeEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_confirmed(
        self,
        db: AsyncSession,
    ) -> list[KnowledgeEntry]:
        """
        Get all user-confirmed knowledge entries.

        Returns:
            list[KnowledgeEntry]: Confirmed entries.
        """
        result = await db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.is_confirmed == True)  # noqa: E712
            .order_by(KnowledgeEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_indexed(
        self,
        db: AsyncSession,
        entry_id: str,
    ) -> None:
        """
        Mark a knowledge entry as indexed in ChromaDB.

        Called after successful ChromaDB vector storage.

        Args:
            db: Async database session.
            entry_id: UUID of the indexed entry.
        """
        entry = await self.get_entry(db, entry_id)
        if entry:
            entry.is_indexed = True
            await db.flush()
            logger.info("Knowledge entry indexed: %s", entry_id)


# ── Singleton instance ────────────────────────────────────────────────────────
knowledge_repository = KnowledgeRepository()