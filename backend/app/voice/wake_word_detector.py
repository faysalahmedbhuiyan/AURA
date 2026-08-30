"""
AURA Backend — Wake Word Detector.

Module: app.voice.wake_word_detector
Purpose: Detects the wake phrase "Hey Aura" (and Bangla equivalent)
         in a short audio chunk. Uses the EXISTING WhisperService
         (already loaded on-demand) rather than a separate always-on
         wake-word model — no new heavy dependency, at the cost of
         being slightly slower than a dedicated wake-word engine
         (e.g. Porcupine). Acceptable tradeoff for 8GB RAM.

Design note: This is NOT an always-on listener by itself — the
frontend/voice_session_manager decides when to check a chunk for the
wake word (e.g. on short rolling audio buffers), keeping Whisper from
running continuously.
"""

import logging
import re

from app.services.whisper_service import whisper_service

logger = logging.getLogger(__name__)

WAKE_PATTERNS = [
    re.compile(r"\baura\b", re.IGNORECASE),
    re.compile(r"অরা", re.IGNORECASE),
    re.compile(r"অরা", re.IGNORECASE),
]


class WakeWordDetector:
    """
    Detects the "Hey Aura" wake phrase in a short audio clip.

    Methods:
        check_audio_bytes: Transcribe a short audio chunk and check
                            for the wake phrase.
    """

    async def check_audio_bytes(self, audio_bytes: bytes, language: str = "en") -> dict:
        """
        Check if a short audio chunk contains the wake phrase.

        Args:
            audio_bytes: Raw audio bytes (WAV format expected, matching
                         WhisperService's existing input contract).
            language: Language hint for transcription.

        Returns:
            dict: {"detected": bool, "transcript": str}
        """
        try:
            result = await whisper_service.transcribe_bytes(audio_bytes, language)
            transcript = result.get("text", "")
        except Exception as e:
            logger.warning("Wake word check failed to transcribe: %s", e)
            return {"detected": False, "transcript": ""}

        detected = any(p.search(transcript) for p in WAKE_PATTERNS)
        return {"detected": detected, "transcript": transcript}


# ── Singleton instance ────────────────────────────────────────────────────────
wake_word_detector = WakeWordDetector()