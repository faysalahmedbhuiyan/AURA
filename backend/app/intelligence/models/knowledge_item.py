"""
AURA Backend — Intelligence Layer Database Models.

Module: app.intelligence.models.knowledge_item
Purpose: SQLAlchemy ORM models for the Intelligence Layer.

         Tables:
         - knowledge_items        : Core knowledge entries
         - knowledge_relationships: Semantic connections between items
         - knowledge_versions     : Version history for evolution

         Design principles:
         - Every item has a type (Knowledge/Skill/Rule/etc)
         - Every item can relate to other items
         - Every update creates a new version (never overwrites)
         - Confidence scores evolve as more sources confirm facts
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class KnowledgeItem(Base):
    """
    Core knowledge entry in the Intelligence Layer.

    Stores structured knowledge with classification,
    metadata, and confidence tracking.
    """

    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Classification
    knowledge_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Knowledge/Skill/Rule/Workflow/Pattern/Template/Experience/Reference",
    )
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="High-level category e.g. Programming/Business/Science",
    )
    subcategory: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Concise 1-3 sentence summary",
    )
    detailed_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Full extracted knowledge content",
    )
    rules_extracted: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON array of rules/patterns extracted",
    )
    concepts_extracted: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON array of key concepts",
    )
    common_mistakes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON array of common mistakes/pitfalls",
    )
    best_practices: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON array of best practices",
    )

    # Metadata
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated tags",
    )
    source: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Source URL or description",
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual",
        comment="manual/web/file/chat/research",
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en",
    )

    # Quality metrics
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7,
        comment="0.0-1.0 confidence in accuracy",
    )
    importance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="0.0-1.0 importance score",
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Current version number",
    )
    source_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Number of sources confirming this knowledge",
    )

    # Status
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    is_indexed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    is_merged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if merged from multiple sources",
    )

    # Timestamps
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
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def to_dict(self) -> dict:
        import json
        def safe_json(val):
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return [val]

        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "title": self.title,
            "summary": self.summary,
            "detailed_notes": self.detailed_notes,
            "rules_extracted": safe_json(self.rules_extracted),
            "concepts_extracted": safe_json(self.concepts_extracted),
            "common_mistakes": safe_json(self.common_mistakes),
            "best_practices": safe_json(self.best_practices),
            "tags": self.tags,
            "source": self.source,
            "source_type": self.source_type,
            "language": self.language,
            "confidence": self.confidence,
            "importance": self.importance,
            "version": self.version,
            "source_count": self.source_count,
            "is_confirmed": self.is_confirmed,
            "is_indexed": self.is_indexed,
            "is_merged": self.is_merged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeRelationship(Base):
    """
    Semantic relationship between two knowledge items.

    Enables AURA to build a knowledge graph where
    everything is interconnected.

    Example:
        Company → [has_department] → Recruitment
        Recruitment → [requires] → Visa
        Visa → [involves] → Medical
    """

    __tablename__ = "knowledge_relationships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    source_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
        comment="Source knowledge item ID",
    )
    target_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
        comment="Target knowledge item ID",
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="is_part_of/requires/leads_to/contradicts/supports/examples/defines",
    )
    strength: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="0.0-1.0 relationship strength",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Why these items are related",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "description": self.description,
        }


class KnowledgeVersion(Base):
    """
    Version history for knowledge evolution.

    Every time a knowledge item is updated,
    the old version is preserved here.
    Knowledge never gets overwritten — it evolves.
    """

    __tablename__ = "knowledge_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    knowledge_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Why this version was created",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "knowledge_id": self.knowledge_id,
            "version_number": self.version_number,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }