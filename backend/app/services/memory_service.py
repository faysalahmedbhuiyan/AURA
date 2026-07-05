"""
AURA Backend — Memory Service.

Module: app.services.memory_service
Purpose: Manages AURA's long-term semantic memory using ChromaDB.
         Stores conversation messages and knowledge entries as vectors.
         Provides semantic search to find relevant past context.

Collections:
    - conversations: Past chat messages for context retrieval
    - knowledge: Verified knowledge entries (user-confirmed only)

Optimized for 8GB RAM — uses persistent disk storage,
loads only queried vectors into memory.
"""

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()

# ── ChromaDB Path ─────────────────────────────────────────────────────────────
CHROMA_PATH = Path(settings.chroma_db_path).resolve()
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

# ── Collection Names ──────────────────────────────────────────────────────────
COLLECTION_CONVERSATIONS = "aura_conversations"
COLLECTION_KNOWLEDGE = "aura_knowledge"


class MemoryService:
    """
    Service for AURA's semantic memory using ChromaDB.

    Manages two collections:
    - conversations: Message history for context-aware responses
    - knowledge: User-confirmed knowledge entries

    Uses persistent ChromaDB storage on disk to minimize RAM usage.
    Vectors are loaded on demand, not kept in memory permanently.

    Methods:
        store_message: Save a message to conversation memory.
        search_conversations: Find semantically similar past messages.
        store_knowledge: Save a confirmed knowledge entry.
        search_knowledge: Find relevant knowledge entries.
        get_relevant_context: Get combined context for RAG.
    """

    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None

    def _get_client(self) -> chromadb.PersistentClient:
        """
        Get or create ChromaDB persistent client.

        Uses lazy initialization to avoid startup overhead.

        Returns:
            chromadb.PersistentClient: ChromaDB client instance.
        """
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(CHROMA_PATH),
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # No data sent to ChromaDB
                    allow_reset=True,
                ),
            )
            logger.info("ChromaDB initialized at %s", CHROMA_PATH)
        return self._client

    def _get_conversation_collection(self) -> chromadb.Collection:
        """Get or create the conversations collection."""
        client = self._get_client()
        return client.get_or_create_collection(
            name=COLLECTION_CONVERSATIONS,
            metadata={"description": "AURA conversation message memory"},
        )

    def _get_knowledge_collection(self) -> chromadb.Collection:
        """Get or create the knowledge collection."""
        client = self._get_client()
        return client.get_or_create_collection(
            name=COLLECTION_KNOWLEDGE,
            metadata={"description": "AURA verified knowledge entries"},
        )

    async def store_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        language: str = "en",
    ) -> None:
        """
        Store a conversation message in ChromaDB for semantic search.

        Args:
            message_id: Unique message UUID from SQLite.
            conversation_id: Parent conversation UUID.
            role: 'user' or 'assistant'.
            content: Message text content.
            language: Language code (bn, en, hi, ko).
        """
        try:
            embedding = await embedding_service.embed(content)
            collection = self._get_conversation_collection()

            collection.upsert(
                ids=[message_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "conversation_id": conversation_id,
                    "role": role,
                    "language": language,
                }],
            )
            logger.debug("Stored message %s in ChromaDB", message_id)

        except Exception as e:
            # Memory storage failure should not break chat
            logger.warning("Failed to store message in ChromaDB: %s", e)

    async def search_conversations(
        self,
        query: str,
        n_results: int = 5,
        conversation_id: str | None = None,
    ) -> list[dict]:
        """
        Search conversation memory for semantically similar messages.

        Args:
            query: Search query text.
            n_results: Maximum number of results to return.
            conversation_id: If provided, search only this conversation.

        Returns:
            list[dict]: Matching messages with content and metadata.
        """
        try:
            embedding = await embedding_service.embed(query)
            collection = self._get_conversation_collection()

            where = None
            if conversation_id:
                where = {"conversation_id": conversation_id}

            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, collection.count() or 1),
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
                    memories.append({
                        "content": doc,
                        "role": meta.get("role", "unknown"),
                        "language": meta.get("language", "en"),
                        "relevance": round(1 - dist, 3),
                    })

            return memories

        except Exception as e:
            logger.warning("Conversation search failed: %s", e)
            return []

    async def store_knowledge(
        self,
        entry_id: str,
        title: str,
        summary: str,
        category: str | None = None,
        tags: str | None = None,
        language: str = "en",
        confidence: float = 0.0,
    ) -> None:
        """
        Store a user-confirmed knowledge entry in ChromaDB.

        Only called after user explicitly confirms the entry.
        Per project rule: AURA never blindly stores internet data.

        Args:
            entry_id: KnowledgeEntry UUID from SQLite.
            title: Knowledge entry title.
            summary: Full knowledge summary text.
            category: Topic category.
            tags: Comma-separated tags.
            language: Language code.
            confidence: Source reliability score (0.0-1.0).
        """
        try:
            # Embed title + summary combined for better retrieval
            text_to_embed = f"{title}\n\n{summary}"
            embedding = await embedding_service.embed(text_to_embed)
            collection = self._get_knowledge_collection()

            collection.upsert(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[summary],
                metadatas=[{
                    "title": title,
                    "category": category or "general",
                    "tags": tags or "",
                    "language": language,
                    "confidence": confidence,
                }],
            )
            logger.info("Stored knowledge entry %s in ChromaDB", entry_id)

        except Exception as e:
            logger.error("Failed to store knowledge in ChromaDB: %s", e)
            raise

    async def search_knowledge(
        self,
        query: str,
        n_results: int = 3,
        min_confidence: float = 0.5,
    ) -> list[dict]:
        """
        Search knowledge base for relevant confirmed entries.

        Args:
            query: Search query text.
            n_results: Maximum results to return.
            min_confidence: Minimum confidence threshold.

        Returns:
            list[dict]: Relevant knowledge entries.
        """
        try:
            embedding = await embedding_service.embed(query)
            collection = self._get_knowledge_collection()

            if collection.count() == 0:
                return []

            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, collection.count()),
                where={"confidence": {"$gte": min_confidence}},
                include=["documents", "metadatas", "distances"],
            )

            knowledge = []
            if results["documents"] and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    knowledge.append({
                        "title": meta.get("title", ""),
                        "content": doc,
                        "category": meta.get("category", ""),
                        "relevance": round(1 - dist, 3),
                        "confidence": meta.get("confidence", 0.0),
                    })

            return knowledge

        except Exception as e:
            logger.warning("Knowledge search failed: %s", e)
            return []

    async def get_relevant_context(
        self,
        query: str,
        conversation_id: str | None = None,
    ) -> str:
        """
        Get combined relevant context for RAG pipeline.

        Searches both conversation memory and knowledge base.
        Returns formatted context string for LLM injection.

        Args:
            query: Current user message.
            conversation_id: Current conversation for scoped search.

        Returns:
            str: Formatted context string, empty if nothing relevant.
        """
        context_parts = []

        # Search knowledge base
        knowledge = await self.search_knowledge(query, n_results=2)
        if knowledge:
            context_parts.append("=== Relevant Knowledge ===")
            for k in knowledge:
                context_parts.append(
                    f"[{k['title']}] {k['content'][:300]}"
                )

        # Search past conversations
        memories = await self.search_conversations(
            query,
            n_results=3,
            conversation_id=conversation_id,
        )
        if memories:
            context_parts.append("=== Relevant Past Context ===")
            for m in memories:
                role_label = "User" if m["role"] == "user" else "AURA"
                context_parts.append(
                    f"[{role_label}] {m['content'][:200]}"
                )

        return "\n".join(context_parts)


# ── Singleton instance ────────────────────────────────────────────────────────
memory_service = MemoryService()