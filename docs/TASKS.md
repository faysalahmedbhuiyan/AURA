# AURA Task List

---

## ✅ Completed Tasks

### Phase 0 — Foundation

- [x] Install Python 3.11.9
- [x] Create venv with Python 3.11
- [x] Create requirements.txt
- [x] Install FastAPI, Uvicorn, Pydantic, pydantic-settings, python-dotenv
- [x] Create app/ package structure
- [x] Create app/config.py — centralized settings
- [x] Create app/main.py — FastAPI entry point
- [x] Create app/api/v1/routes/health.py — health check
- [x] Create .env and .env.example
- [x] Create .gitignore
- [x] Verify server runs at http://127.0.0.1:8000
- [x] Verify Swagger UI at http://127.0.0.1:8000/docs

---

## 🔜 Next Tasks — Phase 1 (Database Foundation)

- [ ] Install SQLAlchemy + aiosqlite
- [ ] Create database/ folder structure
- [ ] Create database connection module
- [ ] Create base model (TimestampMixin)
- [ ] Create Conversation model
- [ ] Create Message model
- [ ] Create KnowledgeEntry model
- [ ] Create database initialization script
- [ ] Add /api/v1/db-health endpoint
- [ ] Write tests for database layer

---

## 📋 Upcoming — Phase 2+

- [ ] Ollama integration
- [ ] Chat endpoint
- [ ] ChromaDB setup
- [ ] Voice pipeline
- [ ] Frontend scaffold
