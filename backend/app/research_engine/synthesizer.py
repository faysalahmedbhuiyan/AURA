"""
AURA Backend — Research Synthesizer.

Module: app.research_engine.synthesizer
Purpose: Synthesizes research results into a coherent summary
         using Ollama LLM with multi-source awareness.

Key principles:
    - Only use provided source content (no hallucination)
    - Flag disagreements between sources explicitly
    - Prefer facts corroborated by multiple sources
    - Always mention source count
    - Respond in requested language
    - Keep synthesis concise but complete
"""

import logging

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are AURA's research synthesizer.

Your job: Create accurate, concise research summaries from provided source excerpts.

STRICT RULES:
1. ONLY use information from the provided sources — never add outside knowledge
2. If sources disagree, explicitly say "Sources disagree about: [topic]"
3. Prefer facts that appear in MULTIPLE sources
4. Always be specific with numbers, dates, names when sources provide them
5. Keep the summary concise but complete
6. Do NOT add disclaimers or meta-commentary
7. Do NOT say "Based on the sources" — just state the facts directly

Format:
- Start with the most important fact
- Use short paragraphs
- Mention source count naturally
- Flag any contradictions"""


class ResearchSynthesizer:
    """
    LLM-powered research synthesizer.

    Combines content from multiple sources into a coherent,
    accurate summary. Detects and flags contradictions.

    Methods:
        synthesize: Create summary from ranked sources.
        create_title: Generate research title.
    """

    async def synthesize(
        self,
        query: str,
        ranked_sources: list,
        language: str = "en",
        max_sources: int = 5,
    ) -> str:
        """
        Synthesize multiple sources into a coherent summary.

        Args:
            query: Original research query.
            ranked_sources: Ranked sources with content.
            language: Output language (bn/en).
            max_sources: Max sources to use in synthesis.

        Returns:
            str: Synthesized research summary.
        """
        from app.services.ollama_service import ollama_service

        # Build source excerpts
        source_excerpts = []
        for i, source in enumerate(ranked_sources[:max_sources], 1):
            content = source.content
            if len(content) > 800:
                content = content[:800] + "..."

            if content:
                source_excerpts.append(
                    f"[Source {i}: {source.domain}]\n{content}"
                )

        if not source_excerpts:
            return (
                "গবেষণায় যথেষ্ট তথ্য পাওয়া যায়নি।"
                if language == "bn"
                else "Insufficient content found from sources."
            )

        sources_text = "\n\n---\n\n".join(source_excerpts)

        # Language instruction
        if language == "bn":
            lang_inst = "বাংলায় উত্তর দাও।"
        else:
            lang_inst = "Answer in English."

        prompt = (
            f"Research Query: {query}\n\n"
            f"Language: {lang_inst}\n\n"
            f"Sources ({len(source_excerpts)} total):\n\n"
            f"{sources_text}\n\n"
            f"Synthesize the above sources into a clear, accurate summary "
            f"about: {query}"
        )

        try:
            summary = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            )
            return summary.strip()

        except Exception as e:
            logger.exception("Synthesis failed: %s", e)
            # Fallback: concatenate snippets
            snippets = [
                s.snippet for s in ranked_sources[:3] if s.snippet
            ]
            return " ".join(snippets)[:1000] if snippets else "Synthesis failed."

    async def create_title(
        self,
        query: str,
        summary: str,
        language: str = "en",
    ) -> str:
        """
        Generate a concise title for the research result.

        Args:
            query: Original query.
            summary: Generated summary.
            language: Title language.

        Returns:
            str: Short descriptive title.
        """
        # Simple title extraction — first meaningful sentence
        try:
            sentences = summary.split("।" if language == "bn" else ".")
            if sentences:
                title = sentences[0].strip()
                if len(title) > 100:
                    title = title[:100] + "..."
                return title
        except Exception:
            pass

        return query[:100]


# ── Singleton ─────────────────────────────────────────────────────────────────
research_synthesizer = ResearchSynthesizer()