# AURA Task List

## ✅ Completed — Phase 0 (Foundation)

- [x] Python 3.11.9 environment
- [x] venv setup
- [x] FastAPI clean architecture
- [x] Health check endpoint
- [x] Swagger UI
- [x] .env + .gitignore
- [x] GitHub repository

## ✅ Completed — Phase 1 (Database)

- [x] SQLAlchemy 2.0 + aiosqlite install
- [x] Base model with UUID + Timestamp mixins
- [x] Async database connection + session management
- [x] Conversation model
- [x] Message model
- [x] KnowledgeEntry model (confirm-before-save)
- [x] Auto table creation on startup
- [x] Database health check endpoint /api/v1/db-health

## 🔜 Next — Phase 2 (Ollama LLM Integration)

- [ ] Install Ollama on Windows
- [ ] Download Qwen2.5:7b model (Q4_K_M)
- [ ] Install ollama Python client
- [ ] Create OllamaService class
- [ ] Create chat endpoint /api/v1/chat
- [ ] Conversation history management
- [ ] Streaming response support
- [ ] Save messages to database
