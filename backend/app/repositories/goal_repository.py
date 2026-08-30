"""
AURA Backend — Goal Repository.

Module: app.repositories.goal_repository
Purpose: Database operations for Goal, Milestone, and Task.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal, Milestone, Task

logger = logging.getLogger(__name__)


class GoalRepository:
    """Repository for goal/milestone/task operations."""

    async def create_goal(self, db: AsyncSession, title: str, description: str | None) -> Goal:
        """Create a new goal."""
        goal = Goal(title=title, description=description)
        db.add(goal)
        await db.flush()
        await db.refresh(goal)
        return goal

    async def create_milestone(
        self, db: AsyncSession, goal_id: str, title: str, order_index: int = 0
    ) -> Milestone:
        """Create a milestone under a goal."""
        milestone = Milestone(goal_id=goal_id, title=title, order_index=order_index)
        db.add(milestone)
        await db.flush()
        await db.refresh(milestone)
        return milestone

    async def create_task(
        self, db: AsyncSession, milestone_id: str, title: str,
        depends_on_task_id: str | None = None,
    ) -> Task:
        """Create a task under a milestone."""
        task = Task(milestone_id=milestone_id, title=title, depends_on_task_id=depends_on_task_id)
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    async def list_goals(self, db: AsyncSession) -> list[Goal]:
        """List all goals, newest first."""
        result = await db.execute(select(Goal).order_by(Goal.created_at.desc()))
        return list(result.scalars().all())

    async def get_goal(self, db: AsyncSession, goal_id: str) -> Goal | None:
        """Get a single goal by id."""
        result = await db.execute(select(Goal).where(Goal.id == goal_id))
        return result.scalar_one_or_none()

    async def list_milestones(self, db: AsyncSession, goal_id: str) -> list[Milestone]:
        """List milestones for a goal, in order."""
        result = await db.execute(
            select(Milestone).where(Milestone.goal_id == goal_id).order_by(Milestone.order_index)
        )
        return list(result.scalars().all())

    async def list_tasks(self, db: AsyncSession, milestone_id: str) -> list[Task]:
        """List tasks for a milestone."""
        result = await db.execute(
            select(Task).where(Task.milestone_id == milestone_id).order_by(Task.created_at)
        )
        return list(result.scalars().all())

    async def get_task(self, db: AsyncSession, task_id: str) -> Task | None:
        """Get a single task by id."""
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def update_task_status(
        self, db: AsyncSession, task_id: str, status: str, blocked_reason: str | None = None
    ) -> Task | None:
        """Update a task's status."""
        task = await self.get_task(db, task_id)
        if not task:
            return None
        task.status = status
        task.blocked_reason = blocked_reason
        await db.flush()
        await db.refresh(task)
        return task

    async def all_tasks_for_goal(self, db: AsyncSession, goal_id: str) -> list[Task]:
        """Get every task across every milestone of a goal."""
        milestones = await self.list_milestones(db, goal_id)
        tasks: list[Task] = []
        for m in milestones:
            tasks.extend(await self.list_tasks(db, m.id))
        return tasks


# ── Singleton instance ────────────────────────────────────────────────────────
goal_repository = GoalRepository()