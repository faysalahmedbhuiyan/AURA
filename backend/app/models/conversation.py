"""
AURA Backend — Conversation Model.

Module: app.models.conversation
Purpose: Represents a chat session between the user and AURA.
         Each conversation contains multiple messages.
         Supports multilingual sessions (bn, en, hi, ko).
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    """
    Conversation model — represents a single chat session.

    Attributes:
        id: UUID primary key.
        title: Optional short title for the conversation.
        language: Language code (bn=Bangla, en=English, hi=Hindi, ko=Korean).
        summary: Optional AI-generated summary of the conversation.
        created_at: When the conversation started.
        updated_at: When the conversation was last updated.
        messages: Related Message records.
    """

    __tablename__ = "conversations"

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Short title for the conversation",
    )

    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="en",
        comment="Language code: bn, en, hi, ko",
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated summary of this conversation",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    messages: Mapped[list["Message"]] = relationship(  # type: ignore[name-defined]
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} lang={self.language}>"