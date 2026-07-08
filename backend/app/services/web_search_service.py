"""
AURA Backend — Web Search Service.

Module: app.services.web_search_service
Purpose: Performs web searches (DuckDuckGo, no API key required) as the
         "Search" step of the Knowledge System pipeline:
         Search → Collect → Verify → Compare → Summarize → Confirm → Store.

This service NEVER saves anything. It only returns candidate search
results for the research pipeline to collect and verify.
"""

import logging

from ddgs import DDGS

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Thin wrapper around DuckDuckGo search (no API key needed).

    Methods:
        search: Return top N search results for a query.
    """

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Search the web for a query.

        Args:
            query: Search query text.
            max_results: Maximum number of results to return.

        Returns:
            list[dict]: Each dict has 'title', 'url', 'snippet'.
                         Empty list on failure (never raises to caller).
        """
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", "").strip(),
                    "url": r.get("href", "").strip(),
                    "snippet": r.get("body", "").strip(),
                })
            logger.info("Web search '%s' returned %d results", query, len(results))
            return results

        except Exception as e:
            logger.warning("Web search failed for '%s': %s", query, e)
            return []


# ── Singleton instance ────────────────────────────────────────────────────────
web_search_service = WebSearchService()