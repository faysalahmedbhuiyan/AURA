# AURA Feature List

> Status: planned = documented only, in-progress = being built, done = complete

---

## Core Features (Phase 0-3) ✅

| Feature                       | Status  | Phase |
| ----------------------------- | ------- | ----- |
| FastAPI Backend               | ✅ done | 0     |
| SQLite Database               | ✅ done | 1     |
| Ollama LLM Chat               | ✅ done | 2     |
| Conversation History          | ✅ done | 2     |
| ChromaDB Vector Memory        | ✅ done | 3     |
| RAG Pipeline                  | ✅ done | 3     |
| Confirm-Before-Save Knowledge | ✅ done | 3     |
| Semantic Search               | ✅ done | 3     |

---

## Phase 4 — Voice System ✅ done

| Feature                                    | Status  |
| ------------------------------------------ | ------- |
| Speech-to-Text (faster-whisper)            | ✅ done |
| Text-to-Speech (Piper)                     | ✅ done |
| Bangla voice support                       | ✅ done |
| Voice chat endpoint                        | ✅ done |
| On-demand model loading (RAM optimization) | ✅ done |

---

## Phase 5 — Frontend ✅ done

| Feature                      | Status                                         |
| ---------------------------- | ---------------------------------------------- |
| React + Electron desktop app | ✅ done                                        |
| Chat UI                      | ✅ done                                        |
| Voice interface              | ✅ done                                        |
| Knowledge management UI      | ✅ done                                        |
| Settings panel               | 📋 planned (slot currently used by Review tab) |

---

## Phase 6 — Knowledge System ✅ done

| Feature                                                                  | Status  |
| ------------------------------------------------------------------------ | ------- |
| Web search integration                                                   | ✅ done |
| Search → Collect → Verify → Summarize → Confirm → Store → Index pipeline | ✅ done |
| Source tracking                                                          | ✅ done |
| Confidence scoring                                                       | ✅ done |
| Knowledge categories                                                     | ✅ done |

---

## Phase 7 — Agents & Automation ✅ done (extensible)

| Feature               | Status     |
| --------------------- | ---------- |
| File management agent | ✅ done    |
| System control agent  | ✅ done    |
| Task automation agent | 📋 planned |
| Web browsing agent    | 📋 planned |

---

## Phase 8 — Self Review Engine ✅ done

| Feature                 | Status  | Priority |
| ----------------------- | ------- | -------- |
| Code quality analyzer   | ✅ done | high     |
| Technical debt detector | ✅ done | high     |
| Improvement suggester   | ✅ done | medium   |
| Affected file mapper    | ✅ done | high     |

**Description:**
AURA analyzes its own codebase for quality issues, detects
technical debt, and suggests improvements. Never applies
changes automatically — always requires user approval.
**Limitation:** Python (.py) files only, via AST — does not analyze
frontend JS/JSX/CSS.

---

## Phase 9 — Self Improvement Planner ✅ done

| Feature                              | Status  | Priority |
| ------------------------------------ | ------- | -------- |
| Improvement request analyzer         | ✅ done | high     |
| Risk estimator                       | ✅ done | high     |
| Affected file lister (cross-project) | ✅ done | high     |
| Benefit explainer                    | ✅ done | medium   |
| Approval gate (never skipped)        | ✅ done | critical |

**Description:**
Before any self-modification, AURA creates a detailed plan:
what changes, which files, what risks, what benefits.
User must explicitly approve before anything happens.
Unlike Phase 8, this maps affected files across the WHOLE
project (backend AND frontend).

---

## Phase 10 — Safe Self Modification ✅ done

| Feature                                  | Status     | Priority                    |
| ---------------------------------------- | ---------- | --------------------------- |
| Change explainer                         | ✅ done    | critical                    |
| Affected file lister                     | ✅ done    | critical                    |
| Automatic backup before change           | ✅ done    | critical                    |
| User confirmation gate                   | ✅ done    | critical                    |
| Change applicator                        | ✅ done    | high                        |
| Post-change test runner                  | 📋 planned | high (deferred to Phase 18) |
| Git commit generator (suggested message) | ✅ done    | high                        |
| Result reporter                          | ✅ done    | high                        |

**Core Rule:** AURA never modifies its own source code
without explicit user confirmation. Ever.
Protected files (main.py, .env, the modification system itself)
can never be modified through this pipeline.

---

## Phase 11 — Rollback System ✅ done

| Feature                                       | Status  | Priority |
| --------------------------------------------- | ------- | -------- |
| Git-based version restore                     | ✅ done | critical |
| Rollback point creator                        | ✅ done | high     |
| Safe restore validator (preview before apply) | ✅ done | high     |
| Rollback history viewer                       | ✅ done | medium   |
| Named snapshots                               | ✅ done | medium   |

---

## Phase 12 — Development Journal ✅ done

| Feature                   | Status  | Priority |
| ------------------------- | ------- | -------- |
| Daily engineering log     | ✅ done | medium   |
| Decision recorder         | ✅ done | high     |
| Change history            | ✅ done | high     |
| Session summary generator | ✅ done | medium   |

---

## Phase 13 — Advanced Memory System ✅ done

| Feature                                   | Status                          | Priority |
| ----------------------------------------- | ------------------------------- | -------- |
| Learning Queue (pending confirmation)     | ✅ done                         | critical |
| Personal Memory (user preferences)        | ✅ done                         | high     |
| Knowledge Base (verified public facts)    | ✅ done (reused from Phase 3/6) | high     |
| Decision Memory (architectural decisions) | ✅ done                         | high     |

**Memory Architecture:**
Memory/
├── personal/ ← User preferences, habits, private info (new, Phase 13)
├── knowledge/ ← Verified public knowledge (Phase 3/6, reused)
├── decisions/ ← Architectural decisions log (new, Phase 13)
└── queue/ ← Pending items awaiting confirmation (new, Phase 13)

---

## Phase 14 — Project Understanding Engine

| Feature                    | Status     | Priority |
| -------------------------- | ---------- | -------- |
| Project structure analyzer | 📋 planned | high     |
| Dependency mapper          | 📋 planned | high     |
| Module relationship graph  | 📋 planned | medium   |
| Code search engine         | 📋 planned | medium   |

---

## Phase 15 — Coding Mentor Mode

| Feature                   | Status     | Priority |
| ------------------------- | ---------- | -------- |
| Code explainer            | 📋 planned | medium   |
| Concept teacher           | 📋 planned | medium   |
| Best practice suggester   | 📋 planned | medium   |
| Interactive learning mode | 📋 planned | low      |

---

## Phase 16 — Goal Manager

| Feature                | Status     | Priority |
| ---------------------- | ---------- | -------- |
| Goal breakdown engine  | 📋 planned | high     |
| Milestone tracker      | 📋 planned | high     |
| Task dependency mapper | 📋 planned | medium   |
| Progress reporter      | 📋 planned | medium   |

---

## Phase 17 — Change Impact Analysis

| Feature                          | Status     | Priority |
| -------------------------------- | ---------- | -------- |
| Pre-change file impact predictor | 📋 planned | critical |
| Module dependency tracer         | 📋 planned | high     |
| Risk level calculator            | 📋 planned | high     |
| Impact report generator          | 📋 planned | medium   |

---

## Phase 18 — Automatic Testing

| Feature                   | Status     | Priority |
| ------------------------- | ---------- | -------- |
| Test runner after changes | 📋 planned | critical |
| Test result summarizer    | 📋 planned | high     |
| Coverage reporter         | 📋 planned | medium   |
| Regression detector       | 📋 planned | high     |

---

## Phase 19 — AI Health Monitor

| Feature                  | Status                             | Priority |
| ------------------------ | ---------------------------------- | -------- |
| CPU usage monitor        | ✅ done (via SystemAgent, Phase 7) | high     |
| RAM usage monitor        | ✅ done (via SystemAgent, Phase 7) | critical |
| Storage monitor          | ✅ done (via SystemAgent, Phase 7) | medium   |
| Ollama model status      | 📋 planned                         | high     |
| ChromaDB health          | 📋 planned                         | high     |
| SQLite health            | 📋 planned                         | high     |
| Alert system + dashboard | 📋 planned                         | high     |

**Note:** Basic CPU/RAM/disk monitoring already exists via Phase 7's
SystemAgent (`GET /api/v1/agents/health`). Phase 19 will build a
dedicated always-on monitor with alerting on top of this foundation.

---

## Immutable Rules (All Phases)

These rules can never be overridden by any feature:

1. AURA never modifies its own code without user approval
2. AURA never permanently stores anything without user confirmation
3. Every important action is logged
4. Every architectural decision is documented
5. Every change is reversible
6. Human approval is always the final gate
