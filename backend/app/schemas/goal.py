"""AURA Backend — Goal Schemas (Phase 16)."""

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """Request to create a goal with LLM-generated breakdown."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    language: str = Field(default="en")


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str


class MilestoneResponse(BaseModel):
    id: str
    title: str
    tasks: list[TaskResponse]


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    milestones: list[MilestoneResponse]


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="not_started | in_progress | blocked | completed")
    blocked_reason: str | None = None


class ProgressResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    percent: float
    blockers: list[dict]