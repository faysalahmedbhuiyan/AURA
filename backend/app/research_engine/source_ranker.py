"""
AURA Backend — Source Ranker.

Module: app.research_engine.source_ranker
Purpose: Ranks research sources by credibility and relevance.
         Assigns trust scores to help AURA avoid misinformation.

Ranking factors:
    - Domain trust (Wikipedia, BBC, Reuters = high)
    - Content length (more detail = more credible)
    - Multiple corroboration (same fact from multiple sources = higher)
    - Recency signals (recent dates in content)
    - HTTPS (basic security check)
"""

import logging
import re
from dataclasses import dataclass

from app.research_engine.content_fetcher import FetchedContent
from app.research_engine.searcher import TRUSTED_DOMAINS, SearchResult

logger = logging.getLogger(__name__)

# Domain tier scoring
TIER_1_DOMAINS = {
    "wikipedia.org", "britannica.com", "nature.com",
    "who.int", "cdc.gov", "nih.gov", "gov.bd",
}
TIER_2_DOMAINS = {
    "bbc.com", "reuters.com", "ap.org", "theguardian.com",
    "python.org", "developer.mozilla.org", "stackoverflow.com",
    "prothomalo.com", "thedailystar.net",
}
TIER_3_DOMAINS = {
    "github.com", "medium.com", "towardsdatascience.com",
    "bdnews24.com", "jugantor.com",
}


@dataclass
class RankedSource:
    """A source with credibility score."""
    url: str
    title: str
    domain: str
    content: str
    snippet: str
    trust_score: float        # 0.0 - 1.0
    relevance_score: float    # 0.0 - 1.0
    combined_score: float     # Weighted combination
    is_trusted: bool
    word_count: int

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "snippet": self.snippet[:300] if self.snippet else "",
            "trust_score": round(self.trust_score, 2),
            "relevance_score": round(self.relevance_score, 2),
            "combined_score": round(self.combined_score, 2),
            "is_trusted": self.is_trusted,
            "word_count": self.word_count,
        }


class SourceRanker:
    """
    Ranks research sources by credibility and relevance.

    Methods:
        rank: Rank a list of sources for a query.
        get_domain_score: Get trust score for a domain.
    """

    def get_domain_score(self, domain: str) -> float:
        """
        Get base trust score for a domain.

        Args:
            domain: Domain name.

        Returns:
            float: Trust score 0.0-1.0.
        """
        if any(d in domain for d in TIER_1_DOMAINS):
            return 0.95
        if any(d in domain for d in TIER_2_DOMAINS):
            return 0.80
        if any(d in domain for d in TIER_3_DOMAINS):
            return 0.65
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return 0.85
        if domain.endswith(".org"):
            return 0.70
        return 0.50

    def _get_content_score(self, content: str, word_count: int) -> float:
        """Score based on content quality."""
        if word_count > 500:
            return 0.9
        if word_count > 200:
            return 0.7
        if word_count > 50:
            return 0.5
        return 0.2

    def _get_relevance_score(
        self,
        content: str,
        snippet: str,
        query: str,
    ) -> float:
        """Score based on keyword relevance."""
        query_words = set(query.lower().split())
        content_lower = (content + " " + snippet).lower()

        matches = sum(1 for word in query_words if word in content_lower)
        if not query_words:
            return 0.5

        ratio = matches / len(query_words)
        return min(ratio * 1.2, 1.0)

    def _has_https(self, url: str) -> bool:
        """Check if URL uses HTTPS."""
        return url.startswith("https://")

    def rank(
        self,
        search_results: list[SearchResult],
        fetched_contents: list[FetchedContent],
        query: str,
    ) -> list[RankedSource]:
        """
        Rank sources combining search results and fetched content.

        Args:
            search_results: Raw search results.
            fetched_contents: Fetched page contents.
            query: Original research query.

        Returns:
            list[RankedSource]: Ranked sources, best first.
        """
        # Build URL → content map
        content_map = {f.url: f for f in fetched_contents if f.success}

        ranked = []
        for result in search_results:
            fetched = content_map.get(result.url)

            content = fetched.content if fetched else ""
            word_count = fetched.word_count if fetched else 0
            title = fetched.title or result.title if fetched else result.title

            # Calculate scores
            domain_score = self.get_domain_score(result.domain)
            content_score = self._get_content_score(content, word_count)
            relevance_score = self._get_relevance_score(
                content, result.snippet, query
            )
            https_bonus = 0.05 if self._has_https(result.url) else 0.0

            trust_score = (domain_score * 0.5 + content_score * 0.3 + https_bonus)
            combined = (
                trust_score * 0.4 +
                relevance_score * 0.4 +
                content_score * 0.2
            )

            ranked.append(RankedSource(
                url=result.url,
                title=title,
                domain=result.domain,
                content=content,
                snippet=result.snippet,
                trust_score=min(trust_score, 1.0),
                relevance_score=min(relevance_score, 1.0),
                combined_score=min(combined, 1.0),
                is_trusted=result.is_trusted,
                word_count=word_count,
            ))

        # Sort by combined score
        ranked.sort(key=lambda s: s.combined_score, reverse=True)
        return ranked


# ── Singleton ─────────────────────────────────────────────────────────────────
source_ranker = SourceRanker()