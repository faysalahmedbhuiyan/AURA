# AURA Changelog

All notable changes to AURA are documented here.
Format: [Version] — Date — Description

---

## [0.1.0] — 2026-07-04

### Added

- FastAPI backend skeleton with clean architecture
- Versioned API structure: /api/v1/
- Health check endpoint: GET /api/v1/health
- Centralized configuration via pydantic-settings
- CORS middleware configured for Electron frontend
- Swagger UI available at /docs
- ReDoc available at /redoc
- .env environment variable support
- .gitignore configured (venv, cache, .env excluded)
- Python 3.11.9 stable environment
- Virtual environment isolation

## [0.2.0] — 2026-07-04

### Added

- Async SQLite database with aiosqlite + SQLAlchemy 2.0
- DeclarativeBase with UUIDMixin and TimestampMixin
- Conversation model (id, title, language, summary)
- Message model (id, conversation_id, role, content, token_count, model_used)
- KnowledgeEntry model (id, title, summary, source, confidence, is_confirmed)
- Database connection module with async session management
- FastAPI lifespan for automatic table creation on startup
- Database health check endpoint: GET /api/v1/db-health

## [0.3.0] — 2026-07-05

### Added

- Ollama LLM integration with qwen2.5:3b model
- OllamaService with chat and stream support
- Chat endpoint: POST /api/v1/chat
- Conversation history endpoint: GET /api/v1/chat/{id}
- ConversationRepository for database operations
- Pydantic schemas for chat request/response validation
- httpx async HTTP client for Ollama communication
- Automatic conversation creation and history tracking
- Message persistence in SQLite database

## [0.4.0] — 2026-07-05

### Added

- ChromaDB vector database integration (persistent, offline)
- EmbeddingService using nomic-embed-text via Ollama
- MemoryService with semantic search and RAG pipeline
- KnowledgeRepository with confirm-before-save enforcement
- Memory routes: search, add, confirm, list knowledge entries
- RAG pipeline integrated into chat endpoint
- Messages automatically stored in ChromaDB after each chat
- Knowledge entries indexed in ChromaDB after user confirmation

## [0.5.0] — 2026-07-06

### Added

- faster-whisper 1.1.1 — offline Speech-to-Text (STT)
- piper-tts 1.4.2 — offline Text-to-Speech (TTS)
- en_US-lessac-medium voice model downloaded
- WhisperService — on-demand model loading, multilingual STT
- TTSService — on-demand model loading, synthesize_wav API
- VoiceRoutes — /transcribe, /speak, /chat endpoints
- python-multipart — file upload support
- On-demand model loading — RAM optimization for 8GB
- Voice output saved to logs/voice/ directory

### Fixed

- TTS WAV bug — switched to synthesize_wav() with set_wav_format=True
- Piper API mismatch — correct method discovered via runtime inspection

## [0.6.0] — 2026-07-06

### Added

- React + Vite + Electron frontend scaffold
- Dark theme UI with CSS variables
- Sidebar navigation (Chat, Memory, Knowledge, Settings)
- ChatWindow — full conversation interface
- MessageBubble — user/assistant message display
- ChatInput — multilingual input (EN/বাং/हिं/한)
- Header with backend status and model indicator
- API service layer (axios) — all backend calls centralized
- Backend connection status check (auto-reconnect every 30s)
- CORS updated for localhost:5173
- CSP updated for Vite WebSocket dev server
- Electron main process + preload security bridge
- Desktop app launches with electron:dev command

### Fixed

- CORS policy — added localhost:5173 to allowed origins
- CSP policy — added WebSocket and localhost to connect-src

## [0.7.0] — 2026-07-08

### Added

- aura-brain custom Ollama model (qwen3:4b base, no-think template)
- Custom Modelfile with /no_think hardcoded per user message
- Knowledge System research pipeline complete
- KnowledgeView React component (Research/Pending/Confirmed tabs)
- researchTopic() API function in frontend service layer
- App.jsx routing fix — Knowledge tab now renders KnowledgeView
- ddgs web search, httpx+BeautifulSoup content fetch
- ResearchService orchestrator (Search→Collect→Verify→Summarize)
- POST /api/v1/knowledge/research endpoint
- Confidence scoring heuristic (trusted domain bonus)

### Changed

- OLLAMA_MODEL changed to aura-brain (qwen3:4b with custom template)
- OllamaService.chat() — thinking content filtered from response
- System prompt improved with direct answer style rules

## [0.8.0] — 2026-07-08

### Added

- FileAgent (list/read/write/search/info/exists) with safe-directory validation
- SystemAgent (ram/cpu/disk/health/info/processes) via psutil
- BaseAgent abstract class + AgentResult standard response format
- POST /api/v1/agents/execute, GET /api/v1/agents/health, GET /api/v1/agents/list
- AgentView React component (Agents tab) with quick actions + JSON executor
- Self Review Engine: AST-based CodeAnalyzer (long functions, missing docstrings,
  too many params, deep nesting, unused imports, file length, TODO/FIXME)
- DebtDetector — per-file and project-wide technical debt scoring
- SuggestionEngine — prioritized, human-readable improvement suggestions
- POST /api/v1/review/analyze — read-only codebase analysis endpoint
- ReviewView React component (Review tab) with debt summary, suggestions,
  worst-files list, and per-file issue drill-down

### Changed

- Sidebar "Agents" tab now renders AgentView (previously reused Memory slot)
- Sidebar "Review" tab (previously Settings slot) now renders ReviewView

### Notes

- Phase 7 and Phase 8 are both analysis/action tools that never modify code
  or take destructive action without explicit confirmation, per Constitution.
- psutil>=6.0.0 added as a new backend dependency.
