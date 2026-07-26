"""
AURA Backend — Self-Improvement Routes.

Module: app.api.v1.routes.self_improve
Purpose: HTTP endpoints for Tier 4-A2 — Self-Improvement Engine.

Endpoints:
    GET  /api/v1/self-improve/health      — Quick health report
    POST /api/v1/self-improve/analyze     — Full analysis
    POST /api/v1/self-improve/improve     — Analyze + generate patches
    POST /api/v1/self-improve/apply       — Apply a confirmed patch
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.self_improve.self_improve_service import self_improve_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ApplyPatchRequest(BaseModel):
    file_path: str = Field(..., description="Relative path from backend root")
    old_text: str = Field(..., min_length=1)
    new_text: str = Field(..., min_length=1)
    description: str = Field(default="Self-improvement patch")
    confirmed: bool = Field(
        default=False,
        description="MUST be True to apply. Review patch carefully first.",
    )


@router.get(
    "/self-improve/health",
    summary="Code Health Report",
    description="Quick health overview of AURA's codebase.",
    tags=["Self-Improvement"],
)
async def get_health() -> dict:
    """Get code health report."""
    return await self_improve_service.get_health_report()


@router.post(
    "/self-improve/analyze",
    summary="Analyze Codebase",
    description="Analyze AURA's Python codebase for issues.",
    tags=["Self-Improvement"],
)
async def analyze_code(max_files: int = 30) -> dict:
    """Analyze codebase and return issues."""
    result = await self_improve_service.analyze(max_files=max_files)
    return result.to_dict()


@router.post(
    "/self-improve/improve",
    summary="Generate Improvements",
    description=(
        "Analyze codebase and generate improvement patches. "
        "Patches are NEVER applied automatically — review before applying."
    ),
    tags=["Self-Improvement"],
)
async def generate_improvements(max_patches: int = 3) -> dict:
    """Analyze + generate improvement patches."""
    return await self_improve_service.generate_improvements(max_patches=max_patches)


@router.post(
    "/self-improve/apply",
    summary="Apply Patch",
    description=(
        "Apply a confirmed improvement patch. "
        "confirmed=True required. Review the patch carefully first."
    ),
    tags=["Self-Improvement"],
)
async def apply_patch(request: ApplyPatchRequest) -> dict:
    """Apply a confirmed patch."""
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmed=True required. Review the patch carefully first.",
        )

    result = await self_improve_service.apply_patch(
        file_path=request.file_path,
        old_text=request.old_text,
        new_text=request.new_text,
        confirmed=request.confirmed,
        description=request.description,
    )

    if not result.get("success") and result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Patch application failed"),
        )

    return result