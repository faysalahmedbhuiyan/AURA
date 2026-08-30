"""
AURA Backend — Ingestion Service.

Module: app.ingestion.ingestion_service
Purpose: Orchestrates PDF/DOCX/text ingestion into the EXISTING Tier 2
         Intelligence pipeline. Provides both a synchronous path (small
         files) and a background path (large files) — a large document
         can take minutes to classify chunk-by-chunk on CPU-only
         hardware, which would exceed any HTTP request timeout if done
         synchronously.
"""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunker import chunker
from app.ingestion.document_parser import document_parser
from app.intelligence.intelligence_service import intelligence_service

logger = logging.getLogger(__name__)

MAX_CHUNKS_PER_FILE = 30  # safety cap even for background jobs


class IngestionService:
    """
    Orchestrates file/text ingestion into the Tier 2 Intelligence Layer.

    Methods:
        ingest_text: Synchronous — chunk raw text, process via Tier 2.
        ingest_text_background: Same pipeline, runs detached from any
                                 HTTP request with its own DB session,
                                 reporting progress via ingestion_job_store.
        ingest_pdf: Parse a PDF, then delegate to ingest_text.
        ingest_docx: Parse a DOCX, then delegate to ingest_text.
    """

    async def ingest_text(
        self,
        db: AsyncSession,
        text: str,
        source_name: str,
        language: str = "en",
        auto_confirm: bool = False,
        conversation_id: str | None = None,
    ) -> dict:
        """Chunk raw text and process each chunk through the Tier 2 pipeline (blocking)."""
        chunks = chunker.split(text)
        total = min(len(chunks), MAX_CHUNKS_PER_FILE)
        created, evolved, failed = 0, 0, 0

        if conversation_id:
            from app.ingestion.job_store import ingestion_job_store

        for i, chunk in enumerate(chunks[:MAX_CHUNKS_PER_FILE]):
            try:
                result = await intelligence_service.process(
                    db=db,
                    title=f"{source_name} (part {i + 1}/{total})",
                    content=chunk,
                    source=source_name,
                    source_type="file",
                    language=language,
                    auto_confirm=auto_confirm,
                )
                if result.get("action") == "evolved":
                    evolved += 1
                else:
                    created += 1
            except Exception as e:
                logger.warning("Chunk %d/%d processing failed: %s", i + 1, total, e)
                failed += 1

            if conversation_id:
                ingestion_job_store.update_progress(conversation_id, i + 1, created, evolved, failed)

        return {
            "source": source_name, "chunks_found": len(chunks),
            "chunks_processed": total, "created": created,
            "evolved": evolved, "failed": failed,
        }

    async def ingest_text_background(
        self,
        conversation_id: str,
        text: str,
        source_name: str,
        language: str = "en",
        auto_confirm: bool = False,
    ) -> None:
        """
        Same pipeline as ingest_text(), but runs detached from any HTTP
        request — creates its OWN database session (the request's
        session is closed by the time this runs) and reports progress
        via ingestion_job_store so the chat endpoint can respond
        immediately instead of blocking.
        """
        from app.database.connection import AsyncSessionLocal
        from app.ingestion.job_store import ingestion_job_store

        chunks = chunker.split(text)
        total = min(len(chunks), MAX_CHUNKS_PER_FILE)
        ingestion_job_store.start(conversation_id, source_name, total)

        created, evolved, failed = 0, 0, 0

        try:
            async with AsyncSessionLocal() as db:
                for i, chunk in enumerate(chunks[:MAX_CHUNKS_PER_FILE]):
                    try:
                        result = await intelligence_service.process(
                            db=db,
                            title=f"{source_name} (part {i + 1}/{total})",
                            content=chunk,
                            source=source_name,
                            source_type="file",
                            language=language,
                            auto_confirm=auto_confirm,
                        )
                        if result.get("action") == "evolved":
                            evolved += 1
                        else:
                            created += 1
                    except Exception as e:
                        logger.warning("Background chunk %d/%d failed: %s", i + 1, total, e)
                        failed += 1

                    ingestion_job_store.update_progress(conversation_id, i + 1, created, evolved, failed)

                await db.commit()

        except Exception as e:
            logger.exception("Background ingestion failed for '%s': %s", source_name, e)
            ingestion_job_store.finish(conversation_id, error=str(e))
            return

        from app.ingestion.staging_store import staging_store
        staging_store.mark_saved(conversation_id)

        ingestion_job_store.finish(conversation_id)
        logger.info(
            "Background ingestion done: %s (%d created, %d evolved, %d failed)",
            source_name, created, evolved, failed,
        )

    async def ingest_pdf(
        self, db: AsyncSession, path: Path, language: str = "en", auto_confirm: bool = False,
    ) -> dict:
        """Parse a PDF and ingest its text (synchronous)."""
        parsed = document_parser.parse_pdf(path)
        return await self.ingest_text(db, parsed["text"], path.name, language, auto_confirm)

    async def ingest_docx(
        self, db: AsyncSession, path: Path, language: str = "en", auto_confirm: bool = False,
    ) -> dict:
        """Parse a DOCX and ingest its text (synchronous)."""
        parsed = document_parser.parse_docx(path)
        return await self.ingest_text(db, parsed["text"], path.name, language, auto_confirm)


# ── Singleton instance ────────────────────────────────────────────────────────
ingestion_service = IngestionService()