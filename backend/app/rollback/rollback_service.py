"""
AURA Backend — Rollback Service.

Module: app.rollback.rollback_service
Purpose: Orchestrates the full Rollback pipeline.

         Workflow (Constitution Rule 11):
         1. Validate target ref exists
         2. Save current state as backup snapshot
         3. Stash any uncommitted changes
         4. Checkout target ref (files only, not HEAD)
         5. Report result with undo instructions

         CRITICAL: Rollback is ALWAYS reversible.
         Before any rollback, current state is saved as a snapshot
         so the user can undo the rollback itself.
"""

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.rollback.git_service import git_service
from app.rollback.snapshot_service import snapshot_service

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("D:/AURA")


class RollbackResult:
    """Result of a rollback operation."""

    def __init__(
        self,
        success: bool,
        target_ref: str,
        pre_rollback_snapshot: str | None = None,
        files_restored: list[str] | None = None,
        message: str = "",
        error: str | None = None,
        undo_instructions: str = "",
    ) -> None:
        self.success = success
        self.target_ref = target_ref
        self.pre_rollback_snapshot = pre_rollback_snapshot
        self.files_restored = files_restored or []
        self.message = message
        self.error = error
        self.undo_instructions = undo_instructions
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "target_ref": self.target_ref,
            "pre_rollback_snapshot": self.pre_rollback_snapshot,
            "files_restored": self.files_restored,
            "message": self.message,
            "error": self.error,
            "undo_instructions": self.undo_instructions,
            "timestamp": self.timestamp,
        }


class RollbackService:
    """
    Orchestrates safe, reversible project rollbacks.

    Every rollback:
    1. Saves current state first (so rollback is undoable)
    2. Validates the target ref
    3. Restores files to target state
    4. Reports what changed and how to undo

    Methods:
        rollback_to_commit  — Restore files to a specific commit
        rollback_files      — Restore specific files to a commit
        get_rollback_preview — Preview what would change
    """

    def _run_git(
        self,
        args: list[str],
        cwd: Path = PROJECT_ROOT,
    ) -> tuple[bool, str, str]:
        """Run a git command."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)

    def get_rollback_preview(
        self,
        target_ref: str,
        project_root: Path = PROJECT_ROOT,
    ) -> dict:
        """
        Preview what a rollback would change WITHOUT applying it.

        Args:
            target_ref: Git ref to preview rollback to.
            project_root: Repository root.

        Returns:
            dict: Files that would change, diff summary.
        """
        if not git_service.is_valid_ref(target_ref, project_root):
            return {
                "valid": False,
                "error": f"Invalid git ref: '{target_ref}'",
            }

        # Get commit info
        ok, commit_info, _ = self._run_git(
            ["log", "-1", "--pretty=%h|%s|%ai", target_ref],
            cwd=project_root,
        )

        commit_data = {}
        if ok and commit_info:
            parts = commit_info.split("|", 2)
            if len(parts) == 3:
                commit_data = {
                    "short_hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                }

        # Get files that would change
        diff = git_service.get_diff(target_ref, "HEAD", project_root)
        changed_files = git_service.get_changed_files(target_ref, project_root)

        return {
            "valid": True,
            "target_ref": target_ref,
            "commit": commit_data,
            "files_that_would_change": changed_files,
            "diff_summary": diff,
            "warning": (
                "This preview shows what would change. "
                "Actual rollback requires confirmed=True and creates a "
                "backup of current state first."
            ),
        }

    def rollback_to_commit(
        self,
        target_ref: str,
        description: str,
        confirmed: bool,
        project_root: Path = PROJECT_ROOT,
    ) -> RollbackResult:
        """
        Restore all project files to a specific commit state.

        Workflow:
        1. Validate confirmed=True
        2. Validate target_ref exists
        3. Save current state as pre-rollback snapshot
        4. Stash any uncommitted work
        5. Checkout target ref files (git checkout <ref> -- .)
        6. Report result with undo instructions

        Args:
            target_ref: Git commit hash, tag, or branch to restore.
            description: Why this rollback is being done.
            confirmed: MUST be True — safety gate.
            project_root: Repository root.

        Returns:
            RollbackResult: Success/failure with undo instructions.
        """
        # ── Gate ─────────────────────────────────────────────────────────────
        if not confirmed:
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                error=(
                    "Rollback rejected — confirmed=True is required. "
                    "Review the preview first, then resubmit with confirmed=True."
                ),
            )

        # ── Validate ref ──────────────────────────────────────────────────────
        if not git_service.is_valid_ref(target_ref, project_root):
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                error=f"Invalid git ref: '{target_ref}'. Check commit hash or branch name.",
            )

        # ── Step 1: Save current state ────────────────────────────────────────
        current_status = git_service.get_status(project_root)
        current_ref = current_status.head_commit if current_status else "unknown"

        pre_snapshot = snapshot_service.create_snapshot(
            name=f"Pre-rollback to {target_ref[:8]}",
            description=(
                f"Automatic backup before rollback to {target_ref}. "
                f"Reason: {description}"
            ),
            git_ref=current_ref,
            phase="rollback_backup",
        )

        logger.info(
            "Pre-rollback snapshot created: %s (ref: %s)",
            pre_snapshot.snapshot_id,
            current_ref,
        )

        # ── Step 2: Stash uncommitted changes ─────────────────────────────────
        if current_status and not current_status.is_clean:
            stash_msg = f"AURA rollback stash: before rollback to {target_ref}"
            self._run_git(
                ["stash", "push", "-m", stash_msg, "--include-untracked"],
                cwd=project_root,
            )
            logger.info("Stashed uncommitted changes before rollback")

        # ── Step 3: Get files that will change ────────────────────────────────
        files_to_restore = git_service.get_changed_files(target_ref, project_root)

        # ── Step 4: Checkout files at target ref ──────────────────────────────
        ok, _, stderr = self._run_git(
            ["checkout", target_ref, "--", "."],
            cwd=project_root,
        )

        if not ok:
            # Restore stash if checkout failed
            self._run_git(["stash", "pop"], cwd=project_root)

            return RollbackResult(
                success=False,
                target_ref=target_ref,
                pre_rollback_snapshot=pre_snapshot.snapshot_id,
                error=f"Git checkout failed: {stderr}",
            )

        logger.info(
            "Rollback completed: restored to %s (%d files)",
            target_ref,
            len(files_to_restore),
        )

        undo_instructions = (
            f"To UNDO this rollback, run:\n"
            f"  git checkout {current_ref} -- .\n"
            f"Or restore snapshot: {pre_snapshot.snapshot_id}\n"
            f"Via API: POST /api/v1/rollback/restore-snapshot "
            f"with snapshot_id='{pre_snapshot.snapshot_id}'"
        )

        return RollbackResult(
            success=True,
            target_ref=target_ref,
            pre_rollback_snapshot=pre_snapshot.snapshot_id,
            files_restored=files_to_restore,
            message=(
                f"Successfully rolled back to {target_ref}. "
                f"{len(files_to_restore)} files restored. "
                f"Pre-rollback state saved as snapshot: {pre_snapshot.snapshot_id}"
            ),
            undo_instructions=undo_instructions,
        )

    def rollback_files(
        self,
        target_ref: str,
        file_paths: list[str],
        description: str,
        confirmed: bool,
        project_root: Path = PROJECT_ROOT,
    ) -> RollbackResult:
        """
        Restore specific files to their state at a commit.

        Safer than full rollback — only touches the specified files.

        Args:
            target_ref: Git commit to restore files from.
            file_paths: List of file paths to restore.
            description: Why these files are being restored.
            confirmed: MUST be True.
            project_root: Repository root.

        Returns:
            RollbackResult: Result with per-file status.
        """
        if not confirmed:
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                error="Rollback rejected — confirmed=True is required.",
            )

        if not file_paths:
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                error="No files specified for partial rollback.",
            )

        if not git_service.is_valid_ref(target_ref, project_root):
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                error=f"Invalid git ref: '{target_ref}'",
            )

        # Save current state
        current_status = git_service.get_status(project_root)
        current_ref = current_status.head_commit if current_status else "unknown"

        pre_snapshot = snapshot_service.create_snapshot(
            name=f"Pre-partial-rollback ({len(file_paths)} files)",
            description=(
                f"Backup before partial rollback of {len(file_paths)} files "
                f"to {target_ref}. Reason: {description}"
            ),
            git_ref=current_ref,
            phase="partial_rollback_backup",
        )

        # Normalize paths for git
        normalized = [p.replace("\\", "/") for p in file_paths]

        ok, _, stderr = self._run_git(
            ["checkout", target_ref, "--"] + normalized,
            cwd=project_root,
        )

        if not ok:
            return RollbackResult(
                success=False,
                target_ref=target_ref,
                pre_rollback_snapshot=pre_snapshot.snapshot_id,
                error=f"Partial rollback failed: {stderr}",
            )

        undo_instructions = (
            f"To UNDO this partial rollback:\n"
            f"  git checkout {current_ref} -- {' '.join(normalized)}\n"
            f"Or restore snapshot: {pre_snapshot.snapshot_id}"
        )

        return RollbackResult(
            success=True,
            target_ref=target_ref,
            pre_rollback_snapshot=pre_snapshot.snapshot_id,
            files_restored=file_paths,
            message=(
                f"Successfully restored {len(file_paths)} file(s) to {target_ref}. "
                f"Backup snapshot: {pre_snapshot.snapshot_id}"
            ),
            undo_instructions=undo_instructions,
        )

    def restore_snapshot(
        self,
        snapshot_id: str,
        confirmed: bool,
        project_root: Path = PROJECT_ROOT,
    ) -> RollbackResult:
        """
        Restore project to a named snapshot's git ref.

        Used to undo a previous rollback.

        Args:
            snapshot_id: Snapshot ID from snapshot_service.
            confirmed: MUST be True.
            project_root: Repository root.

        Returns:
            RollbackResult: Result.
        """
        if not confirmed:
            return RollbackResult(
                success=False,
                target_ref="",
                error="Restore rejected — confirmed=True required.",
            )

        snapshot = snapshot_service.get_snapshot(snapshot_id)
        if not snapshot:
            return RollbackResult(
                success=False,
                target_ref="",
                error=f"Snapshot '{snapshot_id}' not found.",
            )

        return self.rollback_to_commit(
            target_ref=snapshot.git_ref,
            description=f"Restoring snapshot: {snapshot.name}",
            confirmed=confirmed,
            project_root=project_root,
        )


# ── Singleton instance ────────────────────────────────────────────────────────
rollback_service = RollbackService()