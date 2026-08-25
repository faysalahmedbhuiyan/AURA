"""
AURA Backend — Mentor Service.

Module: app.mentor.mentor_service
Purpose: Orchestrates all Coding Mentor Mode capabilities: explaining
         files, teaching concepts, suggesting best practices, and
         answering questions about the codebase. READ-ONLY throughout.
"""

import logging
from pathlib import Path

from app.mentor.code_explainer import code_explainer
from app.mentor.concept_teacher import concept_teacher
from app.mentor.practice_suggester import practice_suggester
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 4000

QA_SYSTEM_PROMPT = (
    "You are a patient coding mentor answering a question about a "
    "specific codebase. You are NOT AURA and you are not having a "
    "general conversation. Answer ONLY using the file context given — "
    "if the context doesn't contain the answer, say so honestly rather "
    "than guessing. Never ask for confirmation or offer to remember "
    "anything. Respond in the requested language."
)


class MentorService:
    """
    Orchestrates Coding Mentor Mode.

    Methods:
        explain_file: Delegate to CodeExplainer.
        teach_concept: Delegate to ConceptTeacher.
        suggest_practices: Delegate to PracticeSuggester.
        ask_question: Answer a question about a specific file's code.
    """

    async def explain_file(self, path: Path, language: str = "en") -> dict:
        """Explain a Python file's structure and purpose."""
        return await code_explainer.explain_file(path, language)

    async def teach_concept(self, concept: str, language: str = "en") -> dict:
        """Teach a programming concept with an example."""
        return await concept_teacher.teach(concept, language)

    def suggest_practices(self, path: Path) -> dict:
        """Suggest best practices for a file with educational framing."""
        return practice_suggester.suggest(path)

    async def ask_question(
        self, question: str, file_path: str | None, language: str = "en"
    ) -> dict:
        """
        Answer a question about the codebase, optionally grounded in a
        specific file's content.

        Args:
            question: The user's question.
            file_path: Optional path to a file for context.
            language: Response language code.

        Returns:
            dict: {"question": str, "answer": str, "context_file": str | None}
        """
        context = ""
        if file_path:
            path = Path(file_path).resolve()
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
                context = f"FILE: {path.name}\n\n{content[:MAX_CONTEXT_CHARS]}"
            else:
                return {
                    "question": question,
                    "answer": f"The file '{file_path}' does not exist.",
                    "context_file": file_path,
                }

        prompt = (
            f"Question: {question}\n\n"
            f"Respond in language code '{language}'.\n\n"
            + (f"Context:\n{context}" if context else "No specific file context was provided.")
        )

        try:
            answer = await ollama_service.chat(
                message=prompt, system_prompt=QA_SYSTEM_PROMPT
            )
        except Exception as e:
            logger.exception("Mentor Q&A failed: %s", e)
            answer = f"Could not generate an answer: {e}"

        return {
            "question": question,
            "answer": answer.strip(),
            "context_file": file_path,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
mentor_service = MentorService()