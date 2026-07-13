"""AURA Backend — NLP Schemas (Phase 20)."""

from pydantic import BaseModel, Field


class DetectLanguageRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DetectLanguageResponse(BaseModel):
    primary: str
    has_bangla_script: bool
    has_hindi_script: bool
    banglish_score: float
    needs_translation: bool


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TranslateResponse(BaseModel):
    original: str
    translated: str


class IntentRequest(BaseModel):
    text: str = Field(..., min_length=1)


class IntentResponse(BaseModel):
    intent: str
    matched_patterns: list[str]