"""
AURA Backend — Concept Teacher.

Module: app.mentor.concept_teacher
Purpose: Explains a programming concept with a clear explanation and a
         short example, using the LLM. READ-ONLY.
"""

import logging

from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

TEACHER_SYSTEM_PROMPT = (
    "You are a patient, clear coding mentor teaching programming concepts "
    "to a learner. You are NOT AURA and you are not having a conversation. "
    "Explain the concept clearly, then give ONE short, runnable code "
    "example illustrating it. Prefer Python examples unless another "
    "language is specifically requested. Never ask for confirmation or "
    "offer to remember anything. Respond in the requested language."
)


class ConceptTeacher:
    """
    Teaches a programming concept on request.

    Methods:
        teach: Explain a concept with an example.
    """

    async def teach(self, concept: str, language: str = "en") -> dict:
        """
        Explain a programming concept.

        Args:
            concept: The concept to explain, e.g. "async/await" or
                     "dependency injection".
            language: Response language code.

        Returns:
            dict: {"concept": str, "explanation": str}
        """
        prompt = (
            f"Explain the programming concept: '{concept}'. "
            f"Respond in language code '{language}'. Structure your "
            f"answer as: a plain-language explanation (2-4 sentences), "
            f"then a short code example in a fenced code block, then "
            f"one sentence on when to use it."
        )

        try:
            explanation = await ollama_service.chat(
                message=prompt, system_prompt=TEACHER_SYSTEM_PROMPT
            )
        except Exception as e:
            logger.exception("Concept teaching failed for '%s': %s", concept, e)
            explanation = f"Could not generate an explanation: {e}"

        return {"concept": concept, "explanation": explanation.strip()}


# ── Singleton instance ────────────────────────────────────────────────────────
concept_teacher = ConceptTeacher()