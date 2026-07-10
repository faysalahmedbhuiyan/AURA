# AURA Development Phases

> Rule: Never start a phase before its dependencies are complete.
> Rule: Always update documentation before moving to next phase.

---

## ✅ Phase 0 — Foundation (Complete)

**Duration:** 1 session
**Goal:** Backend skeleton, environment, health check
**Deliverable:** FastAPI server running at localhost:8000

## ✅ Phase 1 — Database (Complete)

**Duration:** 1 session
**Goal:** SQLite models, async connection, DB health
**Deliverable:** Three core tables, db-health endpoint

## ✅ Phase 2 — LLM Integration (Complete)

**Duration:** 1 session
**Goal:** Ollama chat, conversation history, message persistence
**Deliverable:** POST /api/v1/chat working with qwen2.5:3b

## ✅ Phase 3 — Memory System (Complete)

**Duration:** 1 session
**Goal:** ChromaDB, RAG pipeline, confirm-before-save knowledge
**Deliverable:** Semantic search, RAG-enhanced chat, knowledge system

---

## 🔜 Phase 4 — Voice System

**Dependencies:** Phase 3 ✅
**Goal:** Offline STT + TTS in Bangla and English
**Components:**

- faster-whisper (Speech-to-Text)
- Piper (Text-to-Speech)
- On-demand loading (RAM optimization)
  **Deliverables:**
- POST /api/v1/voice/transcribe
- POST /api/v1/voice/speak
- POST /api/v1/voice/chat

---

## 📋 Phase 5 — Frontend

**Dependencies:** Phase 4 ✅
**Goal:** React + Electron desktop UI
**Components:**

- Chat interface
- Voice interface
- Knowledge management panel
- Settings panel

---

## 📋 Phase 6 — Knowledge System

**Dependencies:** Phase 5 ✅
**Goal:** Intelligent web learning with confirmation pipeline
**Pipeline:** Search → Collect → Verify → Compare → Summarize → Confirm → Store → Index

---

old_str: ## 📋 Phase 7 — Agents & Automation

**Dependencies:** Phase 6 ✅
**Goal:** Task automation, file management, system control

---

## 📋 Phase 8 — Self Review Engine

**Dependencies:** Phase 7 ✅
**Goal:** Code quality analysis, technical debt detection

new_str: ## ✅ Phase 7 — Agents & Automation (Complete, extensible)

**Dependencies:** Phase 6 ✅
**Goal:** Task automation, file management, system control
**Deliverable:** FileAgent, SystemAgent, /api/v1/agents/\* endpoints, AgentView UI
**Note:** More agent types planned for future sessions.

---

## ✅ Phase 8 — Self Review Engine (Complete)

**Dependencies:** Phase 7 ✅
**Goal:** Code quality analysis, technical debt detection
**Deliverable:** AST-based analyzer, debt scoring, suggestion engine, ReviewView UI

old_str: ## 📋 Phase 9 — Self Improvement Planner

**Dependencies:** Phase 8 ✅
**Goal:** Safe improvement planning with risk analysis
**Safety Rule:** Creates plan only — never applies without approval
**Key Features:**

- Improvement request parser
- Risk level estimator (low/medium/high/critical)
- Affected file mapper
- Benefit vs risk explainer
- Approval gate (cannot be bypassed)

---

## 📋 Phase 10 — Safe Self Modification

**Dependencies:** Phase 9 ✅
**Goal:** Controlled, reversible code modification

new_str: ## ✅ Phase 9 — Self Improvement Planner (Complete)

**Dependencies:** Phase 8 ✅
**Goal:** Safe improvement planning with risk analysis
**Deliverable:** RequestParser, ImpactMapper (backend+frontend), RiskEstimator,
POST /api/v1/planning/create, PlanningView UI. Analysis only — no writes.

---

## ✅ Phase 10 — Safe Self Modification (Complete)

**Dependencies:** Phase 9 ✅
**Goal:** Controlled, reversible code modification
**Deliverable:** BackupManager, ChangeApplier, ResultReporter,
POST /api/v1/modification/apply (confirmed=True required, auto-backup),
POST /api/v1/modification/rollback, Apply UI integrated into PlanningView.
**Safety:** Protected files (main.py, .env, modification system itself)
can never be modified through this pipeline. Every apply is backed up first.

## Plan → Backup → Confirm → Apply → Test → Commit → Report

## 📋 Phase 11 — Rollback System

**Dependencies:** Phase 10 ✅
**Goal:** Git-based safe version restoration
**Key Features:**

- Rollback point creator (before every change)
- Safe restore with validation
- Rollback history viewer
- Partial rollback support

---

old_str: ## 📋 Phase 12 — Development Journal

**Dependencies:** Phase 11 ✅
**Goal:** Automated engineering log and decision tracker

new_str: ## ✅ Phase 12 — Development Journal (Complete)

**Dependencies:** Phase 11 ✅
**Goal:** Automated engineering log and decision tracker
**Deliverable:** JournalEntry model (SQLite), session_log/decision/change
categories, POST+GET /api/v1/journal/entries, GET /api/v1/journal/summary,
JournalView UI (Browse/New Entry/Summary tabs). Append-only — entries
are never edited or deleted once created.

## 📋 Phase 13 — Advanced Memory System

**Dependencies:** Phase 12 ✅
**Goal:** Separated, secure, multi-tier memory
**Memory Tiers:**

1. Personal Memory — user preferences (private)
2. Knowledge Base — confirmed public facts
3. Decision Memory — architectural decisions
4. Learning Queue — pending user confirmation
   **Safety Rule:** Nothing moves from Queue to Storage
   without explicit user confirmation

---

## 📋 Phase 14 — Project Understanding Engine

**Dependencies:** Phase 13 ✅
**Goal:** AURA understands its own codebase
**Key Features:**

- Project structure analyzer
- Module dependency mapper
- Code search engine
- Import graph generator

---

## 📋 Phase 15 — Coding Mentor Mode

**Dependencies:** Phase 14 ✅
**Goal:** AURA explains and teaches its own code
**Key Features:**

- Line-by-line code explainer
- Concept teacher with examples
- Best practice suggester
- Interactive Q&A about codebase

---

## 📋 Phase 16 — Goal Manager

**Dependencies:** Phase 15 ✅
**Goal:** Break large goals into trackable milestones
**Key Features:**

- Goal → Milestone → Task breakdown
- Dependency tracking between tasks
- Progress calculation
- Blocker identification

---

## 📋 Phase 17 — Change Impact Analysis

**Dependencies:** Phase 16 ✅
**Goal:** Predict consequences before making changes
**Key Features:**

- File impact predictor
- Module dependency tracer
- Risk level calculator (1-10)
- Impact report generator

---

## 📋 Phase 18 — Automatic Testing

**Dependencies:** Phase 17 ✅
**Goal:** Automated test execution after every change
**Key Features:**

- pytest integration
- Test result summarizer
- Coverage reporter
- Regression detector
- Test failure explainer

---

## 📋 Phase 19 — AI Health Monitor

**Dependencies:** Phase 18 ✅
**Goal:** Real-time system health monitoring
**Monitored Metrics:**

- CPU usage (%)
- RAM usage (GB / %)
- Storage usage (GB / %)
- Ollama model status
- ChromaDB collection health
- SQLite integrity check
- API response times
  **Alert Levels:** info → warning → critical
