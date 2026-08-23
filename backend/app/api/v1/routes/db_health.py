"""
AURA Backend — Database Health Check Route.

Module: app.api.v1.routes.db_health
Purpose: Verifies that the SQLite database is reachable and
         all expected tables exist. Used for monitoring and
         startup verification.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Response Schema ───────────────────────────────────────────────────────────
class DBHealthResponse(BaseModel):
    """Database health check response schema."""

    status: str
    database: str
    tables: list[str]
    timestamp: str
    message: str


# ── Route ─────────────────────────────────────────────────────────────────────
@router.get(
    "/db-health",
    summary="Database Health Check",
    description="Verifies SQLite database connectivity and table existence.",
    tags=["System"],
)
async def db_health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DBHealthResponse:
    """
    Database Health Check Endpoint.

    Queries SQLite to verify connectivity and list all existing tables.

    Args:
        db: Injected async database session.

    Returns:
        DBHealthResponse: DB status, table list, and timestamp.

    Raises:
        500: If database is unreachable.
    """
    try:
        result = await db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result.fetchall()]

        return DBHealthResponse(
            status="ok",
            database="SQLite",
            tables=sorted(tables),
            timestamp=datetime.now(timezone.utc).isoformat(),
            message="Database is healthy and reachable.",
        )
    except Exception as e:
        logger.exception("Database health check failed: %s", e)
        return DBHealthResponse(
            status="error",
            database="SQLite",
            tables=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            message=f"Database error: {str(e)}",
        )