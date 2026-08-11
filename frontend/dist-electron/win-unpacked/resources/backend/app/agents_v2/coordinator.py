"""
AURA Backend — Agent Coordinator.

Module: app.agents_v2.coordinator
Purpose: Routes tasks to appropriate agents.
         Handles sequential execution (8GB RAM — no parallel agents).
         Returns consolidated result.

Architecture:
    User task → Coordinator → detect agent → execute → return result
    
    Sequential only: one agent runs at a time to respect 8GB RAM limit.
    Agent results are NOT auto-saved — user must confirm.
"""

import logging
import re

from app.agents_v2.base_agent_v2 import AgentResult

logger = logging.getLogger(__name__)

# Task type detection patterns
TASK_PATTERNS = {
    "write_code": [
        r'\bwrite\b.*\bcode\b', r'\bgenerate\b.*\bcode\b',
        r'\bcreate\b.*\b(function|class|script|program)\b',
        r'\bcode\b.*\bfor\b',
    ],
    "fix_code": [
        r'\bfix\b.*\b(code|bug|error)\b', r'\bdebug\b',
        r'\b(error|bug|issue)\b.*\bcode\b',
        r'\bnot working\b', r'\bbroken\b',
    ],
    "explain_code": [
        r'\bexplain\b.*\bcode\b', r'\bwhat does\b.*\bcode\b',
        r'\bhow does\b.*\bwork\b',
    ],
    "review_code": [
        r'\breview\b.*\bcode\b', r'\bcode review\b',
        r'\bimprove\b.*\bcode\b',
    ],
    "generate_tests": [
        r'\b(write|generate|create)\b.*\btest\b',
        r'\bunit test\b', r'\btest case\b',
    ],
    "news_search": [
        r'\bnews\b', r'\blatest\b.*\babout\b',
        r'\bখবর\b', r'\bআজকের\b',
    ],
    "web_search": [
        r'\bsearch\b', r'\bfind\b', r'\blook up\b',
        r'\bresearch\b', r'\bwhat is\b',
    ],
}


class AgentCoordinator:
    """
    Central coordinator for multi-agent execution.

    Detects task type, selects appropriate agent,
    executes sequentially, returns result.

    Methods:
        execute: Route and execute a task.
        detect_task_type: Identify task type from message.
        select_agent: Choose best agent for task.
        get_available_agents: List registered agents.
    """

    def __init__(self) -> None:
        from app.agents_v2.coding_agent import coding_agent
        from app.agents_v2.research_agent import research_agent

        self._agents = {
            "coding": coding_agent,
            "research": research_agent,
        }

    def get_available_agents(self) -> list[dict]:
        """List all registered agents."""
        return [
            {
                "id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities,
            }
            for agent_id, agent in self._agents.items()
        ]

    def detect_task_type(self, message: str) -> str:
        """
        Detect task type from message.

        Args:
            message: User message.

        Returns:
            str: Task type key.
        """
        msg_lower = message.lower()
        scores = {}

        for task_type, patterns in TASK_PATTERNS.items():
            score = sum(
                1 for p in patterns
                if re.search(p, msg_lower, re.IGNORECASE)
            )
            if score > 0:
                scores[task_type] = score

        if not scores:
            return "web_search"

        return max(scores, key=scores.get)

    def select_agent(self, task_type: str):
        """
        Select best agent for a task type.

        Args:
            task_type: Detected task type.

        Returns:
            BaseAgentV2: Best agent or None.
        """
        code_tasks = {
            "write_code", "fix_code", "explain_code",
            "review_code", "generate_tests",
        }
        research_tasks = {"news_search", "web_search", "deep_research", "fact_check"}

        if task_type in code_tasks:
            return self._agents.get("coding")
        if task_type in research_tasks:
            return self._agents.get("research")

        # Fallback: find agent that can handle it
        for agent in self._agents.values():
            if agent.can_handle(task_type):
                return agent

        return None

    async def execute(
        self,
        task: str,
        context: dict | None = None,
        agent_id: str | None = None,
    ) -> AgentResult:
        """
        Execute a task through the best available agent.

        Args:
            task: Task description.
            context: Additional context (code, language, etc.)
            agent_id: Force a specific agent (optional).

        Returns:
            AgentResult: Execution result.
        """
        context = context or {}

        # Detect task type if not provided
        if "task_type" not in context:
            context["task_type"] = self.detect_task_type(task)

        task_type = context["task_type"]
        logger.info("Coordinator: task_type=%s task='%s'", task_type, task[:60])

        # Select agent
        if agent_id and agent_id in self._agents:
            agent = self._agents[agent_id]
        else:
            agent = self.select_agent(task_type)

        if not agent:
            from app.agents_v2.base_agent_v2 import AgentResult
            return AgentResult(
                agent_name="coordinator",
                task=task,
                success=False,
                output="",
                error=f"No agent available for task type: {task_type}",
            )

        logger.info("Selected agent: %s", agent.name)
        return await agent.execute(task, context)


agent_coordinator = AgentCoordinator()