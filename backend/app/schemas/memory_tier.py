"""
AURA Backend — Memory Tier Schemas.

Module: app.schemas.memory_tier
Purpose: Pydantic models for Phase 13's multi-tier memory system.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class PersonalMemoryCreate(BaseModel):
    """Request to create a personal memory entry."""

    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    category: str = Field(default="preference")
    is_sensitive: bool = Field(default=False)


class PersonalMemoryResponse(BaseModel):
    """Response schema for a personal memory entry."""

    id: str
    key: str
    value: str
    category: str
    is_sensitive: bool
    created_at: datetime


class DecisionCreate(BaseModel):
    """Request to create a decision record."""

    title: str = Field(..., min_length=1, max_length=255)
    context: str = Field(..., min_length=1)
    decision: str = Field(..., min_length=1)
    consequences: str | None = None
    status: str = Field(default="accepted")
    tags: str | None = None


class DecisionResponse(BaseModel):
    """Response schema for a decision record."""

    id: str
    title: str
    context: str
    decision: str
    consequences: str | None
    status: str
    tags: str | None
    created_at: datetime

class QueueItemCreate(BaseModel):
    """
    Request to add an item to the learning queue.

    payload must contain the fields required by the target tier:
    - target_tier='personal' → {key, value, category?, is_sensitive?}
    - target_tier='decision' → {title, context, decision, consequences?, status?, tags?}
    """

    target_tier: str = Field(..., description="'personal' or 'decision'")
    title: str = Field(..., min_length=1, max_length=255)
    payload: dict = Field(..., description="Fields needed to create the target record")
    source: str = Field(default="manual")


class QueueItemResponse(BaseModel):
    """Response schema for a learning queue item."""

    id: str
    target_tier: str
    title: str
    payload: str
    source: str
    status: str
    created_at: datetime


class ConfirmResponse(BaseModel):
    """Response after confirming/rejecting a queue item."""

    success: bool
    created: dict | None = None
    error: str | None = None