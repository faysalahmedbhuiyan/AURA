"""
AURA Backend — Image Generation Schemas.

Module: app.schemas.image
Purpose: Request/response models for Tier 5 (AI Generation Engine) —
         local SDXL Turbo image generation via DirectML.
"""

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    negative_prompt: str = Field(default="", max_length=500)
    steps: int = Field(default=1, ge=1, le=4)  # SDXL Turbo: 1-4 steps only
    seed: int | None = Field(default=None, description="Omit for random seed.")


class ImageGenerateResponse(BaseModel):
    success: bool
    file_path: str = ""
    file_name: str = ""
    prompt: str = ""
    seed: int = 0
    duration_ms: int = 0
    error: str = ""


class ImageStatusResponse(BaseModel):
    pipeline_loaded: bool
    model_path: str
    provider: str
    ram_available_mb: int
