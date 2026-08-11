"""
AURA Backend — Vault Repository.

Module: app.repositories.vault_repository
Purpose: Database operations for FileVaultItem.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_item import FileVaultItem

logger = logging.getLogger(__name__)


class VaultRepository:
    """Repository for File Vault operations."""

    async def create_item(
        self, db: AsyncSession, name: str, original_filename: str, kind: str,
        file_path: str, full_text: str, page_count: int,
        page_image_paths: list[str], language: str = "en",
    ) -> FileVaultItem:
        """Create a new vault item."""
        item = FileVaultItem(
            name=name, original_filename=original_filename, kind=kind,
            file_path=file_path, full_text=full_text, page_count=page_count,
            page_image_paths=json.dumps(page_image_paths), language=language,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        logger.info("Vault item created: '%s' (%s, %d page(s))", name, kind, page_count)
        return item

    async def list_all(self, db: AsyncSession) -> list[FileVaultItem]:
        """List all vault items, newest first."""
        result = await db.execute(select(FileVaultItem).order_by(FileVaultItem.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, item_id: str) -> FileVaultItem | None:
        """Get a vault item by id."""
        result = await db.execute(select(FileVaultItem).where(FileVaultItem.id == item_id))
        return result.scalar_one_or_none()

    async def find_matching_name(self, db: AsyncSession, message: str) -> FileVaultItem | None:
        """
        Check if a message mentions a known vault item's name (as a
        case-insensitive substring). Prefers the LONGEST matching name,
        to avoid a short name accidentally matching an unrelated phrase.
        """
        items = await self.list_all(db)
        message_lower = message.lower()
        matches = [item for item in items if item.name.lower() in message_lower]
        if not matches:
            return None
        return max(matches, key=lambda item: len(item.name))


# ── Singleton instance ────────────────────────────────────────────────────────
vault_repository = VaultRepository()