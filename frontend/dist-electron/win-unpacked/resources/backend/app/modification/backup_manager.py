"""
AURA Backend — Backup Manager.

Module: app.modification.backup_manager
Purpose: Creates timestamped backups before any file modification and
         restores from them on request. Backups live under
         D:/AURA/backups/ mirroring the original path so restoration
         is unambiguous.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_ROOT = Path("D:/AURA/backups")


class BackupManager:
    """
    Manages file backups for Safe Self Modification.

    Methods:
        create_backup: Copy a file to the backup store before it's changed.
        restore_backup: Copy a backup back over the original file.
        list_backups: List available backups for a given original path.
    """

    def create_backup(self, target: Path) -> dict:
        """
        Create a timestamped backup of a file before modifying it.

        Args:
            target: The file that is about to be modified.

        Returns:
            dict: {
                "backup_path": str,
                "original_path": str,
                "timestamp": str,
                "existed_before": bool,
            }

        Raises:
            FileNotFoundError: If target's parent directory is invalid.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        existed_before = target.exists()

        # Mirror the original path structure under BACKUP_ROOT, with a
        # timestamp suffix so multiple backups of the same file coexist.
        try:
            relative = target.resolve().relative_to(Path("D:/AURA").resolve())
        except ValueError:
            relative = Path(target.name)

        backup_path = BACKUP_ROOT / relative.parent / f"{relative.name}.{timestamp}.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if existed_before:
            shutil.copy2(target, backup_path)
            logger.info("Backup created: %s -> %s", target, backup_path)
        else:
            # File doesn't exist yet — write a marker so restore knows
            # to delete the file rather than overwrite it.
            backup_path.write_text(
                "__AURA_BACKUP_MARKER__:file did not exist before this change",
                encoding="utf-8",
            )
            logger.info(
                "Backup marker created for new file: %s -> %s",
                target, backup_path,
            )

        return {
            "backup_path": str(backup_path),
            "original_path": str(target),
            "timestamp": timestamp,
            "existed_before": existed_before,
        }

    def restore_backup(self, backup_path: str) -> dict:
        """
        Restore a file from a backup, overwriting the current version.

        Args:
            backup_path: Path returned by create_backup().

        Returns:
            dict: {"restored_path": str, "action": "restored"|"deleted"}

        Raises:
            FileNotFoundError: If the backup file does not exist.
        """
        backup = Path(backup_path)
        if not backup.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        original_path_str = backup.name.rsplit(".", 2)[0]  # strip .<ts>.bak
        relative = backup.relative_to(BACKUP_ROOT).parent / original_path_str
        original = Path("D:/AURA") / relative

        content = backup.read_text(encoding="utf-8", errors="replace")
        if content.startswith("__AURA_BACKUP_MARKER__"):
            # File didn't exist before — restore means delete it now.
            if original.exists():
                original.unlink()
            logger.info("Restored by deleting (file was new): %s", original)
            return {"restored_path": str(original), "action": "deleted"}

        shutil.copy2(backup, original)
        logger.info("Restored: %s <- %s", original, backup)
        return {"restored_path": str(original), "action": "restored"}

    def list_backups(self, target: Path) -> list[dict]:
        """
        List all backups available for a given original file path.

        Args:
            target: Original file path.

        Returns:
            list[dict]: Backups sorted newest-first.
        """
        try:
            relative = target.resolve().relative_to(Path("D:/AURA").resolve())
        except ValueError:
            relative = Path(target.name)

        backup_dir = BACKUP_ROOT / relative.parent
        if not backup_dir.exists():
            return []

        matches = sorted(
            backup_dir.glob(f"{relative.name}.*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [
            {"backup_path": str(m), "modified": datetime.fromtimestamp(
                m.stat().st_mtime, tz=timezone.utc
            ).isoformat()}
            for m in matches
        ]


# ── Singleton instance ────────────────────────────────────────────────────────
backup_manager = BackupManager()