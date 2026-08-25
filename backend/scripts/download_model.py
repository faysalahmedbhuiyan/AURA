"""
AURA Backend — SD Turbo Model Downloader (Tier 5).

Module: scripts.download_model
Purpose: One-time script to export SD Turbo (non-XL) to ONNX (fp16)
         so AURA can generate images locally on Intel Iris Xe.
         Run ONCE, then never again.

Why SD Turbo instead of SDXL Turbo:
    SDXL Turbo (~2.6B params) needs a ~5GB UNet — too big for Iris
    Xe's 3.9GB shared VRAM, and Olive-optimized DirectML builds use
    fused ops that don't run on CPU either (no real fallback).
    SD Turbo (~860M params) exported at fp16 with standard ONNX ops
    fits comfortably in both 8GB system RAM and 3.9GB VRAM, AND has
    a genuine CPU fallback path if DirectML ever fails.

IMPORTANT: this saves to whatever `image_model_path` currently resolves
to in app.config (the SAME settings the running app reads at startup)
— NOT a hardcoded drive/folder. That way, wherever AURA is installed,
the app always looks in the exact place this script just saved to. If
you need it somewhere else, set image_model_path in your .env instead
of editing this file.

Usage (from the backend/ folder, venv activated):
    python scripts/download_model.py
"""

import sys
from pathlib import Path

# Make `app.config` importable when run as `python scripts/download_model.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimum.onnxruntime import ORTStableDiffusionPipeline

from app.config import get_settings

MODEL_ID = "stabilityai/sd-turbo"


def _export_pipeline(model_id: str):
    """Export with the lowest peak RAM usage the installed optimum/
    diffusers version supports, falling back gracefully on older
    versions that don't accept these kwargs. low_cpu_mem_usage avoids
    ever holding a full extra fp32 copy of the weights in RAM while
    loading — the single biggest RAM spike during export."""
    import torch

    attempts = [
        dict(export=True, provider="CPUExecutionProvider",
             torch_dtype=torch.float16, low_cpu_mem_usage=True),
        dict(export=True, provider="CPUExecutionProvider",
             low_cpu_mem_usage=True),
        dict(export=True, provider="CPUExecutionProvider"),
    ]
    last_err = None
    for kwargs in attempts:
        try:
            return ORTStableDiffusionPipeline.from_pretrained(model_id, **kwargs)
        except TypeError as e:
            last_err = e
            continue  # this optimum version doesn't support one of the kwargs — try the next
    raise last_err


def main() -> None:
    settings = get_settings()
    # image_model_path is resolved relative to backend/ (this script's
    # parent directory), same as every other relative path in config.py.
    save_dir = (Path(__file__).resolve().parent.parent / settings.image_model_path).resolve()
    save_dir.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {MODEL_ID} to ONNX (low-RAM mode: fp16 + low_cpu_mem_usage)...")
    print("Smaller than SDXL Turbo — safer for 8GB RAM / 3.9GB VRAM.")
    print("Exporting on CPU provider (verification step) — this avoids")
    print("any DirectML VRAM contention during the export itself.")
    print(f"Target folder (from current settings): {save_dir}")

    pipeline = _export_pipeline(MODEL_ID)

    print("Saving ONNX model to disk...")
    pipeline.save_pretrained(save_dir)

    print(f"\nDone. Model saved to: {save_dir}")
    print("You can now delete this script's HuggingFace cache if disk space is tight:")
    print(r"  %USERPROFILE%\.cache\huggingface")


if __name__ == "__main__":
    main()