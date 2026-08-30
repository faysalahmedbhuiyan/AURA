"""
AURA Backend — Language Detector.

Module: app.nlp.language_detector
Purpose: Detects the language of a message using fast, rule-based
         heuristics — NO LLM call, so this runs on every message
         without adding latency or RAM cost.

Detects: bangla | banglish | english | hindi | mixed
"""

import re

BANGLA_RANGE = re.compile(r"[\u0980-\u09FF]")
HINDI_RANGE = re.compile(r"[\u0900-\u097F]")

# Common Banglish (Bangla written in Roman script) words/patterns.
# Not exhaustive — heuristic signal, not a dictionary.
BANGLISH_MARKERS = {
    "ami", "tumi", "apni", "amar", "tomar", "apnar", "ki", "kivabe",
    "keno", "kothay", "kobe", "kemon", "acho", "achen", "korbo",
    "korte", "korchi", "korো", "lagbe", "lage", "hobe", "hoyeche",
    "bhalo", "kharap", "dhonnobad", "sathe", "theke", "jonno",
    "ekta", "onek", "khub", "jani", "janina", "bujhi", "bujhte",
    "chai", "chao", "dao", "dilam", "nilam", "kaj", "kotha",
}

ENGLISH_STOPWORDS = {
    "the", "is", "are", "you", "what", "how", "why", "when", "where",
    "please", "can", "will", "would", "should", "with", "about",
}


class LanguageDetector:
    """
    Fast, rule-based language detector.

    Methods:
        detect: Classify a message as bangla/banglish/english/hindi/mixed.
    """

    def detect(self, text: str) -> dict:
        """
        Detect the language(s) present in a message.

        Args:
            text: The message to analyze.

        Returns:
            dict: {
                "primary": "bangla" | "banglish" | "english" | "hindi" | "mixed",
                "has_bangla_script": bool,
                "has_hindi_script": bool,
                "banglish_score": float,  # 0.0-1.0
                "needs_translation": bool,  # True only for banglish
            }
        """
        if not text.strip():
            return {
                "primary": "english", "has_bangla_script": False,
                "has_hindi_script": False, "banglish_score": 0.0,
                "needs_translation": False,
            }

        has_bangla = bool(BANGLA_RANGE.search(text))
        has_hindi = bool(HINDI_RANGE.search(text))

        words = re.findall(r"[a-zA-Z]+", text.lower())
        banglish_hits = sum(1 for w in words if w in BANGLISH_MARKERS)
        english_hits = sum(1 for w in words if w in ENGLISH_STOPWORDS)
        total_latin_words = max(len(words), 1)
        banglish_score = round(banglish_hits / total_latin_words, 2) if words else 0.0

        # Decide primary language
        if has_bangla and has_hindi:
            primary = "mixed"
        elif has_bangla and banglish_hits == 0:
            primary = "bangla"
        elif has_hindi:
            primary = "hindi"
        elif has_bangla and banglish_hits > 0:
            primary = "mixed"  # both scripts present
        elif banglish_hits > 0 and banglish_hits >= english_hits:
            primary = "banglish"
        else:
            primary = "english"

        return {
            "primary": primary,
            "has_bangla_script": has_bangla,
            "has_hindi_script": has_hindi,
            "banglish_score": banglish_score,
            "needs_translation": primary == "banglish",
        }


# ── Singleton instance ────────────────────────────────────────────────────────
language_detector = LanguageDetector()