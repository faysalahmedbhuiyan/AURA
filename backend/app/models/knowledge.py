"""
AURA Backend — Knowledge Entry Model.

Module: app.models.knowledge
Purpose: Stores verified knowledge entries that AURA has learned.
         Every entry requires user confirmation before being saved.
         Tracks source, confidence, category, and verification status.
"""

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class KnowledgeEntry(Base, UUIDMixin, TimestampMixin):
    """
    KnowledgeEntry model — a single piece of verified knowledge.

    Per project rules: AURA never blindly learns from the internet.
    Every entry goes through: Search → Collect → Verify → Confirm → Store.

    Attributes:
        id: UUID primary key.
        title: Short title of the knowledge entry.
        summary: Full summary of what was learned.
        source_url: Where the information came from.
        source_name: Human-readable source name.
        category: Topic category (science, history, tech, etc).
        tags: Comma-separated tags for retrieval.
        confidence: Float 0.0-1.0 indicating source reliability.
        language: Language of the entry (bn, en, hi, ko).
        is_confirmed: True only after user explicitly confirms.
        is_indexed: True after ChromaDB vector indexing.
        confirmed_at: When the user confirmed this entry.
    """

    __tablename__ = "knowledge_entries"

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Short descriptive title",
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full knowledge summary",
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Original source URL",
    )

    source_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable source name",
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Topic category",
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated tags",
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Source reliability score: 0.0 to 1.0",
    )

    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="en",
        comment="Language code: bn, en, hi, ko",
    )

    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True only after explicit user confirmation",
    )

    is_indexed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after ChromaDB vector indexing",
    )

    confirmed_at: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="ISO timestamp of user confirmation",
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeEntry id={self.id} "
            f"confirmed={self.is_confirmed} "
            f"confidence={self.confidence}>"
        )