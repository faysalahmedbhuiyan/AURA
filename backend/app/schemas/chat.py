"""
AURA Backend — Chat Schemas.

Module: app.schemas.chat
Purpose: Pydantic models for chat request/response validation.
         Used by the chat router for input validation and output serialization.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Schema for incoming chat requests.

    Attributes:
        message: The user's message text.
        conversation_id: Optional existing conversation UUID.
                         If None, a new conversation is created.
        language: Language code for this message.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message text",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Existing conversation UUID. Creates new if None.",
    )
    language: str = Field(
        default="en",
        description="Language code: bn, en, hi, ko",
    )


class ChatResponse(BaseModel):
    """
    Schema for chat responses.

    Attributes:
        conversation_id: UUID of the conversation.
        message_id: UUID of the assistant's message.
        response: The assistant's reply text.
        model: Which LLM model generated the response.
        language: Language code of the response.
    """

    conversation_id: str
    message_id: str
    response: str
    model: str
    language: str


class ConversationHistoryItem(BaseModel):
    """Single message item in conversation history."""

    id: str
    role: str
    content: str
    timestamp: str


class ConversationHistoryResponse(BaseModel):
    """Full conversation history response."""

    conversation_id: str
    language: str
    messages: list[ConversationHistoryItem]
    total: int