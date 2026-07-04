# AURA — Personal AI Operating System

> Offline-first • Modular • Multilingual • Production-quality

AURA is a personal AI operating system built for local, private,
and intelligent computing. It runs entirely on your machine —
no cloud required.

---

## Current Status

| Component    | Status     | Version |
| ------------ | ---------- | ------- |
| Backend      | ✅ Live    | 0.1.0   |
| Frontend     | 🔜 Next    | —       |
| LLM (Ollama) | 🔜 Next    | —       |
| Voice        | 🔜 Planned | —       |
| Memory       | 🔜 Planned | —       |

---

## Tech Stack

| Layer     | Technology                    |
| --------- | ----------------------------- |
| Backend   | Python 3.11, FastAPI, Uvicorn |
| AI/LLM    | Ollama (local), Qwen2.5-7B    |
| Voice STT | faster-whisper                |
| Voice TTS | Piper (ONNX)                  |
| Memory    | ChromaDB + SQLite             |
| Frontend  | React + Electron              |

---

## Quick Start (Backend)

```powershell
cd D:\AURA\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API Docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/v1/health

---

---

## Languages Supported

Bangla • English • Hindi • Korean (phased rollout)

---

## License

Open Source — Free to use, modify, and distribute.

## Project Structure
