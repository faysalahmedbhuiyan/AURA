"""
AURA Backend — Message Model.

Module: app.models.message
Purpose: Represents a single message within a conversation.
         Role is either 'user' or 'assistant'.
         token_count helps monitor RAM usage on low-spec hardware.
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDMixin


class Message(Base, UUIDMixin, TimestampMixin):
    """
    Message model — represents one turn in a conversation.

    Attributes:
        id: UUID primary key.
        conversation_id: FK to parent Conversation.
        role: 'user' or 'assistant'.
        content: The actual message text.
        token_count: Approximate token count (for memory monitoring).
        model_used: Which LLM model generated this response.
        created_at: When the message was sent.
    """

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent conversation UUID",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message sender: 'user' or 'assistant'",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message text content",
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Approximate token count for memory management",
    )

    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model that generated this response",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    conversation: Mapped["Conversation"] = relationship(  # type: ignore[name-defined]
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role}>"