"""
AURA Backend — Video Generation Routes (Tier 5, video half).

Module: app.api.v1.routes.video
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)


class ImageToVideoRequest(BaseModel):
    image_path: str = Field(..., description="Absolute path of an existing generated image")
    prompt: str = Field(default="", max_length=500)


class DialogueLineRequest(BaseModel):
    text: str
    gender: str = Field(default="male", description="'male' or 'female'")


class AddDialogueRequest(BaseModel):
    video_path: str = Field(..., description="Absolute path of an existing generated video")
    lines: list[DialogueLineRequest]


@router.post(
    "/video/add-dialogue", tags=["Video Generation"],
    summary="Add Gendered Dialogue Audio to a Silent Video",
)
async def add_dialogue(request: AddDialogueRequest) -> dict:
    from app.services.video_audio_service import DialogueLine, video_audio_service

    lines = [DialogueLine(text=l.text, gender=l.gender) for l in request.lines]
    return video_audio_service.add_dialogue_to_video(request.video_path, lines)


@router.post(
    "/video/generate", tags=["Video Generation"],
    summary="Generate a Video From Text (Hugging Face free tier)",
)
async def generate_video(request: VideoGenerateRequest) -> dict:
    from app.services.video_service import video_service

    return await video_service.generate_text_to_video(request.prompt)


@router.post(
    "/video/animate", tags=["Video Generation"],
    summary="Animate an Existing Photo Into a Short Video",
)
async def animate_image(request: ImageToVideoRequest) -> dict:
    from app.services.video_service import video_service

    return await video_service.generate_image_to_video(request.image_path, request.prompt)


@router.get(
    "/video/file/{file_name}", tags=["Video Generation"],
    summary="Fetch a Generated Video",
)
async def get_video_file(file_name: str):
    from pathlib import Path

    from app.config import get_settings

    settings = get_settings()
    output_dir = Path(getattr(settings, "video_output_dir", "D:/AURA/assets/generated_video"))
    path = output_dir / file_name
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return FileResponse(path, media_type="video/mp4")
