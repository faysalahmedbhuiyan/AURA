"""
AURA Backend — Translator.

Module: app.nlp.translator
Purpose: Translates Banglish (Bangla written in Roman script) into
         proper Bangla script using the LLM. Only invoked when
         LanguageDetector flags needs_translation=True — keeps the
         hot path (English/Bangla messages) free of extra LLM calls.
"""

import logging

from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

TRANSLATE_SYSTEM_PROMPT = (
    "You are a translation engine. You are NOT AURA and you are not "
    "having a conversation. You are given a message written in Banglish "
    "(Bangla words spelled in Roman/English letters). Translate it into "
    "natural, correctly-spelled Bangla script. Output ONLY the Bangla "
    "translation — no explanation, no quotes, nothing else."
)


class Translator:
    """
    Translates Banglish text to Bangla script via the LLM.

    Methods:
        banglish_to_bangla: Translate a single message.
    """

    async def banglish_to_bangla(self, text: str) -> str:
        """
        Translate Banglish text into Bangla script.

        Args:
            text: Banglish message.

        Returns:
            str: The message in Bangla script. Falls back to the
                 original text if translation fails.
        """
        try:
            result = await ollama_service.chat(
                message=text, system_prompt=TRANSLATE_SYSTEM_PROMPT
            )
            return result.strip() or text
        except Exception as e:
            logger.warning("Banglish translation failed, using original: %s", e)
            return text


# ── Singleton instance ────────────────────────────────────────────────────────
translator = Translator()