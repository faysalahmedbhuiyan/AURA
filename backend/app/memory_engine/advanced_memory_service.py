"""
AURA Backend — Advanced Memory Service.

Module: app.memory_engine.advanced_memory_service
Purpose: Main orchestrator for Phase 22 Advanced Memory Engine.
         Handles all memory CRUD operations across all layers.
         Enforces confirm-before-save for all new memories.

Memory Layers:
    personal    — Facts about Faysal
    preference  — User preferences and habits
    decision    — Important decisions
    project     — Project knowledge
    coding      — Code patterns and solutions
    learning    — Pending confirmation (learning queue)
    journal     — Daily journal entries
    conversation — Short-term chat context

All operations:
    1. New memory → LearningQueue (unconfirmed)
    2. User confirms → MemoryEntry (permanent)
    3. MemoryEntry → ChromaDB index (searchable)
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory_engine.models.memory_models import LearningQueueItem, MemoryEntry
from app.memory_engine.services.importance_scorer import importance_scorer
from app.memory_engine.services.memory_recall import memory_recall
from app.memory_engine.services.memory_summarizer import memory_summarizer

logger = logging.getLogger(__name__)

MemoryLayer = Literal[
    "personal", "preference", "decision", "project",
    "coding", "learning", "journal", "conversation",
]

MemoryType = Literal["semantic", "episodic", "procedural"]


class AdvancedMemoryService:
    """
    Advanced Memory Engine — main service.

    Provides JARVIS-like memory capabilities:
    - Multi-layer memory storage
    - Importance-based retention
    - Semantic recall via ChromaDB
    - LLM-powered summarization
    - Learning queue with confirmation gate

    Methods:
        add_to_queue: Add item to learning queue (unconfirmed)
        confirm_from_queue: Move from queue to permanent memory
        reject_from_queue: Reject a queued item
        create_memory: Create confirmed memory directly
        recall: Search memories semantically
        get_context: Get memory context for chat
        get_layer_memories: List memories in a layer
        get_queue: List pending queue items
        expire_memories: Mark expired memories
    """

    async def add_to_queue(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        suggested_layer: str | None = None,
        source: str | None = None,
        source_type: str = "conversation",
        tags: str | None = None,
        language: str = "bn",
    ) -> LearningQueueItem:
        """
        Add an item to learning queue (awaiting confirmation).

        Per AURA Constitution: Never store automatically.
        All learned items start here.

        Args:
            db: Database session.
            title: Short title.
            content: Full content.
            suggested_layer: AI-suggested memory layer.
            source: Where this info came from.
            source_type: conversation/web/file/user_input
            tags: Comma-separated tags.
            language: Content language.

        Returns:
            LearningQueueItem: Created queue item.
        """
        layer = suggested_layer or importance_scorer.suggest_layer(content, title)
        importance = importance_scorer.score(content, title, layer)

        item = LearningQueueItem(
            title=title,
            content=content,
            suggested_layer=layer,
            suggested_importance=importance,
            source=source,
            source_type=source_type,
            tags=tags,
            language=language,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        logger.info(
            "Added to learning queue: %s (layer=%s, importance=%.2f)",
            item.id, layer, importance,
        )
        return item

    async def confirm_from_queue(
        self,
        db: AsyncSession,
        queue_id: str,
        override_layer: str | None = None,
        override_importance: float | None = None,
        memory_type: MemoryType = "semantic",
    ) -> MemoryEntry | None:
        """
        Confirm a queued item → move to permanent memory.

        Args:
            db: Database session.
            queue_id: LearningQueueItem ID.
            override_layer: Override suggested layer.
            override_importance: Override importance score.
            memory_type: semantic/episodic/procedural.

        Returns:
            MemoryEntry | None: Created permanent memory or None.
        """
        # Get queue item
        result = await db.execute(
            select(LearningQueueItem).where(LearningQueueItem.id == queue_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            logger.warning("Queue item not found: %s", queue_id)
            return None

        if item.is_reviewed:
            logger.warning("Queue item already reviewed: %s", queue_id)
            return None

        # Mark as confirmed
        item.is_reviewed = True
        item.review_result = "confirmed"
        item.reviewed_at = datetime.now(timezone.utc)

        # Create permanent memory
        layer = override_layer or item.suggested_layer
        importance = override_importance or item.suggested_importance

        # Summarize if content is long
        summary = None
        if memory_summarizer.should_summarize(item.content):
            try:
                summary = await memory_summarizer.summarize(
                    item.content, layer, item.language
                )
            except Exception as e:
                logger.warning("Summarization failed: %s", e)

        memory = MemoryEntry(
            layer=layer,
            memory_type=memory_type,
            title=item.title,
            content=item.content,
            summary=summary,
            tags=item.tags,
            importance_score=importance,
            is_confirmed=True,
            source=item.source,
            language=item.language,
        )
        db.add(memory)
        await db.flush()
        await db.refresh(memory)

        # Index in ChromaDB
        indexed = await memory_recall.store_memory(memory)
        if indexed:
            memory.is_indexed = True
            await db.flush()

        logger.info(
            "Confirmed memory %s from queue %s (layer=%s)",
            memory.id, queue_id, layer,
        )
        return memory

    async def reject_from_queue(
        self,
        db: AsyncSession,
        queue_id: str,
    ) -> bool:
        """
        Reject a queued item — permanently discard.

        Args:
            db: Database session.
            queue_id: Queue item to reject.

        Returns:
            bool: True if rejected successfully.
        """
        result = await db.execute(
            select(LearningQueueItem).where(LearningQueueItem.id == queue_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            return False

        item.is_reviewed = True
        item.review_result = "rejected"
        item.reviewed_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info("Rejected queue item: %s", queue_id)
        return True

    async def create_memory(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        layer: MemoryLayer,
        memory_type: MemoryType = "semantic",
        tags: str | None = None,
        category: str | None = None,
        importance_score: float | None = None,
        language: str = "bn",
        source: str | None = None,
    ) -> MemoryEntry:
        """
        Create a confirmed memory directly (bypasses queue).

        Used when user explicitly provides information to remember
        in real-time (e.g. "remember that my birthday is July 5").

        Args:
            db: Database session.
            title: Memory title.
            content: Memory content.
            layer: Memory layer.
            memory_type: semantic/episodic/procedural.
            tags: Comma-separated tags.
            category: Category label.
            importance_score: Override auto-scored importance.
            language: Content language.
            source: Information source.

        Returns:
            MemoryEntry: Created confirmed memory.
        """
        score = importance_score or importance_scorer.score(
            content, title, layer, explicitly_requested=True
        )

        summary = None
        if memory_summarizer.should_summarize(content):
            try:
                summary = await memory_summarizer.summarize(content, layer, language)
            except Exception as e:
                logger.warning("Summarization failed: %s", e)

        memory = MemoryEntry(
            layer=layer,
            memory_type=memory_type,
            title=title,
            content=content,
            summary=summary,
            tags=tags,
            category=category,
            importance_score=score,
            is_confirmed=True,
            source=source,
            language=language,
        )
        db.add(memory)
        await db.flush()
        await db.refresh(memory)

        # Index in ChromaDB
        indexed = await memory_recall.store_memory(memory)
        if indexed:
            memory.is_indexed = True
            await db.flush()

        logger.info(
            "Created memory %s (layer=%s, importance=%.2f)",
            memory.id, layer, score,
        )
        return memory

    async def recall(
        self,
        query: str,
        layer: str | None = None,
        n_results: int = 5,
        min_importance: float = 0.0,
    ) -> list[dict]:
        """Search memories by semantic similarity."""
        return await memory_recall.recall(
            query=query,
            n_results=n_results,
            layer=layer,
            min_importance=min_importance,
        )

    async def get_context_for_chat(
        self,
        query: str,
        language: str = "bn",
    ) -> str:
        """Get formatted memory context for chat injection."""
        return await memory_recall.get_context_for_chat(query, language)

    async def get_layer_memories(
        self,
        db: AsyncSession,
        layer: str,
        limit: int = 20,
        confirmed_only: bool = True,
    ) -> list[MemoryEntry]:
        """
        Get all memories in a specific layer.

        Args:
            db: Database session.
            layer: Memory layer to query.
            limit: Maximum results.
            confirmed_only: Only confirmed memories.

        Returns:
            list[MemoryEntry]: Memories in the layer.
        """
        query = select(MemoryEntry).where(
            MemoryEntry.layer == layer,
            MemoryEntry.is_expired == False,  # noqa: E712
        )
        if confirmed_only:
            query = query.where(MemoryEntry.is_confirmed == True)  # noqa: E712

        query = query.order_by(
            MemoryEntry.importance_score.desc(),
            MemoryEntry.created_at.desc(),
        ).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_queue(
        self,
        db: AsyncSession,
        pending_only: bool = True,
    ) -> list[LearningQueueItem]:
        """
        Get learning queue items.

        Args:
            db: Database session.
            pending_only: Only unreviewed items.

        Returns:
            list[LearningQueueItem]: Queue items.
        """
        query = select(LearningQueueItem)
        if pending_only:
            query = query.where(LearningQueueItem.is_reviewed == False)  # noqa: E712

        query = query.order_by(LearningQueueItem.created_at.desc()).limit(50)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def search_memories(
        self,
        db: AsyncSession,
        query: str,
        layer: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search memories combining semantic + keyword."""
        # Semantic search via ChromaDB
        semantic_results = await memory_recall.recall(
            query=query,
            n_results=limit,
            layer=layer,
        )

        return semantic_results


# ── Singleton ─────────────────────────────────────────────────────────────────
advanced_memory_service = AdvancedMemoryService()