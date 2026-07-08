"""
AURA Backend — Technical Debt Detector.

Module: app.review.debt_detector
Purpose: Aggregates CodeIssue lists into a single technical debt score
         per file and per project. Score is a heuristic, not a precise
         metric — intended to help prioritize review, not to judge.
"""

import logging

from app.review.code_analyzer import CodeIssue

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {"low": 1, "medium": 3, "high": 8}


class DebtDetector:
    """
    Computes technical debt scores from CodeIssue lists.

    Methods:
        score_file: Debt score for a single file's issues.
        score_project: Aggregate debt score + breakdown for all files.
    """

    def score_file(self, issues: list[CodeIssue]) -> int:
        """
        Compute a 0-100 debt score for one file's issues.

        Higher score = more debt. Uncapped raw score is clamped to 100
        so a single very messy file doesn't skew comparisons.

        Args:
            issues: Issues detected in one file.

        Returns:
            int: Debt score from 0 (clean) to 100 (heavy debt).
        """
        raw = sum(SEVERITY_WEIGHTS.get(i.severity, 1) for i in issues)
        return min(raw, 100)

    def score_project(
        self, issues_by_file: dict[str, list[CodeIssue]]
    ) -> dict:
        """
        Compute project-wide debt summary.

        Args:
            issues_by_file: Mapping of file path to its issues.

        Returns:
            dict: {
                "total_score": int,
                "average_score": float,
                "files_analyzed": int,
                "total_issues": int,
                "worst_files": list[{"file", "score", "issue_count"}],
                "by_category": dict[str, int],
                "by_severity": dict[str, int],
            }
        """
        file_scores = []
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        total_issues = 0

        for file_path, issues in issues_by_file.items():
            score = self.score_file(issues)
            file_scores.append({
                "file": file_path,
                "score": score,
                "issue_count": len(issues),
            })
            total_issues += len(issues)
            for issue in issues:
                by_category[issue.category] = by_category.get(issue.category, 0) + 1
                by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1

        files_analyzed = len(issues_by_file)
        total_score = sum(f["score"] for f in file_scores)
        average_score = round(total_score / files_analyzed, 1) if files_analyzed else 0.0

        worst_files = sorted(file_scores, key=lambda f: f["score"], reverse=True)[:10]

        return {
            "total_score": total_score,
            "average_score": average_score,
            "files_analyzed": files_analyzed,
            "total_issues": total_issues,
            "worst_files": worst_files,
            "by_category": by_category,
            "by_severity": by_severity,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
debt_detector = DebtDetector()