"""
AURA Backend — Video Audio Service (Tier 5, video half).

Module: app.services.video_audio_service
Purpose: Adds sound to silent generated video clips —
         1. Synthesizes dialogue lines via Piper TTS, picking a male
            or female voice per line (reuses existing tts_service.py
            infrastructure, just adds a second voice model).
         2. Concatenates the dialogue lines into one audio track.
         3. Muxes that audio onto the silent video via ffmpeg.

Requires: ffmpeg on PATH (see docs — winget install ffmpeg), and a
          second Piper voice model for the opposite gender from the
          existing default (see download_female_voice.py).
"""

import gc
import logging
import subprocess
import uuid
import wave
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AUDIO_TMP_DIR = Path(getattr(settings, "video_output_dir", "D:/AURA/assets/generated_video")) / "_audio_tmp"


class DialogueLine:
    def __init__(self, text: str, gender: str = "male") -> None:
        self.text = text
        self.gender = gender  # "male" | "female"


class VideoAudioService:
    """Synthesizes gendered dialogue and muxes it onto a video."""

    def _voice_paths(self, gender: str) -> tuple[Path, Path]:
        """Return (model_path, config_path) for the requested gender."""
        if gender == "female":
            model = Path(getattr(settings, "piper_model_path_female", ""))
            config = Path(getattr(settings, "piper_model_config_female", ""))
        else:
            model = Path(settings.piper_model_path)
            config = Path(settings.piper_model_config)

        if not model or not model.exists():
            raise FileNotFoundError(
                f"Piper {gender} voice model not found at {model}. "
                f"Run scripts/download_female_voice.py if this is the female voice."
            )
        return model, config

    def _synthesize_line(self, line: DialogueLine, index: int) -> Path:
        from piper import PiperVoice

        model_path, config_path = self._voice_paths(line.gender)
        voice = PiperVoice.load(str(model_path), config_path=str(config_path), use_cuda=False)

        AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = AUDIO_TMP_DIR / f"line_{index}_{uuid.uuid4().hex[:6]}.wav"

        with wave.open(str(out_path), "wb") as wav_file:
            voice.synthesize_wav(line.text, wav_file, set_wav_format=True)

        del voice
        gc.collect()
        return out_path

    def _concat_audio(self, wav_paths: list[Path]) -> Path:
        """Concatenate wav files back-to-back using ffmpeg's concat demuxer."""
        list_file = AUDIO_TMP_DIR / f"concat_{uuid.uuid4().hex[:6]}.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in wav_paths:
                f.write(f"file '{p.resolve()}'\n")

        merged = AUDIO_TMP_DIR / f"merged_{uuid.uuid4().hex[:6]}.wav"
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(merged),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return merged

    def add_dialogue_to_video(self, video_path: str, lines: list[DialogueLine]) -> dict:
        """
        Synthesize each dialogue line with the right gender voice,
        concatenate them, and mux the result onto the given video.
        Returns the path to a NEW video file (original untouched).
        """
        video_file = Path(video_path)
        if not video_file.exists():
            return {"success": False, "error": f"Video not found: {video_path}"}
        if not lines:
            return {"success": False, "error": "No dialogue lines provided."}

        try:
            wav_paths = [self._synthesize_line(line, i) for i, line in enumerate(lines)]
            merged_audio = self._concat_audio(wav_paths)

            output_path = video_file.parent / f"{video_file.stem}_with_audio.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-i", str(merged_audio),
                "-c:v", "copy", "-c:a", "aac",
                "-shortest",
                str(output_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Cleanup temp wavs
            for p in wav_paths:
                p.unlink(missing_ok=True)
            merged_audio.unlink(missing_ok=True)

            return {"success": True, "file_path": str(output_path), "file_name": output_path.name}

        except FileNotFoundError as e:
            return {
                "success": False,
                "error": f"{e}. Is ffmpeg installed and on PATH? (winget install ffmpeg)",
            }
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg failed: %s", e.stderr.decode(errors="ignore") if e.stderr else e)
            return {"success": False, "error": "ffmpeg failed — is it installed and on PATH?"}


video_audio_service = VideoAudioService()
