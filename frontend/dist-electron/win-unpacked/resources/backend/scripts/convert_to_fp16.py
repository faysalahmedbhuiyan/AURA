"""
AURA Backend — Convert Exported ONNX Model to FP16 (Tier 5).
Run ONCE, after download_model.py, before first real generation.

IMPORTANT: this reads/writes at whatever `image_model_path` currently
resolves to in app.config — NOT a hardcoded drive/folder — so it always
operates on the same model the running app actually uses.

Usage (from the backend/ folder, venv activated):
    python scripts/convert_to_fp16.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import onnx
from onnxconverter_common import float16

from app.config import get_settings

SUBMODELS = ["text_encoder", "unet", "vae_encoder", "vae_decoder"]


def convert_one(folder: Path) -> None:
    onnx_path = folder / "model.onnx"
    if not onnx_path.exists():
        print(f"  Skipping {folder.name} (no model.onnx found)")
        return

    print(f"  Converting {folder.name} ...")
    model = onnx.load(str(onnx_path), load_external_data=True)
    model_fp16 = float16.convert_float_to_float16(
        model,
        keep_io_types=True,
    )

    onnx.save(
        model_fp16,
        str(onnx_path),
        save_as_external_data=True,
        all_tensors_to_one_file=True,
        location="model.onnx.data",
    )
    print(f"  Done: {folder.name}")


def main() -> None:
    settings = get_settings()
    model_dir = (Path(__file__).resolve().parent.parent / settings.image_model_path).resolve()

    if not model_dir.exists():
        raise SystemExit(f"Model directory not found: {model_dir}. Run download_model.py first.")

    print(f"Converting model at {model_dir} to fp16...")
    for name in SUBMODELS:
        convert_one(model_dir / name)

    print("\nAll submodels converted to fp16.")


if __name__ == "__main__":
    main()