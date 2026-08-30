"""
AURA Backend — Suggestion Engine.

Module: app.review.suggestion_engine
Purpose: Converts raw CodeIssue lists into prioritized, human-readable
         improvement suggestions. NEVER applies changes — suggestions
         only, per Constitution (Phase 8 is analysis-only; applying
         changes is Phase 10's responsibility, with approval gates).
"""

import logging

from app.review.code_analyzer import CodeIssue

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "long_function": "Long Function",
    "missing_docstring": "Missing Docstring",
    "too_many_params": "Too Many Parameters",
    "deep_nesting": "Deep Nesting",
    "unused_import": "Unused Import",
    "file_length": "File Too Long",
    "todo_comment": "Unresolved TODO/FIXME",
    "syntax_error": "Syntax Error",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class Suggestion:
    """A single actionable improvement suggestion."""

    def __init__(
        self,
        title: str,
        description: str,
        affected_files: list[str],
        priority: str,
        issue_count: int,
    ) -> None:
        self.title = title
        self.description = description
        self.affected_files = affected_files
        self.priority = priority
        self.issue_count = issue_count

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "affected_files": self.affected_files,
            "priority": self.priority,
            "issue_count": self.issue_count,
        }


class SuggestionEngine:
    """
    Generates prioritized suggestions from a project-wide issue set.

    Methods:
        generate: Build a sorted list of Suggestion objects.
    """

    def generate(
        self, issues_by_file: dict[str, list[CodeIssue]]
    ) -> list[Suggestion]:
        """
        Group issues by category and produce one suggestion per category.

        Args:
            issues_by_file: Mapping of file path to its issues.

        Returns:
            list[Suggestion]: Sorted by priority (high first), then by
                               how many files/issues are affected.
        """
        grouped: dict[str, list[tuple[str, CodeIssue]]] = {}

        for file_path, issues in issues_by_file.items():
            for issue in issues:
                grouped.setdefault(issue.category, []).append((file_path, issue))

        suggestions: list[Suggestion] = []
        for category, entries in grouped.items():
            affected_files = sorted({f for f, _ in entries})
            severities = [i.severity for _, i in entries]
            priority = min(severities, key=lambda s: PRIORITY_ORDER.get(s, 2))

            label = CATEGORY_LABELS.get(category, category)
            suggestions.append(Suggestion(
                title=f"{label} ({len(entries)} occurrence(s))",
                description=self._describe(category, len(entries), len(affected_files)),
                affected_files=affected_files,
                priority=priority,
                issue_count=len(entries),
            ))

        suggestions.sort(
            key=lambda s: (PRIORITY_ORDER.get(s.priority, 2), -s.issue_count)
        )
        return suggestions

    def _describe(self, category: str, count: int, file_count: int) -> str:
        """Build a short human-readable description for a category group."""
        base = {
            "long_function": "Some functions are longer than recommended, "
                              "which can hurt readability and testability.",
            "missing_docstring": "Several functions/classes lack docstrings, "
                                  "making the codebase harder to navigate.",
            "too_many_params": "Some functions take many parameters — "
                                "a config object or dataclass could simplify calls.",
            "deep_nesting": "Some functions have deeply nested logic — "
                             "early returns or extraction could flatten them.",
            "unused_import": "Unused imports were detected — safe to remove "
                              "after manual confirmation.",
            "file_length": "Some files are quite long — consider splitting "
                            "into focused modules.",
            "todo_comment": "Unresolved TODO/FIXME markers found in the code.",
            "syntax_error": "One or more files could not be parsed — "
                             "these need immediate attention.",
        }.get(category, "Issues detected in this category.")

        return f"{base} Found in {count} place(s) across {file_count} file(s)."


# ── Singleton instance ────────────────────────────────────────────────────────
suggestion_engine = SuggestionEngine()