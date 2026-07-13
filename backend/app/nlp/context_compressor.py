"""
AURA Backend — Context Compressor.

Module: app.nlp.context_compressor
Purpose: Keeps long conversations within the model's context window
         (8192 tokens for aura-brain/qwen3:8b) by summarizing older
         messages instead of dropping them silently. RAM-aware: uses
         a cheap char-based heuristic for token estimation rather than
         a real tokenizer (avoids adding a new dependency).
"""

import logging

from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

# Rough heuristic: ~4 chars per token for mixed Bangla/English text.
CHARS_PER_TOKEN_ESTIMATE = 4
MAX_CONTEXT_TOKENS = 6000  # leave headroom under the 8192 model limit
KEEP_RECENT_MESSAGES = 6   # always keep the last N messages verbatim

SUMMARY_SYSTEM_PROMPT = (
    "You are a conversation summarizer. You are NOT AURA and you are "
    "not having a conversation. Summarize the following conversation "
    "history into a short paragraph capturing key facts, decisions, "
    "and context that would matter for continuing the conversation. "
    "Output ONLY the summary, in the same language as the conversation."
)


class ContextCompressor:
    """
    Compresses conversation history to fit the model's context window.

    Methods:
        compress_if_needed: Summarize older messages if history is too long.
    """

    def _estimate_tokens(self, messages: list[dict]) -> int:
        """Rough token estimate for a list of {role, content} messages."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // CHARS_PER_TOKEN_ESTIMATE

    async def compress_if_needed(self, history: list[dict]) -> list[dict]:
        """
        Compress conversation history if it exceeds the context budget.

        Args:
            history: Full message history as [{"role", "content"}, ...].

        Returns:
            list[dict]: Possibly compressed history — a summary message
                        prepended, followed by the most recent messages
                        verbatim. Returns the original history unchanged
                        if it's already within budget.
        """
        if self._estimate_tokens(history) <= MAX_CONTEXT_TOKENS:
            return history

        if len(history) <= KEEP_RECENT_MESSAGES:
            return history  # nothing meaningful to compress

        old_messages = history[:-KEEP_RECENT_MESSAGES]
        recent_messages = history[-KEEP_RECENT_MESSAGES:]

        transcript = "\n".join(
            f"{m['role']}: {m['content']}" for m in old_messages
        )[:8000]  # cap input to the summarizer itself

        try:
            summary = await ollama_service.chat(
                message=transcript, system_prompt=SUMMARY_SYSTEM_PROMPT
            )
        except Exception as e:
            logger.warning("Context compression failed, truncating instead: %s", e)
            return recent_messages  # safe fallback — drop old, keep recent

        summary_message = {
            "role": "system",
            "content": f"[Earlier conversation summary]: {summary.strip()}",
        }
        logger.info(
            "Compressed %d old messages into a summary (kept %d recent verbatim)",
            len(old_messages), len(recent_messages),
        )
        return [summary_message] + recent_messages


# ── Singleton instance ────────────────────────────────────────────────────────
context_compressor = ContextCompressor()