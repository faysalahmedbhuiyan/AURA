"""
AURA Backend — Convert Exported ONNX Model to FP16 (Tier 5).
Run ONCE, after download_model.py, before first real generation.
"""

from pathlib import Path

import onnx
from onnxconverter_common import float16

MODEL_DIR = Path("D:/AURA/models/sd/sd-turbo-onnx")
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
    if not MODEL_DIR.exists():
        raise SystemExit(f"Model directory not found: {MODEL_DIR}. Run download_model.py first.")

    print(f"Converting model at {MODEL_DIR} to fp16...")
    for name in SUBMODELS:
        convert_one(MODEL_DIR / name)

    print("\nAll submodels converted to fp16.")


if __name__ == "__main__":
    main()