"""
AURA Backend — Ingestion Routes.

Endpoints:
    POST   /api/v1/ingestion/stage              — Attach a file to a conversation (no save)
    DELETE /api/v1/ingestion/stage/{conv_id}     — Detach the staged file
    POST   /api/v1/ingestion/upload              — Silent bulk upload straight to pending queue
    POST   /api/v1/ingestion/confirm-source       — Bulk-confirm all pending items from one file
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.ingestion.document_parser import document_parser
from app.ingestion.ingestion_service import ingestion_service
from app.ingestion.staging_store import staging_store
from app.intelligence.intelligence_service import intelligence_service
from app.intelligence.models.knowledge_item import KnowledgeItem

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_MB = 25
KIND_MAP = {
    ".pdf": "pdf", ".docx": "docx",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
}


def _detect_kind(filename: str) -> str | None:
    suffix = Path(filename or "").suffix.lower()
    return KIND_MAP.get(suffix)


async def _extract_text(kind: str, path: Path) -> dict:
    """Route to the correct parser based on file kind."""
    if kind == "pdf":
        return document_parser.parse_pdf(path)
    if kind == "docx":
        return document_parser.parse_docx(path)
    return document_parser.parse_image(path)


@router.post(
    "/ingestion/stage",
    summary="Attach a File to the Conversation",
    description=(
        "Upload a PDF/DOCX/image and attach it to a conversation. Extracts "
        "text but saves NOTHING permanently. Your next message is treated "
        "as an instruction about this file — ask questions about it, or "
        "say 'save it' to store it permanently, or 'forget it' to detach "
        "without saving."
    ),
    tags=["Ingestion"],
)
async def stage_file(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    language: str = Form(default="en"),
) -> dict:
    """Extract text from an uploaded file and stage it for the conversation."""
    kind = _detect_kind(file.filename)
    if not kind:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file type. Supported: PDF, DOCX, PNG, JPG.",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_UPLOAD_MB}MB limit.",
        )

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        parsed = await _extract_text(kind, tmp_path)
    except RuntimeError as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    text = parsed.get("text", "")
    if not text.strip():
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text could be extracted from this file.",
        )
     # staging_store copies what it needs from tmp_path (renders PDF pages,
    # copies the original) — safe to delete the temp upload afterward.
    record = staging_store.stage(conversation_id, file.filename, text, kind, source_path=tmp_path)
    tmp_path.unlink(missing_ok=True)
    preview = text[:300] + ("..." if len(text) > 300 else "")
    

    return {
        "filename": record["filename"],
        "kind": kind,
        "char_count": record["char_count"],
        "preview": preview,
    }


@router.delete(
    "/ingestion/stage/{conversation_id}",
    summary="Detach the Staged File",
    tags=["Ingestion"],
)
async def clear_staged_file(conversation_id: str) -> dict:
    """Remove the currently staged file for a conversation without saving it."""
    cleared = staging_store.clear(conversation_id)
    return {"cleared": cleared}


@router.post(
    "/ingestion/upload",
    summary="Silent Bulk Upload",
    description=(
        "Upload a PDF/DOCX straight into the Tier 2 pending queue, without "
        "an interactive attach-and-instruct step. Use /ingestion/stage "
        "instead for the normal chat-driven flow."
    ),
    tags=["Ingestion"],
)
async def upload_document(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    auto_confirm: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload and silently process a PDF/DOCX document via the Tier 2 pipeline."""
    kind = _detect_kind(file.filename)
    if kind not in ("pdf", "docx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint supports PDF and DOCX only. Use /ingestion/stage for images.",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_UPLOAD_MB}MB limit.",
        )

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        if kind == "pdf":
            result = await ingestion_service.ingest_pdf(db, tmp_path, language, auto_confirm)
        else:
            result = await ingestion_service.ingest_docx(db, tmp_path, language, auto_confirm)
    finally:
        tmp_path.unlink(missing_ok=True)

    return result


@router.post(
    "/ingestion/confirm-source",
    summary="Confirm All Pending Items From a Source",
    tags=["Ingestion"],
)
async def confirm_source(source: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Confirm all pending knowledge items that came from a given file."""
    result = await db.execute(
        select(KnowledgeItem).where(
            KnowledgeItem.source == source,
            KnowledgeItem.is_confirmed == False,  # noqa: E712
        )
    )
    pending_items = result.scalars().all()

    if not pending_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pending items found for source '{source}'.",
        )

    confirmed = 0
    for item in pending_items:
        outcome = await intelligence_service.confirm_item(db, item.id)
        if outcome.get("success"):
            confirmed += 1

    return {"source": source, "total_pending": len(pending_items), "confirmed": confirmed}
@router.get(
    "/ingestion/status/{conversation_id}",
    summary="Check Background Save Status",
    tags=["Ingestion"],
)
async def get_ingestion_status(conversation_id: str) -> dict:
    """Check the progress of a background file-save job."""
    from app.ingestion.job_store import ingestion_job_store

    job = ingestion_job_store.get(conversation_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ingestion job found for this conversation.",
        )
    return job