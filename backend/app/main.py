"""
AURA Backend — Application Entry Point.

Module: app.main
Purpose: Initializes the FastAPI application, configures middleware,
         registers all API routers, and manages database lifecycle.

Usage:
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import asyncio
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
                                self_improve, image, video, security, model_bootstrap)
from app.config import get_settings
from app.database.connection import init_db
from app.memory_engine.models import memory_models  # noqa: F401
from app.intelligence.models import knowledge_item  # noqa: F401
from app.services.model_bootstrap_service import run_bootstrap_in_background
from app.services.ollama_bootstrap_service import run_ollama_bootstrap_in_background

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

    # ── Database init — background task, same proven pattern as the model
    # and Ollama bootstraps below (NOT awaited, NOT wrapped in wait_for) ───────
    # Your last log hung for the full 120s with zero extra log lines — that
    # rules out a merely slow init_db(): asyncio.wait_for()'s timeout can
    # only fire at an `await` point inside the wrapped coroutine, so if
    # init_db() does even one blocking synchronous call, it freezes the
    # ENTIRE event loop, including the timer meant to cancel it. A timeout
    # on a frozen loop can never run — which is exactly why the previous
    # 20s-timeout version didn't help.
    #
    # asyncio.create_task() here schedules init_db() but does NOT start
    # running it — nothing else blocks between here and `yield` below, so
    # uvicorn reports "Application startup complete" (and /api/v1/health
    # starts answering) BEFORE init_db() gets its first chance to run at
    # all. This is the same pattern already proven working for the model
    # and Ollama bootstraps in your last log (health check answered
    # instantly; their background work logged a few seconds later).
    app.state.db_ready = False

    async def _run_init_db() -> None:
        try:
            await init_db()
            app.state.db_ready = True
            logger.info("[startup] Database ready.")
        except Exception as e:
            logger.error(
                "[startup] init_db() failed — AURA is still open; "
                "DB-dependent features will report 'initializing' until "
                "this is resolved. Cause: %s", e,
            )

    asyncio.create_task(_run_init_db())

    # ── Model check & safe auto-download (RAM + disk aware) ───────────────────
    # IMPORTANT: this is launched as a background task, NOT awaited here.
    # A first-run model export/download can take many minutes (SD-Turbo
    # export alone can run well past an hour on a slow machine) — awaiting
    # it here previously meant FastAPI's "startup complete" (and therefore
    # /api/v1/health) never fired until it finished, which is exactly why
    # Electron's 120s health-check watchdog was timing out even though the
    # backend process itself was alive and working. The server now becomes
    # reachable immediately; model download progress is exposed instead via
    # GET /api/v1/model-bootstrap-status for the UI to poll.
    asyncio.create_task(run_bootstrap_in_background())

    # ── Ollama auto-install + aura-brain build (also background, also
    # non-blocking) ─────────────────────────────────────────────────────────
    # Chat is 100% dependent on Ollama being installed, running, and having
    # the aura-brain model built. On a fresh PC none of that exists yet —
    # this task detects/installs/starts Ollama, pulls the base model, and
    # builds aura-brain automatically so the person who installed AURA.exe
    # never has to know Ollama exists. Progress: GET /api/v1/ollama-bootstrap-status.
    asyncio.create_task(run_ollama_bootstrap_in_background())

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
app.include_router(model_bootstrap.router, prefix="/api/v1")
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