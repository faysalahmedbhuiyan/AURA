"""
AURA Backend — Result Reporter.

Module: app.modification.result_reporter
Purpose: Builds a human-readable report after a modification attempt,
         summarizing what changed, whether it succeeded, and how to
         undo it if needed.
"""

import logging

logger = logging.getLogger(__name__)


class ResultReporter:
    """
    Builds final reports for Safe Self Modification actions.

    Methods:
        build_report: Compose a full result dict for the API response.
    """

    def build_report(
        self,
        success: bool,
        target_path: str,
        backup_info: dict | None,
        apply_result: dict | None,
        error: str | None,
        suggested_commit_message: str | None,
    ) -> dict:
        """
        Build a structured report of a modification attempt.

        Args:
            success: Whether the change was applied successfully.
            target_path: File that was targeted.
            backup_info: Result from BackupManager.create_backup, if run.
            apply_result: Result from ChangeApplier.apply, if run.
            error: Error message if the attempt failed.
            suggested_commit_message: A ready-to-use git commit message.

        Returns:
            dict: Full report for the API response.
        """
        report = {
            "success": success,
            "target_path": target_path,
            "backup": backup_info,
            "applied": apply_result,
            "error": error,
            "suggested_commit_message": suggested_commit_message,
            "rollback_instructions": (
                f"POST /api/v1/modification/rollback with "
                f"backup_path='{backup_info['backup_path']}'"
                if backup_info else None
            ),
        }
        return report


# ── Singleton instance ────────────────────────────────────────────────────────
result_reporter = ResultReporter()