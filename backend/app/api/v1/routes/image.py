"""
AURA Backend — Image Generation Routes (Tier 5).

Module: app.api.v1.routes.image
Purpose: API endpoints for local AI image generation (SDXL Turbo,
         DirectML, Intel Iris Xe).

Endpoints:
    POST /api/v1/image/generate — Generate an image from a prompt
    GET  /api/v1/image/status   — Pipeline load state + free RAM
    POST /api/v1/image/unload   — Manually free the pipeline from RAM
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.schemas.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageStatusResponse,
    ImageTransformRequest,
    ImageTransformResponse,
)
from app.services.image_service import image_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/image/transform",
    tags=["Image Generation"], summary="Transform an Existing Image (Style Transfer)",
    description=(
        "Restyles an existing image (cartoon, watercolor, sketch, etc.) "
        "using img2img on the same local models. image_path must be an "
        "absolute path to an existing image on disk (e.g. from a "
        "previous /image/generate call, or an uploaded file)."
    ),
)
async def transform_image(request: ImageTransformRequest) -> ImageTransformResponse:
    result = await image_service.transform_image(
        image_path=request.image_path,
        style_prompt=request.style_prompt,
        quality=request.quality,
        strength=request.strength,
        negative_prompt=request.negative_prompt,
        seed=request.seed,
    )
    return ImageTransformResponse(**result)


@router.post(
    "/image/generate", 
    tags=["Image Generation"], summary="Generate an Image Locally",
    description=(
        "Generates a 512x512 image using SDXL Turbo (ONNX, DirectML). "
        "Unloads the Ollama LLM first to free RAM. ~45-90s on Intel Iris Xe."
    ),
)
async def generate_image(request: ImageGenerateRequest) -> ImageGenerateResponse:
    result = await image_service.generate(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        steps=request.steps,
        seed=request.seed,
        quality=request.quality,
    )
    return ImageGenerateResponse(**result)


@router.get(
    "/image/file/{file_name}",
    tags=["Image Generation"], summary="Fetch a Generated Image",
)
async def get_image_file(file_name: str):
    from app.config import get_settings
    from pathlib import Path

    settings = get_settings()
    path = Path(settings.image_output_dir) / file_name
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(path)


@router.get(
    "/image/status", 
    tags=["Image Generation"], summary="Image Pipeline Status",
)
async def get_status() -> ImageStatusResponse:
    return ImageStatusResponse(**image_service.status())


@router.post(
    "/image/unload",
    tags=["Image Generation"], summary="Unload Pipeline From RAM",
)
async def unload_pipeline() -> dict:
    unloaded = image_service.unload_pipeline()
    return {"unloaded": unloaded}
