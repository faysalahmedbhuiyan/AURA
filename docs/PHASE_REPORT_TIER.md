# Tier 2 — Intelligence Layer

**Status:** ✅ Complete
**Date:** 2026-07-17

## Goal

Transform AURA from a raw information storer into an intelligent knowledge processor.

## Architecture

Input Content
↓
[Classifier] — Knowledge type, category, tags, importance
↓
[Evolution Engine] — Duplicate check, merge or create
↓
[ChromaDB] — Semantic indexing
↓
[Relationship Builder] — Build knowledge graph
↓
[Confirmed Knowledge] — Available for recall

## Knowledge Types Supported

| Type       | Description            | Example                                   |
| ---------- | ---------------------- | ----------------------------------------- |
| Knowledge  | Facts, definitions     | "Python is a programming language"        |
| Skill      | How-to, procedures     | "How to create a FastAPI route"           |
| Rule       | Constraints, policies  | "Always use type hints in Python"         |
| Workflow   | Step-by-step processes | "Deployment process: test→build→deploy"   |
| Pattern    | Recurring structures   | "Repository pattern for data access"      |
| Template   | Reusable formats       | "API response template"                   |
| Experience | Decisions, outcomes    | "Chose SQLite over PostgreSQL because..." |
| Reference  | External sources       | "https://fastapi.tiangolo.com"            |

## Knowledge Evolution

- New source confirms → confidence increases, source_count++
- New source adds details → notes merged via LLM, version++
- Similar topic found → evolves existing instead of creating duplicate
- Version history preserved forever

## New Database Tables

- knowledge_items
- knowledge_relationships
- knowledge_versions

## New Endpoints

- POST /api/v1/intelligence/process
- POST /api/v1/intelligence/confirm/{id}
- POST /api/v1/intelligence/search
- GET /api/v1/intelligence/graph/{id}
- GET /api/v1/intelligence/stats
- GET /api/v1/intelligence/items
- GET /api/v1/intelligence/pending
- GET /api/v1/intelligence/items/{id}

## Integration

- Chat route: "save it" now goes through Intelligence Layer
- ChromaDB: Separate "aura_intelligence" collection
- Evolution Engine: LLM-powered knowledge merging
- Relationship Builder: Auto-builds knowledge graph

## Files Created

- backend/app/intelligence/**init**.py
- backend/app/intelligence/models/**init**.py
- backend/app/intelligence/models/knowledge_item.py
- backend/app/intelligence/classifier.py
- backend/app/intelligence/relationship_builder.py
- backend/app/intelligence/evolution_engine.py
- backend/app/intelligence/intelligence_service.py
- backend/app/api/v1/routes/intelligence.py
- docs/PHASE_REPORT_TIER2.md
