"""
AURA Backend — Ingestion Job Tracker.

Module: app.ingestion.job_store
Purpose: In-memory progress tracker for background ingestion jobs.
         Lets the chat endpoint respond immediately instead of blocking
         for minutes while many chunks are classified sequentially via
         the LLM — a single request processing 15+ sequential Ollama
         calls would exceed any reasonable HTTP timeout on this hardware.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_jobs: dict[str, dict] = {}  # conversation_id -> job record


class IngestionJobStore:
    """
    Tracks background ingestion job progress, keyed by conversation_id.

    Methods:
        start: Begin tracking a new job.
        update_progress: Update chunk counts as processing continues.
        finish: Mark a job done or failed.
        get: Retrieve current job status.
    """

    def start(self, conversation_id: str, filename: str, total_chunks: int) -> None:
        """Start tracking a new background ingestion job."""
        _jobs[conversation_id] = {
            "filename": filename,
            "status": "processing",
            "total_chunks": total_chunks,
            "processed": 0,
            "created": 0,
            "evolved": 0,
            "failed": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "error": None,
        }

    def update_progress(
        self, conversation_id: str, processed: int, created: int, evolved: int, failed: int,
    ) -> None:
        """Update progress counters for a running job."""
        job = _jobs.get(conversation_id)
        if job:
            job.update(processed=processed, created=created, evolved=evolved, failed=failed)

    def finish(self, conversation_id: str, error: str | None = None) -> None:
        """Mark a job as done or failed."""
        job = _jobs.get(conversation_id)
        if job:
            job["status"] = "failed" if error else "done"
            job["error"] = error
            job["finished_at"] = datetime.now(timezone.utc).isoformat()

    def get(self, conversation_id: str) -> dict | None:
        """Get the current status of a job, if any exists for this conversation."""
        return _jobs.get(conversation_id)


# ── Singleton instance ────────────────────────────────────────────────────────
ingestion_job_store = IngestionJobStore()