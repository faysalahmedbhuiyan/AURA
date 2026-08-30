"""
AURA Backend — Voice Session Routes (Phase 21).

Purpose: HTTP endpoints for voice session state, wake-word checking,
         and VAD checking. Real-time audio streaming for continuous
         listening is left to the frontend to chunk and POST — a
         WebSocket implementation is noted as a future improvement
         (see PHASE_REPORT.md) rather than built now, to avoid adding
         unverified complexity in this pass.

Endpoints:
    GET  /api/v1/voice-session/state
    POST /api/v1/voice-session/mode
    POST /api/v1/voice-session/check-wake-word
    POST /api/v1/voice-session/check-vad
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.voice_session import (
    SetModeRequest, VADCheckResponse, VoiceStateResponse, WakeWordCheckResponse,
)
from app.voice.vad_service import vad_service
from app.voice.voice_session_manager import voice_session_manager
from app.voice.wake_word_detector import wake_word_detector

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/voice-session/state", response_model=VoiceStateResponse, tags=["Voice Session"])
async def get_state() -> VoiceStateResponse:
    """Get the current voice session state and mode."""
    return VoiceStateResponse(**voice_session_manager.get_state())


@router.post("/voice-session/mode", response_model=VoiceStateResponse, tags=["Voice Session"])
async def set_mode(request: SetModeRequest) -> VoiceStateResponse:
    """Set the voice session mode (always_listening or push_to_talk)."""
    voice_session_manager.set_mode(request.mode)
    return VoiceStateResponse(**voice_session_manager.get_state())


@router.post(
    "/voice-session/check-wake-word", response_model=WakeWordCheckResponse,
    tags=["Voice Session"],
)
async def check_wake_word(
    audio: UploadFile = File(...), language: str = Form(default="en")
) -> WakeWordCheckResponse:
    """Check if a short audio clip contains the 'Hey Aura' wake phrase."""
    audio_bytes = await audio.read()
    result = await wake_word_detector.check_audio_bytes(audio_bytes, language)
    return WakeWordCheckResponse(**result)


@router.post(
    "/voice-session/check-vad", response_model=VADCheckResponse, tags=["Voice Session"],
)
async def check_vad(audio: UploadFile = File(...)) -> VADCheckResponse:
    """
    Check whether an audio buffer contains speech (voice activity detection).

    Expects raw 16-bit mono PCM at 16kHz.
    """
    audio_bytes = await audio.read()
    result = vad_service.detect_speech_segments(audio_bytes)
    return VADCheckResponse(**result)