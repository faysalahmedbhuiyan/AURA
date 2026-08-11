"""
AURA Backend — Practice Suggester.

Module: app.mentor.practice_suggester
Purpose: Reuses Phase 8's code_analyzer to find issues in a file, then
         reframes them as EDUCATIONAL suggestions — explaining why the
         pattern is a concern and how to improve it, rather than just
         flagging it. READ-ONLY.
"""

import logging
from pathlib import Path

from app.review.code_analyzer import code_analyzer

logger = logging.getLogger(__name__)

TEACHING_CONTENT = {
    "long_function": {
        "why": (
            "Long functions try to do too many things at once, which "
            "makes them harder to read, test, and reuse. Each function "
            "should ideally do one clear thing."
        ),
        "how": (
            "Look for logical sections inside the function (e.g. "
            "'validate input', 'compute result', 'format output') and "
            "extract each into its own smaller function with a clear name."
        ),
    },
    "missing_docstring": {
        "why": (
            "Without a docstring, other developers (or you, in six "
            "months) have to read the whole function body just to "
            "understand what it's for."
        ),
        "how": (
            "Add a short docstring explaining what the function does, "
            "its parameters, and what it returns."
        ),
    },
    "too_many_params": {
        "why": (
            "Functions with many parameters are error-prone to call "
            "correctly and hard to remember the order of."
        ),
        "how": (
            "Group related parameters into a single object, dataclass, "
            "or Pydantic model and pass that instead."
        ),
    },
    "deep_nesting": {
        "why": (
            "Deeply nested if/for/while blocks are hard to follow — the "
            "reader has to hold many conditions in their head at once."
        ),
        "how": (
            "Use early returns (`if not condition: return`) to handle "
            "edge cases first, flattening the rest of the function."
        ),
    },
    "unused_import": {
        "why": (
            "Unused imports add noise and can mislead readers about "
            "what the file actually depends on."
        ),
        "how": "Remove the import once you've confirmed it's truly unused.",
    },
    "file_length": {
        "why": (
            "Very long files usually mean the module is handling more "
            "than one responsibility."
        ),
        "how": (
            "Split the file along natural boundaries — e.g. separate "
            "files per class, or group related functions into their "
            "own module."
        ),
    },
    "todo_comment": {
        "why": "Unresolved TODOs represent known, unaddressed work.",
        "how": (
            "Either resolve the TODO now, or turn it into a tracked "
            "task (e.g. a Journal entry) so it isn't forgotten."
        ),
    },
}


class PracticeSuggester:
    """
    Generates educational best-practice suggestions for a file.

    Methods:
        suggest: Analyze a file and return teaching-framed suggestions.
    """

    def suggest(self, path: Path) -> dict:
        """
        Analyze a file and produce educational suggestions.

        Args:
            path: Path to a .py file.

        Returns:
            dict: {"file": str, "suggestions": list[dict]}
        """
        issues = code_analyzer.analyze_file(path)

        by_category: dict[str, list] = {}
        for issue in issues:
            by_category.setdefault(issue.category, []).append(issue)

        suggestions = []
        for category, category_issues in by_category.items():
            teaching = TEACHING_CONTENT.get(category)
            if not teaching:
                continue
            suggestions.append({
                "category": category,
                "occurrences": len(category_issues),
                "why_it_matters": teaching["why"],
                "how_to_improve": teaching["how"],
                "examples": [
                    {"line": i.line, "message": i.message}
                    for i in category_issues[:5]
                ],
            })

        return {"file": str(path), "suggestions": suggestions}


# ── Singleton instance ────────────────────────────────────────────────────────
practice_suggester = PracticeSuggester()