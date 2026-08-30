"""
AURA Backend — Memory Tier Repository.

Module: app.repositories.memory_tier_repository
Purpose: Database operations for PersonalMemoryEntry, DecisionRecord,
         and LearningQueueItem.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_tier import DecisionRecord, LearningQueueItem, PersonalMemoryEntry

logger = logging.getLogger(__name__)


class MemoryTierRepository:
    """Repository for all Phase 13 memory tier operations."""

    # ── Personal Memory ──────────────────────────────────────────────
    async def create_personal(
        self, db: AsyncSession, key: str, value: str,
        category: str = "preference", is_sensitive: bool = False,
    ) -> PersonalMemoryEntry:
        """Create a personal memory entry."""
        entry = PersonalMemoryEntry(
            key=key, value=value, category=category, is_sensitive=is_sensitive
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        logger.info("Personal memory created: %s", key)
        return entry

    async def list_personal(self, db: AsyncSession) -> list[PersonalMemoryEntry]:
        """List all personal memory entries, newest first."""
        result = await db.execute(
            select(PersonalMemoryEntry).order_by(PersonalMemoryEntry.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_personal(self, db: AsyncSession, entry_id: str) -> bool:
        """Delete a personal memory entry by id."""
        result = await db.execute(
            select(PersonalMemoryEntry).where(PersonalMemoryEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return False
        await db.delete(entry)
        await db.flush()
        return True

    # ── Decision Records ─────────────────────────────────────────────
    async def create_decision(
        self, db: AsyncSession, title: str, context: str, decision: str,
        consequences: str | None = None, status: str = "accepted",
        tags: str | None = None,
    ) -> DecisionRecord:
        """Create a decision record."""
        entry = DecisionRecord(
            title=title, context=context, decision=decision,
            consequences=consequences, status=status, tags=tags,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        logger.info("Decision record created: %s", title)
        return entry

    async def list_decisions(self, db: AsyncSession) -> list[DecisionRecord]:
        """List all decision records, newest first."""
        result = await db.execute(
            select(DecisionRecord).order_by(DecisionRecord.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Learning Queue ────────────────────────────────────────────────
    async def create_queue_item(
        self, db: AsyncSession, target_tier: str, title: str,
        payload: str, source: str = "manual",
    ) -> LearningQueueItem:
        """Add a new item to the learning queue (always starts pending)."""
        item = LearningQueueItem(
            target_tier=target_tier, title=title, payload=payload,
            source=source, status="pending",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        logger.info("Learning queue item added: %s -> %s", title, target_tier)
        return item

    async def get_queue_item(self, db: AsyncSession, item_id: str) -> LearningQueueItem | None:
        """Get a single queue item by id."""
        result = await db.execute(
            select(LearningQueueItem).where(LearningQueueItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_queue(
        self, db: AsyncSession, status: str | None = None
    ) -> list[LearningQueueItem]:
        """List learning queue items, optionally filtered by status."""
        query = select(LearningQueueItem).order_by(LearningQueueItem.created_at.desc())
        if status:
            query = query.where(LearningQueueItem.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_queue_status(
        self, db: AsyncSession, item_id: str, status: str
    ) -> LearningQueueItem | None:
        """Mark a queue item as confirmed or rejected."""
        item = await self.get_queue_item(db, item_id)
        if not item:
            return None
        item.status = status
        await db.flush()
        await db.refresh(item)
        return item


# ── Singleton instance ────────────────────────────────────────────────────────
memory_tier_repository = MemoryTierRepository()