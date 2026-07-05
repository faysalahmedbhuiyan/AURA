# AURA System Architecture

> Version: 0.4.0
> Last Updated: 2026-07-05
> Architect: Faysal Ahmed Bhuiyan + Claude (AI Architect)

---

## Architecture Philosophy

AURA follows these core architectural principles:

- **Offline First:** Every feature works without internet
- **User Controlled:** No autonomous action without approval
- **Modular:** Every module is independent and replaceable
- **Explainable:** Every decision is logged and visible
- **Reversible:** Every change can be rolled back
- **RAM Aware:** Optimized for 8GB RAM (i5 11th Gen)

---

## System Overview

┌─────────────────────────────────────────────────────┐
│ AURA Desktop App │
│ (React + Electron Frontend) │
└──────────────────────┬──────────────────────────────┘
│ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────┐
│ FastAPI Backend │
│ │
│ ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│ │ Chat │ │ Voice │ │ Memory │ │
│ │ Routes │ │ Routes │ │ Routes │ │
│ └────┬────┘ └────┬────┘ └────┬─────┘ │
│ │ │ │ │
│ ┌────▼─────────────▼────────────▼─────────────┐ │
│ │ Service Layer │ │
│ │ OllamaService │ MemoryService │ │
│ │ EmbeddingService│ WhisperService │ │
│ │ TTSService │ KnowledgeService │ │
│ └────┬─────────────┬────────────┬─────────────┘ │
│ │ │ │ │
│ ┌────▼──────┐ ┌────▼──────┐ ┌──▼──────────────┐ │
│ │ Ollama │ │ ChromaDB │ │ SQLite │ │
│ │ (qwen3b) │ │ (vectors) │ │ (structured) │ │
│ └───────────┘ └───────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘

---

## Current Implementation (Phase 0-3)

### Backend Layer

backend/
└── app/
├── api/v1/routes/ ← HTTP endpoints
│ ├── health.py ← System health
│ ├── db_health.py ← Database health
│ ├── chat.py ← LLM chat + RAG
│ └── memory.py ← Knowledge management
├── services/ ← Business logic
│ ├── ollama_service.py ← LLM communication
│ ├── embedding_service.py ← Text → Vector
│ └── memory_service.py ← ChromaDB operations
├── repositories/ ← Data access layer
│ ├── conversation_repository.py
│ └── knowledge_repository.py
├── models/ ← SQLAlchemy ORM models
│ ├── conversation.py
│ ├── message.py
│ └── knowledge.py
├── schemas/ ← Pydantic schemas
│ └── chat.py
├── database/ ← DB connection
│ ├── base.py
│ └── connection.py
└── config.py ← Centralized settings

### Data Layer

Database/
├── SQLite (aura.db)
│ ├── conversations ← Chat sessions
│ ├── messages ← Individual messages
│ └── knowledge_entries ← Verified knowledge
└── ChromaDB (chroma/)
├── aura_conversations ← Message vectors
└── aura_knowledge ← Knowledge vectors

---

## Planned Architecture (Phase 8-19)

### Self-Modification Safety System

User Request → Self Review Engine
↓
Impact Analyzer
↓
Risk Calculator
↓
Plan Generator
↓
┌──────────────────┐
│ USER APPROVAL │ ← Cannot be bypassed
│ REQUIRED │
└────────┬─────────┘
↓
Backup Creator
↓
Change Applier
↓
Test Runner
↓
Git Commit Generator
↓
Result Reporter

### Memory Architecture (Phase 13)

Memory System/
├── personal/ ← Private user data
│ ├── preferences/ ← UI, language, behavior prefs
│ ├── habits/ ← Usage patterns
│ └── private/ ← Personal notes (encrypted)
├── knowledge/ ← Confirmed public knowledge
│ ├── confirmed/ ← User-approved facts
│ └── indexed/ ← ChromaDB vectorized
├── decisions/ ← Architectural decision log
│ └── ADR/ ← Architecture Decision Records
└── queue/ ← Pending confirmation
├── learned/ ← From internet, not confirmed
└── suggested/ ← AI suggestions, not applied

### AI Safety Rules (Non-negotiable)

```python
AURA_SAFETY_RULES = {
    "self_modification": "NEVER without user approval",
    "knowledge_storage": "NEVER without user confirmation",
    "action_logging": "ALWAYS — every important action",
    "decision_recording": "ALWAYS — every architecture change",
    "rollback_support": "ALWAYS — every change reversible",
    "human_gate": "ALWAYS — final decision is human",
}
```

---

## Technology Stack (Current)

| Layer       | Technology          | Version | Purpose            |
| ----------- | ------------------- | ------- | ------------------ |
| Backend     | FastAPI             | 0.115.6 | REST API           |
| Runtime     | Python              | 3.11.9  | Core language      |
| LLM         | Ollama + qwen2.5:3b | latest  | Local AI           |
| Embedding   | nomic-embed-text    | latest  | Vectors            |
| Vector DB   | ChromaDB            | 0.5.23  | Semantic search    |
| SQL DB      | SQLite + SQLAlchemy | 2.0.36  | Structured data    |
| Async DB    | aiosqlite           | 0.20.0  | Async SQLite       |
| HTTP Client | httpx               | 0.28.1  | Ollama API calls   |
| Config      | pydantic-settings   | 2.7.0   | Environment config |
| Server      | uvicorn             | 0.34.0  | ASGI server        |

## Technology Stack (Planned)

| Layer           | Technology              | Purpose         |
| --------------- | ----------------------- | --------------- |
| STT             | faster-whisper          | Speech-to-Text  |
| TTS             | Piper                   | Text-to-Speech  |
| Frontend        | React + Electron        | Desktop UI      |
| Testing         | pytest + pytest-asyncio | Automated tests |
| Monitoring      | psutil                  | System health   |
| Version Control | Git                     | Rollback system |

---

## RAM Budget (8GB)

| Component             | RAM Usage   | Status    |
| --------------------- | ----------- | --------- |
| Windows 11            | ~2.5 GB     | always    |
| VS Code               | ~500 MB     | dev only  |
| FastAPI server        | ~150 MB     | always    |
| Ollama qwen2.5:3b     | ~2.0 GB     | on demand |
| ChromaDB              | ~300 MB     | always    |
| nomic-embed-text      | ~274 MB     | on demand |
| faster-whisper (base) | ~500 MB     | on demand |
| Piper TTS             | ~100 MB     | on demand |
| **Total (peak)**      | **~6.3 GB** | safe ✅   |
| **Available buffer**  | **~1.7 GB** | safe ✅   |

---

## API Endpoints (Current)

| Method | Endpoint                              | Description          |
| ------ | ------------------------------------- | -------------------- |
| GET    | /api/v1/health                        | Backend health       |
| GET    | /api/v1/db-health                     | Database health      |
| POST   | /api/v1/chat                          | Chat with AURA       |
| GET    | /api/v1/chat/{id}                     | Conversation history |
| POST   | /api/v1/memory/search                 | Semantic search      |
| POST   | /api/v1/memory/knowledge              | Add knowledge        |
| GET    | /api/v1/memory/knowledge              | List pending         |
| POST   | /api/v1/memory/knowledge/{id}/confirm | Confirm entry        |
| GET    | /api/v1/memory/knowledge/confirmed    | List confirmed       |

## API Endpoints (Planned)

| Method | Endpoint                 | Phase | Description            |
| ------ | ------------------------ | ----- | ---------------------- |
| POST   | /api/v1/voice/transcribe | 4     | Audio → Text           |
| POST   | /api/v1/voice/speak      | 4     | Text → Audio           |
| POST   | /api/v1/voice/chat       | 4     | Audio → AI → Audio     |
| GET    | /api/v1/health/system    | 19    | CPU/RAM/Storage        |
| POST   | /api/v1/self/review      | 8     | Code quality check     |
| POST   | /api/v1/self/plan        | 9     | Improvement plan       |
| POST   | /api/v1/self/modify      | 10    | Apply changes          |
| POST   | /api/v1/self/rollback    | 11    | Restore version        |
| GET    | /api/v1/journal          | 12    | Dev journal            |
| GET    | /api/v1/memory/personal  | 13    | Personal memory        |
| GET    | /api/v1/memory/decisions | 13    | Decision log           |
| POST   | /api/v1/goals            | 16    | Create goal            |
| GET    | /api/v1/goals            | 16    | List goals             |
| POST   | /api/v1/impact           | 17    | Change impact analysis |
