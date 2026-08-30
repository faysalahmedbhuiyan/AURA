"""
AURA Backend — Research Engine Routes.

Module: app.api.v1.routes.research_engine
Purpose: HTTP endpoints for Phase 24 — Autonomous Research Engine.

Endpoints:
    POST /api/v1/research/run          — Full research pipeline
    POST /api/v1/research/quick        — Quick search (no fetch)
    POST /api/v1/research/save         — Save to Advanced Memory (after confirm)
    POST /api/v1/research/queue        — Add to learning queue

All results are PENDING until user confirms via /save endpoint.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.research_engine.research_service import research_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    """Request for full research pipeline."""
    query: str = Field(..., min_length=2, max_length=500)
    language: str = Field(default="en", description="bn or en")
    max_sources: int = Field(default=6, ge=2, le=10)
    deep: bool = Field(
        default=True,
        description="Deep = multi-query search. False = faster single query.",
    )


class QuickSearchRequest(BaseModel):
    """Request for quick search."""
    query: str = Field(..., min_length=2, max_length=500)
    language: str = Field(default="en")
    max_results: int = Field(default=5, ge=1, le=10)


class SaveResearchRequest(BaseModel):
    """Request to save research to Advanced Memory (after confirmation)."""
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=10)
    query: str = Field(...)
    confidence: float = Field(...)
    sources: list[dict] = Field(default_factory=list)
    language: str = Field(default="en")
    category: str | None = None
    tags: str | None = None


class QueueResearchRequest(BaseModel):
    """Request to add research to learning queue."""
    title: str = Field(...)
    summary: str = Field(...)
    query: str = Field(...)
    language: str = Field(default="en")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/research/run",
    summary="Full Research Pipeline",
    description=(
        "Research a topic intelligently: Search → Collect → Rank → "
        "Synthesize. Returns candidate result. NEVER auto-saves. "
        "Use /research/save after user confirmation."
    ),
    tags=["Research Engine"],
)
async def run_research(request: ResearchRequest) -> dict:
    """
    Execute full autonomous research pipeline.

    Pipeline: Search → Collect → Deduplicate → Rank →
              Confidence → Synthesize → Return (NOT saved)

    Args:
        request: Research query and parameters.

    Returns:
        dict: Complete research result with sources and confidence.
              status="pending_confirmation" — never auto-saved.
    """
    try:
        result = await research_service.research(
            query=request.query,
            language=request.language,
            max_sources=request.max_sources,
            deep=request.deep,
        )
        return result.to_dict()

    except Exception as e:
        logger.exception("Research pipeline failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}",
        )


@router.post(
    "/research/quick",
    summary="Quick Search",
    description="Fast search without content fetching. Returns URLs and snippets only.",
    tags=["Research Engine"],
)
async def quick_search(request: QuickSearchRequest) -> dict:
    """Quick search — URLs and snippets only, no content fetching."""
    try:
        return await research_service.quick_search(
            query=request.query,
            language=request.language,
            max_results=request.max_results,
        )
    except Exception as e:
        logger.exception("Quick search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post(
    "/research/save",
    summary="Save Research to Memory",
    description=(
        "Save confirmed research to Advanced Memory Engine. "
        "Only call this after user explicitly confirms the research result. "
        "Creates a confirmed memory in 'learning' layer."
    ),
    tags=["Research Engine"],
    status_code=status.HTTP_201_CREATED,
)
async def save_research(
    request: SaveResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Save confirmed research to Advanced Memory.

    Creates a direct confirmed memory — bypasses learning queue
    since user has already reviewed and approved the content.

    Args:
        request: Research content to save.
        db: Database session.

    Returns:
        dict: Saved memory details.
    """
    from app.memory_engine.advanced_memory_service import advanced_memory_service

    try:
        # Build source attribution
        source_text = ""
        if request.sources:
            source_urls = [
                s.get("url", "") for s in request.sources[:3] if s.get("url")
            ]
            source_text = " | Sources: " + ", ".join(source_urls)

        content = (
            f"Research Query: {request.query}\n\n"
            f"{request.summary}"
            f"{source_text}"
        )

        tags = request.tags or f"research,{request.language}"
        if request.query:
            # Add first 2 words of query as tags
            query_tags = "_".join(request.query.split()[:2]).lower()
            tags = f"{tags},{query_tags}"

        memory = await advanced_memory_service.create_memory(
            db=db,
            title=request.title,
            content=content,
            layer="learning",
            memory_type="semantic",
            tags=tags,
            category=request.category or "research",
            importance_score=round(request.confidence * 0.8, 2),
            language=request.language,
            source=f"web_research:{request.query[:50]}",
        )

        return {
            "saved": True,
            "memory_id": memory.id,
            "title": memory.title,
            "layer": memory.layer,
            "importance_score": memory.importance_score,
            "is_indexed": memory.is_indexed,
            "message": (
                "গবেষণা সফলভাবে মেমরিতে সংরক্ষণ করা হয়েছে।"
                if request.language == "bn" else
                "Research saved to AURA's memory successfully."
            ),
        }

    except Exception as e:
        logger.exception("Save research failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save: {str(e)}",
        )


@router.post(
    "/research/queue",
    summary="Add Research to Learning Queue",
    description=(
        "Add research result to learning queue for deferred confirmation. "
        "User can review and confirm later."
    ),
    tags=["Research Engine"],
    status_code=status.HTTP_201_CREATED,
)
async def queue_research(
    request: QueueResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add research to learning queue for later confirmation."""
    from app.memory_engine.advanced_memory_service import advanced_memory_service

    try:
        item = await advanced_memory_service.add_to_queue(
            db=db,
            title=request.title,
            content=request.summary,
            suggested_layer="learning",
            source=f"web_research:{request.query[:50]}",
            source_type="web",
            language=request.language,
        )

        return {
            "queued": True,
            "queue_id": item.id,
            "title": item.title,
            "message": (
                "শেখার Queue তে যোগ করা হয়েছে। "
                "Confirm করলে স্থায়ীভাবে সংরক্ষণ হবে।"
                if request.language == "bn" else
                "Added to learning queue. Confirm to save permanently."
            ),
        }

    except Exception as e:
        logger.exception("Queue research failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue: {str(e)}",
        )