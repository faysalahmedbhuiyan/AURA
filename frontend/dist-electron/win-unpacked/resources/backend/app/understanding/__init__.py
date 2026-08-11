"""
AURA Backend — Project Understanding Engine Package.

Package: app.understanding
Purpose: Implements Phase 14 — Project Understanding Engine.

         AURA analyzes its own codebase to understand:
         - Project structure (folders, files, sizes)
         - Module dependencies (import graph)
         - API endpoints (FastAPI routes)
         - Database models
         - Code search (keyword/pattern across files)

         All operations are READ-ONLY — nothing is modified.
         Results help AURA give better answers about its own code.

Modules:
    structure_analyzer   — Folder/file tree with metadata
    dependency_mapper    — Python import graph builder
    code_search          — Full-text search across codebase
    understanding_service — Orchestrates all analyzers
"""