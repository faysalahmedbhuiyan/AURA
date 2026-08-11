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

Usage (from D:\\AURA\\backend, venv activated):
    python scripts/download_realistic_model.py
"""

from pathlib import Path

from optimum.onnxruntime import ORTStableDiffusionPipeline

MODEL_ID = "SG161222/Realistic_Vision_V5.1_noVAE"

# D: drive — separate folder from the fast SD-Turbo model, both coexist.
SAVE_DIR = Path("D:/AURA/models/sd/realistic-vision-onnx")


def main() -> None:
    SAVE_DIR.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {MODEL_ID} to ONNX...")
    print("Larger model than SD-Turbo (~4GB) — this will take a while.")
    print("Exporting on CPU provider (avoids any VRAM issues during export).")

    pipeline = ORTStableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        export=True,
        provider="CPUExecutionProvider",
    )

    print("Saving ONNX model to disk...")
    pipeline.save_pretrained(SAVE_DIR)

    print(f"\nDone. Model saved to: {SAVE_DIR}")
    print("This model is SLOW on CPU (~15-20 min/image) — that's expected,")
    print("it's not a bug. Use it only when you explicitly want realism.")


if __name__ == "__main__":
    main()
