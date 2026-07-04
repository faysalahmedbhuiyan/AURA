# AURA Roadmap

> Rule: Never implement a feature before its dependency is complete.

---

## Phase 0 — Foundation ✅ COMPLETE

**Goal:** Backend skeleton, environment setup, health check

| Task                                   | Status  | Date       |
| -------------------------------------- | ------- | ---------- |
| Python 3.11.9 environment setup        | ✅ Done | 2026-07-04 |
| Virtual environment (venv)             | ✅ Done | 2026-07-04 |
| FastAPI project structure              | ✅ Done | 2026-07-04 |
| Clean architecture (api/v1/routes)     | ✅ Done | 2026-07-04 |
| Centralized config (pydantic-settings) | ✅ Done | 2026-07-04 |
| Health check endpoint /api/v1/health   | ✅ Done | 2026-07-04 |
| CORS middleware                        | ✅ Done | 2026-07-04 |
| .env + .gitignore setup                | ✅ Done | 2026-07-04 |
| Swagger UI (/docs)                     | ✅ Done | 2026-07-04 |

---

## Phase 1 — Database Foundation 🔜 NEXT

**Goal:** SQLite setup, database models, migration system
**Dependency:** Phase 0 ✅

| Task                    | Status |
| ----------------------- | ------ |
| SQLite connection setup | 🔜     |
| Database base model     | 🔜     |
| Conversation table      | 🔜     |
| Message table           | 🔜     |
| Knowledge entry table   | 🔜     |
| Database health check   | 🔜     |

---

## Phase 2 — Ollama LLM Integration

**Goal:** Local LLM chat via Ollama
**Dependency:** Phase 1 ✅

| Task                            | Status |
| ------------------------------- | ------ |
| Ollama install + model download | 🔜     |
| Ollama service layer            | 🔜     |
| Chat endpoint /api/v1/chat      | 🔜     |
| Conversation history            | 🔜     |
| Streaming response              | 🔜     |

---

## Phase 3 — Memory System

**Goal:** ChromaDB vector memory + RAG
**Dependency:** Phase 2 ✅

---

## Phase 4 — Voice System

**Goal:** Whisper STT + Piper TTS
**Dependency:** Phase 3 ✅

---

## Phase 5 — Frontend

**Goal:** React + Electron desktop app
**Dependency:** Phase 2 ✅

---

## Phase 6 — Knowledge System

**Goal:** Search → Verify → Store → Retrieve (with confirmation)
**Dependency:** Phase 3 ✅

---

## Phase 7 — Agents & Automation

**Goal:** Task agents, file automation
**Dependency:** Phase 6 ✅
