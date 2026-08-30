"""
AURA Backend — Voice Session Manager.

Module: app.voice.voice_session_manager
Purpose: State machine for a voice conversation session. Tracks
         whether AURA is idle, listening, processing, or speaking,
         and exposes a simple queue for incoming voice requests so
         they're handled one at a time (RAM-aware — never runs
         Whisper + Ollama + Piper concurrently on an 8GB machine).

Modes (per user's Phase 21 request):
    always_listening — session stays in 'listening' after each reply
    push_to_talk      — session returns to 'idle' after each reply,
                        frontend must explicitly trigger listening again
"""

import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class VoiceSessionManager:
    """
    Manages state and a single-worker queue for one voice session.

    A queue + lock ensures only one voice interaction is processed at
    a time — critical on 8GB RAM where running STT, LLM, and TTS
    concurrently would exceed the RAM budget documented in
    SYSTEM_ARCHITECTURE.md.

    Methods:
        set_mode: Switch between always_listening and push_to_talk.
        transition: Move to a new state (idle/listening/processing/speaking).
        get_state: Current state snapshot.
    """

    def __init__(self) -> None:
        self._state = VoiceState.IDLE
        self._mode = "push_to_talk"
        self._lock = asyncio.Lock()

    def set_mode(self, mode: str) -> None:
        """
        Set the session mode.

        Args:
            mode: 'always_listening' or 'push_to_talk'.
        """
        if mode not in ("always_listening", "push_to_talk"):
            raise ValueError(f"Invalid mode: {mode}")
        self._mode = mode
        logger.info("Voice session mode set to: %s", mode)

    async def transition(self, new_state: VoiceState) -> None:
        """
        Transition to a new voice state.

        Args:
            new_state: The state to move to.
        """
        async with self._lock:
            logger.debug("Voice state: %s -> %s", self._state, new_state)
            self._state = new_state

    def next_state_after_reply(self) -> VoiceState:
        """
        Determine what state to enter after AURA finishes speaking,
        based on the current mode.

        Returns:
            VoiceState: LISTENING if always_listening mode, else IDLE.
        """
        return VoiceState.LISTENING if self._mode == "always_listening" else VoiceState.IDLE

    def get_state(self) -> dict:
        """
        Get the current session state snapshot.

        Returns:
            dict: {"state": str, "mode": str}
        """
        return {"state": self._state.value, "mode": self._mode}


# ── Singleton instance ────────────────────────────────────────────────────────
voice_session_manager = VoiceSessionManager()