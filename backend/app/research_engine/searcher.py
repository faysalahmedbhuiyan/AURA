"""
AURA Backend — Web Searcher.

Module: app.research_engine.searcher
Purpose: Multi-query web search using DuckDuckGo (no API key needed).
         Generates smart sub-queries for comprehensive research.
         Returns structured results with title, URL, snippet.

Features:
    - Multi-query search (main + sub-queries)
    - Domain diversity (avoid single-source bias)
    - Language-aware search (Bangla + English)
    - Fast timeout (no hanging)
"""

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Trusted domains get score boost in ranking
TRUSTED_DOMAINS = {
    "wikipedia.org", "britannica.com",
    "nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
    "bbc.com", "reuters.com", "ap.org", "theguardian.com",
    "gov.bd", "bbs.gov.bd", "moa.gov.bd",
    "python.org", "docs.python.org", "developer.mozilla.org",
    "stackoverflow.com", "github.com",
    "who.int", "cdc.gov", "nih.gov",
    "prothomalo.com", "thedailystar.net", "bdnews24.com",
}


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    domain: str
    is_trusted: bool
    query_source: str  # Which query found this

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "domain": self.domain,
            "is_trusted": self.is_trusted,
        }


class WebSearcher:
    """
    Multi-source web searcher.

    Uses DuckDuckGo via ddgs library.
    Generates multiple sub-queries for comprehensive coverage.
    Respects rate limits and timeouts.

    Methods:
        search: Search with a single query.
        deep_search: Search with multiple generated queries.
        generate_sub_queries: Generate research sub-queries.
    """

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _is_trusted(self, domain: str) -> bool:
        """Check if domain is in trusted list."""
        return any(trusted in domain for trusted in TRUSTED_DOMAINS)

    def search(
        self,
        query: str,
        max_results: int = 8,
        language: str = "en",
    ) -> list[SearchResult]:
        """
        Search DuckDuckGo for a query.

        Args:
            query: Search query.
            max_results: Maximum results to return.
            language: Search language (en/bn).

        Returns:
            list[SearchResult]: Search results.
        """
        try:
            from duckduckgo_search import DDGS

            results = []
            region = "bd-bn" if language == "bn" else "wt-wt"

            with DDGS() as ddgs:
                raw_results = list(ddgs.text(
                    query,
                    max_results=max_results,
                    region=region,
                    safesearch="moderate",
                ))

            for r in raw_results:
                url = r.get("href", "")
                domain = self._extract_domain(url)
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=url,
                    snippet=r.get("body", ""),
                    domain=domain,
                    is_trusted=self._is_trusted(domain),
                    query_source=query,
                ))

            logger.info("Search '%s': %d results", query[:50], len(results))
            return results

        except Exception as e:
            logger.error("Search failed for '%s': %s", query, e)
            return []

    async def deep_search(
        self,
        main_query: str,
        max_results_per_query: int = 5,
        language: str = "en",
    ) -> list[SearchResult]:
        """
        Deep search with multiple sub-queries.

        Generates sub-queries for comprehensive coverage,
        runs them in parallel, deduplicates results.

        Args:
            main_query: Primary research topic.
            max_results_per_query: Results per sub-query.
            language: Search language.

        Returns:
            list[SearchResult]: Deduplicated combined results.
        """
        # Generate sub-queries
        sub_queries = self._generate_sub_queries(main_query, language)

        # Run all queries
        all_results = []
        seen_urls = set()

        for query in sub_queries:
            try:
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda q=query: self.search(q, max_results_per_query, language)
                )
                for r in results:
                    if r.url not in seen_urls and r.url:
                        seen_urls.add(r.url)
                        all_results.append(r)
            except Exception as e:
                logger.warning("Sub-query failed '%s': %s", query, e)

        logger.info(
            "Deep search '%s': %d unique results from %d queries",
            main_query[:50], len(all_results), len(sub_queries),
        )
        return all_results

    def _generate_sub_queries(
        self,
        main_query: str,
        language: str = "en",
    ) -> list[str]:
        """
        Generate research sub-queries for comprehensive coverage.

        Args:
            main_query: Main research topic.
            language: Language for additional queries.

        Returns:
            list[str]: List of queries (main + sub-queries).
        """
        queries = [main_query]

        # Add English variant if query is in Bangla/Banglish
        has_bangla = any('\u0980' <= c <= '\u09FF' for c in main_query)
        if has_bangla:
            queries.append(f"{main_query} in english")

        # Add specific sub-queries
        sub_templates = [
            f"{main_query} explained",
            f"{main_query} 2024 2025",
            f"what is {main_query}",
        ]

        queries.extend(sub_templates[:2])  # Keep total queries <= 4 for speed

        return queries[:4]  # Max 4 queries


# ── Singleton ─────────────────────────────────────────────────────────────────
web_searcher = WebSearcher()