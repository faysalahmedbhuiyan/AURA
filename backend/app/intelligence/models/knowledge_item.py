"""
AURA Backend — Intelligence Layer Routes.

Module: app.api.v1.routes.intelligence
Purpose: HTTP endpoints for Tier 2 — Intelligence Layer.

Endpoints:
    POST /api/v1/intelligence/process       — Process new knowledge
    POST /api/v1/intelligence/confirm/{id}  — Confirm pending item
    POST /api/v1/intelligence/search        — Semantic search
    GET  /api/v1/intelligence/graph/{id}    — Knowledge graph
    GET  /api/v1/intelligence/stats         — Statistics
    GET  /api/v1/intelligence/items         — List all items
    GET  /api/v1/intelligence/items/{id}    — Get single item
    GET  /api/v1/intelligence/pending       — List pending items
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db

from app.intelligence.models.knowledge_item import KnowledgeItem

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    source: str | None = None
    source_type: str = Field(default="manual")
    language: str = Field(default="en")
    auto_confirm: bool = Field(
        default=False,
        description="If True, skip confirmation step. Use only for trusted sources.",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    knowledge_type: str | None = None
    category: str | None = None
    n_results: int = Field(default=5, ge=1, le=20)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/intelligence/process",
    summary="Process New Knowledge",
    description=(
        "Run the full intelligence pipeline on new content: "
        "Classify → Deduplicate → Create/Evolve → Relate. "
        "Returns candidate for user confirmation (unless auto_confirm=True)."
    ),
    tags=["Intelligence"],
    status_code=status.HTTP_201_CREATED,
)
async def process_knowledge(
    request: ProcessRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process new knowledge through the full intelligence pipeline."""
    try:
        result = await intelligence_service.process(
            db=db,
            title=request.title,
            content=request.content,
            source=request.source,
            source_type=request.source_type,
            language=request.language,
            auto_confirm=request.auto_confirm,
        )
        return result
    except Exception as e:
        logger.error("Intelligence process failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/intelligence/confirm/{item_id}",
    summary="Confirm Knowledge Item",
    description="Confirm a pending knowledge item for permanent storage and ChromaDB indexing.",
    tags=["Intelligence"],
)
async def confirm_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm a pending knowledge item."""
    result = await intelligence_service.confirm_item(db, item_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Item not found"),
        )
    return result


@router.post(
    "/intelligence/search",
    summary="Search Intelligence Layer",
    description="Semantic search across all confirmed knowledge items.",
    tags=["Intelligence"],
)
async def search_intelligence(request: SearchRequest) -> dict:
    """Search knowledge items semantically."""
    results = await intelligence_service.search(
        query=request.query,
        knowledge_type=request.knowledge_type,
        category=request.category,
        n_results=request.n_results,
    )
    return {"query": request.query, "total": len(results), "results": results}


@router.get(
    "/intelligence/graph/{item_id}",
    summary="Knowledge Graph",
    description="Get interconnected knowledge items as a graph.",
    tags=["Intelligence"],
)
async def get_knowledge_graph(
    item_id: str,
    depth: int = Query(default=2, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get knowledge graph for an item."""
    return await intelligence_service.get_knowledge_graph(db, item_id, depth)


@router.get(
    "/intelligence/stats",
    summary="Intelligence Statistics",
    description="Get statistics about the Intelligence Layer.",
    tags=["Intelligence"],
)
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Get intelligence layer statistics."""
    return await intelligence_service.get_stats(db)


@router.get(
    "/intelligence/items",
    summary="List Knowledge Items",
    description="List all confirmed knowledge items.",
    tags=["Intelligence"],
)
async def list_items(
    knowledge_type: str | None = None,
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List knowledge items with optional filters."""
    query = select(KnowledgeItem).where(
        KnowledgeItem.is_confirmed == True  # noqa: E712
    )
    if knowledge_type:
        query = query.where(KnowledgeItem.knowledge_type == knowledge_type)
    if category:
        query = query.where(KnowledgeItem.category == category)

    query = query.order_by(
        KnowledgeItem.importance.desc(),
        KnowledgeItem.created_at.desc(),
    ).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": len(items),
        "items": [item.to_dict() for item in items],
    }


@router.get(
    "/intelligence/pending",
    summary="List Pending Items",
    description="List knowledge items awaiting confirmation.",
    tags=["Intelligence"],
)
async def list_pending(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List pending knowledge items."""
    query = (
        select(KnowledgeItem)
        .where(KnowledgeItem.is_confirmed == False)  # noqa: E712
        .order_by(KnowledgeItem.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": len(items), "items": [i.to_dict() for i in items]}


@router.get(
    "/intelligence/items/{item_id}",
    summary="Get Knowledge Item",
    description="Get a single knowledge item with full details.",
    tags=["Intelligence"],
)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single knowledge item."""
    result = await db.execute(
        select(KnowledgeItem).where(KnowledgeItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return item.to_dict()