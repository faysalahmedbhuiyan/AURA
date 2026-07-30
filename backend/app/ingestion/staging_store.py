"""
AURA Backend — Upload Staging Store.

Module: app.ingestion.staging_store
Purpose: Holds a staged file (original + text + page images) in memory/
         temp-disk per conversation, until saved to the permanent Vault
         or explicitly removed. Also supports re-staging an
         ALREADY-VAULTED item into a (possibly different) conversation
         by name, enabling cross-conversation recall.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8000
STAGING_ROOT = Path("D:/AURA/vault/_staging")

_staged: dict[str, dict] = {}


class StagingStore:
    """
    In-memory store for one staged (or vault-recalled) file per conversation.
    """

    def stage(
        self,
        conversation_id: str,
        filename: str,
        text: str,
        kind: str,
        source_path: Path | None = None,
    ) -> dict:
        """
        Stage a freshly uploaded file. Copies the original into a temp
        staging dir (so it survives until a later "save it" message in
        a separate HTTP request) and renders PDF page images.
        """
        self._cleanup_staging_dir(conversation_id)

        out_dir = STAGING_ROOT / conversation_id
        original_path = None
        page_image_paths: list[str] = []

        if source_path and source_path.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            original_path = out_dir / f"original{source_path.suffix}"
            shutil.copy2(source_path, original_path)

            if kind == "pdf":
                from app.ingestion.document_parser import document_parser
                try:
                    page_image_paths = document_parser.render_pdf_pages(original_path, out_dir)
                except Exception as e:
                    logger.warning("Failed to render PDF pages for staging: %s", e)
            elif kind == "image":
                page_image_paths = [str(original_path)]

        record = {
            "filename": filename,
            "text": text,
            "kind": kind,
            "char_count": len(text),
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "saved": False,
            "original_path": str(original_path) if original_path else None,
            "page_image_paths": page_image_paths,
            "vault_item_id": None,
            "vault_name": None,
        }
        _staged[conversation_id] = record
        logger.info(
            "Staged file '%s' (%d chars, %d page image(s)) for conversation %s",
            filename, len(text), len(page_image_paths), conversation_id[:8],
        )
        return record

    def stage_from_vault(self, conversation_id: str, vault_item) -> dict:
        """
        Re-stage a vault item for a new conversation (name-based recall).
        """
        import json

        try:
            pages = json.loads(vault_item.page_image_paths or "[]")
        except Exception:
            pages = []

        # Detect if this is an image vault item
        file_path = vault_item.file_path or ""
        ext = Path(file_path).suffix.lower() if file_path else ""
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
        kind = vault_item.kind or ("image" if ext in image_exts else "document")

        staged = {
            "filename": vault_item.original_filename,
            "text": vault_item.full_text or "",
            "kind": kind,
            "pages": vault_item.page_count or 1,
            "page_image_paths": pages,
            "original_path": file_path,
            "saved": True,
            "vault_item_id": vault_item.id,
            "vault_name": vault_item.name,
            "image_url": (
                f"/api/v1/vault/{vault_item.id}/image"
                if kind == "image" else None
            ),
        }
        self._store[conversation_id] = staged
        logger.info("Re-staged vault item '%s' for conv %s", vault_item.name, conversation_id[:8])
        return staged

    def get(self, conversation_id: str) -> dict | None:
        return _staged.get(conversation_id)

    def mark_saved(self, conversation_id: str, vault_item_id: str | None = None) -> None:
        record = _staged.get(conversation_id)
        if record:
            record["saved"] = True
            if vault_item_id:
                record["vault_item_id"] = vault_item_id

    def clear(self, conversation_id: str) -> bool:
        self._cleanup_staging_dir(conversation_id)
        return _staged.pop(conversation_id, None) is not None

    def context_snippet(self, conversation_id: str) -> str | None:
        record = self.get(conversation_id)
        if not record:
            return None
        return record["text"][:MAX_CONTEXT_CHARS]

    def _cleanup_staging_dir(self, conversation_id: str) -> None:
        """Remove temp staging files for a conversation (harmless no-op for vault-restaged records)."""
        staging_dir = STAGING_ROOT / conversation_id
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


# ── Singleton instance ────────────────────────────────────────────────────────
staging_store = StagingStore()