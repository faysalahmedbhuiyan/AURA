"""
AURA Backend — Understanding Service.

Module: app.understanding.understanding_service
Purpose: Orchestrates all Project Understanding Engine analyzers.
         Single entry point for AURA to understand its own codebase.

All operations are READ-ONLY.
Results are cached per session to avoid repeated filesystem scans.
"""

import logging
from functools import lru_cache
from pathlib import Path

from app.understanding.code_search import SearchResult, code_search
from app.understanding.dependency_mapper import DependencyGraph, dependency_mapper
from app.understanding.structure_analyzer import ProjectStructure, structure_analyzer

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("D:/AURA")
BACKEND_ROOT = PROJECT_ROOT / "backend"


class UnderstandingService:
    """
    Orchestrates Project Understanding Engine.

    Provides a unified interface for:
    - Project structure analysis
    - Dependency graph building
    - Code search
    - API route discovery

    Methods:
        get_structure     — Full project file/folder map
        get_dependencies  — Python import dependency graph
        search_code       — Full-text search across codebase
        find_function     — Find function definition
        find_class        — Find class definition
        find_api_routes   — List all FastAPI endpoints
        get_summary       — High-level project overview
    """

    def get_structure(
        self,
        project_root: Path = PROJECT_ROOT,
        max_depth: int = 5,
    ) -> ProjectStructure:
        """
        Get complete project file/folder structure.

        Args:
            project_root: Root to analyze.
            max_depth: Max folder traversal depth.

        Returns:
            ProjectStructure: Complete structure map.
        """
        logger.info("Analyzing project structure at %s", project_root)
        return structure_analyzer.analyze(project_root, max_depth)

    def get_dependencies(
        self,
        backend_root: Path = BACKEND_ROOT,
    ) -> DependencyGraph:
        """
        Build Python module dependency graph.

        Args:
            backend_root: Backend directory root.

        Returns:
            DependencyGraph: Full import graph.
        """
        logger.info("Building dependency graph at %s", backend_root)
        return dependency_mapper.build_graph(backend_root)

    def search_code(
        self,
        query: str,
        project_root: Path = PROJECT_ROOT,
        is_regex: bool = False,
        file_types: list[str] | None = None,
        max_results: int = 50,
    ) -> SearchResult:
        """
        Search codebase for keyword or pattern.

        Args:
            query: Search term or regex.
            project_root: Root to search.
            is_regex: Treat query as regex.
            file_types: Filter by type (python/react/etc).
            max_results: Max results.

        Returns:
            SearchResult: Matching lines with context.
        """
        return code_search.search(
            query, project_root, is_regex, file_types, max_results
        )

    def find_function(
        self,
        function_name: str,
        project_root: Path = PROJECT_ROOT,
    ) -> SearchResult:
        """Find a function definition by name."""
        return code_search.find_function(function_name, project_root)

    def find_class(
        self,
        class_name: str,
        project_root: Path = PROJECT_ROOT,
    ) -> SearchResult:
        """Find a class definition by name."""
        return code_search.find_class(class_name, project_root)

    def find_api_routes(
        self,
        project_root: Path = PROJECT_ROOT,
    ) -> SearchResult:
        """Find all FastAPI API route definitions."""
        return code_search.find_api_routes(project_root)

    def get_summary(
        self,
        project_root: Path = PROJECT_ROOT,
        backend_root: Path = BACKEND_ROOT,
    ) -> dict:
        """
        Get high-level project overview combining all analyzers.

        Returns:
            dict: Concise summary with key metrics.
        """
        logger.info("Generating project summary")

        structure = structure_analyzer.analyze(project_root, max_depth=4)
        routes = code_search.find_api_routes(project_root)

        try:
            deps = dependency_mapper.build_graph(backend_root)
            dep_summary = {
                "total_python_modules": deps.total_modules,
                "most_imported": deps.most_imported[:5],
                "most_dependencies": deps.most_dependencies[:5],
            }
        except Exception as e:
            logger.warning("Dependency analysis failed: %s", e)
            dep_summary = {"error": str(e)}

        return {
            "project_root": str(project_root),
            "structure": {
                "total_files": structure.total_files,
                "total_size_human": structure._human_size(structure.total_size_bytes),
                "file_types": structure.file_type_counts,
                "largest_files": structure.largest_files[:5],
            },
            "api": {
                "total_routes": routes.total_matches,
                "route_files": list({
                    m.relative_path for m in routes.matches
                }),
            },
            "dependencies": dep_summary,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
understanding_service = UnderstandingService()