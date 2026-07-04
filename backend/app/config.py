"""
AURA Backend — Application Configuration.

Module: app.config
Purpose: Centralized configuration management using environment variables.
         All modules import settings from here — never read .env directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All fields have sensible defaults so the app runs
    even without a .env file during development.
    """

    # ── Application ──────────────────────────────────────
    app_name: str = "AURA"
    app_version: str = "0.1.0"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_debug: bool = False

    # ── Ollama ────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # ── Database ──────────────────────────────────────────
    sqlite_db_path: str = "../database/aura.db"
    chroma_db_path: str = "../database/chroma"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """
    Return cached application settings.

    Uses lru_cache so .env is read only once per process,
    not on every request.

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()