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

## Phase 4 — Voice System

| Feature                                    | Status  |
| ------------------------------------------ | ------- |
| Speech-to-Text (faster-whisper)            | 🔜 next |
| Text-to-Speech (Piper)                     | 🔜 next |
| Bangla voice support                       | 🔜 next |
| Voice chat endpoint                        | 🔜 next |
| On-demand model loading (RAM optimization) | 🔜 next |

---

## Phase 5 — Frontend

| Feature                      | Status     |
| ---------------------------- | ---------- |
| React + Electron desktop app | 📋 planned |
| Chat UI                      | 📋 planned |
| Voice interface              | 📋 planned |
| Knowledge management UI      | 📋 planned |
| Settings panel               | 📋 planned |

---

## Phase 6 — Knowledge System

| Feature                                              | Status     |
| ---------------------------------------------------- | ---------- |
| Web search integration                               | 📋 planned |
| Search → Collect → Verify → Confirm → Store pipeline | 📋 planned |
| Source tracking                                      | 📋 planned |
| Confidence scoring                                   | 📋 planned |
| Knowledge categories                                 | 📋 planned |

---

## Phase 7 — Agents & Automation

| Feature               | Status     |
| --------------------- | ---------- |
| File management agent | 📋 planned |
| Task automation agent | 📋 planned |
| Web browsing agent    | 📋 planned |
| System control agent  | 📋 planned |

---

## Phase 8 — Self Review Engine

| Feature                 | Status     | Priority |
| ----------------------- | ---------- | -------- |
| Code quality analyzer   | 📋 planned | high     |
| Technical debt detector | 📋 planned | high     |
| Improvement suggester   | 📋 planned | medium   |
| Affected file mapper    | 📋 planned | high     |

**Description:**
AURA analyzes its own codebase for quality issues, detects
technical debt, and suggests improvements. Never applies
changes automatically — always requires user approval.

---

## Phase 9 — Self Improvement Planner

| Feature                       | Status     | Priority |
| ----------------------------- | ---------- | -------- |
| Improvement request analyzer  | 📋 planned | high     |
| Risk estimator                | 📋 planned | high     |
| Affected file lister          | 📋 planned | high     |
| Benefit explainer             | 📋 planned | medium   |
| Approval gate (never skipped) | 📋 planned | critical |

**Description:**
Before any self-modification, AURA creates a detailed plan:
what changes, which files, what risks, what benefits.
User must explicitly approve before anything happens.

---

## Phase 10 — Safe Self Modification

| Feature                        | Status     | Priority |
| ------------------------------ | ---------- | -------- |
| Change explainer               | 📋 planned | critical |
| Affected file lister           | 📋 planned | critical |
| Automatic backup before change | 📋 planned | critical |
| User confirmation gate         | 📋 planned | critical |
| Change applicator              | 📋 planned | high     |
| Post-change test runner        | 📋 planned | high     |
| Git commit generator           | 📋 planned | high     |
| Result reporter                | 📋 planned | high     |

**Core Rule:** AURA never modifies its own source code
without explicit user confirmation. Ever.

---

## Phase 11 — Rollback System

| Feature                   | Status     | Priority |
| ------------------------- | ---------- | -------- |
| Git-based version restore | 📋 planned | critical |
| Rollback point creator    | 📋 planned | high     |
| Safe restore validator    | 📋 planned | high     |
| Rollback history viewer   | 📋 planned | medium   |

---

## Phase 12 — Development Journal

| Feature                   | Status     | Priority |
| ------------------------- | ---------- | -------- |
| Daily engineering log     | 📋 planned | medium   |
| Decision recorder         | 📋 planned | high     |
| Change history            | 📋 planned | high     |
| Session summary generator | 📋 planned | medium   |

---

## Phase 13 — Advanced Memory System

| Feature                                   | Status     | Priority |
| ----------------------------------------- | ---------- | -------- |
| Learning Queue (pending confirmation)     | 📋 planned | critical |
| Personal Memory (user preferences)        | 📋 planned | high     |
| Knowledge Base (verified public facts)    | 📋 planned | high     |
| Decision Memory (architectural decisions) | 📋 planned | high     |

**Memory Architecture:**
Memory/
├── personal/ ← User preferences, habits, private info
├── knowledge/ ← Verified public knowledge (confirmed)
├── decisions/ ← Architectural decisions log
└── queue/ ← Pending items awaiting confirmation

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

| Feature             | Status     | Priority |
| ------------------- | ---------- | -------- |
| CPU usage monitor   | 📋 planned | high     |
| RAM usage monitor   | 📋 planned | critical |
| Storage monitor     | 📋 planned | medium   |
| Ollama model status | 📋 planned | high     |
| ChromaDB health     | 📋 planned | high     |
| SQLite health       | 📋 planned | high     |
| Alert system        | 📋 planned | high     |

---

## Immutable Rules (All Phases)

These rules can never be overridden by any feature:

1. AURA never modifies its own code without user approval
2. AURA never permanently stores anything without user confirmation
3. Every important action is logged
4. Every architectural decision is documented
5. Every change is reversible
6. Human approval is always the final gate
