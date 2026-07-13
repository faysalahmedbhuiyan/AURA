"""
AURA Backend — Research Trigger Detector.

Module: app.services.research_trigger
Purpose: Detects when a chat message is asking AURA to research
         something online, so the chat endpoint can invoke the
         Phase 6 research pipeline instead of a normal LLM reply.
"""

import re

TRIGGER_PATTERNS = [
    r"online\s*(theke|thaka)?\s*(kore|kore)?\s*(jano|bolo|khoj|search)",
    r"internet\s*(theke)?\s*(khoj|search|jano)",
    r"ইন্টারনেট\s*(থেকে)?\s*(খুঁজে|জানাও|জানো)",
    r"অনলাইন\s*(থেকে)?\s*(খুঁজে|জানাও|জানো)",
    r"\bresearch\b.*\b(this|it|about)\b",
    r"search\s+(kore|for)\s",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


def is_research_request(message: str) -> bool:
    """
    Check if a chat message is asking AURA to research something online.

    Args:
        message: The user's chat message.

    Returns:
        bool: True if a research trigger phrase is detected.
    """
    return any(p.search(message) for p in COMPILED)