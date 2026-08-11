"""
AURA Backend — Risk Estimator.

Module: app.planning.risk_estimator
Purpose: Assigns a risk level (low/medium/high/critical) to a proposed
         change based on which files are affected. NEVER modifies any
         file — estimation only.
"""

import logging

from app.planning.impact_mapper import AffectedFile

logger = logging.getLogger(__name__)

# Filenames that are considered high-blast-radius if touched.
CRITICAL_FILENAMES = {
    "main.py", "config.py", "connection.py", ".env",
    "base.py",
}
HIGH_RISK_FILENAMES = {
    "knowledge.py", "conversation.py", "message.py",  # DB models
    "app.jsx", "main.jsx",  # frontend entry points
}
LOW_RISK_EXTENSIONS = {".md", ".txt"}

RISK_ORDER = ["low", "medium", "high", "critical"]


class RiskAssessment:
    """Risk level with a human-readable explanation."""

    def __init__(self, level: str, explanation: str, factors: list[str]) -> None:
        self.level = level
        self.explanation = explanation
        self.factors = factors

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "explanation": self.explanation,
            "factors": self.factors,
        }


class RiskEstimator:
    """
    Estimates risk for a set of affected files.

    Methods:
        estimate: Compute risk level and explanation.
    """

    def estimate(self, affected_files: list[AffectedFile]) -> RiskAssessment:
        """
        Estimate risk level for a proposed change.

        Args:
            affected_files: Candidate files from ImpactMapper.

        Returns:
            RiskAssessment: Risk level, explanation, and contributing factors.
        """
        if not affected_files:
            return RiskAssessment(
                "low",
                "No files were confidently identified as affected. "
                "Risk cannot be meaningfully assessed — clarify the request.",
                [],
            )

        factors: list[str] = []
        level = "low"

        names = {Path_name(f.path) for f in affected_files}

        if names & CRITICAL_FILENAMES:
            level = "critical"
            factors.append(
                "Touches a critical file (app entrypoint, config, or "
                "database connection) — mistakes here can break the "
                "whole application."
            )

        if names & HIGH_RISK_FILENAMES:
            level = self._max_level(level, "high")
            factors.append(
                "Touches a data model or frontend entry point — "
                "changes here can have wide-reaching effects."
            )

        if len(affected_files) > 10:
            level = self._max_level(level, "high")
            factors.append(
                f"Affects {len(affected_files)} files — a large blast "
                "radius increases the chance of unintended side effects."
            )
        elif len(affected_files) > 4:
            level = self._max_level(level, "medium")
            factors.append(
                f"Affects {len(affected_files)} files — moderate scope."
            )

        all_low_risk_ext = all(
            f.path.endswith(tuple(LOW_RISK_EXTENSIONS)) for f in affected_files
        )
        if all_low_risk_ext:
            level = "low"
            factors.append("Only documentation/text files are affected.")

        if not factors:
            factors.append(
                "Small, contained change with no critical files involved."
            )

        explanation = self._build_explanation(level, len(affected_files))
        return RiskAssessment(level, explanation, factors)

    def _max_level(self, current: str, candidate: str) -> str:
        """Return whichever level is higher in RISK_ORDER."""
        if RISK_ORDER.index(candidate) > RISK_ORDER.index(current):
            return candidate
        return current

    def _build_explanation(self, level: str, file_count: int) -> str:
        """Build a short summary sentence for the risk level."""
        return {
            "low": "This looks like a safe, contained change.",
            "medium": "This change has moderate scope — review the "
                      "affected files list before approving.",
            "high": "This change touches sensitive parts of the system — "
                    "review carefully before approving.",
            "critical": "This change could break core functionality if "
                        "done incorrectly — extra caution required.",
        }.get(level, "Risk could not be determined.")


def Path_name(path_str: str) -> str:
    """Extract filename from a path string (Windows or POSIX)."""
    return path_str.replace("\\", "/").rsplit("/", 1)[-1]


# ── Singleton instance ────────────────────────────────────────────────────────
risk_estimator = RiskEstimator()