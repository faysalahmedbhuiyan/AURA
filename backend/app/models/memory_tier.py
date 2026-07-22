"""
AURA Backend — Memory Tier Models.

Module: app.models.memory_tier
Purpose: Implements Phase 13's multi-tier memory architecture.

Tiers:
    PersonalMemoryEntry — private user preferences/habits
    DecisionRecord       — structured architecture decision records
    LearningQueueItem    — pending items awaiting explicit confirmation

Safety Rule: Nothing moves from LearningQueueItem into PersonalMemoryEntry
or DecisionRecord without explicit user confirmation via the service layer.
KnowledgeEntry (Phase 3) already implements the confirmed-knowledge tier
and is reused as-is — not duplicated here.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class PersonalMemoryEntry(Base, UUIDMixin, TimestampMixin):
    """
    A single user preference/habit/private note.

    Attributes:
        key: Short identifier, e.g. 'preferred_language'.
        value: The stored value (freeform text).
        category: Grouping, e.g. 'preference', 'habit', 'private'.
        is_sensitive: If True, frontend should mask/hide by default.
    """

    __tablename__ = "personal_memory_entries"

    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="preference")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<PersonalMemoryEntry key={self.key!r} category={self.category}>"


class DecisionRecord(Base, UUIDMixin, TimestampMixin):
    """
    A structured Architecture Decision Record (ADR).

    Attributes:
        title: Short decision title.
        context: Why this decision was needed.
        decision: What was decided.
        consequences: Tradeoffs / results of the decision.
        status: 'proposed' | 'accepted' | 'superseded'.
        tags: Comma-separated tags.
    """

    __tablename__ = "decision_records"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    consequences: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DecisionRecord title={self.title!r} status={self.status}>"


class LearningQueueItem(Base, UUIDMixin, TimestampMixin):
    """
    An item awaiting explicit user confirmation before becoming permanent.

    Attributes:
        target_tier: Where this will go if confirmed — 'personal' | 'decision'.
        title: Short title for display.
        payload: JSON-serialized fields needed to create the target record.
        source: Where this came from, e.g. 'chat', 'research', 'manual'.
        status: 'pending' | 'confirmed' | 'rejected'.
    """

    __tablename__ = "learning_queue_items"

    target_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    def __repr__(self) -> str:
        return f"<LearningQueueItem title={self.title!r} status={self.status}>"