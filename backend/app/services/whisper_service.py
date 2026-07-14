"""
AURA Backend — Whisper Speech-to-Text Service.

Module: app.services.whisper_service
Purpose: Converts audio files to text using faster-whisper.
         Supports Bangla, English, Hindi, Korean offline.
         Uses on-demand model loading to optimize 8GB RAM.

Model: base (multilingual, ~74MB, ~500MB RAM when loaded)
Device: CPU (no GPU required)
Compute: int8 (fastest on CPU, minimal quality loss)
"""

import logging
import tempfile
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Language code mapping ─────────────────────────────────────────────────────
LANGUAGE_MAP = {
    "bn": "bn",   # Bangla
    "en": "en",   # English
    "hi": "hi",   # Hindi
    "ko": "ko",   # Korean
}

# ── Supported audio formats ───────────────────────────────────────────────────
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}


class WhisperService:
    """
    Speech-to-Text service using faster-whisper.

    Uses on-demand model loading — model is loaded only when
    a transcription request arrives and unloaded after completion
    to free RAM for other services.

    Supports: Bangla, English, Hindi, Korean (offline)

    Methods:
        transcribe_file: Transcribe an audio file to text.
        transcribe_bytes: Transcribe audio bytes to text.
        is_available: Check if faster-whisper is ready.
    """

    def __init__(self) -> None:
        self._model = None
        self.model_size = settings.whisper_model_size
        self.device = settings.whisper_device
        self.compute_type = settings.whisper_compute_type

    def _load_model(self):
        """
        Load Whisper model into memory on demand.

        Called only when transcription is needed.
        Model stays loaded until explicitly unloaded.
        """
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(
                    "Loading Whisper model: %s on %s",
                    self.model_size,
                    self.device,
                )
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error("Failed to load Whisper model: %s", e)
                raise RuntimeError(f"Whisper model load failed: {str(e)}")
        return self._model

    def _unload_model(self) -> None:
        """
        Unload Whisper model from memory after use.

        Frees ~500MB RAM for other services.
        """
        if self._model is not None:
            del self._model
            self._model = None
            import gc
            gc.collect()
            logger.info("Whisper model unloaded — RAM freed")

    async def transcribe_file(
        self,
        file_path: str | Path,
        language: str = "en",
    ) -> dict:
        """
        Transcribe an audio file to text.

        Loads model on demand, transcribes, then unloads model
        to free RAM. Supports multilingual transcription.

        Args:
            file_path: Path to the audio file.
            language: Language code (bn, en, hi, ko).
                      None = auto-detect language.

        Returns:
            dict: {
                "text": transcribed text,
                "language": detected language,
                "duration": audio duration in seconds,
                "segments": list of timed segments
            }

        Raises:
            FileNotFoundError: If audio file does not exist.
            ValueError: If audio format is not supported.
            RuntimeError: If transcription fails.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {file_path.suffix}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        whisper_lang = LANGUAGE_MAP.get(language, None)

        try:
            model = self._load_model()
            segments, info = model.transcribe(
                str(file_path),
                language=whisper_lang,
                beam_size=5,
                vad_filter=True,           # Remove silence
                vad_parameters={
                    "min_silence_duration_ms": 500,
                },
            )

            segment_list = []
            full_text_parts = []

            for segment in segments:
                segment_list.append({
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                })
                full_text_parts.append(segment.text.strip())

            full_text = " ".join(full_text_parts).strip()

            logger.info(
                "Transcribed %s — lang: %s, duration: %.1fs",
                file_path.name,
                info.language,
                info.duration,
            )

            return {
                "text": full_text,
                "language": info.language,
                "duration": round(info.duration, 2),
                "segments": segment_list,
            }

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            # Corrupt/near-empty audio (e.g. an extremely short recording)
            # commonly raises an EOF-style error from the decoder. Treat
            # this as "nothing was said" rather than a hard 500 error.
            if "End of file" in str(e) or "Invalid data" in str(e):
                return {
                    "text": "", "language": language,
                    "duration": 0.0, "segments": [],
                }
            raise RuntimeError(f"Transcription error: {str(e)}")
        finally:
            # Always unload after transcription to free RAM
            self._unload_model()

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: str = "en",
        suffix: str = ".wav",
    ) -> dict:
        """
        Transcribe audio bytes to text.

        Saves bytes to a temp file, transcribes, then deletes.
        Used when audio comes directly from HTTP upload.

        Args:
            audio_bytes: Raw audio file bytes.
            language: Language code (bn, en, hi, ko).
            suffix: File extension (.wav, .mp3, etc).

        Returns:
            dict: Same as transcribe_file().

        Raises:
            RuntimeError: If transcription fails.
        """
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            result = await self.transcribe_file(tmp_path, language)
            return result
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def is_available(self) -> bool:
        """
        Check if faster-whisper is importable and ready.

        Returns:
            bool: True if faster-whisper is installed.
        """
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False


# ── Singleton instance ────────────────────────────────────────────────────────
whisper_service = WhisperService()