"""
AURA Backend — Planning Routes.

Module: app.api.v1.routes.planning
Purpose: API endpoint for AURA's Self Improvement Planner (Phase 9).
         Produces plans only — never modifies any file. Applying a
         plan requires Phase 10, which does not exist yet.

Endpoint:
    POST /api/v1/planning/create — Create an improvement plan.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.planning.plan_service import plan_service
from app.schemas.planning import PlanRequest, PlanResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/planning/create",
    response_model=PlanResponse,
    summary="Create an Improvement Plan",
    description=(
        "Analyzes a free-text improvement request, identifies candidate "
        "affected files across the whole project (backend and frontend), "
        "and estimates risk. NEVER modifies any file — this endpoint only "
        "plans. Applying a plan is a future capability (Phase 10) that "
        "does not exist yet."
    ),
    tags=["Self Improvement Planning"],
)
async def create_plan(request: PlanRequest) -> PlanResponse:
    """
    Create an improvement plan from a free-text request.

    Args:
        request: Description of the desired change and project root.

    Returns:
        PlanResponse: Structured plan with affected files and risk.

    Raises:
        404: If project_root does not exist.
    """
    root = Path(request.project_root).resolve()
    if not root.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project root does not exist: {root}",
        )

    plan = plan_service.create_plan(request.description, root)
    return PlanResponse(**plan)