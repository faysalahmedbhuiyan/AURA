"""
AURA Backend — NLP Routes (Phase 20).

Standalone testing endpoints for the NLP engine. The main integration
point is nlp_service.process_incoming(), which chat.py calls directly
— these routes exist for testing/debugging each component in isolation.

Endpoints:
    POST /api/v1/nlp/detect-language
    POST /api/v1/nlp/translate
    POST /api/v1/nlp/detect-intent
"""

import logging

from fastapi import APIRouter

from app.nlp.intent_detector import intent_detector
from app.nlp.language_detector import language_detector
from app.nlp.translator import translator
from app.schemas.nlp import (
    DetectLanguageRequest, DetectLanguageResponse,
    IntentRequest, IntentResponse,
    TranslateRequest, TranslateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/nlp/detect-language",  tags=["NLP"])
async def detect_language(request: DetectLanguageRequest) -> DetectLanguageResponse:
    """Detect the language of a message (rule-based, no LLM call)."""
    return DetectLanguageResponse(**language_detector.detect(request.text))


@router.post("/nlp/translate",  tags=["NLP"])
async def translate(request: TranslateRequest) -> TranslateResponse:
    """Translate Banglish text into Bangla script."""
    result = await translator.banglish_to_bangla(request.text)
    return TranslateResponse(original=request.text, translated=result)


@router.post("/nlp/detect-intent",  tags=["NLP"])
async def detect_intent(request: IntentRequest) -> IntentResponse:
    """Detect the intent of a message."""
    return IntentResponse(**intent_detector.detect(request.text))