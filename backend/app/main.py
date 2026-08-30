"""
AURA Backend — Application Entry Point.

Module: app.main
Purpose: Initializes the FastAPI application, configures middleware,
         registers all API routers, and manages database lifecycle.

Usage:
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os
import sys
import shutil
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import (agents, chat, db_health, health, nlp, memory,memory_tiers, goals, mentor, voice, voice_session, rollback,journal, research, review,
                                planning, understanding, modification, research_engine, intelligence, advanced_memory, ingestion, vault, computer_control, agents_v2,
                                self_improve, image, video, security)
from app.config import get_settings
from app.database.connection import init_db
from app.memory_engine.models import memory_models  # noqa: F401
from app.intelligence.models import knowledge_item  # noqa: F401
from app.services.model_bootstrap_service import check_and_prepare_models

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    Runs init_db() on startup and checks/prepares every local AI model
    AURA needs (downloading anything missing, RAM/disk permitting).
    """
    logger.info("AURA backend starting up...")
    await init_db()

    # ── Model check & safe auto-download (RAM + disk aware) ───────────────────
    try:
        await check_and_prepare_models()
    except Exception as e:
        # A problem here should never take down the whole backend — worst
        # case, the affected feature (e.g. image generation) reports a
        # clear error the next time it's used.
        logger.error("Model check/bootstrap failed unexpectedly: %s", e)

    # ── Security Monitor (Linux Only) ──────────────────────────────────────────
    import platform
    if platform.system() == "Linux":
        try:
            from app.security.security_service import security_service
            security_service.start()
            logger.info("AURA security monitor auto-started (Linux detected).")
        except Exception as e:
            logger.warning("Security monitor auto-start failed (non-fatal): %s", e)
    else:
        logger.info("Security monitor skipped — not running on Linux.")

    logger.info("AURA backend ready.")
    yield

    if platform.system() == "Linux":
        from app.security.security_service import security_service
        security_service.stop()
    logger.info("AURA backend shutting down.")


# ── FastAPI Initialization ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AURA — Personal AI Operating System. "
        "Offline-first, modular, multilingual, production-quality."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")
app.include_router(db_health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(planning.router, prefix="/api/v1")
app.include_router(modification.router, prefix="/api/v1")
app.include_router(rollback.router, prefix="/api/v1")
app.include_router(journal.router, prefix="/api/v1")
app.include_router(memory_tiers.router, prefix="/api/v1")
app.include_router(understanding.router, prefix="/api/v1")
app.include_router(mentor.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(nlp.router, prefix="/api/v1")
app.include_router(voice_session.router, prefix="/api/v1")
app.include_router(advanced_memory.router, prefix="/api/v1")
app.include_router(research_engine.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(computer_control.router, prefix="/api/v1")
app.include_router(agents_v2.router, prefix="/api/v1")
app.include_router(self_improve.router, prefix="/api/v1")
app.include_router(image.router, prefix="/api/v1")
app.include_router(video.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")
# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint — redirects to docs."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
        "db_health": "/api/v1/db-health",
    }