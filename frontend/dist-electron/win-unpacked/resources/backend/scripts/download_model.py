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

Usage (from D:\\AURA\\backend, venv activated):
    python scripts/download_model.py
"""

from pathlib import Path

from optimum.onnxruntime import ORTStableDiffusionPipeline

MODEL_ID = "stabilityai/sd-turbo"

# D: drive — keeps the 8GB C: drive / RAM untouched.
SAVE_DIR = Path("D:/AURA/models/sd/sd-turbo-onnx")


def main() -> None:
    SAVE_DIR.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {MODEL_ID} to ONNX (fp32, standard ops)...")
    print("Smaller than SDXL Turbo — safer for 8GB RAM / 3.9GB VRAM.")
    print("Exporting on CPU provider (verification step) — this avoids")
    print("any DirectML VRAM contention during the export itself.")

    pipeline = ORTStableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        export=True,
        provider="CPUExecutionProvider",
    )

    print("Saving ONNX model to disk...")
    pipeline.save_pretrained(SAVE_DIR)

    print(f"\nDone. Model saved to: {SAVE_DIR}")
    print("You can now delete this script's HuggingFace cache if disk space is tight:")
    print(r"  %USERPROFILE%\.cache\huggingface")


if __name__ == "__main__":
    main()
