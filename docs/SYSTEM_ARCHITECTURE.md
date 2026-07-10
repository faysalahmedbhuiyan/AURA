# AURA System Architecture

> Version: 0.12.0
> Last Updated: 2026-07-10
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

┌─────────────────────────────────────────────────────────────┐
│ AURA Desktop App │
│ (React + Electron Frontend) │
└──────────────────────────┬────────────────────────────────────┘
│ HTTP
┌──────────────────────────▼────────────────────────────────────┐
│ FastAPI Backend │
│ │
│ Chat │ Voice │ Memory │ Knowledge │ Agents │ Review │ Planning │
│ Modification │ Rollback │ Journal │ Memory-Tiers │
│ │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ Service / Domain Layer │ │
│ │ OllamaService │ MemoryService │ ResearchService │ │
│ │ EmbeddingService │ WhisperService │ TTSService │ │
│ │ FileAgent/SystemAgent │ CodeAnalyzer/DebtDetector │ │
│ │ RequestParser/ImpactMapper/RiskEstimator │ │
│ │ BackupManager/ChangeApplier │ GitService/SnapshotService │ │
│ │ JournalRepository │ MemoryTierService │ │
│ └───────┬─────────────────┬────────────────┬─────────────┘ │
│ │ │ │ │
│ ┌───────▼──────┐ ┌───────▼──────┐ ┌──────▼──────────┐ │
│ │ Ollama │ │ ChromaDB │ │ SQLite │ │
│ │ (aura-brain) │ │ (vectors) │ │ (structured) │ │
│ └───────────────┘ └───────────────┘ └───────────────────┘ │
└───────────────────────────────────────────────────────────────┘

---

## Current Implementation (Phase 0-13)

### Backend Layer

backend/
└── app/
├── agents/ ← Phase 7
│ ├── base_agent.py
│ ├── file_agent.py
│ └── system_agent.py
├── api/v1/routes/ ← HTTP endpoints
│ ├── health.py
│ ├── db_health.py
│ ├── chat.py
│ ├── memory.py ← Phase 3/6: Knowledge (confirm/store)
│ ├── voice.py ← Phase 4
│ ├── research.py ← Phase 6: Search/Collect/Summarize
│ ├── agents.py ← Phase 7
│ ├── review.py ← Phase 8
│ ├── planning.py ← Phase 9
│ ├── modification.py ← Phase 10
│ ├── rollback.py ← Phase 11
│ ├── journal.py ← Phase 12
│ └── memory_tiers.py ← Phase 13
├── journal/ ← Phase 12
│ └── summary_generator.py
├── modification/ ← Phase 10
│ ├── backup_manager.py
│ ├── change_applier.py
│ ├── result_reporter.py
│ └── modification_service.py
├── planning/ ← Phase 9
│ ├── request_parser.py
│ ├── impact_mapper.py
│ ├── risk_estimator.py
│ └── plan_service.py
├── review/ ← Phase 8
│ ├── code_analyzer.py
│ ├── debt_detector.py
│ ├── suggestion_engine.py
│ └── review_service.py
├── rollback/ ← Phase 11
│ ├── git_service.py
│ ├── snapshot_service.py
│ └── rollback_service.py
├── services/ ← Business logic
│ ├── ollama_service.py ← LLM communication (aura-brain)
│ ├── embedding_service.py
│ ├── memory_service.py ← ChromaDB operations
│ ├── whisper_service.py ← Phase 4
│ ├── tts_service.py ← Phase 4
│ ├── web_search_service.py ← Phase 6
│ ├── content_fetch_service.py← Phase 6
│ └── research_service.py ← Phase 6
├── repositories/ ← Data access layer
│ ├── conversation_repository.py
│ ├── knowledge_repository.py
│ ├── journal_repository.py ← Phase 12
│ └── memory_tier_repository.py ← Phase 13
├── models/ ← SQLAlchemy ORM models
│ ├── conversation.py
│ ├── message.py
│ ├── knowledge.py
│ ├── journal.py ← Phase 12
│ └── memory_tier.py ← Phase 13
├── schemas/ ← Pydantic schemas
│ ├── chat.py
│ ├── research.py
│ ├── review.py
│ ├── planning.py
│ ├── modification.py
│ ├── journal.py
│ └── memory_tier.py
├── database/ ← DB connection
│ ├── base.py
│ └── connection.py
└── config.py ← Centralized settings

### Data Layer

Database/
├── SQLite (aura.db)
│ ├── conversations
│ ├── messages
│ ├── knowledge_entries ← Phase 3/6 (also acts as "Knowledge Base" tier, Phase 13)
│ ├── journal_entries ← Phase 12
│ ├── personal_memory_entries ← Phase 13
│ ├── decision_records ← Phase 13
│ └── learning_queue_items ← Phase 13
└── ChromaDB (chroma/)
├── aura_conversations ← Message vectors
└── aura_knowledge ← Knowledge vectors
D:\AURA\backups\ ← Phase 10: auto file backups (mirrors project structure)
D:\AURA.aura\snapshots\ ← Phase 11: named restore points (JSON)

---

## Safety Systems (Phase 7-13, implemented)

### Self-Modification Safety Pipeline (Phase 8-11)

User Request → Self Review Engine (Phase 8, Python-only, read-only)
↓
Self Improvement Planner (Phase 9, cross-project, read-only)
↓ ImpactMapper + RiskEstimator
┌──────────────────┐
│ USER APPROVAL │ ← confirmed=True, non-bypassable
│ REQUIRED │
└────────┬───────────┘
↓
Safe Self Modification (Phase 10)
Backup → Apply → Report (with rollback instructions)
↓
Rollback System (Phase 11) ← available at any time via Git or named snapshots

### Multi-Tier Memory (Phase 13, implemented)

Memory/
├── personal/ ← PersonalMemoryEntry — private preferences (Phase 13)
├── knowledge/ ← KnowledgeEntry — confirmed public facts (Phase 3/6, reused)
├── decisions/ ← DecisionRecord — architectural decisions (Phase 13)
└── queue/ ← LearningQueueItem — pending confirmation (Phase 13)
**Confirm-before-save enforcement:** `MemoryTierService.confirm_item()` is
the ONLY path by which a queue item can be promoted to `personal` or
`decision`. Rejected items are marked `rejected` and never promoted.

### AI Safety Rules (Non-negotiable, verified in practice)

```python
AURA_SAFETY_RULES = {
    "self_modification": "NEVER without user approval (confirmed=True)",
    "knowledge_storage": "NEVER without user confirmation (queue → confirm)",
    "action_logging": "ALWAYS — every agent/modification action logged",
    "decision_recording": "ALWAYS — DecisionRecord + Journal decision entries",
    "rollback_support": "ALWAYS — backups (Phase 10) + Git/snapshots (Phase 11)",
    "human_gate": "ALWAYS — final decision is human",
}
```

---

## Technology Stack (Current)

| Layer             | Technology                          | Version    | Purpose                            |
| ----------------- | ----------------------------------- | ---------- | ---------------------------------- |
| Backend           | FastAPI                             | 0.115.6    | REST API                           |
| Runtime           | Python                              | 3.11.9     | Core language                      |
| LLM               | Ollama + aura-brain (qwen3:4b base) | latest     | Local AI, no-think template        |
| Embedding         | nomic-embed-text                    | latest     | Vectors                            |
| Vector DB         | ChromaDB                            | 0.5.23     | Semantic search                    |
| SQL DB            | SQLite + SQLAlchemy                 | 2.0.36     | Structured data                    |
| Async DB          | aiosqlite                           | 0.20.0     | Async SQLite                       |
| HTTP Client       | httpx                               | 0.28.1     | Ollama + web fetch                 |
| Config            | pydantic-settings                   | 2.7.0      | Environment config                 |
| Server            | uvicorn                             | 0.34.0     | ASGI server                        |
| STT               | faster-whisper                      | 1.1.1      | Speech-to-Text                     |
| TTS               | piper-tts                           | 1.4.2      | Text-to-Speech                     |
| Web Search        | ddgs                                | >=9.0.0    | DuckDuckGo search, no API key      |
| HTML Parsing      | beautifulsoup4 + lxml               | >=4.12/5.0 | Content extraction for research    |
| System Monitoring | psutil                              | >=6.0.0    | RAM/CPU/disk (Phase 7 SystemAgent) |
| Version Control   | Git                                 | —          | Used by Rollback System (Phase 11) |
| Frontend          | React 19 + Vite 8 + Electron 37     | —          | Desktop UI                         |

---

## RAM Budget (8GB) — unchanged since Phase 4

| Component                    | RAM Usage   | Status    |
| ---------------------------- | ----------- | --------- |
| Windows 11                   | ~2.5 GB     | always    |
| VS Code                      | ~500 MB     | dev only  |
| FastAPI server               | ~150 MB     | always    |
| Ollama aura-brain (qwen3:4b) | ~2.5 GB     | on demand |
| ChromaDB                     | ~300 MB     | always    |
| nomic-embed-text             | ~274 MB     | on demand |
| faster-whisper (base)        | ~500 MB     | on demand |
| Piper TTS                    | ~100 MB     | on demand |
| **Total (peak)**             | **~6.8 GB** | safe ✅   |
| **Available buffer**         | **~1.2 GB** | safe ✅   |

---

## API Endpoints (Current, Phase 0-13)

| Method | Endpoint                                | Phase | Description                                        |
| ------ | --------------------------------------- | ----- | -------------------------------------------------- |
| GET    | /api/v1/health                          | 0     | Backend health                                     |
| GET    | /api/v1/db-health                       | 1     | Database health                                    |
| POST   | /api/v1/chat                            | 2     | Chat with AURA                                     |
| GET    | /api/v1/chat/{id}                       | 2     | Conversation history                               |
| POST   | /api/v1/memory/search                   | 3     | Semantic search                                    |
| POST   | /api/v1/memory/knowledge                | 3     | Add knowledge (pending)                            |
| GET    | /api/v1/memory/knowledge                | 3     | List pending knowledge                             |
| POST   | /api/v1/memory/knowledge/{id}/confirm   | 3     | Confirm entry                                      |
| GET    | /api/v1/memory/knowledge/confirmed      | 3     | List confirmed knowledge                           |
| POST   | /api/v1/voice/transcribe                | 4     | Audio → Text                                       |
| POST   | /api/v1/voice/speak                     | 4     | Text → Audio                                       |
| POST   | /api/v1/voice/chat                      | 4     | Audio → AI → Audio                                 |
| POST   | /api/v1/knowledge/research              | 6     | Search→Collect→Summarize (read-only)               |
| POST   | /api/v1/agents/execute                  | 7     | Execute a FileAgent/SystemAgent action             |
| GET    | /api/v1/agents/health                   | 7     | Quick system health check                          |
| GET    | /api/v1/agents/list                     | 7     | List available agents                              |
| POST   | /api/v1/review/analyze                  | 8     | Read-only codebase analysis (Python only)          |
| POST   | /api/v1/planning/create                 | 9     | Create improvement plan (cross-project, read-only) |
| POST   | /api/v1/modification/apply              | 10    | Apply confirmed change (auto-backup)               |
| POST   | /api/v1/modification/rollback           | 10    | Restore from a specific backup                     |
| GET    | /api/v1/rollback/status                 | 11    | Git status + HEAD                                  |
| GET    | /api/v1/rollback/log                    | 11    | Commit history                                     |
| GET    | /api/v1/rollback/preview/{ref}          | 11    | Preview rollback (read-only)                       |
| POST   | /api/v1/rollback/commit                 | 11    | Full rollback (confirmed=True)                     |
| POST   | /api/v1/rollback/files                  | 11    | Partial rollback (specific files)                  |
| GET    | /api/v1/rollback/snapshots              | 11    | List named snapshots                               |
| POST   | /api/v1/rollback/snapshots              | 11    | Create named snapshot                              |
| POST   | /api/v1/rollback/restore-snapshot       | 11    | Restore from snapshot                              |
| DELETE | /api/v1/rollback/snapshots/{id}         | 11    | Delete snapshot record                             |
| POST   | /api/v1/journal/entries                 | 12    | Create journal entry                               |
| GET    | /api/v1/journal/entries                 | 12    | List journal entries (filter/search)               |
| GET    | /api/v1/journal/summary                 | 12    | Summarize entries over N days                      |
| POST   | /api/v1/memory-tiers/personal           | 13    | Create personal memory entry (direct)              |
| GET    | /api/v1/memory-tiers/personal           | 13    | List personal memory                               |
| DELETE | /api/v1/memory-tiers/personal/{id}      | 13    | Delete personal memory entry                       |
| POST   | /api/v1/memory-tiers/decisions          | 13    | Create decision record (direct)                    |
| GET    | /api/v1/memory-tiers/decisions          | 13    | List decision records                              |
| POST   | /api/v1/memory-tiers/queue              | 13    | Add item to learning queue (pending)               |
| GET    | /api/v1/memory-tiers/queue              | 13    | List queue items (filter by status)                |
| POST   | /api/v1/memory-tiers/queue/{id}/confirm | 13    | Confirm — promotes to target tier                  |
| POST   | /api/v1/memory-tiers/queue/{id}/reject  | 13    | Reject — never becomes permanent                   |

## API Endpoints (Planned, Phase 14-19)

| Method | Endpoint                     | Phase | Description                                                                               |
| ------ | ---------------------------- | ----- | ----------------------------------------------------------------------------------------- |
| GET    | /api/v1/health/system        | 19    | Dedicated always-on health monitor (basic version already exists via Phase 7 SystemAgent) |
| GET    | /api/v1/project/structure    | 14    | Project structure analysis                                                                |
| GET    | /api/v1/project/dependencies | 14    | Module dependency graph                                                                   |
| POST   | /api/v1/mentor/explain       | 15    | Line-by-line code explanation                                                             |
| POST   | /api/v1/goals                | 16    | Create goal                                                                               |
| GET    | /api/v1/goals                | 16    | List goals                                                                                |
| POST   | /api/v1/impact               | 17    | Change impact analysis                                                                    |
| POST   | /api/v1/testing/run          | 18    | Run automated tests                                                                       |
