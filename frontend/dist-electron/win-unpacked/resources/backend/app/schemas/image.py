"""
AURA Backend — Image Generation Schemas.

Module: app.schemas.image
Purpose: Request/response models for Tier 5 (AI Generation Engine) —
         local SDXL Turbo image generation via DirectML.
"""

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: str = Field(default="", max_length=500)
    steps: int | None = Field(default=None, ge=1, le=50)
    seed: int | None = Field(default=None, description="Omit for random seed.")
    quality: str = Field(
        default="fast",
        description="'fast' (SD-Turbo, ~1-2 min) or 'realistic' (Realistic Vision, ~15-20 min)",
    )


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


class ImageTransformRequest(BaseModel):
    image_path: str = Field(..., description="Absolute path to an existing image on disk")
    style_prompt: str = Field(..., min_length=1, max_length=2000, description="e.g. 'cartoon style', 'watercolor painting'")
    negative_prompt: str = Field(default="", max_length=500)
    quality: str = Field(default="fast", description="'fast' or 'realistic'")
    strength: float = Field(
        default=0.65, ge=0.1, le=1.0,
        description="0.1-1.0. Lower = closer to original photo, higher = more stylized.",
    )
    seed: int | None = Field(default=None)


class ImageTransformResponse(BaseModel):
    success: bool
    file_path: str = ""
    file_name: str = ""
    style_prompt: str = ""
    strength: float = 0.0
    seed: int = 0
    duration_ms: int = 0
    quality: str = ""
    error: str = ""
