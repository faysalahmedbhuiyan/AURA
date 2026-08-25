"""
AURA Backend — Realistic Vision Model Downloader (Tier 5, quality upgrade).

Module: scripts.download_realistic_model
Purpose: One-time script to export "Realistic Vision V5.1" (a
         photorealistic SD1.5 checkpoint) to ONNX, alongside the
         existing fast SD-Turbo model. Run ONCE, then never again.

Why this model:
    Same architecture family as SD-Turbo (so the same ORTStableDiffusion-
    Pipeline / optimum export path works, no new dependency risk), but
    trained for photorealism instead of speed. Trade-off: needs ~20-25
    steps with classifier-free guidance (not 1 step like Turbo), so it's
    much slower on CPU — budget ~15-20 minutes per image on this hardware.

IMPORTANT: this saves to whatever `image_realistic_model_path` currently
resolves to in app.config — NOT a hardcoded drive/folder — so the app
always finds it wherever AURA is actually installed. Override via .env
if you want a different location.

Usage (from the backend/ folder, venv activated):
    python scripts/download_realistic_model.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimum.onnxruntime import ORTStableDiffusionPipeline

from app.config import get_settings

MODEL_ID = "SG161222/Realistic_Vision_V5.1_noVAE"


def main() -> None:
    settings = get_settings()
    save_dir = (Path(__file__).resolve().parent.parent / settings.image_realistic_model_path).resolve()
    save_dir.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {MODEL_ID} to ONNX...")
    print("Larger model than SD-Turbo (~4GB) — this will take a while.")
    print("Exporting on CPU provider (avoids any VRAM issues during export).")
    print(f"Target folder (from current settings): {save_dir}")

    pipeline = ORTStableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        export=True,
        provider="CPUExecutionProvider",
    )

    print("Saving ONNX model to disk...")
    pipeline.save_pretrained(save_dir)

    print(f"\nDone. Model saved to: {save_dir}")
    print("This model is SLOW on CPU (~15-20 min/image) — that's expected,")
    print("it's not a bug. Use it only when you explicitly want realism.")


if __name__ == "__main__":
    main()