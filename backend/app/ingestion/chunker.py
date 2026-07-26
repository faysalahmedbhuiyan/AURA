"""
AURA Backend — Text Chunker.

Module: app.ingestion.chunker
Purpose: Splits long extracted text into overlapping chunks sized for
         the Tier 2 classifier's LLM prompt, preserving context across
         boundaries via overlap.
"""

CHUNK_SIZE = 4000
CHUNK_OVERLAP = 200


class Chunker:
    """
    Splits text into overlapping chunks.

    Methods:
        split: Chunk a text string.
    """

    def split(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: The full text to split.
            chunk_size: Max characters per chunk.
            overlap: Characters shared between consecutive chunks.

        Returns:
            list[str]: Non-empty chunks.
        """
        text = text.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
        return chunks


# ── Singleton instance ────────────────────────────────────────────────────────
chunker = Chunker()