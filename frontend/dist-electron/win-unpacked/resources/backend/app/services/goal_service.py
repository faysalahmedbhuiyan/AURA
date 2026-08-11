"""
AURA Backend — Goal Service.

Module: app.services.goal_service
Purpose: Breaks a goal description into milestones/tasks using the LLM,
         calculates progress, and identifies blockers.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.goal_repository import goal_repository
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

BREAKDOWN_SYSTEM_PROMPT = (
    "You are a project planning assistant. You break a goal down into "
    "milestones and tasks. You are NOT AURA and you are not having a "
    "conversation — output ONLY the structured breakdown as instructed. "
    "Never ask for confirmation or offer to remember anything."
)


class GoalService:
    """Orchestrates goal breakdown, progress, and blocker detection."""

    async def create_goal_with_breakdown(
        self, db: AsyncSession, title: str, description: str | None, language: str = "en"
    ) -> dict:
        """
        Create a goal and use the LLM to break it into milestones/tasks.

        Args:
            db: Async database session.
            title: Goal title.
            description: Optional extra context for the LLM.
            language: Response language for milestone/task titles.

        Returns:
            dict: Created goal with milestones and tasks.
        """
        goal = await goal_repository.create_goal(db, title, description)

        prompt = (
            f"Break this goal into 2-5 milestones, each with 2-4 tasks. "
            f"Respond in language code '{language}'.\n\n"
            f"GOAL: {title}\n"
            f"{'CONTEXT: ' + description if description else ''}\n\n"
            "Format EXACTLY like this, nothing else:\n"
            "MILESTONE: <milestone title>\n"
            "TASK: <task title>\n"
            "TASK: <task title>\n"
            "MILESTONE: <milestone title>\n"
            "TASK: <task title>\n"
        )

        try:
            raw = await ollama_service.chat(message=prompt, system_prompt=BREAKDOWN_SYSTEM_PROMPT)
        except Exception as e:
            logger.error("Goal breakdown failed: %s", e)
            raw = ""

        milestones_data = self._parse_breakdown(raw)
        if not milestones_data:
            # Fallback — single milestone with the goal itself as one task
            milestones_data = [{"title": "Get started", "tasks": [title]}]

        result_milestones = []
        for i, m in enumerate(milestones_data):
            milestone = await goal_repository.create_milestone(db, goal.id, m["title"], i)
            tasks = []
            for t_title in m["tasks"]:
                task = await goal_repository.create_task(db, milestone.id, t_title)
                tasks.append({"id": task.id, "title": task.title, "status": task.status})
            result_milestones.append({
                "id": milestone.id, "title": milestone.title, "tasks": tasks,
            })

        return {
            "id": goal.id, "title": goal.title, "description": goal.description,
            "status": goal.status, "milestones": result_milestones,
        }

    def _parse_breakdown(self, raw: str) -> list[dict]:
        """Parse the MILESTONE:/TASK: formatted LLM output."""
        milestones = []
        current = None
        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("MILESTONE:"):
                if current:
                    milestones.append(current)
                current = {"title": line.split(":", 1)[1].strip(), "tasks": []}
            elif line.upper().startswith("TASK:") and current:
                current["tasks"].append(line.split(":", 1)[1].strip())
        if current:
            milestones.append(current)
        return [m for m in milestones if m["title"] and m["tasks"]]

    async def get_progress(self, db: AsyncSession, goal_id: str) -> dict:
        """
        Calculate progress and identify blockers for a goal.

        Args:
            db: Async database session.
            goal_id: UUID of the goal.

        Returns:
            dict: {"total_tasks", "completed_tasks", "percent", "blockers"}
        """
        tasks = await goal_repository.all_tasks_for_goal(db, goal_id)
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")
        percent = round((completed / total) * 100, 1) if total else 0.0

        blockers = []
        for t in tasks:
            if t.status == "blocked":
                blockers.append({"task_id": t.id, "title": t.title, "reason": t.blocked_reason})
            elif t.depends_on_task_id:
                dep = await goal_repository.get_task(db, t.depends_on_task_id)
                if dep and dep.status != "completed" and t.status != "completed":
                    blockers.append({
                        "task_id": t.id, "title": t.title,
                        "reason": f"Waiting on task '{dep.title}' to complete first.",
                    })

        return {
            "total_tasks": total, "completed_tasks": completed,
            "percent": percent, "blockers": blockers,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
goal_service = GoalService()