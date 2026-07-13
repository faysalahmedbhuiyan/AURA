"""
AURA Backend — Goal Routes (Phase 16).

Endpoints:
    POST /api/v1/goals                     — Create goal + LLM breakdown
    GET  /api/v1/goals                      — List goals
    GET  /api/v1/goals/{id}/progress        — Progress + blockers
    POST /api/v1/goals/tasks/{id}/status    — Update task status
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.repositories.goal_repository import goal_repository
from app.schemas.goal import (
    GoalCreate, GoalResponse, MilestoneResponse, ProgressResponse,
    TaskResponse, TaskStatusUpdate,
)
from app.services.goal_service import goal_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/goals", response_model=GoalResponse, status_code=201, tags=["Goals"])
async def create_goal(request: GoalCreate, db: AsyncSession = Depends(get_db)) -> GoalResponse:
    """Create a goal — AURA breaks it into milestones/tasks via LLM."""
    result = await goal_service.create_goal_with_breakdown(
        db, request.title, request.description, request.language
    )
    return GoalResponse(**result)


@router.get("/goals", response_model=list[GoalResponse], tags=["Goals"])
async def list_goals(db: AsyncSession = Depends(get_db)) -> list[GoalResponse]:
    """List all goals with their milestones/tasks."""
    goals = await goal_repository.list_goals(db)
    results = []
    for g in goals:
        milestones = await goal_repository.list_milestones(db, g.id)
        m_data = []
        for m in milestones:
            tasks = await goal_repository.list_tasks(db, m.id)
            m_data.append(MilestoneResponse(
                id=m.id, title=m.title,
                tasks=[TaskResponse(id=t.id, title=t.title, status=t.status) for t in tasks],
            ))
        results.append(GoalResponse(
            id=g.id, title=g.title, description=g.description,
            status=g.status, milestones=m_data,
        ))
    return results


@router.get("/goals/{goal_id}/progress", response_model=ProgressResponse, tags=["Goals"])
async def get_progress(goal_id: str, db: AsyncSession = Depends(get_db)) -> ProgressResponse:
    """Get progress percentage and blockers for a goal."""
    goal = await goal_repository.get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    result = await goal_service.get_progress(db, goal_id)
    return ProgressResponse(**result)


@router.post("/goals/tasks/{task_id}/status", response_model=TaskResponse, tags=["Goals"])
async def update_task_status(
    task_id: str, request: TaskStatusUpdate, db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Update a task's status (not_started/in_progress/blocked/completed)."""
    task = await goal_repository.update_task_status(
        db, task_id, request.status, request.blocked_reason
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return TaskResponse(id=task.id, title=task.title, status=task.status)