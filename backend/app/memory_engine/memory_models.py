"""
AURA Backend — Advanced Memory Models.

Module: app.memory_engine.models.memory_models
Purpose: SQLAlchemy ORM models for all memory layers.
         Each memory type has its own table for clean separation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MemoryEntry(Base):
    """
    Universal memory entry for all memory layers.

    Stores any type of memory with metadata for
    importance scoring, expiration, and recall.
    """

    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    layer: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Memory layer: personal/preference/decision/project/coding/learning",
    )
    memory_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Semantic/Episodic/Procedural",
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="Short descriptive title",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Full memory content",
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="LLM-generated summary for long content",
    )
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated tags",
    )
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
    )
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="0.0 (low) to 1.0 (critical)",
    )
    recall_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="How many times this memory was recalled",
    )
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="User confirmed this memory",
    )
    is_indexed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Indexed in ChromaDB",
    )
    is_expired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    source: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Where this memory came from",
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="bn",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Memory expiration time (None = permanent)",
    )
    last_recalled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "layer": self.layer,
            "memory_type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "category": self.category,
            "importance_score": self.importance_score,
            "recall_count": self.recall_count,
            "is_confirmed": self.is_confirmed,
            "is_indexed": self.is_indexed,
            "source": self.source,
            "language": self.language,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_recalled_at": self.last_recalled_at.isoformat() if self.last_recalled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LearningQueueItem(Base):
    """
    Items waiting for user confirmation before permanent storage.

    Per AURA Constitution: Never store automatically.
    Every learned item starts here and moves to MemoryEntry
    only after explicit user confirmation.
    """

    __tablename__ = "learning_queue"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_layer: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Suggested memory layer",
    )
    suggested_importance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="conversation",
        comment="conversation/web/file/user_input",
    )
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="bn")
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    review_result: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="confirmed/rejected/deferred",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "suggested_layer": self.suggested_layer,
            "suggested_importance": self.suggested_importance,
            "source": self.source,
            "source_type": self.source_type,
            "tags": self.tags,
            "language": self.language,
            "is_reviewed": self.is_reviewed,
            "review_result": self.review_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }