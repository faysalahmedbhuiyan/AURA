"""
AURA Backend — Health Check Routes.

Module: app.api.v1.routes.health
Purpose: Provides health check endpoints to verify backend status.
         Used by frontend and monitoring tools.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()
settings = get_settings()


# ── Response Schema ───────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app: str
    version: str
    timestamp: str
    message: str
    db_ready: bool = True


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get(
    "/health",
    summary="Health Check",
    description="Returns current status of the AURA backend server.",
    tags=["System"],
)
async def health_check(request: Request) -> HealthResponse:
    """
    Health Check Endpoint.

    Confirms AURA backend is running and responsive. ALWAYS returns 200 —
    this must never block Electron's startup watchdog. db_ready=False means
    the server is up but the database is still initializing (or hit a
    startup problem); the UI can show a brief "please wait" for
    DB-dependent actions in that case instead of the app looking dead.

    Returns:
        HealthResponse: Server status, version, DB readiness, and UTC timestamp.
    """
    db_ready = getattr(request.app.state, "db_ready", True)
    return HealthResponse(
        status="ok" if db_ready else "starting",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        message="AURA backend is running successfully." if db_ready else "AURA backend is up; still finishing startup.",
        db_ready=db_ready,
    )