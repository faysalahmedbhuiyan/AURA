"""
AURA Backend — Review Routes.

Module: app.api.v1.routes.review
Purpose: API endpoint for AURA's Self Review Engine (Phase 8).
         Analysis only — never modifies any file.

Endpoint:
    POST /api/v1/review/analyze — Analyze a path and return a report.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.review.review_service import review_service
from app.schemas.review import ReviewRequest, ReviewResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Reuse the same safe-directory principle as FileAgent
SAFE_BASE_DIRS = [Path.home(), Path("D:/AURA"), Path("D:/")]


@router.post(
    "/review/analyze",
    response_model=ReviewResponse,
    summary="Analyze Code Quality",
    description=(
        "Runs AURA's Self Review Engine on a file or directory. "
        "READ-ONLY — never modifies any file. Returns a debt score, "
        "prioritized suggestions, and the full issue list."
    ),
    tags=["Self Review"],
)
async def analyze_path(request: ReviewRequest) -> ReviewResponse:
    """
    Analyze a Python file or directory for code quality issues.

    Args:
        request: Path to analyze and optional file cap.

    Returns:
        ReviewResponse: Debt summary, suggestions, and issue list.

    Raises:
        404: If the path does not exist.
    """
    target = Path(request.path).resolve()

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path does not exist: {target}",
        )

    report = review_service.review_path(target, max_files=request.max_files)
    return ReviewResponse(**report)