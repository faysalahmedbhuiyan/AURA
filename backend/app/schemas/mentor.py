"""
AURA Backend — Mentor Schemas.

Module: app.schemas.mentor
Purpose: Pydantic models for Coding Mentor Mode (Phase 15).
"""

from pydantic import BaseModel, Field


class ExplainFileRequest(BaseModel):
    """Request to explain a Python file."""

    path: str = Field(..., description="Absolute path to a .py file")
    language: str = Field(default="en")


class ExplainFileResponse(BaseModel):
    """Response with file structure and explanation."""

    file: str
    structure: list[dict]
    explanation: str


class ConceptRequest(BaseModel):
    """Request to teach a programming concept."""

    concept: str = Field(..., min_length=1, max_length=200)
    language: str = Field(default="en")


class ConceptResponse(BaseModel):
    """Response with concept explanation and example."""

    concept: str
    explanation: str


class PracticeSuggestRequest(BaseModel):
    """Request for educational best-practice suggestions."""

    path: str = Field(..., description="Absolute path to a .py file")


class PracticeSuggestResponse(BaseModel):
    """Response with teaching-framed suggestions."""

    file: str
    suggestions: list[dict]


class AskQuestionRequest(BaseModel):
    """Request to ask a question about the codebase."""

    question: str = Field(..., min_length=1, max_length=1000)
    file_path: str | None = Field(default=None)
    language: str = Field(default="en")


class AskQuestionResponse(BaseModel):
    """Response with the mentor's answer."""

    question: str
    answer: str
    context_file: str | None