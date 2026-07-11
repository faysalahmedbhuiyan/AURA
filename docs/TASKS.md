# AURA Task List

## ✅ Completed — Phase 0 (Foundation)

- [x] Python 3.11.9 environment
- [x] FastAPI clean architecture
- [x] Health check endpoint
- [x] GitHub repository

## ✅ Completed — Phase 1 (Database)

- [x] SQLAlchemy 2.0 + aiosqlite
- [x] Conversation, Message, KnowledgeEntry models
- [x] Database health check endpoint

## ✅ Completed — Phase 2 (LLM Integration)

- [x] Ollama + qwen2.5:3b (later migrated to aura-brain)
- [x] OllamaService (chat + stream)
- [x] Chat endpoint with history
- [x] Message persistence

## ✅ Completed — Phase 3 (Memory System)

- [x] ChromaDB + nomic-embed-text
- [x] EmbeddingService
- [x] MemoryService (store + search + RAG)
- [x] KnowledgeRepository (confirm-before-save)
- [x] Memory endpoints
- [x] RAG pipeline in chat

## ✅ Completed — Phase 4 (Voice System)

- [x] faster-whisper install + STT service
- [x] piper-tts install + TTS service
- [x] English voice model downloaded
- [x] Voice routes (transcribe, speak, chat)
- [x] On-demand model loading
- [x] Audio verified working

## ✅ Completed — Phase 5 (Frontend)

- [x] Node.js + npm install
- [x] React app scaffold
- [x] Electron setup
- [x] Chat UI component
- [x] Voice interface component
- [x] API connection to FastAPI backend
- [x] Knowledge management UI
- [ ] Dedicated Settings panel (slot currently used by Review tab)

## ✅ Completed — Phase 6 (Knowledge System)

- [x] DuckDuckGo web search (ddgs)
- [x] Content fetch (httpx + BeautifulSoup)
- [x] ResearchService pipeline
- [x] POST /api/v1/knowledge/research
- [x] KnowledgeView UI (Research/Pending/Confirmed)
- [x] aura-brain custom model with thinking disabled

## ✅ Completed — Phase 7 (Agents & Automation)

- [x] BaseAgent + AgentResult
- [x] FileAgent (list/read/write/search/info/exists)
- [x] SystemAgent (ram/cpu/disk/health/info/processes)
- [x] /api/v1/agents/\* endpoints
- [x] AgentView UI
- [ ] Task automation agent (future)
- [ ] Web browsing agent (future)

## ✅ Completed — Phase 8 (Self Review Engine)

- [x] AST-based CodeAnalyzer
- [x] DebtDetector
- [x] SuggestionEngine
- [x] POST /api/v1/review/analyze
- [x] ReviewView UI
- [ ] JS/JSX analysis support (future, separate parser needed)

## ✅ Completed — Phase 9 (Self Improvement Planner)

- [x] RequestParser
- [x] ImpactMapper (backend + frontend)
- [x] RiskEstimator
- [x] POST /api/v1/planning/create
- [x] PlanningView UI

## ✅ Completed — Phase 10 (Safe Self Modification)

- [x] BackupManager
- [x] ChangeApplier
- [x] ResultReporter
- [x] POST /api/v1/modification/apply
- [x] POST /api/v1/modification/rollback
- [x] Apply UI in PlanningView
- [x] Load-current-content safety fix
- [ ] Post-change automated test runner (deferred to Phase 18)

## ✅ Completed — Phase 11 (Rollback System)

- [x] GitService
- [x] SnapshotService
- [x] RollbackService
- [x] /api/v1/rollback/\* endpoints
- [x] RollbackView UI

## ✅ Completed — Phase 12 (Development Journal)

- [x] JournalEntry model
- [x] JournalRepository
- [x] SummaryGenerator
- [x] /api/v1/journal/\* endpoints
- [x] JournalView UI

## ✅ Completed — Phase 13 (Advanced Memory System)

- [x] PersonalMemoryEntry model
- [x] DecisionRecord model
- [x] LearningQueueItem model
- [x] MemoryTierService (confirm/reject)
- [x] /api/v1/memory-tiers/\* endpoints
- [x] MemoryTiersView UI
- [x] Verified: queue items never become permanent without confirm

## ✅ Completed — Phase 14 (Project Understanding Engine)

- [x] (Completed in a prior session — see PHASES.md)

## ✅ Completed — Phase 15 (Coding Mentor Mode)

- [x] CodeExplainer
- [x] ConceptTeacher
- [x] PracticeSuggester (reuses Phase 8 analyzer)
- [x] /api/v1/mentor/\* endpoints
- [x] MentorView UI

## 🔜 Next — Phase 16 (Goal Manager)

- [ ] Goal breakdown engine
- [ ] Milestone tracker
- [ ] Task dependency mapper
- [ ] Progress reporter
