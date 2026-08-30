# Tier 5 — Integration Guide

## 1. Install remaining Python packages

You already have `onnxruntime-directml`, `optimum`, `diffusers`, `huggingface_hub` sorted.
Add these two (needed by `image_service.py`):

```powershell
cd D:\AURA\backend
.\venv\Scripts\Activate.ps1
pip install psutil numpy
```

(`psutil` is very likely already installed since SystemAgent uses it — check with
`pip show psutil` first.)

## 2. Copy new files into place

| From this delivery                          | To                                                  |
| -------------------------------------------- | ---------------------------------------------------- |
| `backend/scripts/download_model.py`          | `D:\AURA\backend\scripts\download_model.py`           |
| `backend/app/schemas/image.py`               | `D:\AURA\backend\app\schemas\image.py`                |
| `backend/app/services/image_service.py`      | `D:\AURA\backend\app\services\image_service.py`       |
| `backend/app/api/v1/routes/image.py`         | `D:\AURA\backend\app\api\v1\routes\image.py`          |
| `frontend/src/components/ImageGenView.jsx`   | `D:\AURA\frontend\src\components\ImageGenView.jsx`    |

## 3. Add settings to `app/config.py`

Add these fields inside the `Settings` class (near the Voice section):

```python
    # ── Image Generation (Tier 5) ──────────────────────────
    image_model_path: str = "D:/AURA/models/sd/sdxl-turbo-onnx"
    image_output_dir: str = "D:/AURA/assets/generated"
```

## 4. Register the router in `app/main.py`

Add `image` to the existing import block:

```python
from app.api.v1.routes import (agents, chat, db_health, health, nlp, memory,
                                memory_tiers, goals, mentor, voice, voice_session, rollback,
                                journal, research, review, planning, understanding,
                                modification, research_engine, intelligence, advanced_memory,
                                ingestion, vault, computer_control, agents_v2, self_improve,
                                image)   # <-- add this
```

And add one line next to the other `include_router` calls:

```python
app.include_router(image.router, prefix="/api/v1")
```

## 5. Download the model (one-time, ~4GB)

```powershell
cd D:\AURA\backend
.\venv\Scripts\Activate.ps1
python scripts\download_model.py
```

Takes several minutes. Downloads to `D:\AURA\models\sd\sdxl-turbo-onnx`.

## 6. Start the backend and smoke-test

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/image/generate `
  -H "Content-Type: application/json" `
  -d '{\"prompt\": \"a red bicycle in a garden, digital art\"}'
```

First call will be slow (pipeline loads into RAM + DirectML compiles kernels —
can take 1-2 minutes extra the very first time only). Expect **~45-90s per
image** after that, per your hardware notes.

Check `GET /api/v1/image/status` any time to see if the pipeline is loaded
and how much RAM is free.

## 7. Wire up the frontend

In your sidebar navigation component (wherever `MentorView`, `KnowledgeView`
etc. are registered as tabs — same pattern), add:

```jsx
import ImageGenView from "./components/ImageGenView";
// ...
<ImageGenView />
```

## Notes on your 8GB RAM constraint

- `image_service.py` calls Ollama's `/api/generate` with `keep_alive: 0`
  right before every generation — this force-unloads `aura-brain` from RAM
  immediately instead of waiting for Ollama's default 5-minute idle timeout.
- The SDXL Turbo pipeline itself stays loaded in RAM after first use (for
  speed on repeated generations). Call `POST /api/v1/image/unload` when the
  user goes back to heavy chat/agent use, to free that RAM back up.
- If free RAM drops under 800MB when a generation is requested, the service
  returns an error instead of attempting generation (better than a hard
  crash/freeze).
- Resolution is hard-locked at 512x512 and steps capped at 1-4 (SDXL Turbo's
  designed range) — do not raise these on this hardware.

## What's still NOT done (next after this works)

- **Video generation** (Tier 5's other half) — cloud API integration
  (free-tier providers, auto-fallback chain). Separate service, no GPU
  needed. Say the word and I'll draft that next — you'll need to tell me
  which free video APIs you already have accounts/keys for, if any.
- No frontend "generation history" gallery yet — currently each image is
  just a single result on screen. Easy to add via a new SQLite table +
  endpoint if you want persistence.
