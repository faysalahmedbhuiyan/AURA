"""
AURA Backend — Confidence Calculator.

Module: app.research_engine.confidence_calc
Purpose: Calculates overall confidence score for research results.

Confidence is based on:
    - Source count (more sources = higher confidence)
    - Source diversity (different domains = better)
    - Trust tier of sources
    - Corroboration (same facts in multiple sources)
    - Presence of trusted domains

AURA never auto-assigns full confidence (max 0.92).
User should verify any critical information independently.
"""

import logging
import re

from app.research_engine.source_ranker import RankedSource

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Calculates research confidence score.

    Always caps at 0.92 — no research is 100% certain.
    User should always verify critical information.

    Methods:
        calculate: Calculate confidence for ranked sources.
        get_confidence_label: Human-readable confidence label.
    """

    def calculate(
        self,
        ranked_sources: list[RankedSource],
        query: str,
    ) -> float:
        """
        Calculate overall confidence score.

        Args:
            ranked_sources: Ranked and scored sources.
            query: Original research query.

        Returns:
            float: Confidence score 0.0-0.92.
        """
        if not ranked_sources:
            return 0.1

        # Factor 1: Source count
        source_count = len(ranked_sources)
        if source_count >= 5:
            count_score = 0.9
        elif source_count >= 3:
            count_score = 0.75
        elif source_count >= 2:
            count_score = 0.60
        else:
            count_score = 0.35

        # Factor 2: Domain diversity
        domains = set(s.domain for s in ranked_sources)
        diversity_score = min(len(domains) / 5, 1.0)

        # Factor 3: Average trust score of top 3 sources
        top_3 = ranked_sources[:3]
        avg_trust = sum(s.trust_score for s in top_3) / len(top_3)

        # Factor 4: Trusted domain presence
        trusted_count = sum(1 for s in ranked_sources if s.is_trusted)
        trusted_bonus = min(trusted_count * 0.1, 0.3)

        # Factor 5: Content quality (sources with actual content)
        content_sources = sum(1 for s in ranked_sources if s.word_count > 100)
        content_score = min(content_sources / max(source_count, 1), 1.0)

        # Weighted combination
        confidence = (
            count_score * 0.25 +
            diversity_score * 0.20 +
            avg_trust * 0.30 +
            content_score * 0.15 +
            trusted_bonus * 0.10
        )

        # Cap at 0.92 — AURA never claims perfect certainty
        confidence = min(confidence, 0.92)
        confidence = max(confidence, 0.10)  # Minimum floor

        logger.info(
            "Confidence: %.2f (sources=%d, trusted=%d, diversity=%d)",
            confidence, source_count, trusted_count, len(domains),
        )
        return round(confidence, 2)

    def get_confidence_label(self, score: float) -> str:
        """
        Get human-readable confidence label.

        Args:
            score: Confidence score 0.0-1.0.

        Returns:
            str: Label with emoji.
        """
        if score >= 0.80:
            return "🟢 High Confidence"
        elif score >= 0.60:
            return "🟡 Medium Confidence"
        elif score >= 0.40:
            return "🟠 Low Confidence"
        else:
            return "🔴 Very Low Confidence — Verify manually"


# ── Singleton ─────────────────────────────────────────────────────────────────
confidence_calculator = ConfidenceCalculator()