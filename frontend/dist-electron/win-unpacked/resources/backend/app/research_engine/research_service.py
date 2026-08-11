"""
AURA Backend — Research Service.

Module: app.research_engine.research_service
Purpose: Main orchestrator for Phase 24 — Autonomous Research Engine.

         Complete pipeline:
         Search → Collect → Deduplicate → Rank → Confidence → Synthesize → Present

         NEVER auto-saves. Always returns candidate for user review.
         User must explicitly confirm before saving to memory.

         Integration:
         - Advanced Memory Engine (Phase 22) for storage after confirmation
         - Existing Knowledge System (Phase 6) endpoints preserved
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Complete research result ready for user review."""
    query: str
    title: str
    summary: str
    language: str
    confidence: float
    confidence_label: str
    total_sources: int
    successful_sources: int
    sources: list[dict]
    timestamp: str
    status: str = "pending_confirmation"  # Never auto-confirmed

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "title": self.title,
            "summary": self.summary,
            "language": self.language,
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "total_sources": self.total_sources,
            "successful_sources": self.successful_sources,
            "sources": self.sources,
            "timestamp": self.timestamp,
            "status": self.status,
            "warning": (
                "এই তথ্য এখনো confirm হয়নি। "
                "Confirm করলেই AURA এর memory তে save হবে।"
                if self.language == "bn" else
                "This research is NOT saved. "
                "Confirm to save to AURA's memory."
            ),
        }


class ResearchService:
    """
    Autonomous Research Engine — main orchestrator.

    Executes full research pipeline and returns candidate
    result for user confirmation.

    CRITICAL: Never stores automatically.
    All results marked status="pending_confirmation".

    Methods:
        research: Full research pipeline.
        quick_search: Fast search without content fetching.
    """

    async def research(
        self,
        query: str,
        language: str = "en",
        max_sources: int = 6,
        deep: bool = True,
    ) -> ResearchResult:
        """
        Execute full research pipeline.

        Args:
            query: Research topic/question.
            language: Response language (bn/en).
            max_sources: Maximum sources to fetch.
            deep: Use deep multi-query search.

        Returns:
            ResearchResult: Complete result (NEVER auto-saved).
        """
        from app.research_engine.confidence_calc import confidence_calculator
        from app.research_engine.content_fetcher import content_fetcher
        from app.research_engine.searcher import web_searcher
        from app.research_engine.source_ranker import source_ranker
        from app.research_engine.synthesizer import research_synthesizer

        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Starting research: '%s' (lang=%s)", query, language)

        # ── Step 1: Search ────────────────────────────────────────────────────
        if deep:
            search_results = await web_searcher.deep_search(
                query, max_results_per_query=5, language=language
            )
        else:
            search_results = web_searcher.search(
                query, max_results=8, language=language
            )

        if not search_results:
            return ResearchResult(
                query=query,
                title=f"No results found: {query}",
                summary=(
                    "ইন্টারনেটে এই বিষয়ে তথ্য পাওয়া যায়নি।"
                    if language == "bn" else
                    "No results found for this query."
                ),
                language=language,
                confidence=0.0,
                confidence_label="🔴 No Results",
                total_sources=0,
                successful_sources=0,
                sources=[],
                timestamp=timestamp,
            )

        # ── Step 2: Collect content ───────────────────────────────────────────
        urls_to_fetch = [r.url for r in search_results[:max_sources] if r.url]
        fetched = await content_fetcher.fetch_batch(urls_to_fetch)

        successful_fetches = [f for f in fetched if f.success]
        logger.info(
            "Fetched %d/%d URLs successfully",
            len(successful_fetches), len(urls_to_fetch),
        )

        # ── Step 3 & 4: Rank sources ──────────────────────────────────────────
        ranked = source_ranker.rank(search_results, fetched, query)

        # Keep only sources with content or good snippets
        usable = [
            r for r in ranked
            if r.word_count > 50 or len(r.snippet) > 100
        ]

        if not usable:
            usable = ranked[:5]  # Fallback to top search results

        # ── Step 5: Calculate confidence ──────────────────────────────────────
        confidence = confidence_calculator.calculate(usable, query)
        conf_label = confidence_calculator.get_confidence_label(confidence)

        # ── Step 6: Synthesize ────────────────────────────────────────────────
        summary = await research_synthesizer.synthesize(
            query=query,
            ranked_sources=usable,
            language=language,
            max_sources=5,
        )

        title = await research_synthesizer.create_title(query, summary, language)

        # ── Step 7: Build result ──────────────────────────────────────────────
        source_dicts = [s.to_dict() for s in usable[:8]]

        logger.info(
            "Research complete: confidence=%.2f, sources=%d",
            confidence, len(usable),
        )

        return ResearchResult(
            query=query,
            title=title,
            summary=summary,
            language=language,
            confidence=confidence,
            confidence_label=conf_label,
            total_sources=len(search_results),
            successful_sources=len(successful_fetches),
            sources=source_dicts,
            timestamp=timestamp,
        )

    async def quick_search(
        self,
        query: str,
        language: str = "en",
        max_results: int = 5,
    ) -> dict:
        """
        Quick search — no content fetching, just search results.

        Much faster than full research.
        Good for "what links exist about X" queries.

        Args:
            query: Search query.
            language: Language.
            max_results: Maximum results.

        Returns:
            dict: Quick search results with URLs and snippets.
        """
        from app.research_engine.searcher import web_searcher

        results = web_searcher.search(query, max_results, language)
        return {
            "query": query,
            "total": len(results),
            "results": [r.to_dict() for r in results],
            "note": "Quick search — no content fetched. Use /research for full analysis.",
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
research_service = ResearchService()