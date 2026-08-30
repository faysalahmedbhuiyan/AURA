"""
AURA Backend — Modification Schemas.

Module: app.schemas.modification
Purpose: Pydantic models for the Safe Self Modification pipeline
         (Phase 10).
"""

from pydantic import BaseModel, Field


class ApplyChangeRequest(BaseModel):
    """
    Request to apply a confirmed change to a file.

    confirmed MUST be explicitly set True by the caller — this is the
    non-bypassable approval gate from the Constitution.
    """

    path: str = Field(..., description="Absolute path to the target file")
    new_content: str = Field(..., description="Full new content for the file")
    confirmed: bool = Field(
        ..., description="Must be True. Explicit user approval gate."
    )
    reason: str = Field(
        default="", max_length=300,
        description="Short reason for the change, used in commit message",
    )


class RollbackRequest(BaseModel):
    """Request to restore a file from a backup."""

    backup_path: str = Field(..., description="Path to the .bak file")


class ModificationReport(BaseModel):
    """Report of a modification attempt."""

    success: bool
    target_path: str
    backup: dict | None
    applied: dict | None
    error: str | None
    suggested_commit_message: str | None
    rollback_instructions: str | None


class RollbackReport(BaseModel):
    """Report of a rollback attempt."""

    success: bool
    result: dict | None
    error: str | None