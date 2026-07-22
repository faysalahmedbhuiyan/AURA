"""
AURA Backend — Database Connection.

Module: app.database.connection
Purpose: Creates and manages the async SQLite engine and session factory.
         Provides get_db dependency for FastAPI route injection.
         Provides init_db() to create all tables on startup.

Usage:
    from app.database.connection import get_db, init_db
"""

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.database.base import Base
from app.memory_engine.models import memory_models  # noqa: F401

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Ensure database directory exists ─────────────────────────────────────────
DB_PATH = Path(settings.sqlite_db_path).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Async SQLite Engine ───────────────────────────────────────────────────────
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    echo=settings.app_debug,       # SQL logging only in debug mode
    future=True,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    Called once on application startup via FastAPI lifespan.
    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS.

    Raises:
        Exception: If database connection or table creation fails.
    """
    try:
        async with engine.begin() as conn:
            # Import all models so Base knows about them
            from app.models import conversation, knowledge, message  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully at %s", DB_PATH)
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Automatically commits on success and rolls back on error.
    Always closes the session after the request completes.

    Yields:
        AsyncSession: An active database session.

    Example:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()