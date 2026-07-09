"""
AURA Backend — Snapshot Service.

Module: app.rollback.snapshot_service
Purpose: Manages named snapshots — user-friendly restore points
         stored as JSON metadata alongside Git refs.

         A snapshot = Git stash/tag + human name + description.
         Snapshots are stored in D:/AURA/.aura/snapshots/

All snapshot operations are logged per Constitution Rule 13.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("D:/AURA")
SNAPSHOT_DIR = PROJECT_ROOT / ".aura" / "snapshots"


class Snapshot:
    """A named restore point."""

    def __init__(
        self,
        name: str,
        description: str,
        git_ref: str,
        created_at: str,
        snapshot_id: str,
        phase: str = "",
    ) -> None:
        self.name = name
        self.description = description
        self.git_ref = git_ref
        self.created_at = created_at
        self.snapshot_id = snapshot_id
        self.phase = phase

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "name": self.name,
            "description": self.description,
            "git_ref": self.git_ref,
            "created_at": self.created_at,
            "phase": self.phase,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            git_ref=data.get("git_ref", ""),
            created_at=data.get("created_at", ""),
            snapshot_id=data.get("snapshot_id", ""),
            phase=data.get("phase", ""),
        )


class SnapshotService:
    """
    Named snapshot management.

    Snapshots are JSON files in .aura/snapshots/ that reference
    a Git commit hash. They give restore points human-readable names.

    Methods:
        create_snapshot  — Create a named restore point
        list_snapshots   — List all saved snapshots
        get_snapshot     — Get a snapshot by ID
        delete_snapshot  — Delete a snapshot record (not the commit)
    """

    def _ensure_dir(self) -> None:
        """Ensure snapshot directory exists."""
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        gitignore = SNAPSHOT_DIR.parent / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# AURA internal files\n")

    def create_snapshot(
        self,
        name: str,
        description: str,
        git_ref: str,
        phase: str = "",
    ) -> Snapshot:
        """
        Create a named snapshot pointing to a Git ref.

        Args:
            name: Human-readable snapshot name.
            description: What state this captures.
            git_ref: Git commit hash to point to.
            phase: Optional phase label (e.g. "Phase 10 complete").

        Returns:
            Snapshot: Created snapshot.
        """
        self._ensure_dir()

        timestamp = datetime.now(timezone.utc)
        snapshot_id = f"snap_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        snapshot = Snapshot(
            name=name,
            description=description,
            git_ref=git_ref,
            created_at=timestamp.isoformat(),
            snapshot_id=snapshot_id,
            phase=phase,
        )

        snap_file = SNAPSHOT_DIR / f"{snapshot_id}.json"
        snap_file.write_text(
            json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info("Snapshot created: %s → %s", snapshot_id, git_ref)
        return snapshot

    def list_snapshots(self) -> list[Snapshot]:
        """
        List all saved snapshots, newest first.

        Returns:
            list[Snapshot]: All saved snapshots.
        """
        if not SNAPSHOT_DIR.exists():
            return []

        snapshots = []
        for snap_file in sorted(SNAPSHOT_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(snap_file.read_text(encoding="utf-8"))
                snapshots.append(Snapshot.from_dict(data))
            except Exception as e:
                logger.warning("Could not read snapshot %s: %s", snap_file, e)

        return snapshots

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        """
        Get a specific snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier.

        Returns:
            Snapshot | None: Snapshot or None if not found.
        """
        snap_file = SNAPSHOT_DIR / f"{snapshot_id}.json"
        if not snap_file.exists():
            return None

        try:
            data = json.loads(snap_file.read_text(encoding="utf-8"))
            return Snapshot.from_dict(data)
        except Exception as e:
            logger.error("Could not read snapshot %s: %s", snapshot_id, e)
            return None

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot record (does not affect Git history).

        Args:
            snapshot_id: Snapshot to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        snap_file = SNAPSHOT_DIR / f"{snapshot_id}.json"
        if snap_file.exists():
            snap_file.unlink()
            logger.info("Snapshot deleted: %s", snapshot_id)
            return True
        return False


# ── Singleton instance ────────────────────────────────────────────────────────
snapshot_service = SnapshotService()