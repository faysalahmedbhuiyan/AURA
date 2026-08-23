"""
AURA Backend — Modification Service.

Module: app.modification.modification_service
Purpose: Orchestrates the Safe Self Modification workflow:
         Confirm → Backup → Apply → Report.
         This is the ONLY entry point that may write to project files
         on the user's behalf. Every step enforces the Constitution's
         self-modification rules — no step can be skipped.
"""

import logging
from pathlib import Path

from app.modification.backup_manager import backup_manager
from app.modification.change_applier import change_applier
from app.modification.result_reporter import result_reporter

logger = logging.getLogger(__name__)

# Files AURA will NEVER modify through this pipeline, regardless of
# confirmation — protects the modification system from modifying
# itself or the core app entrypoint into a broken state.
PROTECTED_FILES = {
    "main.py", ".env", "modification_service.py",
    "backup_manager.py", "change_applier.py",
}


class ModificationService:
    """
    Orchestrates safe, confirmed file modifications.

    Methods:
        apply_change: Full Confirm -> Backup -> Apply -> Report pipeline.
        rollback: Restore a file from a specific backup.
    """

    def apply_change(
        self,
        path: str,
        new_content: str,
        confirmed: bool,
        reason: str,
    ) -> dict:
        """
        Apply a confirmed change to a single file, with automatic backup.

        Args:
            path: Absolute path to the file to change.
            new_content: The full new content for the file.
            confirmed: Must be True — this is the explicit user approval
                       gate. If False, nothing happens.
            reason: Short human-readable reason for the change, used to
                    build the suggested commit message.

        Returns:
            dict: Report from ResultReporter — success, backup info,
                  applied info, and rollback instructions.
        """
        target = Path(path).resolve()

        if not confirmed:
            return result_reporter.build_report(
                success=False,
                target_path=str(target),
                backup_info=None,
                apply_result=None,
                error=(
                    "Change was not applied — confirmed=True is required. "
                    "This is an explicit safety gate; nothing was touched."
                ),
                suggested_commit_message=None,
            )

        if target.name in PROTECTED_FILES:
            return result_reporter.build_report(
                success=False,
                target_path=str(target),
                backup_info=None,
                apply_result=None,
                error=(
                    f"'{target.name}' is a protected file and cannot be "
                    "modified through the Safe Self Modification pipeline. "
                    "Edit it manually if changes are truly needed."
                ),
                suggested_commit_message=None,
            )

        try:
            backup_info = backup_manager.create_backup(target)
        except Exception as e:
            logger.exception("Backup failed for %s: %s", target, e)
            return result_reporter.build_report(
                success=False,
                target_path=str(target),
                backup_info=None,
                apply_result=None,
                error=f"Backup failed, change was NOT applied: {e}",
                suggested_commit_message=None,
            )

        try:
            apply_result = change_applier.apply(target, new_content)
        except Exception as e:
            logger.exception("Apply failed for %s: %s", target, e)
            return result_reporter.build_report(
                success=False,
                target_path=str(target),
                backup_info=backup_info,
                apply_result=None,
                error=(
                    f"Write failed: {e}. A backup was already created — "
                    f"the file should be unchanged, but verify manually."
                ),
                suggested_commit_message=None,
            )

        commit_message = self._build_commit_message(target, reason)

        return result_reporter.build_report(
            success=True,
            target_path=str(target),
            backup_info=backup_info,
            apply_result=apply_result,
            error=None,
            suggested_commit_message=commit_message,
        )

    def rollback(self, backup_path: str) -> dict:
        """
        Restore a file from a specific backup.

        Args:
            backup_path: Path to a .bak file created by create_backup.

        Returns:
            dict: {"success": bool, "result": dict | None, "error": str | None}
        """
        try:
            result = backup_manager.restore_backup(backup_path)
            return {"success": True, "result": result, "error": None}
        except Exception as e:
            logger.exception("Rollback failed for %s: %s", backup_path, e)
            return {"success": False, "result": None, "error": str(e)}

    def _build_commit_message(self, target: Path, reason: str) -> str:
        """Build a conventional-commit-style suggested message."""
        short_reason = reason.strip() or "update file"
        return f"fix: {target.name} — {short_reason}"


# ── Singleton instance ────────────────────────────────────────────────────────
modification_service = ModificationService()