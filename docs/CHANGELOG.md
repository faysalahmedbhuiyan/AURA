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
