"""
AURA Backend — Video Generation Service (Tier 5, video half).

Module: app.services.video_service
Purpose: Text-to-video and image-to-video (photo animation) generation
         via Hugging Face's free Inference Providers — no local GPU
         needed, matches the original Tier 5 plan (image local, video
         cloud with a free tier).

Model: Wan-AI/Wan2.2-TI2V-5B, routed through the "fal-ai" provider.
Honest limitations (see conversation / TIER5_STATUS.md for detail):
    - Free tier is credit-limited (~10 clips/month, not unlimited).
    - Native output is NOT guaranteed 1080p — expect ~720p or lower.
    - No native audio — output is a silent video clip in v1.
    - This does NOT do face-swap / identity-transfer into a separate
      generated character. image_to_video() only ANIMATES the exact
      photo you provide (the same person/subject stays themselves,
      just gets motion) — it does not composite that face onto a
      different generated scene or character.

Requires: HF_TOKEN in .env (free — see docs/HOW_TO_GET_HF_TOKEN.md)
"""

import logging
import time
import uuid
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OUTPUT_DIR = Path(getattr(settings, "video_output_dir", "D:/AURA/assets/generated_video"))
MODEL_ID = "Wan-AI/Wan2.2-TI2V-5B"
PROVIDER = "fal-ai"


class VideoService:
    """Cloud (Hugging Face free tier) video generation — no local GPU needed."""

    def _get_client(self):
        from huggingface_hub import InferenceClient

        token = getattr(settings, "hf_token", None)
        if not token:
            raise ValueError(
                "HF_TOKEN not set in .env — get a free token at "
                "huggingface.co/settings/tokens and add HF_TOKEN=... to .env"
            )
        return InferenceClient(provider=PROVIDER, api_key=token)

    async def generate_text_to_video(self, prompt: str) -> dict:
        """Generate a short silent video clip from a text prompt."""
        start = time.time()
        try:
            client = self._get_client()
        except ValueError as e:
            return {"success": False, "error": str(e)}

        try:
            logger.info("Requesting text-to-video from HF (%s) ...", MODEL_ID)
            video_bytes = client.text_to_video(prompt, model=MODEL_ID)
        except Exception as e:
            logger.exception("Video generation failed")
            return {"success": False, "error": f"Video generation failed: {e}"}

        return self._save(video_bytes, prompt, start)

    async def generate_image_to_video(self, image_path: str, prompt: str = "") -> dict:
        """
        Animate an existing photo into a short video clip. The subject
        in the photo stays the same subject — this ONLY adds motion to
        what's already in the image, it does not swap faces or identities.
        """
        start = time.time()
        try:
            client = self._get_client()
        except ValueError as e:
            return {"success": False, "error": str(e)}

        img_file = Path(image_path)
        if not img_file.exists():
            return {"success": False, "error": f"Image not found: {image_path}"}

        try:
            logger.info("Requesting image-to-video from HF (%s) ...", MODEL_ID)
            with open(img_file, "rb") as f:
                image_bytes = f.read()
            video_bytes = client.image_to_video(
                image_bytes, prompt=prompt or None, model=MODEL_ID,
            )
        except Exception as e:
            logger.exception("Video generation failed")
            return {"success": False, "error": f"Video generation failed: {e}"}

        return self._save(video_bytes, prompt or f"animate:{img_file.name}", start)

    def _save(self, video_bytes: bytes, prompt: str, start: float) -> dict:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex[:12]}.mp4"
        file_path = OUTPUT_DIR / file_name
        with open(file_path, "wb") as f:
            f.write(video_bytes)

        duration_ms = int((time.time() - start) * 1000)
        logger.info("Video generated in %dms -> %s", duration_ms, file_path)

        return {
            "success": True,
            "file_path": str(file_path),
            "file_name": file_name,
            "prompt": prompt,
            "duration_ms": duration_ms,
        }


video_service = VideoService()
