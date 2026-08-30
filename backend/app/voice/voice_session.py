"""AURA Backend — Voice Session Schemas (Phase 21)."""

from pydantic import BaseModel, Field


class SetModeRequest(BaseModel):
    mode: str = Field(..., description="'always_listening' or 'push_to_talk'")


class VoiceStateResponse(BaseModel):
    state: str
    mode: str


class WakeWordCheckResponse(BaseModel):
    detected: bool
    transcript: str


class VADCheckResponse(BaseModel):
    total_frames: int
    speech_frames: int
    speech_ratio: float
    has_speech: bool