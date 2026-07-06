"""
AURA Backend — Piper Text-to-Speech Service.

Module: app.services.tts_service
Purpose: Converts text to speech using Piper TTS (offline, ONNX-based).
         Supports multiple languages via separate voice models.
         Uses on-demand loading to optimize 8GB RAM.

Current voice: en_US-lessac-medium (English)
Planned: bn_BD (Bangla), hi_IN (Hindi), ko_KR (Korean)

Voice models are configured via .env — no code change needed
when adding new language support.

API Note (piper-tts 1.4.2):
    Correct method: PiperVoice.synthesize_wav(text, wav_file, set_wav_format=True)
    set_wav_format=True → Piper sets channels, sample width, frame rate automatically.
"""

import gc
import logging
import uuid
import wave
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSService:
    """
    Text-to-Speech service using Piper TTS.

    Uses on-demand model loading — model loaded per request,
    unloaded after to free ~100MB RAM.

    Designed for multi-language expansion:
    - Add new voice model to /models/
    - Update PIPER_MODEL_PATH in .env
    - No code changes required

    Methods:
        speak: Convert text to audio file.
        speak_bytes: Convert text to audio bytes.
        is_available: Check if Piper is ready.
    """

    def __init__(self) -> None:
        self.model_path = Path(settings.piper_model_path).resolve()
        self.model_config = Path(settings.piper_model_config).resolve()
        self.output_dir = Path(settings.voice_output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_model(self):
        """
        Load Piper voice model on demand.

        Returns:
            piper.PiperVoice: Loaded voice model instance.

        Raises:
            FileNotFoundError: If model files don't exist.
            RuntimeError: If model loading fails.
        """
        try:
            from piper import PiperVoice

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Piper model not found: {self.model_path}\n"
                    "Please download the voice model to D:\\AURA\\models\\"
                )

            logger.info("Loading Piper model: %s", self.model_path.name)
            voice = PiperVoice.load(
                str(self.model_path),
                config_path=str(self.model_config),
                use_cuda=False,
            )
            logger.info("Piper model loaded successfully")
            return voice

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to load Piper model: %s", e)
            raise RuntimeError(f"TTS model load failed: {str(e)}")

    async def speak(
        self,
        text: str,
        output_filename: str | None = None,
    ) -> Path:
        """
        Convert text to speech and save as WAV file.

        Uses piper-tts 1.4.2 correct API:
            synthesize_wav(text, wav_file, set_wav_format=True)
        set_wav_format=True → Piper automatically configures
        channels, sample width, and frame rate on the wav_file.

        Args:
            text: Text to convert to speech.
            output_filename: Optional output filename.
                             Auto-generated UUID if None.

        Returns:
            Path: Path to the generated WAV file.

        Raises:
            ValueError: If text is empty.
            RuntimeError: If synthesis produces no audio.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty for TTS")

        if output_filename is None:
            output_filename = f"aura_speech_{uuid.uuid4().hex[:8]}.wav"

        output_path = self.output_dir / output_filename

        try:
            voice = self._load_model()

            # synthesize_wav with set_wav_format=True —
            # Piper handles all WAV header configuration automatically
            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize_wav(
                    text,
                    wav_file,
                    set_wav_format=True,
                )

            # Verify audio was actually written
            file_size = output_path.stat().st_size
            if file_size <= 44:
                raise RuntimeError(
                    "TTS produced empty audio — no frames written"
                )

            logger.info(
                "TTS synthesized: %s (%d chars, %d bytes)",
                output_path.name,
                len(text),
                file_size,
            )
            return output_path

        except Exception as e:
            if output_path.exists():
                output_path.unlink()
            logger.error("TTS synthesis failed: %s", e)
            raise RuntimeError(f"TTS error: {str(e)}")
        finally:
            gc.collect()
            logger.info("Piper model unloaded — RAM freed")

    async def speak_bytes(self, text: str) -> bytes:
        """
        Convert text to speech and return raw WAV bytes.

        Used when audio needs to be returned directly
        in HTTP response without saving to disk.

        Args:
            text: Text to convert to speech.

        Returns:
            bytes: WAV audio data.

        Raises:
            RuntimeError: If synthesis fails.
        """
        output_path = await self.speak(text)
        try:
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            output_path.unlink()
            return audio_bytes
        except Exception as e:
            raise RuntimeError(f"TTS bytes error: {str(e)}")

    def is_available(self) -> bool:
        """
        Check if Piper TTS is installed and model exists.

        Returns:
            bool: True if Piper is ready to use.
        """
        try:
            import piper  # noqa: F401
            return self.model_path.exists()
        except ImportError:
            return False


# ── Singleton instance ────────────────────────────────────────────────────────
tts_service = TTSService()