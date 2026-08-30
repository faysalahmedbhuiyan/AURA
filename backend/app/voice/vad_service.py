"""
AURA Backend — Voice Activity Detection Service.

Module: app.voice.vad_service
Purpose: Detects whether an audio frame contains speech, using
         webrtcvad (lightweight, CPU-only, no GPU needed). Used to
         know when the user has started/stopped talking, enabling
         continuous listening mode without transcribing silence.
"""

import logging

import webrtcvad

logger = logging.getLogger(__name__)

# webrtcvad requires 16-bit mono PCM at 8/16/32/48kHz, in 10/20/30ms frames.
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE_BYTES = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000) * 2)  # 16-bit = 2 bytes/sample


class VADService:
    """
    Wraps webrtcvad for speech/silence detection.

    Methods:
        is_speech: Check if a single 30ms PCM frame contains speech.
        detect_speech_segments: Find speech start/end within a longer buffer.
    """

    def __init__(self, aggressiveness: int = 2) -> None:
        """
        Args:
            aggressiveness: 0 (least aggressive filtering) to 3 (most
                             aggressive, filters more non-speech). 2 is
                             a balanced default.
        """
        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, frame: bytes) -> bool:
        """
        Check if a single audio frame contains speech.

        Args:
            frame: Raw 16-bit mono PCM bytes, exactly FRAME_SIZE_BYTES long,
                   sampled at SAMPLE_RATE.

        Returns:
            bool: True if speech is detected in this frame.
        """
        if len(frame) != FRAME_SIZE_BYTES:
            logger.warning(
                "VAD frame size mismatch: got %d bytes, expected %d",
                len(frame), FRAME_SIZE_BYTES,
            )
            return False
        try:
            return self._vad.is_speech(frame, SAMPLE_RATE)
        except Exception as e:
            logger.warning("VAD check failed: %s", e)
            return False

    def detect_speech_segments(self, audio_bytes: bytes) -> dict:
        """
        Scan a longer audio buffer and report the speech ratio.

        Args:
            audio_bytes: Raw 16-bit mono PCM at SAMPLE_RATE.

        Returns:
            dict: {
                "total_frames": int,
                "speech_frames": int,
                "speech_ratio": float,
                "has_speech": bool,
            }
        """
        frames = [
            audio_bytes[i:i + FRAME_SIZE_BYTES]
            for i in range(0, len(audio_bytes) - FRAME_SIZE_BYTES + 1, FRAME_SIZE_BYTES)
        ]
        speech_count = sum(1 for f in frames if self.is_speech(f))
        total = len(frames) or 1
        ratio = round(speech_count / total, 2)

        return {
            "total_frames": len(frames),
            "speech_frames": speech_count,
            "speech_ratio": ratio,
            "has_speech": ratio > 0.1,  # >10% of frames contain speech
        }


# ── Singleton instance ────────────────────────────────────────────────────────
vad_service = VADService()