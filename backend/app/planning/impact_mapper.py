"""
AURA Backend — Impact Mapper.

Module: app.planning.impact_mapper
Purpose: Finds candidate files affected by an improvement request.
         Works across the WHOLE project (backend + frontend), unlike
         the Phase 8 review engine which only analyzes Python via AST.
         Uses filename and keyword matching — a heuristic, not a
         guarantee. NEVER modifies any file.
"""

import logging
from pathlib import Path

from app.planning.request_parser import RequestAnalysis

logger = logging.getLogger(__name__)

SKIP_DIRS = {
    "venv", "__pycache__", "node_modules", ".git", "dist", "build",
    ".vite", ".vite-temp", "chroma",
}

SCANNABLE_EXTENSIONS = {
    ".py", ".jsx", ".js", ".css", ".md", ".json",
}

MAX_CONTENT_SCAN_BYTES = 20_000  # skip huge files for keyword scan (RAM-aware)
MAX_CANDIDATES = 30


class AffectedFile:
    """A single file identified as potentially affected by a request."""

    def __init__(self, path: str, relevance: float, reason: str) -> None:
        self.path = path
        self.relevance = relevance  # 0.0 - 1.0
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "relevance": round(self.relevance, 2),
            "reason": self.reason,
        }


class ImpactMapper:
    """
    Maps a parsed request to candidate affected files.

    Methods:
        map_impact: Find and rank candidate files for a request.
    """

    def map_impact(
        self, analysis: RequestAnalysis, project_root: Path
    ) -> list[AffectedFile]:
        """
        Find files likely affected by the request.

        Args:
            analysis: Parsed request from RequestParser.
            project_root: Root directory to search (e.g. D:/AURA).

        Returns:
            list[AffectedFile]: Ranked candidates, highest relevance first.
        """
        candidates: dict[str, AffectedFile] = {}

        # Step 1: explicitly mentioned files — highest confidence
        if analysis.mentioned_files:
            for mention in analysis.mentioned_files:
                matches = self._find_by_filename(project_root, mention)
                for match in matches:
                    candidates[str(match)] = AffectedFile(
                        str(match), 1.0,
                        f"Explicitly mentioned in request as '{mention}'.",
                    )

        # Step 2: keyword search across filenames and content
        if analysis.keywords:
            self._keyword_scan(project_root, analysis, candidates)

        ranked = sorted(
            candidates.values(), key=lambda f: f.relevance, reverse=True
        )
        return ranked[:MAX_CANDIDATES]

    def _find_by_filename(self, root: Path, mention: str) -> list[Path]:
        """Find files whose name matches an explicitly mentioned filename."""
        target_name = Path(mention).name.lower()
        matches = []
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.name.lower() == target_name:
                matches.append(path)
        return matches

    def _keyword_scan(
        self,
        root: Path,
        analysis: RequestAnalysis,
        candidates: dict[str, AffectedFile],
    ) -> None:
        """Score files by how many request keywords appear in name/content."""
        scope = analysis.likely_scope
        keywords = analysis.keywords

        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if not path.is_file() or path.suffix not in SCANNABLE_EXTENSIONS:
                continue
            if scope == "backend" and path.suffix in (".jsx", ".css"):
                continue
            if scope == "frontend" and path.suffix == ".py":
                continue

            score, matched_keywords = self._score_file(path, keywords)
            if score <= 0:
                continue

            path_str = str(path)
            relevance = min(score / max(len(keywords), 1), 1.0)

            if path_str in candidates:
                if relevance > candidates[path_str].relevance:
                    candidates[path_str].relevance = relevance
                continue

            candidates[path_str] = AffectedFile(
                path_str, relevance,
                f"Matched keywords: {', '.join(matched_keywords)}.",
            )

    def _score_file(
        self, path: Path, keywords: list[str]
    ) -> tuple[int, list[str]]:
        """Count how many keywords appear in a file's name or content."""
        matched = []
        name_lower = path.name.lower()

        for kw in keywords:
            if kw in name_lower:
                matched.append(kw)

        try:
            if path.stat().st_size <= MAX_CONTENT_SCAN_BYTES:
                content = path.read_text(
                    encoding="utf-8", errors="replace"
                ).lower()
                for kw in keywords:
                    if kw not in matched and kw in content:
                        matched.append(kw)
        except Exception:
            pass  # unreadable file — filename match only

        return len(matched), matched


# ── Singleton instance ────────────────────────────────────────────────────────
impact_mapper = ImpactMapper()