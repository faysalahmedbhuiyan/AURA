"""
AURA Backend — Security Routes (Tier 6, B).

Module: app.api.v1.routes.security
Endpoints:
    POST /api/v1/security/start   — start the monitor loop
    POST /api/v1/security/stop    — stop the monitor loop
    GET  /api/v1/security/status  — running state + recent alerts
    POST /api/v1/security/cancel-shutdown — abort a pending shutdown
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/security/start", tags=["Security"], summary="Start Security Monitor")
async def start_monitor() -> dict:
    from app.security.security_service import security_service

    started = security_service.start()
    return {"started": started}


@router.post("/security/stop", tags=["Security"], summary="Stop Security Monitor")
async def stop_monitor() -> dict:
    from app.security.security_service import security_service

    stopped = security_service.stop()
    return {"stopped": stopped}


@router.get("/security/status", tags=["Security"], summary="Security Monitor Status")
async def get_status() -> dict:
    from app.security.security_service import security_service

    return security_service.status()


@router.post("/security/cancel-shutdown", tags=["Security"], summary="Abort Pending Shutdown")
async def cancel_shutdown() -> dict:
    from app.security.firewall_controller import firewall_controller

    return firewall_controller.cancel_shutdown()
