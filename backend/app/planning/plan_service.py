"""
AURA Backend — Plan Service.

Module: app.planning.plan_service
Purpose: Orchestrates the full Self Improvement Planning pipeline:
         parse request → map affected files → estimate risk → build
         a final plan. NEVER modifies any file. Applying a plan is a
         future Phase 10 capability that does not exist yet — every
         plan returned here is inert and requires human review.
"""

import logging
from pathlib import Path

from app.planning.impact_mapper import impact_mapper
from app.planning.request_parser import request_parser
from app.planning.risk_estimator import risk_estimator

logger = logging.getLogger(__name__)


class PlanService:
    """
    Orchestrates improvement plan creation.

    Methods:
        create_plan: Full pipeline from raw request text to a structured,
                     human-reviewable plan.
    """

    def create_plan(self, description: str, project_root: Path) -> dict:
        """
        Create an improvement plan from a free-text request.

        Args:
            description: What the user wants improved/changed.
            project_root: Root directory to search for affected files.

        Returns:
            dict: {
                "request": str,
                "analysis": dict,
                "affected_files": list[dict],
                "risk": dict,
                "status": "pending_approval",
                "approval_note": str,
            }
        """
        analysis = request_parser.parse(description)
        affected_files = impact_mapper.map_impact(analysis, project_root)
        risk = risk_estimator.estimate(affected_files)

        return {
            "request": description,
            "analysis": analysis.to_dict(),
            "affected_files": [f.to_dict() for f in affected_files],
            "risk": risk.to_dict(),
            "status": "pending_approval",
            "approval_note": (
                "This is a plan only — no file has been changed. "
                "Applying plans is not yet implemented (Phase 10). "
                "Review the affected files and risk level, then decide "
                "manually what to do next."
            ),
        }


# ── Singleton instance ────────────────────────────────────────────────────────
plan_service = PlanService()