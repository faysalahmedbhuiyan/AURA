"""
AURA Backend — Intent Detector.

Module: app.nlp.intent_detector
Purpose: Classifies a message's intent using fast keyword heuristics
         first (no LLM cost), falling back to LLM classification only
         for ambiguous cases. Used to route messages — e.g. a "research
         this" intent can trigger Phase 6's research pipeline instead
         of a normal chat reply (already wired conceptually in Phase 6
         follow-up; this formalizes and extends detection).
"""

import re

INTENT_PATTERNS = {
    "research_request": [
        r"online\s*(theke|thaka)?\s*(kore)?\s*(jano|bolo|khoj|search)",
        r"internet\s*(theke)?\s*(khoj|search|jano)",
        r"ইন্টারনেট\s*(থেকে)?\s*(খুঁজে|জানাও|জানো)",
        r"অনলাইন\s*(থেকে)?\s*(খুঁজে|জানাও|জানো)",
        r"\bresearch\b", r"search\s+(kore|for)",
    ],
    "file_request": [
        r"\bfile\b.*\b(read|open|dekho|poro)\b",
        r"ফাইল.*(পড়ো|দেখো|খোলো)",
    ],
    "code_request": [
        r"\bcode\b.*\b(fix|write|generate|debug|banao)\b",
        r"কোড.*(লেখো|ঠিক করো|বানাও)",
    ],
    "memory_request": [
        r"মনে রাখো", r"remember this", r"save (this|it)",
    ],
    "question": [
        r"^(what|why|how|when|where|who|which)\b",
        r"^(কি|কেন|কীভাবে|কখন|কোথায়|কে)\b",
        r"\?$",
    ],
}

COMPILED = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns]
    for intent, patterns in INTENT_PATTERNS.items()
}


class IntentDetector:
    """
    Rule-based intent classifier.

    Methods:
        detect: Classify a message's intent.
    """

    def detect(self, text: str) -> dict:
        """
        Detect the intent of a message.

        Args:
            text: The message to classify.

        Returns:
            dict: {"intent": str, "matched_patterns": list[str]}
                  intent is one of: research_request, file_request,
                  code_request, memory_request, question, general_chat
        """
        matched: dict[str, list[str]] = {}
        for intent, patterns in COMPILED.items():
            hits = [p.pattern for p in patterns if p.search(text)]
            if hits:
                matched[intent] = hits

        if not matched:
            return {"intent": "general_chat", "matched_patterns": []}

        # Priority order — research/file/code/memory take precedence
        # over the generic "question" intent if both match.
        priority = ["research_request", "file_request", "code_request", "memory_request", "question"]
        for intent in priority:
            if intent in matched:
                return {"intent": intent, "matched_patterns": matched[intent]}

        return {"intent": "general_chat", "matched_patterns": []}


# ── Singleton instance ────────────────────────────────────────────────────────
intent_detector = IntentDetector()