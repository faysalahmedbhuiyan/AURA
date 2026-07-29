"""
AURA Backend — Image Generation Service (Tier 5).

Module: app.services.image_service
Purpose: Local text-to-image generation, two quality modes:
    - "fast": SD-Turbo, 1 step, ~1-2 min/image (existing, unchanged default)
    - "realistic": Realistic Vision V5.1, ~20-25 steps, ~15-20 min/image

Hardware target:
    CPU: Intel i5 11th Gen | RAM: 8GB | GPU: Intel Iris Xe (DirectML)
    Resolution fixed at 512x512 — safe ceiling for 8GB RAM.

RAM/CPU discipline:
    - Ollama's LLM is force-unloaded before every generation.
    - ONNX Runtime threads capped at ~70% of logical CPUs, leaving
      headroom for the OS/UI instead of pegging every core.
    - Only one pipeline (fast OR realistic) stays loaded at a time —
      switching quality unloads the other to stay within 8GB RAM.
"""

import gc
import logging
import math
import os
import time
import uuid
from pathlib import Path

import httpx
import psutil

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OUTPUT_DIR = Path(settings.image_output_dir)
FAST_MODEL_PATH = Path(settings.image_model_path)
REALISTIC_MODEL_PATH = Path(
    getattr(settings, "image_realistic_model_path", "D:/AURA/models/sd/realistic-vision-onnx")
)

# Leave ~30% of logical CPUs free for the OS/UI/other AURA features.
_CPU_THREAD_CAP = max(1, math.floor((os.cpu_count() or 4) * 0.7))


class ImageService:
    """Lazy-loaded local image generation, RAM/CPU-aware, two quality modes."""

    def __init__(self) -> None:
        self._pipeline = None
        self._loaded_quality: str | None = None  # "fast" | "realistic" | None
        self._provider = "not loaded yet"

    # ── RAM guard ─────────────────────────────────────────────────
    async def _unload_ollama(self) -> None:
        """Force-unload the LLM from Ollama's RAM before generating."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_model, "keep_alive": 0},
                )
                logger.info("Ollama model unloaded to free RAM for image gen.")
        except Exception as e:
            logger.warning("Could not unload Ollama (may not be running): %s", e)

    def _session_options(self):
        from onnxruntime import SessionOptions

        opts = SessionOptions()
        opts.intra_op_num_threads = _CPU_THREAD_CAP
        opts.inter_op_num_threads = max(1, _CPU_THREAD_CAP // 2)
        return opts

    def _load_pipeline(self, quality: str):
        if self._pipeline is not None and self._loaded_quality == quality:
            return self._pipeline

        if self._pipeline is not None:
            self.unload_pipeline()

        model_path = FAST_MODEL_PATH if quality == "fast" else REALISTIC_MODEL_PATH
        pipeline_label = "SD-Turbo (fast)" if quality == "fast" else "Realistic Vision (realistic)"

        if not model_path.exists():
            script = "download_model.py" if quality == "fast" else "download_realistic_model.py"
            raise FileNotFoundError(
                f"{pipeline_label} model not found at {model_path}. "
                f"Run scripts/{script} first."
            )

        from optimum.onnxruntime import ORTStableDiffusionPipeline

        # DirectML (Iris Xe, 3.9GB shared VRAM) reliably OOMs mid-generation
        # on this hardware for both models — it loads fine but crashes during
        # denoising. Proven-working path: force CPU only, no DirectML attempt.
        logger.info(
            "Loading %s on CPU (capped at %d threads, ~70%% of logical CPUs) ...",
            pipeline_label, _CPU_THREAD_CAP,
        )
        self._pipeline = ORTStableDiffusionPipeline.from_pretrained(
            str(model_path), provider="CPUExecutionProvider",
            session_options=self._session_options(),
        )
        self._provider = "CPUExecutionProvider"
        logger.info("%s loaded on CPU.", pipeline_label)

        self._loaded_quality = quality
        return self._pipeline

    def unload_pipeline(self) -> bool:
        if self._pipeline is None:
            return False
        self._pipeline = None
        self._loaded_quality = None
        self._provider = "not loaded yet"
        gc.collect()
        logger.info("Image pipeline unloaded from RAM.")
        return True

    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def status(self) -> dict:
        return {
            "pipeline_loaded": self.is_loaded(),
            "loaded_quality": self._loaded_quality,
            "model_path": str(FAST_MODEL_PATH if self._loaded_quality != "realistic" else REALISTIC_MODEL_PATH),
            "provider": self._provider,
            "cpu_thread_cap": _CPU_THREAD_CAP,
            "ram_available_mb": int(psutil.virtual_memory().available / (1024 * 1024)),
        }

    # ── Generation ────────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int | None = None,
        seed: int | None = None,
        quality: str = "fast",
    ) -> dict:
        start = time.time()

        if quality not in ("fast", "realistic"):
            quality = "fast"

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
            pipeline = self._load_pipeline(quality)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

        import numpy as np

        used_seed = seed if seed is not None else int(time.time())
        generator = np.random.RandomState(used_seed)

        if quality == "fast":
            actual_steps = steps or 1
            guidance_scale = 0.0  # required for Turbo models
        else:
            actual_steps = steps or 22
            guidance_scale = 7.0  # standard CFG for a non-Turbo model
            if not negative_prompt:
                negative_prompt = (
                    "cartoon, illustration, painting, drawing, anime, 3d render, "
                    "blurry, low quality, distorted, deformed"
                )

        est_minutes = "1-2" if quality == "fast" else "15-20"
        logger.info(
            "Generating (%s quality, %d steps, guidance=%.1f) — est. %s min",
            quality, actual_steps, guidance_scale, est_minutes,
        )

        try:
            result = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt or None,
                num_inference_steps=actual_steps,
                guidance_scale=guidance_scale,
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
            "quality": quality,
            "provider": self._provider,
        }


image_service = ImageService()