"""
AURA Backend — Request Parser.

Module: app.planning.request_parser
Purpose: Parses a free-text improvement request into structured signals:
         explicitly mentioned files, keywords, and a guessed scope
         (backend / frontend / full project).
"""

import re
import logging

logger = logging.getLogger(__name__)

FILE_MENTION_PATTERN = re.compile(
    r"\b[\w\-/\\.]+\.(py|jsx|js|css|md|json|txt)\b", re.IGNORECASE
)

FRONTEND_HINTS = (
    "frontend", "ui", "component", "jsx", "css", "design", "button",
    "sidebar", "page", "screen", "style", "layout", "react",
)
BACKEND_HINTS = (
    "backend", "api", "endpoint", "database", "model", "service",
    "route", "schema", "repository", "agent", "server",
)

STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or",
    "please", "make", "it", "this", "that", "with", "should", "need",
    "want", "add", "fix", "update", "change",
}


class RequestAnalysis:
    """Structured result of parsing an improvement request."""

    def __init__(
        self,
        raw_text: str,
        mentioned_files: list[str],
        keywords: list[str],
        likely_scope: str,
    ) -> None:
        self.raw_text = raw_text
        self.mentioned_files = mentioned_files
        self.keywords = keywords
        self.likely_scope = likely_scope  # backend | frontend | full

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text,
            "mentioned_files": self.mentioned_files,
            "keywords": self.keywords,
            "likely_scope": self.likely_scope,
        }


class RequestParser:
    """
    Parses free-text improvement requests.

    Methods:
        parse: Extract mentioned files, keywords, and likely scope.
    """

    def parse(self, description: str) -> RequestAnalysis:
        """
        Parse an improvement request description.

        Args:
            description: Free-text request, e.g. "make the sidebar
                          buttons rounder" or "add retry logic to
                          ollama_service.py".

        Returns:
            RequestAnalysis: Structured signals extracted from text.
        """
        mentioned_files = sorted(set(
            m.group(0) for m in FILE_MENTION_PATTERN.finditer(description)
        ))

        words = re.findall(r"[a-zA-Z_]+", description.lower())
        keywords = sorted(set(
            w for w in words if w not in STOPWORDS and len(w) > 2
        ))

        frontend_score = sum(1 for k in keywords if k in FRONTEND_HINTS)
        backend_score = sum(1 for k in keywords if k in BACKEND_HINTS)

        if any(f.endswith((".jsx", ".js", ".css")) for f in mentioned_files):
            frontend_score += 2
        if any(f.endswith(".py") for f in mentioned_files):
            backend_score += 2

        if frontend_score > backend_score:
            likely_scope = "frontend"
        elif backend_score > frontend_score:
            likely_scope = "backend"
        else:
            likely_scope = "full"

        return RequestAnalysis(
            raw_text=description,
            mentioned_files=mentioned_files,
            keywords=keywords,
            likely_scope=likely_scope,
        )


# ── Singleton instance ────────────────────────────────────────────────────────
request_parser = RequestParser()