"""
AURA Backend — Reasoning Service (Tier 6, A2-A4).

Module: app.services.reasoning_service
Purpose:
    A2: Critical Thinking Engine  — analyze a claim/topic with evidence
    A3: Problem Solving Framework — break a problem down, weigh options
    A4: Knowledge Synthesis       — combine multiple known facts into
                                    one coherent, connected answer

Honesty note (same as A1/coding work): qwen2.5:3b does NOT reason like
a human. What this module does is impose STRUCTURE on the LLM calls —
explicit steps a small model can follow reliably (restate -> gather ->
weigh -> conclude) — which measurably improves output quality over a
single unstructured call, without pretending it's genuine cognition.
All three reuse the EXISTING Tier 2 knowledge base (intelligence_service
.search) so answers are grounded in what AURA has actually been taught,
not just the model's raw (often wrong, for a 3B model) prior knowledge.
"""

import logging

logger = logging.getLogger(__name__)


class ReasoningService:
    """Structured multi-step reasoning over AURA's existing knowledge base."""

    async def critical_think(self, topic: str, language: str = "en") -> dict:
        """
        A2: Analyze a claim/topic — assumptions, evidence for/against,
        balanced conclusion. Grounded in the knowledge base where
        relevant content exists.
        """
        from app.intelligence.intelligence_service import intelligence_service
        from app.services.ollama_service import ollama_service

        try:
            search_results = await intelligence_service.search(
                query=topic, knowledge_type=None, category=None, n_results=5,
            )
        except Exception as e:
            logger.warning("Knowledge search failed for critical_think: %s", e)
            search_results = []

        context = self._format_evidence(search_results)

        prompt = (
            f"Topic to analyze critically: {topic}\n\n"
            + (
                f"Possibly relevant known information (ONLY use pieces that are "
                f"genuinely about this topic — ignore anything unrelated, even "
                f"if it was retrieved):\n{context}\n\n"
                if context else ""
            )
            + "Provide a critical analysis with exactly these sections:\n"
            "1. KEY CLAIM: restate the core claim/question in one sentence\n"
            "2. ASSUMPTIONS: what is being assumed (2-4 bullets)\n"
            "3. EVIDENCE FOR: supporting points (use the known information above if relevant)\n"
            "4. EVIDENCE AGAINST / LIMITATIONS: counterpoints or gaps\n"
            "5. BALANCED CONCLUSION: a measured, non-absolute takeaway\n"
            "Be concise — a few bullets per section, not essays."
        )

        answer = await ollama_service.chat(
            message=prompt, history=[],
            system_prompt="You are a careful, structured critical-thinking assistant. Follow the requested section format exactly.",
        )

        return {"success": True, "topic": topic, "analysis": answer.strip(), "sources_used": len(search_results)}

    async def solve_problem(self, problem: str, language: str = "en") -> dict:
        """
        A3: Break a problem into sub-problems, propose options with
        trade-offs, recommend the best one with reasoning.
        """
        from app.services.ollama_service import ollama_service

        # Stage 1: Decompose
        decompose_prompt = (
            f"Problem: {problem}\n\n"
            f"Break this into 2-5 concrete sub-problems or key questions "
            f"that need answering to solve it. Bullet points only, no solutions yet."
        )
        breakdown = await ollama_service.chat(
            message=decompose_prompt, history=[],
            system_prompt="You are a structured problem-solving assistant.",
        )

        # Stage 2: Options + recommendation, grounded in the breakdown
        solve_prompt = (
            f"Problem: {problem}\n\n"
            f"Sub-problems identified:\n{breakdown.strip()}\n\n"
            f"Now provide:\n"
            f"1. OPTIONS: 2-3 possible approaches, each with a one-line trade-off\n"
            f"2. RECOMMENDATION: which option is best and why (2-3 sentences)\n"
            f"3. NEXT STEPS: concrete first actions to take"
        )
        solution = await ollama_service.chat(
            message=solve_prompt, history=[],
            system_prompt="You are a structured problem-solving assistant. Be concrete and actionable.",
        )

        return {"success": True, "problem": problem, "breakdown": breakdown.strip(), "solution": solution.strip()}

    async def synthesize_knowledge(self, topic: str, language: str = "en") -> dict:
        """
        A4: Pull everything AURA already knows about a topic and weave
        it into one coherent answer, noting connections and any
        contradictions between sources.
        """
        from app.intelligence.intelligence_service import intelligence_service
        from app.services.ollama_service import ollama_service

        try:
            search_results = await intelligence_service.search(
                query=topic, knowledge_type=None, category=None, n_results=8,
            )
        except Exception as e:
            logger.warning("Knowledge search failed for synthesize_knowledge: %s", e)
            search_results = []

        if not search_results:
            msg = (
                f"'{topic}' নিয়ে এখনো কিছু শেখানো হয়নি — আগে document/URL/YouTube থেকে শেখাও।"
                if language == "bn" else
                f"Nothing has been taught about '{topic}' yet — teach AURA via a document/URL/YouTube first."
            )
            return {"success": False, "error": msg}

        context = self._format_evidence(search_results)

        prompt = (
            f"Topic: {topic}\n\n"
             f"Retrieved information (ONLY synthesize pieces that are genuinely "
            f"about '{topic}' — silently skip anything tangential/unrelated):\n{context}\n\n"
            f"Synthesize this into ONE coherent explanation. Connect related points, "
            f"note if any sources seem to contradict each other, and organize logically "
            f"rather than just listing facts."
        )
        synthesis = await ollama_service.chat(
            message=prompt, history=[],
            system_prompt="You are a knowledge-synthesis assistant. Weave separate facts into one coherent narrative.",
        )

        return {
            "success": True, "topic": topic,
            "synthesis": synthesis.strip(), "sources_used": len(search_results),
        }

    def _format_evidence(self, search_results: list) -> str:
        if not search_results:
            return ""
        lines = []
        for i, item in enumerate(search_results, 1):
            title = item.get("title") or item.get("content", "")[:60]
            content = item.get("content", "")[:300]
            lines.append(f"[{i}] {title}: {content}")
        return "\n".join(lines)


reasoning_service = ReasoningService()
