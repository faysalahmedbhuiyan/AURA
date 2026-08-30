"""
AURA Backend — Change Applier.

Module: app.modification.change_applier
Purpose: Writes new content to a file. This is the ONLY function in
         AURA that performs the actual write for Safe Self Modification,
         and it is only ever called after backup_manager has created a
         backup and the caller has verified confirmed=True.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeApplier:
    """
    Applies a single content change to a file.

    Methods:
        apply: Write new_content to target, creating parent dirs if needed.
    """

    def apply(self, target: Path, new_content: str) -> dict:
        """
        Write new_content to target.

        Args:
            target: File path to write.
            new_content: Full new content for the file.

        Returns:
            dict: {"path": str, "bytes_written": int}
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
        bytes_written = len(new_content.encode("utf-8"))

        logger.info("Applied change: %s (%d bytes)", target, bytes_written)

        return {"path": str(target), "bytes_written": bytes_written}


# ── Singleton instance ────────────────────────────────────────────────────────
change_applier = ChangeApplier()