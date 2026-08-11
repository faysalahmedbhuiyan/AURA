"""
AURA Backend — Download a Second Piper Voice (female), for gendered
dialogue in generated videos.

Module: scripts.download_female_voice
Purpose: Your existing Piper voice (en_US-lessac-medium) is used for
         AURA's own voice. This downloads a second, female English
         voice (en_US-amy-medium) purely for character dialogue in
         generated videos — it does NOT change AURA's own voice.

Usage (from D:\\AURA\\backend, venv activated):
    python scripts/download_female_voice.py
"""

from pathlib import Path

import httpx

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
FILES = ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"]

SAVE_DIR = Path("D:/AURA/models/piper")


def main() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    for fname in FILES:
        dest = SAVE_DIR / fname
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

    print(f"\nDone. Female voice model saved to: {SAVE_DIR}")
    print("Add these to config.py / .env:")
    print(f'  piper_model_path_female = "{SAVE_DIR / "en_US-amy-medium.onnx"}"')
    print(f'  piper_model_config_female = "{SAVE_DIR / "en_US-amy-medium.onnx.json"}"')


if __name__ == "__main__":
    main()
