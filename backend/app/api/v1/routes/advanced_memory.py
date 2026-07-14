"""
AURA Backend — Advanced Memory Routes.

Module: app.api.v1.routes.advanced_memory
Purpose: HTTP endpoints for Phase 22 — Advanced Memory Engine.

Endpoints:
    POST /api/v1/memory/advanced/queue          — Add to learning queue
    GET  /api/v1/memory/advanced/queue          — List pending queue
    POST /api/v1/memory/advanced/queue/{id}/confirm — Confirm queue item
    POST /api/v1/memory/advanced/queue/{id}/reject  — Reject queue item
    POST /api/v1/memory/advanced/create         — Create memory directly
    GET  /api/v1/memory/advanced/layer/{layer}  — Get layer memories
    POST /api/v1/memory/advanced/recall         — Search memories
    GET  /api/v1/memory/advanced/context        — Get chat context
    GET  /api/v1/memory/advanced/stats          — Memory statistics
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.memory_engine.advanced_memory_service import advanced_memory_service

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_LAYERS = {
    "personal", "preference", "decision", "project",
    "coding", "learning", "journal", "conversation",
}
VALID_TYPES = {"semantic", "episodic", "procedural"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class AddToQueueRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    suggested_layer: str | None = None
    source: str | None = None
    source_type: str = Field(default="conversation")
    tags: str | None = None
    language: str = Field(default="bn")


class CreateMemoryRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    layer: str = Field(..., description="personal/preference/decision/project/coding/journal")
    memory_type: str = Field(default="semantic")
    tags: str | None = None
    category: str | None = None
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str = Field(default="bn")
    source: str | None = None


class ConfirmQueueRequest(BaseModel):
    override_layer: str | None = None
    override_importance: float | None = Field(default=None, ge=0.0, le=1.0)
    memory_type: str = Field(default="semantic")


class RecallRequest(BaseModel):
    query: str = Field(..., min_length=1)
    layer: str | None = None
    n_results: int = Field(default=5, ge=1, le=20)
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/memory/advanced/queue",
    summary="Add to Learning Queue",
    description="Add item to learning queue. Requires confirmation before permanent storage.",
    tags=["Advanced Memory"],
    status_code=status.HTTP_201_CREATED,
)
async def add_to_queue(
    request: AddToQueueRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add item to learning queue (unconfirmed)."""
    item = await advanced_memory_service.add_to_queue(
        db=db,
        title=request.title,
        content=request.content,
        suggested_layer=request.suggested_layer,
        source=request.source,
        source_type=request.source_type,
        tags=request.tags,
        language=request.language,
    )
    return item.to_dict()


@router.get(
    "/memory/advanced/queue",
    summary="List Learning Queue",
    description="Get all pending items in the learning queue awaiting confirmation.",
    tags=["Advanced Memory"],
)
async def get_queue(
    pending_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List learning queue items."""
    items = await advanced_memory_service.get_queue(db, pending_only)
    return {
        "total": len(items),
        "items": [item.to_dict() for item in items],
    }


@router.post(
    "/memory/advanced/queue/{queue_id}/confirm",
    summary="Confirm Queue Item",
    description="Confirm a learning queue item → permanently stored and indexed.",
    tags=["Advanced Memory"],
)
async def confirm_queue_item(
    queue_id: str,
    request: ConfirmQueueRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm a queued item → permanent memory."""
    memory = await advanced_memory_service.confirm_from_queue(
        db=db,
        queue_id=queue_id,
        override_layer=request.override_layer,
        override_importance=request.override_importance,
        memory_type=request.memory_type,
    )

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue item '{queue_id}' not found or already reviewed.",
        )

    return {
        "confirmed": True,
        "memory": memory.to_dict(),
    }


@router.post(
    "/memory/advanced/queue/{queue_id}/reject",
    summary="Reject Queue Item",
    description="Reject and discard a learning queue item.",
    tags=["Advanced Memory"],
)
async def reject_queue_item(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a queued item."""
    success = await advanced_memory_service.reject_from_queue(db, queue_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue item '{queue_id}' not found.",
        )
    return {"rejected": True, "queue_id": queue_id}


@router.post(
    "/memory/advanced/create",
    summary="Create Memory Directly",
    description="Create a confirmed memory directly (bypasses queue). "
                "Use when user explicitly asks AURA to remember something.",
    tags=["Advanced Memory"],
    status_code=status.HTTP_201_CREATED,
)
async def create_memory(
    request: CreateMemoryRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a confirmed memory directly."""
    if request.layer not in VALID_LAYERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid layer. Valid: {', '.join(VALID_LAYERS)}",
        )

    if request.memory_type not in VALID_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory_type. Valid: {', '.join(VALID_TYPES)}",
        )

    memory = await advanced_memory_service.create_memory(
        db=db,
        title=request.title,
        content=request.content,
        layer=request.layer,
        memory_type=request.memory_type,
        tags=request.tags,
        category=request.category,
        importance_score=request.importance_score,
        language=request.language,
        source=request.source,
    )

    return memory.to_dict()


@router.get(
    "/memory/advanced/layer/{layer}",
    summary="Get Layer Memories",
    description="Get all confirmed memories in a specific layer.",
    tags=["Advanced Memory"],
)
async def get_layer_memories(
    layer: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get memories from a specific layer."""
    if layer not in VALID_LAYERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid layer. Valid: {', '.join(VALID_LAYERS)}",
        )

    memories = await advanced_memory_service.get_layer_memories(
        db, layer, limit
    )
    return {
        "layer": layer,
        "total": len(memories),
        "memories": [m.to_dict() for m in memories],
    }


@router.post(
    "/memory/advanced/recall",
    summary="Recall Memories",
    description="Search memories semantically across all or specific layers.",
    tags=["Advanced Memory"],
)
async def recall_memories(request: RecallRequest) -> dict:
    """Search memories by semantic similarity."""
    results = await advanced_memory_service.recall(
        query=request.query,
        layer=request.layer,
        n_results=request.n_results,
        min_importance=request.min_importance,
    )
    return {
        "query": request.query,
        "total": len(results),
        "results": results,
    }


@router.get(
    "/memory/advanced/context",
    summary="Get Memory Context for Chat",
    description="Get relevant memory context formatted for LLM injection.",
    tags=["Advanced Memory"],
)
async def get_memory_context(
    query: str,
    language: str = "bn",
) -> dict:
    """Get memory context for chat."""
    context = await advanced_memory_service.get_context_for_chat(query, language)
    return {
        "query": query,
        "context": context,
        "has_context": bool(context),
    }


@router.get(
    "/memory/advanced/stats",
    summary="Memory Statistics",
    description="Get statistics about all memory layers.",
    tags=["Advanced Memory"],
)
async def get_memory_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get memory statistics."""
    from sqlalchemy import func, select
    from app.memory_engine.models.memory_models import MemoryEntry, LearningQueueItem

    stats = {}

    # Count by layer
    for layer in VALID_LAYERS:
        result = await db.execute(
            select(func.count(MemoryEntry.id)).where(
                MemoryEntry.layer == layer,
                MemoryEntry.is_confirmed == True,  # noqa: E712
                MemoryEntry.is_expired == False,  # noqa: E712
            )
        )
        stats[layer] = result.scalar() or 0

    # Queue stats
    pending_result = await db.execute(
        select(func.count(LearningQueueItem.id)).where(
            LearningQueueItem.is_reviewed == False  # noqa: E712
        )
    )
    pending_count = pending_result.scalar() or 0

    total_result = await db.execute(
        select(func.count(MemoryEntry.id)).where(
            MemoryEntry.is_confirmed == True,  # noqa: E712
        )
    )
    total_memories = total_result.scalar() or 0

    return {
        "total_confirmed_memories": total_memories,
        "pending_queue_items": pending_count,
        "by_layer": stats,
    }