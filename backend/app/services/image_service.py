"""
AURA Backend — Image Generation Service (Tier 5).

Module: app.services.image_service
Purpose: Local text-to-image generation using SDXL Turbo (ONNX) on
         Intel Iris Xe via DirectML. Designed for 8GB RAM machines:
         - Pipeline is lazy-loaded (not on server startup).
         - Ollama's LLM is unloaded (keep_alive=0) right before a
           generation to free RAM headroom for the diffusion model.
         - Pipeline can be manually unloaded via /image/unload.

Hardware target:
    CPU: Intel i5 11th Gen | RAM: 8GB | GPU: Intel Iris Xe (DirectML)
    Resolution fixed at 512x512 — safe ceiling for 8GB RAM.
"""

import gc
import logging
import time
import uuid
from pathlib import Path

import httpx
import psutil

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OUTPUT_DIR = Path(settings.image_output_dir)
MODEL_PATH = Path(settings.image_model_path)


class ImageService:
    """Lazy-loaded local SDXL Turbo generation, RAM-aware."""

    def __init__(self) -> None:
        self._pipeline = None  # loaded on first generate() call
        self._provider = "not loaded yet"

    # ── RAM guard ─────────────────────────────────────────────────
    async def _unload_ollama(self) -> None:
        """Ask Ollama to drop the LLM from memory immediately.

        Ollama keeps models resident for a keep_alive window (default
        5 min). On an 8GB machine, having aura-brain AND SDXL Turbo
        loaded at once risks an OOM crash — so we force-unload the
        LLM right before every image generation.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_model, "keep_alive": 0},
                )
                logger.info("Ollama model unloaded to free RAM for image gen.")
        except Exception as e:
            # Non-fatal — Ollama may not be running at all, that's fine.
            logger.warning("Could not unload Ollama (may not be running): %s", e)

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"SD Turbo ONNX model not found at {MODEL_PATH}. "
                f"Run scripts/download_model.py first."
            )

        from optimum.onnxruntime import ORTStableDiffusionPipeline

        if settings.image_try_gpu:
            try:
                logger.info("image_try_gpu=True — attempting DirectML load...")
                self._pipeline = ORTStableDiffusionPipeline.from_pretrained(
                    str(MODEL_PATH), provider="DmlExecutionProvider",
                )
                self._provider = "DmlExecutionProvider"
                logger.info("Pipeline loaded on GPU (DirectML).")
                return self._pipeline
            except Exception as e:
                logger.warning(
                    "DirectML failed (%s) — falling back to the known-working "
                    "CPU path.", e
                )

        logger.info("Loading SD Turbo pipeline on CPU ...")
        self._pipeline = ORTStableDiffusionPipeline.from_pretrained(
            str(MODEL_PATH), provider="CPUExecutionProvider",
        )
        self._provider = "CPUExecutionProvider"
        logger.info("Pipeline loaded on CPU.")
        return self._pipeline

    def unload_pipeline(self) -> bool:
        """Free the pipeline from RAM. Call this after a generation
        burst if the user is about to go back to heavy chat use."""
        if self._pipeline is None:
            return False
        self._pipeline = None
        self._provider = "not loaded yet"
        gc.collect()
        logger.info("Image pipeline unloaded from RAM.")
        return True

    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def status(self) -> dict:
        return {
            "pipeline_loaded": self.is_loaded(),
            "model_path": str(MODEL_PATH),
            "provider": self._provider,
            "ram_available_mb": int(psutil.virtual_memory().available / (1024 * 1024)),
        }

    # ── Generation ────────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 1,
        seed: int | None = None,
    ) -> dict:
        start = time.time()

        # Guard: warn (but don't block) if RAM is already critically low.
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        if available_mb < 800:
            return {
                "success": False,
                "error": (
                    f"Only {available_mb:.0f}MB RAM free — too low to safely "
                    f"generate. Close other apps and try again."
                ),
            }

        await self._unload_ollama()

        try:
            pipeline = self._load_pipeline()
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

        import numpy as np

        used_seed = seed if seed is not None else int(time.time())
        generator = np.random.RandomState(used_seed)

        try:
            result = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt or None,
                num_inference_steps=steps,
                guidance_scale=0.0,  # SDXL Turbo: guidance must be 0
                height=512,
                width=512,
                generator=generator,
            )
            image = result.images[0]
        except Exception as e:
            logger.exception("Image generation failed")
            return {"success": False, "error": f"Generation failed: {e}"}

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex[:12]}.png"
        file_path = OUTPUT_DIR / file_name
        image.save(file_path)

        duration_ms = int((time.time() - start) * 1000)
        logger.info("Image generated in %dms -> %s", duration_ms, file_path)

        return {
            "success": True,
            "file_path": str(file_path),
            "file_name": file_name,
            "prompt": prompt,
            "seed": used_seed,
            "duration_ms": duration_ms,
        }


image_service = ImageService()