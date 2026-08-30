# AURA Roadmap

> Rule: Never implement a feature before its dependency is complete.

---

## Phase 0 — Foundation ✅ COMPLETE

| Task                                   | Status  | Date       |
| -------------------------------------- | ------- | ---------- |
| Python 3.11.9 environment              | ✅ Done | 2026-07-04 |
| Virtual environment (venv)             | ✅ Done | 2026-07-04 |
| FastAPI project structure              | ✅ Done | 2026-07-04 |
| Clean architecture (api/v1/routes)     | ✅ Done | 2026-07-04 |
| Centralized config (pydantic-settings) | ✅ Done | 2026-07-04 |
| Health check endpoint                  | ✅ Done | 2026-07-04 |
| CORS middleware                        | ✅ Done | 2026-07-04 |
| .env + .gitignore setup                | ✅ Done | 2026-07-04 |
| Swagger UI (/docs)                     | ✅ Done | 2026-07-04 |

## Phase 1 — Database Foundation ✅ COMPLETE

| Task                               | Status  | Date       |
| ---------------------------------- | ------- | ---------- |
| SQLAlchemy 2.0 + aiosqlite         | ✅ Done | 2026-07-04 |
| Base model + UUID/Timestamp mixins | ✅ Done | 2026-07-04 |
| Async connection + session         | ✅ Done | 2026-07-04 |
| Conversation model                 | ✅ Done | 2026-07-04 |
| Message model                      | ✅ Done | 2026-07-04 |
| KnowledgeEntry model               | ✅ Done | 2026-07-04 |
| Database health check endpoint     | ✅ Done | 2026-07-04 |

## Phase 2 — Ollama LLM Integration ✅ COMPLETE

| Task                               | Status  | Date       |
| ---------------------------------- | ------- | ---------- |
| Ollama install + model download    | ✅ Done | 2026-07-05 |
| OllamaService (chat + stream)      | ✅ Done | 2026-07-05 |
| Chat endpoint /api/v1/chat         | ✅ Done | 2026-07-05 |
| Conversation history               | ✅ Done | 2026-07-05 |
| Message persistence                | ✅ Done | 2026-07-05 |
| Multilingual support (bn/en/hi/ko) | ✅ Done | 2026-07-05 |

## Phase 3 — Memory System ✅ COMPLETE

| Task                                      | Status  | Date       |
| ----------------------------------------- | ------- | ---------- |
| ChromaDB 0.5.23 install                   | ✅ Done | 2026-07-05 |
| nomic-embed-text model                    | ✅ Done | 2026-07-05 |
| EmbeddingService                          | ✅ Done | 2026-07-05 |
| MemoryService + RAG pipeline              | ✅ Done | 2026-07-05 |
| KnowledgeRepository (confirm-before-save) | ✅ Done | 2026-07-05 |
| Memory endpoints                          | ✅ Done | 2026-07-05 |
| RAG pipeline verified                     | ✅ Done | 2026-07-05 |

## Phase 4 — Voice System ✅ COMPLETE

| Task                               | Status  | Date       |
| ---------------------------------- | ------- | ---------- |
| faster-whisper 1.1.1 (STT)         | ✅ Done | 2026-07-06 |
| piper-tts 1.4.2 (TTS)              | ✅ Done | 2026-07-06 |
| en_US-lessac-medium voice model    | ✅ Done | 2026-07-06 |
| WhisperService (on-demand loading) | ✅ Done | 2026-07-06 |
| TTSService (synthesize_wav API)    | ✅ Done | 2026-07-06 |
| POST /api/v1/voice/transcribe      | ✅ Done | 2026-07-06 |
| POST /api/v1/voice/speak           | ✅ Done | 2026-07-06 |
| POST /api/v1/voice/chat            | ✅ Done | 2026-07-06 |

## Phase 5 — Frontend ✅ COMPLETE

| Task                                 | Status  | Date       |
| ------------------------------------ | ------- | ---------- |
| React 19 + Vite 8 scaffold           | ✅ Done | 2026-07-06 |
| Electron 37 desktop shell            | ✅ Done | 2026-07-06 |
| Dark theme design system             | ✅ Done | 2026-07-06 |
| Sidebar navigation                   | ✅ Done | 2026-07-06 |
| ChatWindow component                 | ✅ Done | 2026-07-06 |
| MessageBubble component              | ✅ Done | 2026-07-06 |
| ChatInput (multilingual EN/BN/HI/KO) | ✅ Done | 2026-07-06 |
| API service layer (axios)            | ✅ Done | 2026-07-06 |
| Backend connection status            | ✅ Done | 2026-07-06 |
| CORS + CSP configured                | ✅ Done | 2026-07-06 |

## Phase 6 — Knowledge System ✅ COMPLETE

| Task                                       | Status  | Date       |
| ------------------------------------------ | ------- | ---------- |
| DuckDuckGo web search (ddgs)               | ✅ Done | 2026-07-07 |
| Content fetch (httpx + BeautifulSoup)      | ✅ Done | 2026-07-07 |
| ResearchService (Search→Collect→Summarize) | ✅ Done | 2026-07-07 |
| POST /api/v1/knowledge/research            | ✅ Done | 2026-07-07 |
| Research schemas                           | ✅ Done | 2026-07-07 |
| KnowledgeView React component              | ✅ Done | 2026-07-07 |
| Research → Pending → Confirm UI flow       | ✅ Done | 2026-07-07 |
| Confidence scoring heuristic               | ✅ Done | 2026-07-07 |

## Phase 7 — Agents & Automation 🔜 NEXT

**Dependency:** Phase 6 ✅

## Phase 8-19 — 📋 Planned

See docs/PHASES.md for full details.

## Summary

| Phase | Name                         | Status      |
| ----- | ---------------------------- | ----------- |
| 0     | Foundation                   | ✅ Complete |
| 1     | Database                     | ✅ Complete |
| 2     | LLM Integration              | ✅ Complete |
| 3     | Memory System                | ✅ Complete |
| 4     | Voice System                 | ✅ Complete |
| 5     | Frontend                     | ✅ Complete |
| 6     | Knowledge System             | ✅ Complete |
| 7     | Agents & Automation          | 🔜 Next     |
| 8     | Self Review Engine           | 📋 Planned  |
| 9     | Self Improvement Planner     | 📋 Planned  |
| 10    | Safe Self Modification       | 📋 Planned  |
| 11    | Rollback System              | 📋 Planned  |
| 12    | Development Journal          | 📋 Planned  |
| 13    | Advanced Memory System       | 📋 Planned  |
| 14    | Project Understanding Engine | 📋 Planned  |
| 15    | Coding Mentor Mode           | 📋 Planned  |
| 16    | Goal Manager                 | 📋 Planned  |
| 17    | Change Impact Analysis       | 📋 Planned  |
| 18    | Automatic Testing            | 📋 Planned  |
| 19    | AI Health Monitor            | 📋 Planned  |
