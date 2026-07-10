"""
AURA Backend — Code Search.

Module: app.understanding.code_search
Purpose: Full-text search across the AURA codebase.
         Finds functions, classes, patterns, and keywords.
         Supports regex and plain text search.

READ-ONLY — never modifies any file.
RAM-aware: skips large files and limits results.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_DIRS = {
    "venv", "__pycache__", "node_modules", ".git",
    "dist", "build", ".aura", "chroma",
}

SEARCHABLE_EXTENSIONS = {
    ".py", ".jsx", ".js", ".css", ".md", ".json",
    ".txt", ".env.example", ".html",
}

MAX_FILE_SIZE = 500_000   # 500KB — skip huge files
MAX_RESULTS = 100
CONTEXT_LINES = 2         # Lines of context around match


@dataclass
class SearchMatch:
    """A single search result match."""
    file_path: str
    relative_path: str
    line_number: int
    line_content: str
    context_before: list[str]
    context_after: list[str]
    file_type: str

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "line_number": self.line_number,
            "line_content": self.line_content.strip(),
            "context_before": [l.rstrip() for l in self.context_before],
            "context_after": [l.rstrip() for l in self.context_after],
            "file_type": self.file_type,
        }


@dataclass
class SearchResult:
    """Full search result set."""
    query: str
    is_regex: bool
    total_matches: int
    files_searched: int
    matches: list[SearchMatch]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "is_regex": self.is_regex,
            "total_matches": self.total_matches,
            "files_searched": self.files_searched,
            "matches": [m.to_dict() for m in self.matches[:MAX_RESULTS]],
        }


class CodeSearch:
    """
    Full-text code search engine for AURA codebase.

    Methods:
        search: Search codebase for a keyword or pattern.
        find_function: Find a function definition by name.
        find_class: Find a class definition by name.
        find_api_routes: Find all FastAPI route definitions.
    """

    def search(
        self,
        query: str,
        project_root: Path,
        is_regex: bool = False,
        file_types: list[str] | None = None,
        max_results: int = 50,
    ) -> SearchResult:
        """
        Search codebase for a keyword or pattern.

        Args:
            query: Search term or regex pattern.
            project_root: Root directory to search.
            is_regex: Treat query as regex pattern.
            file_types: Filter by file type (e.g. ["python", "react"]).
            max_results: Maximum results to return.

        Returns:
            SearchResult: Matching lines with context.
        """
        max_results = min(max_results, MAX_RESULTS)
        matches: list[SearchMatch] = []
        files_searched = 0

        try:
            if is_regex:
                pattern = re.compile(query, re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(query), re.IGNORECASE)
        except re.error as e:
            return SearchResult(
                query=query,
                is_regex=is_regex,
                total_matches=0,
                files_searched=0,
                matches=[],
            )

        for path in sorted(project_root.rglob("*")):
            if len(matches) >= max_results:
                break

            if any(part in SKIP_DIRS for part in path.parts):
                continue

            if not path.is_file():
                continue

            if path.suffix not in SEARCHABLE_EXTENSIONS and path.name not in {".env.example"}:
                continue

            try:
                if path.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            file_type = self._get_file_type(path)
            if file_types and file_type not in file_types:
                continue

            try:
                lines = path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
            except Exception:
                continue

            files_searched += 1
            rel_path = str(path.relative_to(project_root)).replace("\\", "/")

            for i, line in enumerate(lines):
                if len(matches) >= max_results:
                    break

                if pattern.search(line):
                    context_before = lines[max(0, i - CONTEXT_LINES):i]
                    context_after = lines[i + 1:min(len(lines), i + 1 + CONTEXT_LINES)]

                    matches.append(SearchMatch(
                        file_path=str(path),
                        relative_path=rel_path,
                        line_number=i + 1,
                        line_content=line,
                        context_before=context_before,
                        context_after=context_after,
                        file_type=file_type,
                    ))

        return SearchResult(
            query=query,
            is_regex=is_regex,
            total_matches=len(matches),
            files_searched=files_searched,
            matches=matches,
        )

    def find_function(
        self,
        function_name: str,
        project_root: Path,
    ) -> SearchResult:
        """
        Find a Python function definition by name.

        Args:
            function_name: Function name to find.
            project_root: Root to search.

        Returns:
            SearchResult: Matching function definitions.
        """
        pattern = rf"^\s*(?:async\s+)?def\s+{re.escape(function_name)}\s*\("
        return self.search(
            pattern,
            project_root,
            is_regex=True,
            file_types=["python"],
        )

    def find_class(
        self,
        class_name: str,
        project_root: Path,
    ) -> SearchResult:
        """
        Find a Python class definition by name.

        Args:
            class_name: Class name to find.
            project_root: Root to search.

        Returns:
            SearchResult: Matching class definitions.
        """
        pattern = rf"^\s*class\s+{re.escape(class_name)}\s*[\(:]"
        return self.search(
            pattern,
            project_root,
            is_regex=True,
            file_types=["python"],
        )

    def find_api_routes(
        self,
        project_root: Path,
    ) -> SearchResult:
        """
        Find all FastAPI route definitions.

        Returns:
            SearchResult: All @router.get/post/put/delete/patch decorators.
        """
        pattern = r"@router\.(get|post|put|delete|patch)\s*\("
        return self.search(
            pattern,
            project_root,
            is_regex=True,
            file_types=["python"],
        )

    def _get_file_type(self, path: Path) -> str:
        ext_map = {
            ".py": "python", ".jsx": "react", ".js": "javascript",
            ".css": "stylesheet", ".md": "markdown", ".json": "json",
            ".html": "html", ".txt": "text",
        }
        return ext_map.get(path.suffix.lower(), "other")


# ── Singleton ─────────────────────────────────────────────────────────────────
code_search = CodeSearch()