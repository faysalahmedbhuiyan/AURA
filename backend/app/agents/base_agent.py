"""
AURA Backend — Base Agent.

Module: app.agents.base_agent
Purpose: Abstract base class for all AURA agents.
         Enforces logging, error handling, and result schema
         across all agent implementations.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentResult:
    """
    Standard result container for all agent actions.

    Every agent returns this — ensures consistent response format
    across all agent types.
    """

    def __init__(
        self,
        success: bool,
        action: str,
        data: dict | list | str | None = None,
        error: str | None = None,
    ) -> None:
        self.success = success
        self.action = action
        self.data = data
        self.error = error
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "success": self.success,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all AURA agents.

    All agents must implement:
        - name: Human-readable agent name
        - description: What this agent does
        - execute(): Main action method

    All agents automatically get:
        - Structured logging
        - Error handling
        - Result standardization
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """What this agent does."""

    @abstractmethod
    async def execute(self, action: str, params: dict) -> AgentResult:
        """
        Execute an agent action.

        Args:
            action: Action name to perform.
            params: Action-specific parameters.

        Returns:
            AgentResult: Standardized result with success/data/error.
        """

    def log_action(self, action: str, params: dict) -> None:
        """Log every agent action — per Constitution Rule 13."""
        logger.info(
            "[%s] Action: %s | Params: %s",
            self.name,
            action,
            params,
        )

    def log_result(self, result: AgentResult) -> None:
        """Log every agent result."""
        if result.success:
            logger.info(
                "[%s] ✅ Success: %s",
                self.name,
                result.action,
            )
        else:
            logger.error(
                "[%s] ❌ Failed: %s | Error: %s",
                self.name,
                result.action,
                result.error,
            )