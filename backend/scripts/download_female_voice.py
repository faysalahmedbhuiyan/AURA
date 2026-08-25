"""
AURA Backend — Download a Second Piper Voice (female), for gendered
dialogue in generated videos.

Module: scripts.download_female_voice
Purpose: Your existing Piper voice (en_US-lessac-medium) is used for
         AURA's own voice. This downloads a second, female English
         voice (en_US-amy-medium) purely for character dialogue in
         generated videos — it does NOT change AURA's own voice.

IMPORTANT: this saves to whatever `piper_model_path_female` currently
resolves to in app.config — NOT a hardcoded drive/folder — so the app
always finds it wherever AURA is actually installed.

Usage (from the backend/ folder, venv activated):
    python scripts/download_female_voice.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from app.config import get_settings

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
FILES = ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"]


def main() -> None:
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent
    save_dir = (backend_dir / settings.piper_model_path_female).resolve().parent
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target folder (from current settings): {save_dir}")

    for fname in FILES:
        dest = save_dir / fname
        if dest.exists():
            print(f"Already have {fname}, skipping.")
            continue

        url = f"{BASE_URL}/{fname}"
        print(f"Downloading {fname} ...")
        with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        print(f"Saved: {dest}")

    print(f"\nDone. Female voice model saved to: {save_dir}")
    print("These paths already match your current .env / config.py settings —")
    print("no further changes needed unless you moved image_model_path elsewhere.")


if __name__ == "__main__":
    main()