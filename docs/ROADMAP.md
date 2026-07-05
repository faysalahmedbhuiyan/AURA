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

## Phase 1 — Database Foundation ✅ COMPLETE

| Task                           | Status  | Date       |
| ------------------------------ | ------- | ---------- |
| SQLAlchemy + aiosqlite install | ✅ Done | 2026-07-04 |
| Base model + mixins            | ✅ Done | 2026-07-04 |
| Async connection + session     | ✅ Done | 2026-07-04 |
| Conversation model             | ✅ Done | 2026-07-04 |
| Message model                  | ✅ Done | 2026-07-04 |
| KnowledgeEntry model           | ✅ Done | 2026-07-04 |
| Database health check endpoint | ✅ Done | 2026-07-04 |

## Phase 2 — Ollama LLM Integration ✅ COMPLETE

| Task                            | Status  | Date       |
| ------------------------------- | ------- | ---------- |
| Ollama install + model download | ✅ Done | 2026-07-05 |
| OllamaService class             | ✅ Done | 2026-07-05 |
| Chat endpoint /api/v1/chat      | ✅ Done | 2026-07-05 |
| Conversation history            | ✅ Done | 2026-07-05 |
| Message persistence             | ✅ Done | 2026-07-05 |
| Multilingual support            | ✅ Done | 2026-07-05 |

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
