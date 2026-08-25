"""
AURA Backend — Memory Tier Routes.

Module: app.api.v1.routes.memory_tiers
Purpose: API endpoints for Phase 13's Advanced Memory System.
         Personal Memory and Decision Records can only be created
         directly for simple cases, OR via the Learning Queue for
         anything that should require explicit confirmation first.

Endpoints:
    POST /api/v1/memory-tiers/personal          — Create personal memory (direct)
    GET  /api/v1/memory-tiers/personal          — List personal memory
    DELETE /api/v1/memory-tiers/personal/{id}   — Delete personal memory entry

    POST /api/v1/memory-tiers/decisions         — Create decision record (direct)
    GET  /api/v1/memory-tiers/decisions         — List decision records

    POST /api/v1/memory-tiers/queue             — Add item to learning queue
    GET  /api/v1/memory-tiers/queue             — List queue items (filter by status)
    POST /api/v1/memory-tiers/queue/{id}/confirm — Confirm — promotes to target tier
    POST /api/v1/memory-tiers/queue/{id}/reject  — Reject — never becomes permanent
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.database.connection import get_db
from app.repositories.memory_tier_repository import memory_tier_repository
from app.schemas.memory_tier import (
    ConfirmResponse,
    DecisionCreate,
    DecisionResponse,
    PersonalMemoryCreate,
    PersonalMemoryResponse,
    QueueItemCreate,
    QueueItemResponse,
)
from app.services.memory_tier_service import memory_tier_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Personal Memory ────────────────────────────────────────────────────────────
@router.post(
    "/memory-tiers/personal", 
    status_code=201, tags=["Memory Tiers"],
    summary="Create Personal Memory Entry",
)
async def create_personal(
    request: PersonalMemoryCreate, db: AsyncSession = Depends(get_db)
) -> PersonalMemoryResponse:
    """Create a personal memory entry directly (no queue needed for simple prefs)."""
    entry = await memory_tier_repository.create_personal(
        db, key=request.key, value=request.value,
        category=request.category, is_sensitive=request.is_sensitive,
    )
    return PersonalMemoryResponse(
        id=entry.id, key=entry.key, value=entry.value,
        category=entry.category, is_sensitive=entry.is_sensitive,
        created_at=entry.created_at,
    )


@router.get(
    "/memory-tiers/personal", 
    tags=["Memory Tiers"], summary="List Personal Memory Entries",
)
async def list_personal(db: AsyncSession = Depends(get_db)) -> list[PersonalMemoryResponse]:
    """List all personal memory entries."""
    entries = await memory_tier_repository.list_personal(db)
    return [
        PersonalMemoryResponse(
            id=e.id, key=e.key, value=e.value, category=e.category,
            is_sensitive=e.is_sensitive, created_at=e.created_at,
        )
        for e in entries
    ]


@router.delete(
    "/memory-tiers/personal/{entry_id}", tags=["Memory Tiers"],
    summary="Delete Personal Memory Entry",
)
async def delete_personal(entry_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Delete a personal memory entry."""
    deleted = await memory_tier_repository.delete_personal(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found.")
    return {"success": True, "deleted_id": entry_id}


# ── Decision Records ────────────────────────────────────────────────────────────
@router.post(
    "/memory-tiers/decisions",
    status_code=201, tags=["Memory Tiers"],
    summary="Create Decision Record",
)
async def create_decision(
    request: DecisionCreate, db: AsyncSession = Depends(get_db)
) -> DecisionResponse:
    """Create an architecture decision record directly."""
    entry = await memory_tier_repository.create_decision(
        db, title=request.title, context=request.context,
        decision=request.decision, consequences=request.consequences,
        status=request.status, tags=request.tags,
    )
    return DecisionResponse(
        id=entry.id, title=entry.title, context=entry.context,
        decision=entry.decision, consequences=entry.consequences,
        status=entry.status, tags=entry.tags, created_at=entry.created_at,
    )


@router.get(
    "/memory-tiers/decisions", 
    tags=["Memory Tiers"], summary="List Decision Records",
)
async def list_decisions(db: AsyncSession = Depends(get_db)) -> list[DecisionResponse]:
    """List all decision records."""
    entries = await memory_tier_repository.list_decisions(db)
    return [
        DecisionResponse(
            id=e.id, title=e.title, context=e.context, decision=e.decision,
            consequences=e.consequences, status=e.status, tags=e.tags,
            created_at=e.created_at,
        )
        for e in entries
    ]


# ── Learning Queue ────────────────────────────────────────────────────────────
@router.post(
    "/memory-tiers/queue", 
    status_code=status.HTTP_201_CREATED, 
    tags=["Memory Tiers"],
    summary="Add Item to Learning Queue",
    description=(
        "Adds a pending item that requires explicit confirmation before "
        "becoming permanent memory. Nothing here is saved permanently yet."
    ),
    responses={
        400: {"description": "Invalid target tier provided. Must be 'personal' or 'decision'."}
    },
)
async def create_queue_item(
    request: QueueItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QueueItemResponse:
    """Add a new item to the learning queue (always starts as 'pending')."""
    if request.target_tier not in ("personal", "decision"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_tier must be 'personal' or 'decision'.",
        )
    item = await memory_tier_repository.create_queue_item(
        db,
        target_tier=request.target_tier,
        title=request.title,
        payload=json.dumps(request.payload),
        source=request.source,
    )
    return QueueItemResponse(
        id=item.id,
        target_tier=item.target_tier,
        title=item.title,
        payload=item.payload,
        source=item.source,
        status=item.status,
        created_at=item.created_at,
    )

@router.post(
    "/memory-tiers/queue", 
    status_code=status.HTTP_201_CREATED, 
    tags=["Memory Tiers"],
    summary="Add Item to Learning Queue",
    description=(
        "Adds a pending item that requires explicit confirmation before "
        "becoming permanent memory. Nothing here is saved permanently yet."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid target tier provided. Must be 'personal' or 'decision'."
        }
    },
)
async def create_queue_item(
    request: QueueItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QueueItemResponse:
    """Add a new item to the learning queue (always starts as 'pending')."""
    if request.target_tier not in ("personal", "decision"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_tier must be 'personal' or 'decision'.",
        )
    item = await memory_tier_repository.create_queue_item(
        db,
        target_tier=request.target_tier,
        title=request.title,
        payload=json.dumps(request.payload),
        source=request.source,
    )
    return QueueItemResponse(
        id=item.id,
        target_tier=item.target_tier,
        title=item.title,
        payload=item.payload,
        source=item.source,
        status=item.status,
        created_at=item.created_at,
    )


@router.post(
    "/memory-tiers/queue/{item_id}/confirm", 
    tags=["Memory Tiers"], summary="Confirm Queue Item",
    description=(
        "The ONLY way a queue item becomes permanent memory. "
        "Promotes it into Personal Memory or Decision Records."
    ),
)
async def confirm_queue_item(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> ConfirmResponse:
    """Confirm a queue item, creating the permanent record."""
    result = await memory_tier_service.confirm_item(db, item_id)
    return ConfirmResponse(**result)


@router.post(
    "/memory-tiers/queue/{item_id}/reject",
    tags=["Memory Tiers"], summary="Reject Queue Item",
)
async def reject_queue_item(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> ConfirmResponse:
    """Reject a queue item — it will never become permanent."""
    result = await memory_tier_service.reject_item(db, item_id)
    return ConfirmResponse(success=result["success"], created=None, error=result["error"])