# AURA Changelog

All notable changes to AURA are documented here.
Format: [Version] — Date — Description

---

## [0.1.0] — 2026-07-04

### Added

- FastAPI backend skeleton with clean architecture
- Versioned API structure: /api/v1/
- Health check endpoint: GET /api/v1/health
- Centralized configuration via pydantic-settings
- CORS middleware configured for Electron frontend
- Swagger UI available at /docs
- ReDoc available at /redoc
- .env environment variable support
- .gitignore configured (venv, cache, .env excluded)
- Python 3.11.9 stable environment
- Virtual environment isolation
