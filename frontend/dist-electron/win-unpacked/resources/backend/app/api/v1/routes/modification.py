"""
AURA Backend — Modification Routes.

Module: app.api.v1.routes.modification
Purpose: API endpoints for AURA's Safe Self Modification system
         (Phase 10). This is the only route module in AURA that can
         write to project files — every write requires explicit
         confirmed=True and is automatically backed up first.

Endpoints:
    POST /api/v1/modification/apply    — Apply a confirmed change
    POST /api/v1/modification/rollback — Restore from a backup
"""

import logging

from fastapi import APIRouter

from app.modification.modification_service import modification_service
from app.schemas.modification import (
    ApplyChangeRequest,
    ModificationReport,
    RollbackReport,
    RollbackRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/modification/apply",
    response_model=ModificationReport,
    summary="Apply a Confirmed File Change",
    description=(
        "Applies new content to a file. REQUIRES confirmed=True — this "
        "is a non-bypassable safety gate. A timestamped backup is "
        "created automatically before any write. Protected files "
        "(main.py, .env, and the modification system itself) can never "
        "be changed through this endpoint."
    ),
    tags=["Self Modification"],
)
async def apply_change(request: ApplyChangeRequest) -> ModificationReport:
    """
    Apply a confirmed change to a single file.

    Args:
        request: Target path, new content, confirmation flag, and reason.

    Returns:
        ModificationReport: Success status, backup info, and rollback
                             instructions.
    """
    report = modification_service.apply_change(
        path=request.path,
        new_content=request.new_content,
        confirmed=request.confirmed,
        reason=request.reason,
    )
    return ModificationReport(**report)


@router.post(
    "/modification/rollback",
    response_model=RollbackReport,
    summary="Rollback a Change",
    description="Restores a file from a specific backup created by /apply.",
    tags=["Self Modification"],
)
async def rollback_change(request: RollbackRequest) -> RollbackReport:
    """
    Restore a file from a backup.

    Args:
        request: Path to the backup file to restore.

    Returns:
        RollbackReport: Success status and what was restored/deleted.
    """
    result = modification_service.rollback(request.backup_path)
    return RollbackReport(**result)