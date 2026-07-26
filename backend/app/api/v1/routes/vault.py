"""
AURA Backend — File Vault Routes.

Endpoints:
    GET /api/v1/vault                    — List all saved vault items
    GET /api/v1/vault/{item_id}          — Get one item's details
    GET /api/v1/vault/{item_id}/page/{n} — Serve a rendered page image
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.repositories.vault_repository import vault_repository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/vault", summary="List Vault Items", tags=["File Vault"])
async def list_vault(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all permanently saved files in the vault."""
    items = await vault_repository.list_all(db)
    return [
        {"id": i.id, "name": i.name, "kind": i.kind, "page_count": i.page_count, "created_at": i.created_at}
        for i in items
    ]


@router.get("/vault/{item_id}", summary="Get Vault Item Details", tags=["File Vault"])
async def get_vault_item(item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Get details of one vault item, including a text preview."""
    item = await vault_repository.get_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")
    return {
        "id": item.id, "name": item.name, "kind": item.kind,
        "page_count": item.page_count, "text_preview": item.full_text[:500],
        "created_at": item.created_at,
    }


@router.get("/vault/{item_id}/page/{page_number}", summary="Get a Page Image", tags=["File Vault"])
async def get_vault_page(item_id: str, page_number: int, db: AsyncSession = Depends(get_db)):
    """Serve a rendered page image for a vault item."""
    item = await vault_repository.get_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")

    paths = json.loads(item.page_image_paths or "[]")
    if page_number < 1 or page_number > len(paths):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not available ({len(paths)} page image(s) exist).",
        )

    path = Path(paths[page_number - 1])
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page image missing on disk.")

    return FileResponse(path, media_type="image/png")