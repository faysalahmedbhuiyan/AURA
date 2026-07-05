"""
AURA Backend — Conversation Repository.

Module: app.repositories.conversation_repository
Purpose: All database operations for Conversation and Message models.
         Services use this repository — never query DB directly.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)


class ConversationRepository:
    """
    Repository for Conversation and Message database operations.

    All methods are async and accept a db session as parameter.
    Session lifecycle is managed by the FastAPI dependency (get_db).

    Methods:
        create_conversation: Create a new conversation.
        get_conversation: Get conversation by ID with messages.
        add_message: Add a message to a conversation.
        get_history: Get message history as list of dicts.
    """

    async def create_conversation(
        self,
        db: AsyncSession,
        language: str = "en",
        title: str | None = None,
    ) -> Conversation:
        """
        Create a new conversation in the database.

        Args:
            db: Async database session.
            language: Language code (bn, en, hi, ko).
            title: Optional conversation title.

        Returns:
            Conversation: The newly created conversation.
        """
        conversation = Conversation(
            language=language,
            title=title,
        )
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
        logger.info("Created conversation: %s", conversation.id)
        return conversation

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> Conversation | None:
        """
        Get a conversation by ID, including all messages.

        Args:
            db: Async database session.
            conversation_id: UUID of the conversation.

        Returns:
            Conversation | None: The conversation or None if not found.
        """
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        model_used: str | None = None,
    ) -> Message:
        """
        Add a message to an existing conversation.

        Args:
            db: Async database session.
            conversation_id: Parent conversation UUID.
            role: 'user' or 'assistant'.
            content: Message text content.
            model_used: LLM model name (for assistant messages).

        Returns:
            Message: The newly created message.
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            token_count=len(content.split()),  # Approximate word count
        )
        db.add(message)
        await db.flush()
        await db.refresh(message)
        return message

    async def get_history(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        """
        Get conversation history as a list of role/content dicts.

        Format matches Ollama's expected message format.

        Args:
            db: Async database session.
            conversation_id: UUID of the conversation.

        Returns:
            list[dict]: [{"role": "user", "content": "..."}, ...]
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]


# ── Singleton instance ────────────────────────────────────────────────────────
conversation_repository = ConversationRepository()