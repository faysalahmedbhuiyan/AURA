"""
AURA Backend — Journal Entry Model.

Module: app.models.journal
Purpose: Stores AURA's development journal — session logs, architecture
         decision records (ADR), and change history entries. Implements
         Phase 12 of the Constitution.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class JournalEntry(Base, UUIDMixin, TimestampMixin):
    """
    JournalEntry model — one entry in AURA's development journal.

    Attributes:
        id: UUID primary key.
        category: One of 'session_log', 'decision', 'change'.
        title: Short title for the entry.
        content: Full entry text (freeform, markdown-friendly).
        tags: Comma-separated tags for filtering/search.
        files_created: Comma-separated file paths created in this entry.
        files_modified: Comma-separated file paths modified in this entry.
        files_deleted: Comma-separated file paths deleted in this entry.
        related_phase: Optional phase label, e.g. 'Phase 12'.
    """

    __tablename__ = "journal_entries"

    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="session_log | decision | change",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated tags",
    )

    files_created: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated file paths",
    )

    files_modified: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated file paths",
    )

    files_deleted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated file paths",
    )

    related_phase: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<JournalEntry id={self.id} category={self.category} title={self.title!r}>"