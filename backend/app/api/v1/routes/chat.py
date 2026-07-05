"""
AURA Backend — Chat Routes.

Module: app.api.v1.routes.chat
Purpose: Handles chat requests between user and AURA LLM.
         Saves all messages to SQLite database.
         Supports conversation history and multilingual input.

Endpoints:
    POST /api/v1/chat          — Send message, get response
    GET  /api/v1/chat/{id}     — Get conversation history
"""

import logging
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryItem,
    ConversationHistoryResponse,
)
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AURA",
    description="Send a message to AURA and receive an AI response. "
                "Conversation history is maintained automatically.",
    tags=["Chat"],
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Chat Endpoint — Send message to AURA, get AI response.

    Flow:
        1. Check Ollama is available
        2. Get or create conversation
        3. Load conversation history
        4. Save user message to DB
        5. Send to Ollama with history context
        6. Save assistant response to DB
        7. Return response

    Args:
        request: ChatRequest with message, conversation_id, language.
        db: Injected async database session.

    Returns:
        ChatResponse: AI response with conversation and message IDs.

    Raises:
        503: If Ollama server is not available.
        404: If conversation_id provided but not found.
        500: If LLM or database error occurs.
    """
    # ── Step 1: Check Ollama availability ────────────────────────────────────
    if not await ollama_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AURA LLM is not available. Please ensure Ollama is running.",
        )

    # ── Step 2: Get or create conversation ───────────────────────────────────
    if request.conversation_id:
        conversation = await conversation_repository.get_conversation(
            db, request.conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found.",
            )
    else:
        conversation = await conversation_repository.create_conversation(
            db,
            language=request.language,
        )

    # ── Step 3: Load history ──────────────────────────────────────────────────
    history = await conversation_repository.get_history(db, conversation.id)

    # ── Step 4: Save user message ─────────────────────────────────────────────
    await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )

    # ── Step 5: Get LLM response ──────────────────────────────────────────────
    try:
        ai_response = await ollama_service.chat(
            message=request.message,
            history=history,
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # ── Step 6: Save assistant response ──────────────────────────────────────
    assistant_message = await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        model_used=ollama_service.model,
    )

    logger.info(
        "Chat completed | conversation=%s | model=%s",
        conversation.id,
        ollama_service.model,
    )

    # ── Step 7: Return response ───────────────────────────────────────────────
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        response=ai_response,
        model=ollama_service.model,
        language=request.language,
    )


@router.get(
    "/chat/{conversation_id}",
    response_model=ConversationHistoryResponse,
    summary="Get Conversation History",
    description="Retrieve full message history for a conversation.",
    tags=["Chat"],
)
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationHistoryResponse:
    """
    Get full conversation history by conversation ID.

    Args:
        conversation_id: UUID of the conversation.
        db: Injected async database session.

    Returns:
        ConversationHistoryResponse: All messages in the conversation.

    Raises:
        404: If conversation not found.
    """
    conversation = await conversation_repository.get_conversation(
        db, conversation_id
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    messages = [
        ConversationHistoryItem(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.created_at.replace(
                tzinfo=timezone.utc
            ).isoformat(),
        )
        for msg in conversation.messages
    ]

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        language=conversation.language,
        messages=messages,
        total=len(messages),
    )