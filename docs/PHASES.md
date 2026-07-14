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
**Deliverable:** POST /api/v1/chat working (later migrated to aura-brain)

## ✅ Phase 3 — Memory System (Complete)

**Duration:** 1 session
**Goal:** ChromaDB, RAG pipeline, confirm-before-save knowledge
**Deliverable:** Semantic search, RAG-enhanced chat, knowledge system

---

## ✅ Phase 4 — Voice System (Complete)

**Dependencies:** Phase 3 ✅
**Goal:** Offline STT + TTS in Bangla and English
**Deliverable:**

- POST /api/v1/voice/transcribe
- POST /api/v1/voice/speak
- POST /api/v1/voice/chat

---

## ✅ Phase 5 — Frontend (Complete)

**Dependencies:** Phase 4 ✅
**Goal:** React + Electron desktop UI
**Deliverable:** Chat interface, Voice interface, Sidebar navigation, dark theme

---

## ✅ Phase 6 — Knowledge System (Complete)

**Dependencies:** Phase 5 ✅
**Goal:** Intelligent web learning with confirmation pipeline
**Pipeline:** Search → Collect → Verify → Compare → Summarize → Confirm → Store → Index
**Deliverable:** ResearchService, POST /api/v1/knowledge/research, KnowledgeView UI

---

## ✅ Phase 7 — Agents & Automation (Complete, extensible)

**Dependencies:** Phase 6 ✅
**Goal:** Task automation, file management, system control
**Deliverable:** FileAgent, SystemAgent, /api/v1/agents/\* endpoints, AgentView UI
**Note:** More agent types (web browsing, task scheduling) planned for future sessions.

---

## ✅ Phase 8 — Self Review Engine (Complete)

**Dependencies:** Phase 7 ✅
**Goal:** Code quality analysis, technical debt detection
**Safety Rule:** Analysis only — never modifies code automatically
**Deliverable:** AST-based CodeAnalyzer, DebtDetector, SuggestionEngine,
POST /api/v1/review/analyze, ReviewView UI
**Scope Limitation:** Python (.py) files only — does not analyze frontend JS/JSX.

---

## ✅ Phase 9 — Self Improvement Planner (Complete)

**Dependencies:** Phase 8 ✅
**Goal:** Safe improvement planning with risk analysis
**Safety Rule:** Creates plan only — never applies without approval
**Deliverable:** RequestParser, ImpactMapper (backend AND frontend files),
RiskEstimator (low/medium/high/critical), POST /api/v1/planning/create,
PlanningView UI

---

## ✅ Phase 10 — Safe Self Modification (Complete)

**Dependencies:** Phase 9 ✅
**Goal:** Controlled, reversible code modification
**Safety Rules:**

- Always explain what will change
- Always list every affected file
- Always create backup before change
- Always wait for user confirmation (confirmed=True, non-bypassable)
- Always report result with rollback instructions
- Protected files (main.py, .env, modification system itself) can never
  be modified through this pipeline

**Workflow:** Plan → Backup → Confirm → Apply → Report
**Deliverable:** BackupManager, ChangeApplier, ResultReporter,
POST /api/v1/modification/apply, POST /api/v1/modification/rollback,
Apply UI integrated into PlanningView

---

## ✅ Phase 11 — Rollback System (Complete)

**Dependencies:** Phase 10 ✅
**Goal:** Git-based safe version restoration
**Deliverable:** GitService, SnapshotService, RollbackService,
GET /api/v1/rollback/status, /log, /preview/{ref},
POST /api/v1/rollback/commit, /files, /snapshots, /restore-snapshot,
DELETE /api/v1/rollback/snapshots/{id}, RollbackView UI
**Note:** Every rollback auto-creates a pre-rollback snapshot; rollback
itself is always reversible.

---

## ✅ Phase 12 — Development Journal (Complete)

**Dependencies:** Phase 11 ✅
**Goal:** Automated engineering log and decision tracker
**Deliverable:** JournalEntry model (SQLite), session_log/decision/change
categories, POST+GET /api/v1/journal/entries, GET /api/v1/journal/summary,
JournalView UI (Browse/New Entry/Summary tabs). Append-only — entries
are never edited or deleted once created.

---

## ✅ Phase 13 — Advanced Memory System (Complete)

**Dependencies:** Phase 12 ✅
**Goal:** Separated, secure, multi-tier memory
**Memory Tiers:**

1. Personal Memory — user preferences (private) — new in this phase
2. Knowledge Base — confirmed public facts — reused from Phase 3/6 (KnowledgeEntry)
3. Decision Memory — architectural decisions — new in this phase
4. Learning Queue — pending user confirmation — new in this phase

**Safety Rule:** Nothing moves from Queue to Storage without explicit
user confirmation — verified via confirm/reject/double-confirm tests.
**Deliverable:** PersonalMemoryEntry, DecisionRecord, LearningQueueItem
models, MemoryTierService (queue promotion), /api/v1/memory-tiers/\*
endpoints, MemoryTiersView UI

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

old_str: ## 📋 Phase 15 — Coding Mentor Mode

**Dependencies:** Phase 14 ✅
**Goal:** AURA explains and teaches its own code
**Key Features:**

- Line-by-line code explainer
- Concept teacher with examples
- Best practice suggester
- Interactive Q&A about codebase

new_str: ## ✅ Phase 15 — Coding Mentor Mode (Complete)

**Dependencies:** Phase 14 ✅
**Goal:** AURA explains and teaches its own code
**Deliverable:** CodeExplainer (AST + LLM), ConceptTeacher, PracticeSuggester
(reuses Phase 8 analyzer with educational framing), interactive Q&A endpoint
grounded in optional file context. POST /api/v1/mentor/{explain,concept,practices,ask}.
MentorView UI (4 tabs). Fully read-only.

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

# Phase 22 — Advanced Memory Engine

**Status:** ✅ Complete
**Date:** 2026-07-13

## Goal

Create human-like long-term memory with multiple layers.

## Memory Layers Implemented

| Layer        | Purpose                 | Base Importance |
| ------------ | ----------------------- | --------------- |
| personal     | Facts about Faysal      | 0.85            |
| decision     | Important decisions     | 0.80            |
| project      | Project knowledge       | 0.75            |
| coding       | Code patterns/solutions | 0.70            |
| preference   | User preferences        | 0.65            |
| journal      | Daily log               | 0.55            |
| learning     | Pending confirmation    | 0.60            |
| conversation | Short-term context      | 0.40            |

## Memory Types

- **Semantic**: General knowledge and facts
- **Episodic**: Event-based memories (what happened when)
- **Procedural**: How-to knowledge (how to do things)

## Features

- Importance scoring (0.0-1.0) with keyword analysis
- Memory summarization via Ollama LLM (>500 chars)
- ChromaDB semantic search across all layers
- Learning Queue (confirm-before-save enforced)
- Recall frequency tracking
- Context injection into chat responses

## New Database Tables

- memory_entries: All confirmed memories
- learning_queue: Pending confirmation items

## New Endpoints

- POST /api/v1/memory/advanced/queue
- GET /api/v1/memory/advanced/queue
- POST /api/v1/memory/advanced/queue/{id}/confirm
- POST /api/v1/memory/advanced/queue/{id}/reject
- POST /api/v1/memory/advanced/create
- GET /api/v1/memory/advanced/layer/{layer}
- POST /api/v1/memory/advanced/recall
- GET /api/v1/memory/advanced/context
- GET /api/v1/memory/advanced/stats

## Integration

- Chat route: Advanced memory context injected automatically
- ChromaDB: Separate collection "aura_advanced_memory"
- Existing memory system: Unchanged (no regression)

## Files Created

- backend/app/memory_engine/**init**.py
- backend/app/memory_engine/models/memory_models.py
- backend/app/memory_engine/models/**init**.py
- backend/app/memory_engine/services/importance_scorer.py
- backend/app/memory_engine/services/memory_summarizer.py
- backend/app/memory_engine/services/memory_recall.py
- backend/app/memory_engine/services/**init**.py
- backend/app/memory_engine/advanced_memory_service.py
- backend/app/api/v1/routes/advanced_memory.py
- docs/PHASE_REPORT_22.md
