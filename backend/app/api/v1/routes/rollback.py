"""
AURA Backend — Rollback System Routes.

Module: app.api.v1.routes.rollback
Purpose: HTTP endpoints for Phase 11 — Rollback System.

Endpoints:
    GET  /api/v1/rollback/status           — Git status + HEAD
    GET  /api/v1/rollback/log              — Commit history
    GET  /api/v1/rollback/preview/{ref}    — Preview rollback (no changes)
    POST /api/v1/rollback/commit           — Full rollback to commit
    POST /api/v1/rollback/files            — Partial rollback (specific files)
    GET  /api/v1/rollback/snapshots        — List named snapshots
    POST /api/v1/rollback/snapshots        — Create named snapshot
    POST /api/v1/rollback/restore-snapshot — Restore from snapshot
    DELETE /api/v1/rollback/snapshots/{id} — Delete snapshot record
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.rollback.git_service import git_service
from app.rollback.rollback_service import rollback_service
from app.rollback.snapshot_service import snapshot_service

logger = logging.getLogger(__name__)
router = APIRouter()

PROJECT_ROOT = Path("D:/AURA")


# ── Request Schemas ───────────────────────────────────────────────────────────

class CommitRollbackRequest(BaseModel):
    """Request to roll back to a specific commit."""
    target_ref: str = Field(..., description="Git commit hash, tag, or branch")
    description: str = Field(..., min_length=3, description="Reason for rollback")
    confirmed: bool = Field(default=False, description="MUST be True to proceed")
    project_root: str = Field(default="D:/AURA")


class FilesRollbackRequest(BaseModel):
    """Request to roll back specific files."""
    target_ref: str = Field(..., description="Git commit to restore files from")
    file_paths: list[str] = Field(..., min_length=1, description="Files to restore")
    description: str = Field(..., min_length=3)
    confirmed: bool = Field(default=False)
    project_root: str = Field(default="D:/AURA")


class CreateSnapshotRequest(BaseModel):
    """Request to create a named snapshot."""
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=3)
    git_ref: str = Field(..., description="Git ref this snapshot points to")
    phase: str = Field(default="")


class RestoreSnapshotRequest(BaseModel):
    """Request to restore from a named snapshot."""
    snapshot_id: str = Field(...)
    confirmed: bool = Field(default=False)
    project_root: str = Field(default="D:/AURA")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/rollback/status",
    summary="Git Status",
    description="Get current branch, HEAD commit, and working tree state.",
    tags=["Rollback"],
)
async def get_status() -> dict:
    """Get current git repository status."""
    status_obj = git_service.get_status(PROJECT_ROOT)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Not a git repository or git not installed.",
        )
    return status_obj.to_dict()


@router.get(
    "/rollback/log",
    summary="Commit History",
    description="Get recent commit history for rollback selection.",
    tags=["Rollback"],
)
async def get_log(limit: int = 20) -> dict:
    """Get recent commits."""
    limit = min(max(limit, 1), 50)
    commits = git_service.get_log(limit, PROJECT_ROOT)
    return {
        "total": len(commits),
        "commits": [c.to_dict() for c in commits],
    }


@router.get(
    "/rollback/preview/{target_ref}",
    summary="Preview Rollback",
    description="Preview what would change in a rollback — no files modified.",
    tags=["Rollback"],
)
async def preview_rollback(target_ref: str) -> dict:
    """Preview a rollback without applying it."""
    preview = rollback_service.get_rollback_preview(target_ref, PROJECT_ROOT)

    if not preview.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=preview.get("error", "Invalid ref"),
        )

    return preview


@router.post(
    "/rollback/commit",
    summary="Rollback to Commit",
    description=(
        "Roll back ALL project files to a specific commit. "
        "Creates a backup snapshot first. confirmed=True required."
    ),
    tags=["Rollback"],
)
async def rollback_to_commit(request: CommitRollbackRequest) -> dict:
    """Roll back all files to a specific commit."""
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "confirmed=True required. "
                "Use GET /api/v1/rollback/preview/{ref} to preview first."
            ),
        )

    root = Path(request.project_root).resolve()
    result = rollback_service.rollback_to_commit(
        target_ref=request.target_ref,
        description=request.description,
        confirmed=request.confirmed,
        project_root=root,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error,
        )

    return result.to_dict()


@router.post(
    "/rollback/files",
    summary="Partial Rollback",
    description="Restore specific files to their state at a commit.",
    tags=["Rollback"],
)
async def rollback_files(request: FilesRollbackRequest) -> dict:
    """Roll back specific files to a commit."""
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmed=True required for file rollback.",
        )

    root = Path(request.project_root).resolve()
    result = rollback_service.rollback_files(
        target_ref=request.target_ref,
        file_paths=request.file_paths,
        description=request.description,
        confirmed=request.confirmed,
        project_root=root,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error,
        )

    return result.to_dict()


@router.get(
    "/rollback/snapshots",
    summary="List Snapshots",
    description="List all named rollback snapshots.",
    tags=["Rollback"],
)
async def list_snapshots() -> dict:
    """List all named snapshots."""
    snaps = snapshot_service.list_snapshots()
    return {
        "total": len(snaps),
        "snapshots": [s.to_dict() for s in snaps],
    }


@router.post(
    "/rollback/snapshots",
    summary="Create Snapshot",
    description="Create a named snapshot pointing to a git ref.",
    tags=["Rollback"],
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(request: CreateSnapshotRequest) -> dict:
    """Create a named snapshot."""
    if not git_service.is_valid_ref(request.git_ref, PROJECT_ROOT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid git ref: '{request.git_ref}'",
        )

    snap = snapshot_service.create_snapshot(
        name=request.name,
        description=request.description,
        git_ref=request.git_ref,
        phase=request.phase,
    )
    return snap.to_dict()


@router.post(
    "/rollback/restore-snapshot",
    summary="Restore from Snapshot",
    description="Restore project to a named snapshot's git ref.",
    tags=["Rollback"],
)
async def restore_snapshot(request: RestoreSnapshotRequest) -> dict:
    """Restore from a named snapshot."""
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmed=True required to restore a snapshot.",
        )

    root = Path(request.project_root).resolve()
    result = rollback_service.restore_snapshot(
        snapshot_id=request.snapshot_id,
        confirmed=request.confirmed,
        project_root=root,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error,
        )

    return result.to_dict()


@router.delete(
    "/rollback/snapshots/{snapshot_id}",
    summary="Delete Snapshot",
    description="Delete a snapshot record (does not affect git history).",
    tags=["Rollback"],
)
async def delete_snapshot(snapshot_id: str) -> dict:
    """Delete a snapshot record."""
    deleted = snapshot_service.delete_snapshot(snapshot_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot '{snapshot_id}' not found.",
        )
    return {"deleted": True, "snapshot_id": snapshot_id}