"""
AURA Backend — Base Agent v2.

Module: app.agents_v2.base_agent_v2
Purpose: Abstract base for all Tier 4 agents.
         Every agent has: name, description, capabilities, execute().
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Structured message between agents."""
    sender: str
    content: str
    message_type: str = "text"
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_name: str
    task: str
    success: bool
    output: str
    metadata: dict = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "task": self.task,
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class BaseAgentV2(ABC):
    """Abstract base for all Tier 4 agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """What this agent does."""

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """List of task types this agent can handle."""

    @abstractmethod
    async def execute(self, task: str, context: dict) -> AgentResult:
        """Execute a task."""

    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle a task type."""
        return any(
            task_type.lower() in cap.lower()
            for cap in self.capabilities
        )

    def log(self, msg: str, level: str = "info") -> None:
        getattr(logger, level)("[%s] %s", self.name, msg)