from pathlib import Path

from optimum.onnxruntime import ORTStableDiffusionXLPipeline

MODEL_ID = "stabilityai/sdxl-turbo"
SAVE_DIR = Path("D:/AURA/models/sd/sdxl-turbo-onnx")

SAVE_DIR.parent.mkdir(parents=True, exist_ok=True)

print("Downloading and exporting SDXL Turbo...")
print("This may take several minutes on the first run.")

pipeline = ORTStableDiffusionXLPipeline.from_pretrained(
    MODEL_ID,
    export=True,
    provider="DmlExecutionProvider",
)

print("Saving model...")
pipeline.save_pretrained(SAVE_DIR)

print(f"\nDone!")
print(f"Model saved to: {SAVE_DIR}")