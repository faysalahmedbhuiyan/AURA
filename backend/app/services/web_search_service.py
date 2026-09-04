"""
AURA Backend — Web Search Service.

Module: app.services.web_search_service
Purpose: Performs web searches (DuckDuckGo, no API key required) as the
         "Search" step of the Knowledge System pipeline:
         Search → Collect → Verify → Compare → Summarize → Confirm → Store.

This is also the search backend used directly by chat.py's deterministic
"search" intent — see app.research_engine.searcher.web_searcher for the
OTHER search implementation, which requires a local SearXNG instance
running via Docker. That's fine for a dev machine with Docker set up, but
the packaged desktop app never starts Docker/SearXNG for the end user, so
chat's web search was silently falling through to the LLM (which has no
real search tool and just improvised a plausible-looking but fake
"[Real-time Web Search Results]" answer) instead of showing a clear error
or, better, actually searching. This service has no external dependency
beyond internet access, so it's the one wired into chat now.

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
        search_news: Return top N NEWS-specific results for a query.
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

    def search_news(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Search NEWS specifically (recent articles, not general web pages).

        Args:
            query: News search query text.
            max_results: Maximum number of results to return.

        Returns:
            list[dict]: Each dict has 'title', 'url', 'snippet', 'date'.
                        Falls back to plain search() if news search fails
                        or returns nothing — never raises to caller.
        """
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.news(query, max_results=max_results))

            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", "").strip(),
                    "url": r.get("url", "").strip(),
                    "snippet": r.get("body", "").strip(),
                    "date": r.get("date", ""),
                })
            if results:
                logger.info("News search '%s' returned %d results", query, len(results))
                return results
            logger.info("News search '%s' returned nothing — falling back to general search", query)
            return self.search(query, max_results)

        except Exception as e:
            logger.warning("News search failed for '%s', falling back to general: %s", query, e)
            return self.search(query, max_results)


# ── Singleton instance ────────────────────────────────────────────────────────
web_search_service = WebSearchService()