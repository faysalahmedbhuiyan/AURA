"""
AURA Backend — Mentor Routes.

Module: app.api.v1.routes.mentor
Purpose: API endpoints for Coding Mentor Mode (Phase 15). All
         endpoints are READ-ONLY — no file is ever modified.

Endpoints:
    POST /api/v1/mentor/explain    — Explain a Python file
    POST /api/v1/mentor/concept    — Teach a programming concept
    POST /api/v1/mentor/practices  — Educational best-practice suggestions
    POST /api/v1/mentor/ask        — Ask a question about the codebase
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.mentor.mentor_service import mentor_service
from app.schemas.mentor import (
    AskQuestionRequest,
    AskQuestionResponse,
    ConceptRequest,
    ConceptResponse,
    ExplainFileRequest,
    ExplainFileResponse,
    PracticeSuggestRequest,
    PracticeSuggestResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/mentor/explain", response_model=ExplainFileResponse,
    tags=["Coding Mentor"], summary="Explain a Python File",
    description="Explains a file's structure and purpose. READ-ONLY.",
)
async def explain_file(request: ExplainFileRequest) -> ExplainFileResponse:
    """Explain a Python file's structure and behavior."""
    path = Path(request.path).resolve()
    if not path.exists() or path.suffix != ".py":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Python file not found: {path}",
        )
    result = await mentor_service.explain_file(path, request.language)
    return ExplainFileResponse(**result)


@router.post(
    "/mentor/concept", response_model=ConceptResponse,
    tags=["Coding Mentor"], summary="Teach a Programming Concept",
)
async def teach_concept(request: ConceptRequest) -> ConceptResponse:
    """Explain a programming concept with an example."""
    result = await mentor_service.teach_concept(request.concept, request.language)
    return ConceptResponse(**result)


@router.post(
    "/mentor/practices", response_model=PracticeSuggestResponse,
    tags=["Coding Mentor"], summary="Educational Best-Practice Suggestions",
    description="Analyzes a Python file and explains WHY each pattern matters and HOW to improve it.",
)
async def suggest_practices(request: PracticeSuggestRequest) -> PracticeSuggestResponse:
    """Suggest best practices for a file with educational framing."""
    path = Path(request.path).resolve()
    if not path.exists() or path.suffix != ".py":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Python file not found: {path}",
        )
    result = mentor_service.suggest_practices(path)
    return PracticeSuggestResponse(**result)


@router.post(
    "/mentor/ask", response_model=AskQuestionResponse,
    tags=["Coding Mentor"], summary="Ask a Question About the Codebase",
)
async def ask_question(request: AskQuestionRequest) -> AskQuestionResponse:
    """Answer a question, optionally grounded in a specific file."""
    result = await mentor_service.ask_question(
        request.question, request.file_path, request.language
    )
    return AskQuestionResponse(**result)