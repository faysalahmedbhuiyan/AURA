"""
AURA Backend — Memory Summarizer.

Module: app.memory_engine.services.memory_summarizer
Purpose: Summarizes long memory content using Ollama LLM.
         Keeps memory entries concise for faster recall.
         RAM-aware: Only summarizes content > 500 chars.
"""

import logging

logger = logging.getLogger(__name__)

SUMMARIZE_THRESHOLD = 500  # Characters before summarization kicks in


class MemorySummarizer:
    """
    LLM-powered memory summarizer.

    Compresses long memory content into concise summaries.
    Uses existing OllamaService — no new model needed.

    Methods:
        should_summarize: Check if content needs summarization.
        summarize: Generate summary using Ollama.
        summarize_conversation: Summarize a conversation thread.
    """

    def should_summarize(self, content: str) -> bool:
        """Check if content is long enough to need summarization."""
        return len(content) > SUMMARIZE_THRESHOLD

    async def summarize(
        self,
        content: str,
        layer: str = "general",
        language: str = "bn",
    ) -> str:
        """
        Generate a concise summary of memory content.

        Args:
            content: Content to summarize.
            layer: Memory layer for context.
            language: Language for summary (bn/en).

        Returns:
            str: Concise summary (max ~200 words).
        """
        if not self.should_summarize(content):
            return content

        try:
            from app.services.ollama_service import ollama_service

            lang_instruction = (
                "বাংলায় সারসংক্ষেপ লিখুন।"
                if language == "bn"
                else "Write the summary in English."
            )

            prompt = (
                f"নিচের তথ্যটি সংক্ষিপ্ত করুন। {lang_instruction} "
                f"মূল তথ্য রাখুন, অপ্রয়োজনীয় বিষয় বাদ দিন। "
                f"সর্বোচ্চ ৩-৪ বাক্যে লিখুন।\n\n"
                f"Content:\n{content[:3000]}"
            )

            summary = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt=(
                    "You are a memory summarizer. "
                    "Create concise, accurate summaries. "
                    "Preserve all important facts. "
                    "Keep summaries under 200 words."
                ),
            )
            return summary.strip()

        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            # Fallback: truncate
            return content[:500] + "... [truncated]"

    async def summarize_conversation(
        self,
        messages: list[dict],
        language: str = "bn",
    ) -> str:
        """
        Summarize a conversation thread into key points.

        Args:
            messages: List of {role, content} message dicts.
            language: Summary language.

        Returns:
            str: Key points from the conversation.
        """
        if not messages:
            return ""

        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:200]}"
            for msg in messages[-10:]  # Last 10 messages
        ])

        try:
            from app.services.ollama_service import ollama_service

            lang_inst = (
                "বাংলায় লিখুন।" if language == "bn"
                else "Write in English."
            )

            prompt = (
                f"এই কথোপকথনের মূল বিষয়গুলো সংক্ষেপে লিখুন। {lang_inst}\n\n"
                f"{conversation_text}"
            )

            summary = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt="Summarize conversations concisely. Extract key information only.",
            )
            return summary.strip()

        except Exception as e:
            logger.warning("Conversation summarization failed: %s", e)
            return conversation_text[:300]


# ── Singleton ─────────────────────────────────────────────────────────────────
memory_summarizer = MemorySummarizer()