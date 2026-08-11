"""
AURA Backend — Health Check Routes.

Module: app.api.v1.routes.health
Purpose: Provides health check endpoints to verify backend status.
         Used by frontend and monitoring tools.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
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


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns current status of the AURA backend server.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """
    Health Check Endpoint.

    Confirms AURA backend is running and responsive.
    Used by the frontend and monitoring tools.

    Returns:
        HealthResponse: Server status, version, and UTC timestamp.
    """
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        message="AURA backend is running successfully.",
    )