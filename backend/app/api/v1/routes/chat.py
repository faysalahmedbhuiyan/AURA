"""
AURA Backend — Chat Routes.

Module: app.api.v1.routes.chat
Purpose: Handles chat requests between user and AURA LLM.
         Integrates RAG pipeline with ChromaDB memory.
         Saves all messages to SQLite and ChromaDB.

Endpoints:
    POST /api/v1/chat          — Send message, get response
    GET  /api/v1/chat          — List all conversations (sidebar history)
    GET  /api/v1/chat/{id}     — Get conversation history
"""

import logging
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryItem,
    ConversationHistoryResponse,
)
from app.services.memory_service import memory_service
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/chat",
    summary="List Conversations",
    description="Get all conversations for sidebar history.",
    tags=["Chat"],
)
async def list_conversations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List all conversations for ChatGPT-style sidebar history.

    Returns conversations sorted by most recent first,
    with first message preview and message count.

    Args:
        limit: Maximum conversations to return (default 50).
        db: Injected async database session.

    Returns:
        list[dict]: Conversation list with metadata.
    """
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    conv_list = []
    for conv in conversations:
        # Message count
        count_result = await db.execute(
            select(func.count(Message.id)).where(
                Message.conversation_id == conv.id
            )
        )
        msg_count = count_result.scalar() or 0

        # First user message for title preview
        first_msg_result = await db.execute(
            select(Message.content)
            .where(
                Message.conversation_id == conv.id,
                Message.role == "user",
            )
            .order_by(Message.created_at)
            .limit(1)
        )
        first_msg = first_msg_result.scalar()

        conv_list.append({
            "id": conv.id,
            "title": conv.title,
            "first_message": first_msg,
            "language": conv.language,
            "message_count": msg_count,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        })

    return conv_list


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AURA",
    description="Send a message to AURA and receive an AI response. "
                "Uses RAG pipeline with ChromaDB memory for context.",
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
        1. Check Ollama availability
        2. Get or create conversation
        3. Load conversation history from SQLite
        4. Get relevant context from ChromaDB (RAG)
        5. Save user message to SQLite + ChromaDB
        6. Send to Ollama with history + RAG context
        7. Save assistant response to SQLite + ChromaDB
        8. Return response

    Args:
        request: ChatRequest with message, conversation_id, language.
        db: Injected async database session.

    Returns:
        ChatResponse: AI response with conversation and message IDs.

    Raises:
        503: If Ollama is not available.
        404: If conversation_id not found.
        500: If LLM or database error occurs.
    """
    # ── Step 1: Check Ollama ──────────────────────────────────────────────────
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
            db, language=request.language,
        )

    # ── Step 3: Load SQLite history ───────────────────────────────────────────
    history = await conversation_repository.get_history(db, conversation.id)

    # ── Step 4: RAG — Get relevant context from ChromaDB ─────────────────────
    context = await memory_service.get_relevant_context(
        query=request.message,
        conversation_id=conversation.id,
    )

    enriched_message = request.message
    if context:
        enriched_message = (
            f"{request.message}\n\n"
            f"[Relevant context from memory:\n{context}]"
        )

    # ── Step 5: Save user message ─────────────────────────────────────────────
    user_message = await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )

    # Store in ChromaDB (non-blocking)
    await memory_service.store_message(
        message_id=user_message.id,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        language=request.language,
    )

    # ── Step 6: Get LLM response ──────────────────────────────────────────────
    try:
        ai_response = await ollama_service.chat(
            message=enriched_message,
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

    # ── Step 7: Save assistant response ──────────────────────────────────────
    assistant_message = await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        model_used=ollama_service.model,
    )

    # Store assistant response in ChromaDB
    await memory_service.store_message(
        message_id=assistant_message.id,
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        language=request.language,
    )

    logger.info(
        "Chat completed | conversation=%s | model=%s | rag=%s",
        conversation.id,
        ollama_service.model,
        bool(context),
    )

    # ── Step 8: Return response ───────────────────────────────────────────────
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