"""
AURA Backend — Voice Assistant Engine Package.

Package: app.voice
Purpose: Phase 21 — transforms AURA into a voice-first assistant on
         top of the existing Whisper (STT) and Piper (TTS) services.
         Adds wake-word detection, voice activity detection (VAD),
         and a session state machine for conversation mode.

Hardware-realistic scope (i5 11th gen, 8GB RAM, no GPU):
- True streaming STT/TTS (token-by-token) is NOT feasible with
  faster-whisper/Piper as currently integrated — this package uses
  chunk-based near-real-time processing instead.
- True full-duplex barge-in (interrupting TTS mid-sentence with new
  speech) is NOT implemented — VAD detects new speech and stops
  playback, which is a practical approximation, not true barge-in.

Modules:
    wake_word_detector    — Lightweight keyword-spot for "Aura"
    vad_service            — Voice activity detection (webrtcvad)
    voice_session_manager   — State machine: idle -> listening ->
                               processing -> speaking -> idle
"""