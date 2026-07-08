"""
AURA Backend — Review Service.

Module: app.review.review_service
Purpose: Orchestrates the full Self Review Engine pipeline:
         scan directory → analyze each file → compute debt score →
         generate suggestions. READ-ONLY end to end.
"""

import logging
from pathlib import Path

from app.review.code_analyzer import CodeIssue, code_analyzer
from app.review.debt_detector import debt_detector
from app.review.suggestion_engine import suggestion_engine

logger = logging.getLogger(__name__)

# Directories to skip during scan (never analyze dependencies/build output)
SKIP_DIRS = {
    "venv", "__pycache__", "node_modules", ".git", "dist", "build",
    ".vite", ".vite-temp", "chroma",
}


class ReviewService:
    """
    Orchestrates codebase review.

    Methods:
        review_path: Scan a directory (or single file) and produce
                     a full report: issues, debt score, suggestions.
    """

    def review_path(self, target: Path, max_files: int = 200) -> dict:
        """
        Run the full review pipeline on a directory or file.

        Args:
            target: Path to a .py file or a directory to scan recursively.
            max_files: Safety cap on number of files analyzed in one run
                       (RAM/time awareness for an 8GB machine).

        Returns:
            dict: {
                "target": str,
                "files_analyzed": int,
                "debt_summary": dict,
                "suggestions": list[dict],
                "issues": list[dict],   (capped for payload size)
            }
        """
        py_files = self._collect_py_files(target, max_files)

        issues_by_file: dict[str, list[CodeIssue]] = {}
        for file_path in py_files:
            issues = code_analyzer.analyze_file(file_path)
            issues_by_file[str(file_path)] = issues

        debt_summary = debt_detector.score_project(issues_by_file)
        suggestions = suggestion_engine.generate(issues_by_file)

        all_issues = [
            issue.to_dict()
            for issues in issues_by_file.values()
            for issue in issues
        ]
        # Cap raw issue list in the response — worst_files/suggestions
        # already summarize; full list is for drill-down, not a wall of text.
        all_issues = all_issues[:300]

        return {
            "target": str(target),
            "files_analyzed": len(py_files),
            "debt_summary": debt_summary,
            "suggestions": [s.to_dict() for s in suggestions],
            "issues": all_issues,
        }

    def _collect_py_files(self, target: Path, max_files: int) -> list[Path]:
        """Collect .py files under target, skipping noise directories."""
        if target.is_file() and target.suffix == ".py":
            return [target]

        if not target.is_dir():
            return []

        collected: list[Path] = []
        for path in target.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            collected.append(path)
            if len(collected) >= max_files:
                logger.warning(
                    "Review capped at %d files — some files skipped.",
                    max_files,
                )
                break

        return collected


# ── Singleton instance ────────────────────────────────────────────────────────
review_service = ReviewService()