"""
AURA Backend — Application Entry Point.

Module: app.main
Purpose: Initializes the FastAPI application, configures middleware,
         and registers all API routers.

Usage:
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import health
from app.config import get_settings

# ── Settings ──────────────────────────────────────────────────────────────────
settings = get_settings()

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
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint — redirects to docs."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }