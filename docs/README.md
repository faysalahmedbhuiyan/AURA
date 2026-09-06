# AURA — Personal AI Operating System

> Offline-first • Modular • Multilingual • Production-quality

AURA is a personal AI operating system built for local, private,
and intelligent computing. It runs entirely on your machine —
no cloud required.

---

## Current Status (as of Phase 13)

| Component                | Status  | Notes                                         |
| ------------------------ | ------- | --------------------------------------------- |
| Backend                  | ✅ Live | FastAPI, 13 phases complete                   |
| Frontend                 | ✅ Live | React + Electron desktop app                  |
| LLM (Ollama)             | ✅ Live | Custom `aura-brain` model (qwen3:4b base)     |
| Voice                    | ✅ Live | faster-whisper (STT) + Piper (TTS)            |
| Memory (RAG)             | ✅ Live | ChromaDB + SQLite                             |
| Knowledge System         | ✅ Live | Web research pipeline, confirm-before-save    |
| Agents (File/System)     | ✅ Live | Extensible, more agents planned               |
| Self Review Engine       | ✅ Live | Python-only (AST-based)                       |
| Self Improvement Planner | ✅ Live | Cross-project (backend + frontend)            |
| Safe Self Modification   | ✅ Live | Confirmed + auto-backed-up writes only        |
| Rollback System          | ✅ Live | Git-based + named snapshots                   |
| Development Journal      | ✅ Live | Append-only session/decision/change log       |
| Advanced Memory System   | ✅ Live | Personal / Knowledge / Decision / Queue tiers |

---

## Tech Stack

| Layer             | Technology                                     |
| ----------------- | ---------------------------------------------- |
| Backend           | Python 3.11, FastAPI, Uvicorn                  |
| AI/LLM            | Ollama (local), custom `aura-brain` (qwen3:4b) |
| Voice STT         | faster-whisper                                 |
| Voice TTS         | Piper (ONNX)                                   |
| Memory            | ChromaDB + SQLite                              |
| Frontend          | React 19 + Vite 8 + Electron 37                |
| Web Search        | ddgs (DuckDuckGo, no API key)                  |
| Content Fetch     | httpx + BeautifulSoup + lxml                   |
| System Monitoring | psutil                                         |
| Version Control   | Git (used by Rollback System)                  |

---

## Quick Start (Backend)

```powershell
cd D:\AURA\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API Docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/v1/health

## Quick Start (Frontend)

```powershell
cd D:\AURA\frontend
npm run dev
```

---

## Languages Supported

Bangla • English • Hindi • Korean (phased rollout)

---

## Project Structure

D:\AURA
├── backend\ ← FastAPI application
│ └── app
│ ├── agents\ ← Phase 7: FileAgent, SystemAgent
│ ├── api\v1\routes\ ← All HTTP endpoints
│ ├── journal\ ← Phase 12: Development Journal
│ ├── modification\ ← Phase 10: Safe Self Modification
│ ├── models\ ← SQLAlchemy ORM models
│ ├── planning\ ← Phase 9: Self Improvement Planner
│ ├── repositories\ ← Data access layer
│ ├── review\ ← Phase 8: Self Review Engine
│ ├── rollback\ ← Phase 11: Rollback System
│ ├── schemas\ ← Pydantic schemas
│ ├── services\ ← Business logic (Ollama, Memory, Research, etc.)
│ └── config.py
├── frontend\ ← React + Electron desktop app
├── docs\ ← All project documentation (this file's folder)
├── backups\ ← Auto-created file backups (Phase 10)
└── database\ ← SQLite + ChromaDB data

---

## Documentation

- `docs/PHASES.md` — Full phase-by-phase specification
- `docs/PROGRESS.md` — Current progress tracker
- `docs/ROADMAP.md` — Task-level roadmap with dates
- `docs/FEATURE_LIST.md` — Feature-by-feature status
- `docs/CHANGELOG.md` — Version history
- `docs/SYSTEM_ARCHITECTURE.md` — Architecture diagrams and tech stack
- `docs/TASKS.md` — Task checklist

---

## License

Licensed by Faymina Group
<<<<<<< HEAD
=======

>>>>>>> 33e4a0622aeb13231b6b60b6686bd4dd9be8a086
