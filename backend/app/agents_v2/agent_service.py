"""
AURA Backend — Agent Service.

Module: app.agents_v2.agent_service
Purpose: High-level service for multi-agent operations.
         Provides simple interface for chat and API routes.
"""

import logging

from app.agents_v2.coordinator import agent_coordinator

logger = logging.getLogger(__name__)


class AgentService:
    """High-level agent service."""

    async def run(
        self,
        task: str,
        context: dict | None = None,
        agent_id: str | None = None,
    ) -> dict:
        """
        Run a task through the agent framework.

        Args:
            task: Task description.
            context: Task context.
            agent_id: Force specific agent.

        Returns:
            dict: Result with output and metadata.
        """
        result = await agent_coordinator.execute(task, context, agent_id)

        return {
            "success": result.success,
            "agent": result.agent_name,
            "task": result.task,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
            "duration_ms": result.duration_ms,
        }

    def list_agents(self) -> list[dict]:
        """List all available agents."""
        return agent_coordinator.get_available_agents()


agent_service = AgentService()