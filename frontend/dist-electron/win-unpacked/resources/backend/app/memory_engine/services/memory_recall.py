"""
AURA Backend — Memory Recall Engine.

Module: app.memory_engine.services.memory_recall
Purpose: Smart recall of relevant memories for AURA's responses.
         Combines semantic search (ChromaDB) with structured
         retrieval (SQLite) for comprehensive memory access.

Memory recall triggers:
    - Every chat message (background semantic search)
    - Explicit recall requests ("মনে আছে?", "what did I say about...")
    - Context-based auto-recall (topic detection)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.memory_engine.models.memory_models import MemoryEntry
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "aura_advanced_memory"
CHROMA_PATH = Path(settings.chroma_db_path).resolve()


class MemoryRecall:
    """
    Smart memory recall engine.

    Searches across all memory layers using semantic similarity.
    Combines ChromaDB vector search with SQLite metadata filtering.

    Methods:
        store_memory: Index a confirmed memory in ChromaDB.
        recall: Search memories by semantic similarity.
        recall_by_layer: Search within a specific layer.
        update_recall_stats: Track recall frequency.
    """

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(CHROMA_PATH),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def _get_collection(self) -> chromadb.Collection:
        return self._get_client().get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "AURA advanced memory layers"},
        )

    async def store_memory(
        self,
        memory: MemoryEntry,
    ) -> bool:
        """
        Index a confirmed memory in ChromaDB.

        Args:
            memory: Confirmed MemoryEntry to index.

        Returns:
            bool: True if indexed successfully.
        """
        try:
            text_to_embed = f"{memory.title}\n\n{memory.content}"
            if memory.summary:
                text_to_embed = f"{memory.title}\n\n{memory.summary}"

            embedding = await embedding_service.embed(text_to_embed[:2000])

            if not embedding:
                return False

            collection = self._get_collection()
            collection.upsert(
                ids=[memory.id],
                embeddings=[embedding],
                documents=[memory.content[:1000]],
                metadatas=[{
                    "layer": memory.layer,
                    "memory_type": memory.memory_type,
                    "title": memory.title[:200],
                    "importance": memory.importance_score,
                    "tags": memory.tags or "",
                    "category": memory.category or "",
                    "language": memory.language,
                }],
            )
            logger.info("Indexed memory %s in ChromaDB", memory.id)
            return True

        except Exception as e:
            logger.exception("Failed to index memory %s: %s", memory.id, e)
            return False

    async def recall(
        self,
        query: str,
        n_results: int = 5,
        layer: str | None = None,
        min_importance: float = 0.0,
        language: str | None = None,
    ) -> list[dict]:
        """
        Recall memories semantically similar to query.

        Args:
            query: Search query text.
            n_results: Maximum results.
            layer: Filter by memory layer (None = all layers).
            min_importance: Minimum importance score.
            language: Filter by language.

        Returns:
            list[dict]: Recalled memories ranked by relevance.
        """
        try:
            embedding = await embedding_service.embed(query)
            if not embedding:
                return []

            collection = self._get_collection()
            total = collection.count()

            if total == 0:
                return []

            # Build filters
            where_conditions = []
            if layer:
                where_conditions.append({"layer": {"$eq": layer}})
            if min_importance > 0:
                where_conditions.append({"importance": {"$gte": min_importance}})
            if language:
                where_conditions.append({"language": {"$eq": language}})

            where = None
            if len(where_conditions) == 1:
                where = where_conditions[0]
            elif len(where_conditions) > 1:
                where = {"$and": where_conditions}

            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, total),
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            memories = []
            if results["documents"] and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    relevance = round(1 - float(dist), 3)
                    if relevance > 0.3:  # Minimum relevance threshold
                        memories.append({
                            "content": doc,
                            "title": meta.get("title", ""),
                            "layer": meta.get("layer", ""),
                            "memory_type": meta.get("memory_type", ""),
                            "importance": meta.get("importance", 0.5),
                            "tags": meta.get("tags", ""),
                            "language": meta.get("language", "bn"),
                            "relevance": relevance,
                        })

            # Sort by combined relevance + importance
            memories.sort(
                key=lambda m: m["relevance"] * 0.7 + m["importance"] * 0.3,
                reverse=True,
            )
            return memories

        except Exception as e:
            logger.warning("Memory recall failed: %s", e)
            return []

    async def recall_by_layer(
        self,
        query: str,
        layer: str,
        n_results: int = 3,
    ) -> list[dict]:
        """Recall memories from a specific layer."""
        return await self.recall(query, n_results, layer=layer)

    async def get_context_for_chat(
        self,
        query: str,
        language: str = "bn",
    ) -> str:
        """
        Get relevant memory context for chat injection.

        Searches all layers and formats as context string
        for injection into LLM prompt.

        Args:
            query: Current user message.
            language: Language for context.

        Returns:
            str: Formatted memory context (empty if nothing relevant).
        """
        memories = await self.recall(
            query=query,
            n_results=5,
            min_importance=0.4,
        )

        if not memories:
            return ""

        context_parts = []

        # Group by layer
        personal = [m for m in memories if m["layer"] == "personal"]
        preferences = [m for m in memories if m["layer"] == "preference"]
        decisions = [m for m in memories if m["layer"] == "decision"]
        projects = [m for m in memories if m["layer"] == "project"]
        others = [m for m in memories if m["layer"] not in
                  ("personal", "preference", "decision", "project")]

        if personal:
            context_parts.append("=== Personal Info ===")
            for m in personal[:2]:
                context_parts.append(f"• {m['title']}: {m['content'][:150]}")

        if preferences:
            context_parts.append("=== Preferences ===")
            for m in preferences[:2]:
                context_parts.append(f"• {m['content'][:150]}")

        if decisions:
            context_parts.append("=== Past Decisions ===")
            for m in decisions[:2]:
                context_parts.append(f"• {m['title']}: {m['content'][:150]}")

        if projects:
            context_parts.append("=== Project Context ===")
            for m in projects[:2]:
                context_parts.append(f"• {m['content'][:150]}")

        if others:
            context_parts.append("=== Relevant Memory ===")
            for m in others[:2]:
                context_parts.append(f"• {m['content'][:150]}")

        return "\n".join(context_parts)

    async def update_recall_stats(
        self,
        memory_id: str,
        db: AsyncSession,
    ) -> None:
        """Track how often a memory is recalled."""
        try:
            result = await db.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            memory = result.scalar_one_or_none()
            if memory:
                memory.recall_count += 1
                memory.last_recalled_at = datetime.now(timezone.utc)
                await db.flush()
        except Exception as e:
            logger.warning("Failed to update recall stats: %s", e)


# ── Singleton ─────────────────────────────────────────────────────────────────
memory_recall = MemoryRecall()