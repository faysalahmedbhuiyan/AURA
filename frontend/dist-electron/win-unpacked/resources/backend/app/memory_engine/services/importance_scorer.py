"""
AURA Backend — Importance Scorer.

Module: app.memory_engine.services.importance_scorer
Purpose: Scores memory importance from 0.0 to 1.0.
         Higher score = more important = longer retention.

Scoring factors:
    - Keywords (personal info, decisions = high)
    - Recency (recent = higher)
    - User behavior (explicitly asked to save = high)
    - Content length (detailed = moderate boost)
"""

import logging
import re

logger = logging.getLogger(__name__)

# High importance keywords
HIGH_IMPORTANCE = {
    # Personal
    "name", "নাম", "birthday", "জন্মদিন", "address", "ঠিকানা",
    "phone", "ফোন", "email", "family", "পরিবার", "wife", "husband",
    "children", "সন্তান", "job", "চাকরি", "salary", "বেতন",
    # Decisions
    "decision", "সিদ্ধান্ত", "decided", "সিদ্ধান্ত নিয়েছি",
    "important", "গুরুত্বপূর্ণ", "critical", "জরুরি",
    # Projects
    "project", "প্রজেক্ট", "deadline", "ডেডলাইন", "goal", "লক্ষ্য",
    "plan", "পরিকল্পনা", "business", "ব্যবসা",
    # Passwords/Credentials (flag but don't store plaintext)
    "password", "পাসওয়ার্ড", "login", "credential",
}

MEDIUM_IMPORTANCE = {
    "preference", "পছন্দ", "like", "পছন্দ করি", "dislike", "অপছন্দ",
    "always", "সবসময়", "never", "কখনো না", "usually", "সাধারণত",
    "remember", "মনে রাখো", "note", "নোট",
    "work", "কাজ", "task", "টাস্ক", "meeting", "মিটিং",
}

LOW_IMPORTANCE = {
    "today", "আজ", "now", "এখন", "weather", "আবহাওয়া",
    "news", "খবর", "random", "এলোমেলো",
}


class ImportanceScorer:
    """
    Scores memory importance for retention priority.

    Score ranges:
        0.9 - 1.0: Critical (personal identity, major decisions)
        0.7 - 0.9: High (projects, goals, preferences)
        0.5 - 0.7: Medium (general knowledge, tasks)
        0.3 - 0.5: Low (casual conversation, temporary info)
        0.0 - 0.3: Minimal (trivia, one-time queries)

    Methods:
        score: Calculate importance score for content.
        score_for_layer: Get base score for a memory layer.
    """

    def score(
        self,
        content: str,
        title: str = "",
        layer: str = "conversation",
        explicitly_requested: bool = False,
    ) -> float:
        """
        Calculate importance score for memory content.

        Args:
            content: Memory content to score.
            title: Optional title for additional context.
            layer: Memory layer (affects base score).
            explicitly_requested: User explicitly asked to save this.

        Returns:
            float: Importance score 0.0 to 1.0.
        """
        score = self.score_for_layer(layer)
        text = (content + " " + title).lower()

        # Explicit save request → boost
        if explicitly_requested:
            score = min(score + 0.3, 1.0)

        # High importance keywords
        high_matches = sum(1 for kw in HIGH_IMPORTANCE if kw in text)
        score = min(score + (high_matches * 0.1), 1.0)

        # Medium importance keywords
        medium_matches = sum(1 for kw in MEDIUM_IMPORTANCE if kw in text)
        score = min(score + (medium_matches * 0.05), 1.0)

        # Low importance keywords (slight penalty)
        low_matches = sum(1 for kw in LOW_IMPORTANCE if kw in text)
        score = max(score - (low_matches * 0.05), 0.1)

        # Content length bonus (detailed info is more valuable)
        word_count = len(content.split())
        if word_count > 100:
            score = min(score + 0.1, 1.0)
        elif word_count > 50:
            score = min(score + 0.05, 1.0)

        return round(score, 2)

    def score_for_layer(self, layer: str) -> float:
        """
        Get base importance score for a memory layer.

        Args:
            layer: Memory layer name.

        Returns:
            float: Base score for this layer.
        """
        base_scores = {
            "personal": 0.85,
            "decision": 0.80,
            "project": 0.75,
            "coding": 0.70,
            "preference": 0.65,
            "learning": 0.60,
            "conversation": 0.40,
            "journal": 0.55,
        }
        return base_scores.get(layer, 0.50)

    def suggest_layer(self, content: str, title: str = "") -> str:
        """
        Suggest appropriate memory layer for content.

        Args:
            content: Content to classify.
            title: Optional title.

        Returns:
            str: Suggested layer name.
        """
        text = (content + " " + title).lower()

        layer_keywords = {
            "personal": ["name", "নাম", "birthday", "address", "family", "পরিবার", "i am", "আমি"],
            "decision": ["decided", "decision", "সিদ্ধান্ত", "choose", "selected", "বেছে নিলাম"],
            "project": ["project", "প্রজেক্ট", "deadline", "goal", "লক্ষ্য", "milestone"],
            "coding": ["code", "কোড", "function", "class", "bug", "error", "algorithm", "library"],
            "preference": ["prefer", "like", "পছন্দ", "always use", "favorite", "প্রিয়"],
            "journal": ["today", "আজ", "felt", "happened", "meeting", "মিটিং", "event"],
            "learning": ["learn", "শিখলাম", "discovered", "found out", "new", "নতুন"],
        }

        scores = {}
        for layer, keywords in layer_keywords.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                scores[layer] = matches

        if scores:
            return max(scores, key=scores.get)
        return "conversation"


# ── Singleton ─────────────────────────────────────────────────────────────────
importance_scorer = ImportanceScorer()