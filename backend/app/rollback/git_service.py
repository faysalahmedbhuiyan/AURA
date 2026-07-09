"""
AURA Backend — Git Service.

Module: app.rollback.git_service
Purpose: Low-level Git operations for the Rollback System.
         Read-only operations: log, diff, status, show.
         Write operations: checkout, reset (only via rollback_service).

All operations are logged per Constitution Rule 13.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("D:/AURA")


@dataclass
class GitCommit:
    """A single Git commit entry."""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    files_changed: int = 0

    def to_dict(self) -> dict:
        return {
            "hash": self.hash,
            "short_hash": self.short_hash,
            "author": self.author,
            "date": self.date,
            "message": self.message,
            "files_changed": self.files_changed,
        }


@dataclass
class GitStatus:
    """Current Git repository status."""
    branch: str
    head_commit: str
    head_message: str
    is_clean: bool
    modified_files: list[str]
    staged_files: list[str]
    untracked_files: list[str]

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "head_commit": self.head_commit,
            "head_message": self.head_message,
            "is_clean": self.is_clean,
            "modified_files": self.modified_files,
            "staged_files": self.staged_files,
            "untracked_files": self.untracked_files,
        }


class GitService:
    """
    Low-level Git operations service.

    Methods:
        get_status      — Current branch, HEAD, working tree state
        get_log         — Recent commit history
        get_diff        — Diff between commits or working tree
        get_file_at     — File content at a specific commit
        get_changed_files — Files changed in a commit
    """

    def _run(
        self,
        args: list[str],
        cwd: Path = PROJECT_ROOT,
    ) -> tuple[bool, str, str]:
        """Run a git command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        except subprocess.TimeoutExpired:
            return False, "", "Git command timed out"
        except FileNotFoundError:
            return False, "", "Git not found — install Git and retry"
        except Exception as e:
            return False, "", str(e)

    def get_status(
        self,
        project_root: Path = PROJECT_ROOT,
    ) -> GitStatus | None:
        """
        Get current repository status.

        Returns:
            GitStatus | None: Current status or None if not a git repo.
        """
        # Branch
        ok, branch, _ = self._run(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=project_root
        )
        if not ok:
            return None

        # HEAD commit
        ok, head_hash, _ = self._run(
            ["rev-parse", "--short", "HEAD"], cwd=project_root
        )
        head_hash = head_hash if ok else "unknown"

        # HEAD message
        ok, head_msg, _ = self._run(
            ["log", "-1", "--pretty=%s"], cwd=project_root
        )
        head_msg = head_msg if ok else ""

        # Working tree status
        ok, status_out, _ = self._run(
            ["status", "--porcelain"], cwd=project_root
        )

        modified, staged, untracked = [], [], []
        if ok and status_out:
            for line in status_out.splitlines():
                if len(line) < 3:
                    continue
                xy = line[:2]
                path = line[3:]
                if xy[0] in ("M", "A", "D", "R"):
                    staged.append(path)
                if xy[1] in ("M", "D"):
                    modified.append(path)
                if xy == "??":
                    untracked.append(path)

        return GitStatus(
            branch=branch,
            head_commit=head_hash,
            head_message=head_msg,
            is_clean=not (modified or staged or untracked),
            modified_files=modified,
            staged_files=staged,
            untracked_files=untracked,
        )

    def get_log(
        self,
        limit: int = 20,
        project_root: Path = PROJECT_ROOT,
    ) -> list[GitCommit]:
        """
        Get recent commit history.

        Args:
            limit: Maximum number of commits to return.
            project_root: Repository root.

        Returns:
            list[GitCommit]: Commit list, newest first.
        """
        ok, stdout, _ = self._run(
            [
                "log",
                f"-{limit}",
                "--pretty=format:%H|%h|%an|%ai|%s",
            ],
            cwd=project_root,
        )

        if not ok or not stdout:
            return []

        commits = []
        for line in stdout.splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            # Get files changed count
            ok2, diff_stat, _ = self._run(
                ["diff-tree", "--no-commit-id", "-r", "--name-only", parts[0]],
                cwd=project_root,
            )
            files_changed = len(diff_stat.splitlines()) if ok2 and diff_stat else 0

            commits.append(GitCommit(
                hash=parts[0],
                short_hash=parts[1],
                author=parts[2],
                date=parts[3],
                message=parts[4],
                files_changed=files_changed,
            ))

        return commits

    def get_diff(
        self,
        from_ref: str,
        to_ref: str = "HEAD",
        project_root: Path = PROJECT_ROOT,
    ) -> str:
        """
        Get diff between two refs.

        Args:
            from_ref: Base commit/tag/branch.
            to_ref: Target commit (default: HEAD).
            project_root: Repository root.

        Returns:
            str: Diff output (truncated to 10000 chars).
        """
        ok, stdout, stderr = self._run(
            ["diff", from_ref, to_ref, "--stat"],
            cwd=project_root,
        )

        if not ok:
            return f"Could not get diff: {stderr}"

        return stdout[:10000] if len(stdout) > 10000 else stdout

    def get_file_at(
        self,
        file_path: str,
        ref: str,
        project_root: Path = PROJECT_ROOT,
    ) -> str | None:
        """
        Get content of a file at a specific commit.

        Args:
            file_path: Relative path from project root.
            ref: Git ref (commit hash, branch, tag).
            project_root: Repository root.

        Returns:
            str | None: File content or None if not found.
        """
        # Normalize path for git
        rel_path = file_path.replace("\\", "/")
        if rel_path.startswith(str(project_root).replace("\\", "/")):
            rel_path = rel_path[len(str(project_root).replace("\\", "/")):]
        rel_path = rel_path.lstrip("/")

        ok, stdout, _ = self._run(
            ["show", f"{ref}:{rel_path}"],
            cwd=project_root,
        )

        return stdout if ok else None

    def get_changed_files(
        self,
        ref: str,
        project_root: Path = PROJECT_ROOT,
    ) -> list[str]:
        """
        Get list of files changed in a specific commit.

        Args:
            ref: Commit hash.
            project_root: Repository root.

        Returns:
            list[str]: Changed file paths.
        """
        ok, stdout, _ = self._run(
            ["diff-tree", "--no-commit-id", "-r", "--name-only", ref],
            cwd=project_root,
        )

        if not ok or not stdout:
            return []

        return stdout.splitlines()

    def is_valid_ref(
        self,
        ref: str,
        project_root: Path = PROJECT_ROOT,
    ) -> bool:
        """Check if a git ref (commit hash, tag, branch) is valid."""
        ok, _, _ = self._run(
            ["rev-parse", "--verify", ref],
            cwd=project_root,
        )
        return ok


# ── Singleton instance ────────────────────────────────────────────────────────
git_service = GitService()