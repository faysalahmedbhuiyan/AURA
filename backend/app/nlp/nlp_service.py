"""
AURA Backend — NLP Service.

Module: app.nlp.nlp_service
Purpose: Orchestrates the Natural Language Intelligence pipeline —
         this is the single entry point chat.py should call BEFORE
         sending a message to ollama_service. Handles language
         detection, Banglish translation, intent detection, and
         context compression in one pass.
"""

import logging

from app.nlp.context_compressor import context_compressor
from app.nlp.intent_detector import intent_detector
from app.nlp.language_detector import language_detector
from app.nlp.translator import translator

logger = logging.getLogger(__name__)


class NLPService:
    """
    Orchestrates language detection, translation, intent detection,
    and context compression for an incoming chat message.

    Methods:
        process_incoming: Full pipeline for a new user message.
        prepare_context: Compress history before sending to the LLM.
    """

    async def process_incoming(self, message: str) -> dict:
        """
        Process an incoming user message before it reaches the LLM.

        Args:
            message: Raw user message text.

        Returns:
            dict: {
                "original_message": str,
                "processed_message": str,  # translated if Banglish
                "language": dict,           # LanguageDetector output
                "intent": dict,             # IntentDetector output
            }
        """
        language = language_detector.detect(message)
        intent = intent_detector.detect(message)

        processed_message = message
        if language["needs_translation"]:
            processed_message = await translator.banglish_to_bangla(message)
            logger.info("Translated Banglish -> Bangla: %r -> %r", message, processed_message)

        return {
            "original_message": message,
            "processed_message": processed_message,
            "language": language,
            "intent": intent,
        }

    async def prepare_context(self, history: list[dict]) -> list[dict]:
        """
        Compress conversation history if needed before sending to the LLM.

        Args:
            history: Full conversation history.

        Returns:
            list[dict]: History within the model's context budget.
        """
        return await context_compressor.compress_if_needed(history)


# ── Singleton instance ────────────────────────────────────────────────────────
nlp_service = NLPService()