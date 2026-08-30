"""
AURA Backend — Memory Routes.

Module: app.api.v1.routes.memory
Purpose: API endpoints for AURA's memory and knowledge system.
         Enforces confirm-before-save for all knowledge entries.

Endpoints:
    GET  /api/v1/memory/search          — Semantic search
    POST /api/v1/memory/knowledge       — Add knowledge entry (pending)
    GET  /api/v1/memory/knowledge       — List pending entries
    POST /api/v1/memory/knowledge/{id}/confirm — Confirm an entry
    GET  /api/v1/memory/knowledge/confirmed    — List confirmed entries
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.repositories.knowledge_repository import knowledge_repository
from app.services.memory_service import memory_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────
class KnowledgeCreateRequest(BaseModel):
    """Request schema for creating a knowledge entry."""

    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=10)
    source_url: str | None = None
    source_name: str | None = None
    category: str | None = None
    tags: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    language: str = Field(default="en")


class KnowledgeResponse(BaseModel):
    """Response schema for knowledge entries."""

    id: str
    title: str
    summary: str
    source_name: str | None
    category: str | None
    tags: str | None
    confidence: float
    language: str
    is_confirmed: bool
    is_indexed: bool
    confirmed_at: str | None


class SearchRequest(BaseModel):
    """Request schema for semantic memory search."""

    query: str = Field(..., min_length=1)
    conversation_id: str | None = None
    n_results: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    """Response schema for memory search results."""

    query: str
    results: list[dict]
    total: int


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post(
    "/memory/search",
    response_model=SearchResponse,
    summary="Semantic Memory Search",
    description="Search AURA's memory for semantically similar content.",
    tags=["Memory"],
)
async def search_memory(request: SearchRequest) -> SearchResponse:
    """
    Search AURA's semantic memory.

    Searches both conversation history and knowledge base
    for content semantically similar to the query.

    Args:
        request: SearchRequest with query and optional filters.

    Returns:
        SearchResponse: Matching memories ranked by relevance.
    """
    conversations = await memory_service.search_conversations(
        query=request.query,
        n_results=request.n_results,
        conversation_id=request.conversation_id,
    )
    knowledge = await memory_service.search_knowledge(
        query=request.query,
        n_results=3,
    )

    results = [
        {"type": "conversation", **c} for c in conversations
    ] + [
        {"type": "knowledge", **k} for k in knowledge
    ]

    results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
    )


@router.post(
    "/memory/knowledge",
    response_model=KnowledgeResponse,
    summary="Add Knowledge Entry",
    description="Add a new knowledge entry for user review. "
                "Entry is NOT active until confirmed.",
    tags=["Memory"],
    status_code=status.HTTP_201_CREATED,
)
async def add_knowledge(
    request: KnowledgeCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """
    Add a new knowledge entry (unconfirmed).

    Entry is stored but NOT used in responses until
    user explicitly confirms it. Enforces AURA's
    confirm-before-save principle.

    Args:
        request: Knowledge entry data.
        db: Injected database session.

    Returns:
        KnowledgeResponse: Created entry with is_confirmed=False.
    """
    entry = await knowledge_repository.create_entry(
        db,
        title=request.title,
        summary=request.summary,
        source_url=request.source_url,
        source_name=request.source_name,
        category=request.category,
        tags=request.tags,
        confidence=request.confidence,
        language=request.language,
    )

    return KnowledgeResponse(
        id=entry.id,
        title=entry.title,
        summary=entry.summary,
        source_name=entry.source_name,
        category=entry.category,
        tags=entry.tags,
        confidence=entry.confidence,
        language=entry.language,
        is_confirmed=entry.is_confirmed,
        is_indexed=entry.is_indexed,
        confirmed_at=entry.confirmed_at,
    )


@router.get(
    "/memory/knowledge",
    response_model=list[KnowledgeResponse],
    summary="List Pending Knowledge",
    description="List all unconfirmed knowledge entries awaiting review.",
    tags=["Memory"],
)
async def list_pending_knowledge(
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeResponse]:
    """
    List all unconfirmed knowledge entries.

    Returns entries that have been added but not yet
    confirmed by the user.

    Args:
        db: Injected database session.

    Returns:
        list[KnowledgeResponse]: Pending knowledge entries.
    """
    entries = await knowledge_repository.get_pending(db)
    return [
        KnowledgeResponse(
            id=e.id,
            title=e.title,
            summary=e.summary,
            source_name=e.source_name,
            category=e.category,
            tags=e.tags,
            confidence=e.confidence,
            language=e.language,
            is_confirmed=e.is_confirmed,
            is_indexed=e.is_indexed,
            confirmed_at=e.confirmed_at,
        )
        for e in entries
    ]


@router.post(
    "/memory/knowledge/{entry_id}/confirm",
    response_model=KnowledgeResponse,
    summary="Confirm Knowledge Entry",
    description="User confirms a knowledge entry. "
                "Entry is then indexed in ChromaDB and used in responses.",
    tags=["Memory"],
)
async def confirm_knowledge(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeResponse:
    """
    Confirm a knowledge entry for use in AURA's responses.

    After confirmation:
    1. Entry marked as confirmed in SQLite
    2. Entry indexed in ChromaDB vector store
    3. Entry becomes available for RAG pipeline

    Args:
        entry_id: UUID of the entry to confirm.
        db: Injected database session.

    Returns:
        KnowledgeResponse: Updated entry with is_confirmed=True.

    Raises:
        404: If entry not found.
    """
    entry = await knowledge_repository.confirm_entry(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry {entry_id} not found.",
        )

    # Index in ChromaDB after confirmation
    try:
        await memory_service.store_knowledge(
            entry_id=entry.id,
            title=entry.title,
            summary=entry.summary,
            category=entry.category,
            tags=entry.tags,
            language=entry.language,
            confidence=entry.confidence,
        )
        await knowledge_repository.mark_indexed(db, entry.id)
    except Exception as e:
        logger.exception("ChromaDB indexing failed for %s: %s", entry_id, e)

    return KnowledgeResponse(
        id=entry.id,
        title=entry.title,
        summary=entry.summary,
        source_name=entry.source_name,
        category=entry.category,
        tags=entry.tags,
        confidence=entry.confidence,
        language=entry.language,
        is_confirmed=entry.is_confirmed,
        is_indexed=entry.is_indexed,
        confirmed_at=entry.confirmed_at,
    )


@router.get(
    "/memory/knowledge/confirmed",
    response_model=list[KnowledgeResponse],
    summary="List Confirmed Knowledge",
    description="List all user-confirmed knowledge entries in AURA's memory.",
    tags=["Memory"],
)
async def list_confirmed_knowledge(
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeResponse]:
    """
    List all confirmed knowledge entries.

    Args:
        db: Injected database session.

    Returns:
        list[KnowledgeResponse]: Confirmed and indexed entries.
    """
    entries = await knowledge_repository.get_confirmed(db)
    return [
        KnowledgeResponse(
            id=e.id,
            title=e.title,
            summary=e.summary,
            source_name=e.source_name,
            category=e.category,
            tags=e.tags,
            confidence=e.confidence,
            language=e.language,
            is_confirmed=e.is_confirmed,
            is_indexed=e.is_indexed,
            confirmed_at=e.confirmed_at,
        )
        for e in entries
    ]