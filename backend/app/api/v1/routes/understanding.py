"""
AURA Backend — Project Understanding Routes.

Module: app.api.v1.routes.understanding
Purpose: HTTP endpoints for Phase 14 — Project Understanding Engine.
         All endpoints are READ-ONLY.

Endpoints:
    GET  /api/v1/understanding/summary       — High-level project overview
    GET  /api/v1/understanding/structure     — Full file/folder tree
    GET  /api/v1/understanding/dependencies  — Python import graph
    POST /api/v1/understanding/search        — Code search
    GET  /api/v1/understanding/routes        — All API endpoints
    GET  /api/v1/understanding/function/{name} — Find function
    GET  /api/v1/understanding/class/{name}    — Find class
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.understanding.understanding_service import understanding_service

logger = logging.getLogger(__name__)
router = APIRouter()

PROJECT_ROOT = Path("D:/AURA")
BACKEND_ROOT = PROJECT_ROOT / "backend"


# ── Request Schemas ───────────────────────────────────────────────────────────

class CodeSearchRequest(BaseModel):
    """Request for code search."""
    query: str = Field(..., min_length=1, max_length=200)
    is_regex: bool = Field(default=False)
    file_types: list[str] | None = Field(
        default=None,
        description="Filter: python, react, javascript, stylesheet, markdown, json",
    )
    max_results: int = Field(default=30, ge=1, le=100)
    project_root: str = Field(default="D:/AURA")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/understanding/summary",
    summary="Project Summary",
    description="High-level overview of AURA project: files, routes, dependencies.",
    tags=["Project Understanding"],
)
async def get_summary() -> dict:
    """Get high-level project summary."""
    try:
        return understanding_service.get_summary(PROJECT_ROOT, BACKEND_ROOT)
    except Exception as e:
        logger.exception("Summary failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {e}",
        )


@router.get(
    "/understanding/structure",
    summary="Project Structure",
    description="Complete file and folder tree with metadata.",
    tags=["Project Understanding"],
)
async def get_structure(
    max_depth: int = Query(default=5, ge=1, le=8),
    project_root: str = Query(default="D:/AURA"),
) -> dict:
    """Get project file/folder structure."""
    root = Path(project_root).resolve()
    if not root.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project root not found: {root}",
        )

    try:
        structure = understanding_service.get_structure(root, max_depth)
        return structure.to_dict()
    except Exception as e:
        logger.exception("Structure analysis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/understanding/dependencies",
    summary="Dependency Graph",
    description="Python module import dependency graph for backend.",
    tags=["Project Understanding"],
)
async def get_dependencies() -> dict:
    """Get Python import dependency graph."""
    try:
        graph = understanding_service.get_dependencies(BACKEND_ROOT)
        return graph.to_dict()
    except Exception as e:
        logger.exception("Dependency mapping failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/understanding/search",
    summary="Code Search",
    description="Full-text search across AURA codebase. Supports regex.",
    tags=["Project Understanding"],
)
async def search_code(request: CodeSearchRequest) -> dict:
    """Search codebase for keyword or pattern."""
    root = Path(request.project_root).resolve()
    if not root.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project root not found: {root}",
        )

    try:
        result = understanding_service.search_code(
            query=request.query,
            project_root=root,
            is_regex=request.is_regex,
            file_types=request.file_types,
            max_results=request.max_results,
        )
        return result.to_dict()
    except Exception as e:
        logger.exception("Code search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/understanding/routes",
    summary="API Routes",
    description="Find all FastAPI route definitions across the backend.",
    tags=["Project Understanding"],
)
async def get_api_routes() -> dict:
    """Find all FastAPI API routes."""
    try:
        result = understanding_service.find_api_routes(PROJECT_ROOT)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/understanding/function/{function_name}",
    summary="Find Function",
    description="Find a Python function definition by name.",
    tags=["Project Understanding"],
)
async def find_function(function_name: str) -> dict:
    """Find a function definition."""
    try:
        result = understanding_service.find_function(function_name, PROJECT_ROOT)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/understanding/class/{class_name}",
    summary="Find Class",
    description="Find a Python class definition by name.",
    tags=["Project Understanding"],
)
async def find_class(class_name: str) -> dict:
    """Find a class definition."""
    try:
        result = understanding_service.find_class(class_name, PROJECT_ROOT)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )