"""
AURA Backend — Web Searcher (SearXNG).

Module: app.research_engine.searcher
Purpose: Web search using local SearXNG instance at localhost:8080.
         SearXNG aggregates Google, Bing, DuckDuckGo simultaneously.
         No API key. No rate limits. Fast and private.

SearXNG must be running via Docker:
    cd D:\\AURA && docker-compose up -d
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

SEARXNG_BASE = "http://localhost:8080"
SEARXNG_SEARCH = f"{SEARXNG_BASE}/search"
TIMEOUT = 12.0

TRUSTED_DOMAINS = {
    "wikipedia.org", "britannica.com",
    "nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
    "bbc.com", "bbc.co.uk", "reuters.com", "ap.org",
    "apnews.com", "theguardian.com", "aljazeera.com",
    "cnn.com", "bloomberg.com", "dw.com", "france24.com",
    "gov.bd", "bangladesh.gov.bd", "bbs.gov.bd",
    "python.org", "docs.python.org", "developer.mozilla.org",
    "stackoverflow.com", "github.com",
    "who.int", "cdc.gov", "nih.gov",
    "prothomalo.com", "thedailystar.net", "bdnews24.com",
    "jugantor.com", "kalerkantho.com", "samakal.com",
}


@dataclass
class SearchResult:
    """A single search result from SearXNG."""
    title: str
    url: str
    snippet: str
    domain: str
    is_trusted: bool
    query_source: str
    score: float = 0.0

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
    Web searcher using local SearXNG instance.

    SearXNG runs at localhost:8080 via Docker.
    Aggregates multiple search engines simultaneously.
    Supports general search, news search, and deep multi-query search.

    Methods:
        search: General web search.
        search_news: News-specific search (time_range=day).
        deep_search: Multi-query search for research.
        is_available: Check if SearXNG is running.
    """

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL."""
        try:
            from urllib.parse import urlparse
            netloc = urlparse(url).netloc.lower()
            return netloc.replace("www.", "")
        except Exception:
            return ""

    def _is_trusted(self, domain: str) -> bool:
        """Check if domain is in trusted list."""
        return any(t in domain for t in TRUSTED_DOMAINS)

    def _parse_results(
        self,
        raw: list[dict],
        query: str,
    ) -> list[SearchResult]:
        """Parse SearXNG JSON results into SearchResult objects."""
        results = []
        for r in raw:
            url = r.get("url", "")
            if not url:
                continue
            domain = self._extract_domain(url)
            # SearXNG uses 'content' for snippets
            snippet = (
                r.get("content", "")
                or r.get("snippet", "")
                or r.get("description", "")
            )
            results.append(SearchResult(
                title=r.get("title", "No title"),
                url=url,
                snippet=snippet[:500] if snippet else "",
                domain=domain,
                is_trusted=self._is_trusted(domain),
                query_source=query,
                score=float(r.get("score", 0.0)),
            ))
        return results

    def _do_request(
        self,
        params: dict,
    ) -> list[dict]:
        """
        Make synchronous HTTP request to SearXNG.

        Args:
            params: Query parameters for SearXNG.

        Returns:
            list[dict]: Raw result list from SearXNG JSON response.
        """
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(SEARXNG_SEARCH, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    def search(
        self,
        query: str,
        max_results: int = 8,
        language: str = "en",
    ) -> list[SearchResult]:
        """
        General web search via SearXNG.

        Args:
            query: Search query string.
            max_results: Maximum results to return.
            language: 'en' or 'bn'.

        Returns:
            list[SearchResult]: Parsed and filtered results.
        """
        params = {
            "q": query,
            "format": "json",
            "language": "bn-BD" if language == "bn" else "en-US",
            "safesearch": "1",
            "categories": "general",
        }

        try:
            raw = self._do_request(params)
            results = self._parse_results(raw[:max_results], query)
            logger.info(
                "SearXNG search '%s': %d results",
                query[:60], len(results),
            )
            return results
        except httpx.ConnectError:
            logger.error(
                "SearXNG not reachable at %s — start Docker: "
                "cd D:\\AURA && docker-compose up -d",
                SEARXNG_BASE,
            )
            return []
        except httpx.TimeoutException:
            logger.error("SearXNG timeout for: %s", query[:60])
            return []
        except Exception as e:
            logger.error("SearXNG search error: %s", e)
            return []

    def search_news(
        self,
        query: str,
        max_results: int = 8,
        language: str = "en",
    ) -> list[SearchResult]:
        """
        News search via SearXNG with time_range=day.

        Searches only today's news articles.
        Falls back to general search if news search fails.

        Args:
            query: News search query.
            max_results: Maximum results.
            language: 'en' or 'bn'.

        Returns:
            list[SearchResult]: Today's news results.
        """
        params = {
            "q": query,
            "format": "json",
            "language": "bn-BD" if language == "bn" else "en-US",
            "safesearch": "1",
            "categories": "news",
            "time_range": "day",
        }

        try:
            raw = self._do_request(params)
            results = self._parse_results(raw[:max_results], query)

            if not results:
                # Fallback: general search without time_range
                logger.info("No news results, falling back to general search")
                return self.search(query, max_results, language)

            logger.info(
                "SearXNG news '%s': %d results",
                query[:60], len(results),
            )
            return results

        except httpx.ConnectError:
            logger.error("SearXNG not reachable for news search")
            return []
        except Exception as e:
            logger.warning("News search failed, trying general: %s", e)
            return self.search(query, max_results, language)

    async def deep_search(
        self,
        main_query: str,
        max_results_per_query: int = 6,
        language: str = "en",
    ) -> list[SearchResult]:
        """
        Deep research search with multiple sub-queries.

        Generates sub-queries, searches each one, deduplicates.
        Used by the Research Engine for comprehensive coverage.

        Args:
            main_query: Primary research topic.
            max_results_per_query: Results per sub-query.
            language: Search language.

        Returns:
            list[SearchResult]: Deduplicated combined results.
        """
        sub_queries = self._generate_sub_queries(main_query, language)
        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in sub_queries:
            try:
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda q=query: self.search(
                        q, max_results_per_query, language
                    ),
                )
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)
            except Exception as e:
                logger.warning("Sub-query '%s' failed: %s", query[:40], e)

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
        """Generate 2-3 sub-queries for comprehensive research."""
        queries = [main_query]

        has_bangla = any('\u0980' <= c <= '\u09FF' for c in main_query)
        if has_bangla:
            queries.append(f"{main_query} বাংলাদেশ সর্বশেষ")
        else:
            queries.append(f"{main_query} 2025 latest")

        return queries[:3]

    async def is_available(self) -> bool:
        """
        Check if SearXNG is running and reachable.

        Returns:
            bool: True if SearXNG responds successfully.
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    SEARXNG_SEARCH,
                    params={"q": "test", "format": "json"},
                )
                return response.status_code == 200
        except Exception:
            return False


# ── Singleton ─────────────────────────────────────────────────────────────────
web_searcher = WebSearcher()