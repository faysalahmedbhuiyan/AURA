"""
AURA Backend — Research Service.

Module: app.services.research_service
Purpose: Orchestrates the full Knowledge System pipeline:
         Search → Collect → Verify → Compare → Summarize.
         Produces a candidate knowledge entry for user review.
         NEVER saves anything — confirm-before-save is enforced
         by the existing knowledge_repository / memory routes.
"""

import logging

from app.services.content_fetch_service import content_fetch_service
from app.services.ollama_service import ollama_service  # TODO: VERIFY interface
from app.services.web_search_service import web_search_service

logger = logging.getLogger(__name__)

# Domains considered more reliable — nudges confidence score up.
TRUSTED_DOMAIN_HINTS = (
    ".gov", ".edu", "wikipedia.org", "britannica.com",
    "who.int", "nature.com", "reuters.com", "bbc.com",
)


class ResearchService:
    """
    Runs the Search → Collect → Verify → Summarize pipeline.

    Methods:
        research: Full pipeline, returns a candidate dict ready for
                  the /knowledge/research endpoint response.
    """

    async def research(
        self,
        query: str,
        language: str = "en",
        max_sources: int = 4,
    ) -> dict:
        """
        Run the full research pipeline for a query.

        Args:
            query: What the user wants AURA to learn about.
            language: Response language code.
            max_sources: Max number of sources to search & collect.

        Returns:
            dict: {
                "title": str,
                "summary": str,
                "sources": list[{"url", "name", "snippet"}],
                "suggested_confidence": float,
                "language": str,
            }
        """
        # ── Step 1: Search ──────────────────────────────────────
        search_results = web_search_service.search(query, max_results=max_sources)
        if not search_results:
            return self._empty_candidate(query, language)

        # ── Step 2: Collect ─────────────────────────────────────
        collected = []
        for result in search_results:
            content = await content_fetch_service.fetch(result["url"])
            if content:
                collected.append({**result, "content": content})

        if not collected:
            # Fall back to snippets only if full-page fetch failed everywhere
            collected = [{**r, "content": r["snippet"]} for r in search_results if r["snippet"]]

        if not collected:
            return self._empty_candidate(query, language)

        # ── Step 3 & 4: Verify / Compare + Step 5: Summarize ────
        summary, title = await self._summarize(query, collected, language)

        # ── Confidence scoring ───────────────────────────────────
        confidence = self._estimate_confidence(collected)

        sources = [
            {"url": c["url"], "name": self._domain_name(c["url"]), "snippet": c["snippet"]}
            for c in collected
        ]

        return {
            "title": title,
            "summary": summary,
            "sources": sources,
            "suggested_confidence": confidence,
            "language": language,
        }

    async def _summarize(
        self,
        query: str,
        collected: list[dict],
        language: str,
    ) -> tuple[str, str]:
        """
        Ask the LLM to verify/compare sources and produce one summary.

        Instructs the model to only include facts that multiple
        sources agree on, and to note explicitly if sources conflict.

        Returns:
            tuple[str, str]: (summary_text, suggested_title)
        """
        sources_block = "\n\n".join(
            f"SOURCE {i+1} ({c['url']}):\n{c['content'][:1500]}"
            for i, c in enumerate(collected)
        )

        prompt = (
            f"You are AURA's research assistant. A user wants to learn about: "
            f"\"{query}\".\n\n"
            f"Below are excerpts from {len(collected)} independent web sources.\n\n"
            f"{sources_block}\n\n"
            "Instructions:\n"
            "1. Write a concise, factual summary (150-250 words) using ONLY "
            "information that appears in these sources.\n"
            "2. Prefer facts that multiple sources agree on. If sources "
            "conflict on a fact, mention the disagreement explicitly rather "
            "than picking one side.\n"
            "3. Do not add outside knowledge not present in the sources.\n"
            f"4. Write the summary in language code '{language}'.\n"
            "5. On the first line, output a short title (max 10 words) "
            "prefixed with 'TITLE:'. Then a blank line, then the summary.\n"
        )

        research_system_prompt = (
            "You are a factual research-summarization assistant. "
            "You are NOT AURA and you are NOT talking to a specific person. "
            "You only summarize the source text you are given. "
            "You never ask for confirmation, never offer to remember anything, "
            "and never add a conversational greeting or sign-off — output ONLY "
            "the TITLE line and the summary as instructed."
        )
        try:
            raw_response = await ollama_service.chat(
                message=prompt,
                system_prompt=research_system_prompt,
            )
            text = raw_response.strip()
            logger.debug("Raw research LLM output: %r", text)
        except Exception as e:
            logger.error("LLM summarization failed: %s", e)
            # Degrade gracefully — return raw concatenation so the pipeline
            # still produces a reviewable candidate instead of failing.
            text = f"TITLE: {query}\n\n" + " ".join(c["content"][:300] for c in collected)

        title = query
        summary = text
        if text.upper().startswith("TITLE:"):
            first_line, _, rest = text.partition("\n")
            title = first_line.split(":", 1)[1].strip() or query
            rest = rest.strip()
            # Guard: if the model only produced a title with nothing after it,
            # keep the full raw text as the summary instead of returning empty.
            summary = rest if rest else text

        if not summary.strip():
            summary = text or f"No summary could be generated for '{query}'."

        return summary, title

    def _estimate_confidence(self, collected: list[dict]) -> float:
        """
        Heuristic confidence score: base + per-source corroboration
        + trusted-domain bonus. Always capped to [0.1, 0.9] — never
        auto-assigns full 1.0 trust, since a human must still confirm.
        """
        base = 0.4
        per_source_bonus = min(len(collected) * 0.1, 0.3)
        trusted_bonus = 0.1 if any(
            hint in c["url"] for c in collected for hint in TRUSTED_DOMAIN_HINTS
        ) else 0.0

        confidence = base + per_source_bonus + trusted_bonus
        return round(min(max(confidence, 0.1), 0.9), 2)

    def _domain_name(self, url: str) -> str:
        """Extract a human-readable source name from a URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return url

    def _empty_candidate(self, query: str, language: str) -> dict:
        """Fallback candidate when search/collection completely fails."""
        return {
            "title": query,
            "summary": (
                "No web results could be retrieved for this query. "
                "Please check your internet connection or try a different query."
            ),
            "sources": [],
            "suggested_confidence": 0.0,
            "language": language,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
research_service = ResearchService()