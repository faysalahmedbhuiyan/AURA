"""
AURA Backend — Embedding Service.

Module: app.services.embedding_service
Purpose: Converts text to vector embeddings using Ollama's
         nomic-embed-text model. Used by MemoryService for
         ChromaDB storage and semantic search.

Optimized for 8GB RAM — uses lightweight nomic-embed-text
which requires only ~274MB compared to heavier alternatives.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OLLAMA_EMBED_URL = f"{settings.ollama_base_url}/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


class EmbeddingService:
    """
    Service for generating text embeddings via Ollama.

    Uses nomic-embed-text model for efficient, offline embedding
    generation. Optimized for low-RAM environments.

    Methods:
        embed: Convert single text to vector.
        embed_batch: Convert multiple texts to vectors.
        is_available: Check if embedding model is ready.
    """

    async def embed(self, text: str) -> list[float]:
        """
        Convert a single text string to a vector embedding.

        Args:
            text: Input text to embed. Will be truncated if too long.

        Returns:
            list[float]: Vector embedding (768 dimensions).

        Raises:
            ConnectionError: If Ollama is unreachable.
            RuntimeError: If embedding generation fails.
        """
        # Truncate text to avoid token limit issues
        text = text[:2000] if len(text) > 2000 else text

        payload = {
            "model": EMBED_MODEL,
            "prompt": text,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    OLLAMA_EMBED_URL,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["embedding"]

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama for embedding")
            raise ConnectionError(
                "Ollama is not running. Cannot generate embeddings."
            )
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise RuntimeError(f"Embedding error: {str(e)}")

    async def embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Convert multiple texts to vector embeddings.

        Processes sequentially to avoid overwhelming 8GB RAM.

        Args:
            texts: List of text strings to embed.

        Returns:
            list[list[float]]: List of vector embeddings.
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

    async def is_available(self) -> bool:
        """
        Check if the embedding model is available in Ollama.

        Returns:
            bool: True if nomic-embed-text is ready.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.ollama_base_url}/api/tags"
                )
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return any("nomic-embed-text" in m for m in models)
        except Exception:
            return False


# ── Singleton instance ────────────────────────────────────────────────────────
embedding_service = EmbeddingService()