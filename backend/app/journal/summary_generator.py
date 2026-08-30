"""
AURA Backend — Summary Generator.

Module: app.journal.summary_generator
Purpose: Builds a human-readable summary from a list of journal entries,
         grouped by category, for a given time window.
"""

import logging

from app.models.journal import JournalEntry

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "session_log": "Session Logs",
    "decision": "Architecture Decisions",
    "change": "Changes",
}


class SummaryGenerator:
    """
    Generates a summary report from journal entries.

    Methods:
        generate: Build a structured summary grouped by category.
    """

    def generate(self, entries: list[JournalEntry], days: int) -> dict:
        """
        Build a summary of journal entries.

        Args:
            entries: Entries to summarize (already filtered by date).
            days: The lookback window used, for display purposes.

        Returns:
            dict: {
                "period_days": int,
                "total_entries": int,
                "by_category": dict[str, int],
                "groups": dict[str, list[dict]],
                "files_touched": list[str],
            }
        """
        by_category: dict[str, int] = {}
        groups: dict[str, list[dict]] = {}
        files_touched: set[str] = set()

        for entry in entries:
            by_category[entry.category] = by_category.get(entry.category, 0) + 1
            groups.setdefault(entry.category, []).append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "tags": entry.tags,
                "related_phase": entry.related_phase,
                "created_at": entry.created_at,
            })

            for field in (entry.files_created, entry.files_modified, entry.files_deleted):
                if field:
                    files_touched.update(f.strip() for f in field.split(",") if f.strip())

        return {
            "period_days": days,
            "total_entries": len(entries),
            "by_category": by_category,
            "groups": groups,
            "files_touched": sorted(files_touched),
        }


# ── Singleton instance ────────────────────────────────────────────────────────
summary_generator = SummaryGenerator()