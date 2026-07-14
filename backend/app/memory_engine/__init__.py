"""
AURA Backend — Advanced Memory Engine Package.

Package: app.memory_engine
Purpose: Phase 22 — Human-like long-term memory system.

         Memory Layers:
         - Conversation  : Recent chat context (short-term)
         - Personal      : Facts about Faysal (name, location, preferences)
         - Preference    : UI/behavior preferences
         - Decision      : Important decisions and their context
         - Project       : Project-specific knowledge
         - Coding        : Code patterns, snippets, solutions
         - Learning Queue: Pending items awaiting confirmation

         Features:
         - Importance scoring (0.0-1.0)
         - Memory expiration (TTL-based)
         - Memory summarization (LLM-powered)
         - Semantic recall (ChromaDB-powered)
         - Episodic memory (event-based)
         - Procedural memory (how-to knowledge)

         Integration:
         - ChromaDB: Vector storage for semantic search
         - SQLite: Structured metadata storage
         - Existing MemoryService: Extended, not replaced
"""