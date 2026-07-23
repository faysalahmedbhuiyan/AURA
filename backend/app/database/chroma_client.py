"""
AURA — Shared ChromaDB Client.

Single instance shared across all services to avoid
'An instance of Chroma already exists' conflict.
"""

import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

os.environ["ANONYMIZED_TELEMETRY"] = "False"

_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Get or create the shared ChromaDB client.
    Always returns the same instance (singleton).
    """
    global _client
    if _client is None:
        from app.config import get_settings
        settings = get_settings()
        path = Path(settings.chroma_db_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
    return _client