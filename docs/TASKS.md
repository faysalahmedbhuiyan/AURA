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

- [x] Ollama + qwen2.5:3b
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

## 🔜 Next — Phase 4 (Voice System)

- [ ] faster-whisper install (STT)
- [ ] Piper TTS install
- [ ] Bangla voice model download
- [ ] VoiceService class
- [ ] POST /api/v1/voice/transcribe
- [ ] POST /api/v1/voice/speak
- [ ] Audio file handling
