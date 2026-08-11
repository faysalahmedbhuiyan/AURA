"""
AURA Backend — Voice Routes.

Module: app.api.v1.routes.voice
Purpose: Handles Speech-to-Text and Text-to-Speech requests.
         Integrates with chat pipeline for full voice conversation.

Endpoints:
    POST /api/v1/voice/transcribe  — Audio file → Text
    POST /api/v1/voice/speak       — Text → Audio file
    POST /api/v1/voice/chat        — Audio → LLM → Audio
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import ChatRequest
from app.services.memory_service import memory_service
from app.services.ollama_service import ollama_service
from app.services.tts_service import tts_service
from app.services.whisper_service import whisper_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Response Schemas ──────────────────────────────────────────────────────────
class TranscribeResponse(BaseModel):
    """Response schema for audio transcription."""

    text: str
    language: str
    duration: float
    segments: list[dict]


class SpeakRequest(BaseModel):
    """Request schema for text-to-speech."""

    text: str
    language: str = "en"


class VoiceChatResponse(BaseModel):
    """Response schema for voice chat."""

    transcribed_text: str
    response_text: str
    conversation_id: str
    audio_file: str
    language: str


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post(
    "/voice/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe Audio to Text",
    description="Upload an audio file and get transcribed text. "
                "Supports Bangla, English, Hindi, Korean.",
    tags=["Voice"],
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="en", description="Language code: bn, en, hi, ko"),
) -> TranscribeResponse:
    """
    Transcribe uploaded audio file to text.

    Supports WAV, MP3, M4A, OGG, FLAC, WebM formats.
    Uses faster-whisper with on-demand model loading.

    Args:
        file: Uploaded audio file.
        language: Expected language code.

    Returns:
        TranscribeResponse: Transcribed text with timing info.

    Raises:
        400: If file format is not supported.
        503: If Whisper is not available.
        500: If transcription fails.
    """
    if not whisper_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-Text service is not available.",
        )

    # Get file extension
    filename = file.filename or "audio.wav"
    suffix = "." + filename.rsplit(".", 1)[-1].lower()

    try:
        audio_bytes = await file.read()
        result = await whisper_service.transcribe_bytes(
            audio_bytes=audio_bytes,
            language=language,
            suffix=suffix,
        )

        return TranscribeResponse(
            text=result["text"],
            language=result["language"],
            duration=result["duration"],
            segments=result["segments"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/voice/speak",
    summary="Convert Text to Speech",
    description="Convert text to audio using Piper TTS. Returns WAV file.",
    tags=["Voice"],
    response_class=FileResponse,
)
async def speak_text(request: SpeakRequest) -> FileResponse:
    """
    Convert text to speech audio file.

    Uses Piper TTS with on-demand model loading.
    Returns WAV audio file for download or playback.

    Args:
        request: SpeakRequest with text and language.

    Returns:
        FileResponse: WAV audio file.

    Raises:
        400: If text is empty.
        503: If TTS is not available.
        500: If synthesis fails.
    """
    if not tts_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-Speech service is not available. "
                   "Please check Piper model installation.",
        )

    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty.",
        )

    try:
        audio_path = await tts_service.speak(request.text)

        return FileResponse(
            path=str(audio_path),
            media_type="audio/wav",
            filename=audio_path.name,
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/voice/chat",
    response_model=VoiceChatResponse,
    summary="Voice Chat with AURA",
    description="Upload audio, AURA transcribes, thinks, and responds with audio.",
    tags=["Voice"],
)
async def voice_chat(
    file: UploadFile = File(..., description="Audio file with your message"),
    language: str = Form(default="en", description="Language code: bn, en, hi, ko"),
    conversation_id: str = Form(default="", description="Existing conversation UUID"),
    db: AsyncSession = Depends(get_db),
) -> VoiceChatResponse:
    """
    Full voice conversation with AURA.

    Complete pipeline:
    1. Transcribe user audio → text (Whisper)
    2. Get or create conversation
    3. Get RAG context from ChromaDB
    4. Send to Ollama LLM with history + context
    5. Convert LLM response → audio (Piper)
    6. Return text + audio file path

    Args:
        file: Audio file with user's spoken message.
        language: Language code for STT and response.
        conversation_id: Optional existing conversation UUID.
        db: Injected database session.

    Returns:
        VoiceChatResponse: Transcription, text response, audio file.

    Raises:
        503: If Whisper or Ollama is not available.
        500: If any pipeline step fails.
    """
    # ── Check services ────────────────────────────────────────────────────────
    if not whisper_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-Text is not available.",
        )

    if not await ollama_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not available. Please start Ollama.",
        )

    # ── Step 1: Transcribe audio ──────────────────────────────────────────────
    filename = file.filename or "audio.wav"
    suffix = "." + filename.rsplit(".", 1)[-1].lower()

    try:
        audio_bytes = await file.read()
        transcription = await whisper_service.transcribe_bytes(
            audio_bytes=audio_bytes,
            language=language,
            suffix=suffix,
        )
        user_text = transcription["text"]

        if not user_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not transcribe audio. Please speak clearly.",
            )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )

    # ── Step 2: Get or create conversation ───────────────────────────────────
    conv_id = conversation_id.strip() if conversation_id.strip() else None

    if conv_id:
        conversation = await conversation_repository.get_conversation(
            db, conv_id
        )
        if not conversation:
            conversation = await conversation_repository.create_conversation(
                db, language=language
            )
    else:
        conversation = await conversation_repository.create_conversation(
            db, language=language
        )

    # ── Step 3: Load history + RAG context ───────────────────────────────────
    history = await conversation_repository.get_history(
        db, conversation.id
    )
    context = await memory_service.get_relevant_context(
        query=user_text,
        conversation_id=conversation.id,
    )

    enriched_message = user_text
    if context:
        enriched_message = (
            f"{user_text}\n\n[Relevant context:\n{context}]"
        )

    # ── Step 4: Save user message ─────────────────────────────────────────────
    user_msg = await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="user",
        content=user_text,
    )
    await memory_service.store_message(
        message_id=user_msg.id,
        conversation_id=conversation.id,
        role="user",
        content=user_text,
        language=language,
    )

    # ── Step 5: Get LLM response ──────────────────────────────────────────────
    try:
        ai_response = await ollama_service.chat(
            message=enriched_message,
            history=history,
        )
    except (ConnectionError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # ── Step 6: Save assistant message ───────────────────────────────────────
    assistant_msg = await conversation_repository.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        model_used=ollama_service.model,
    )
    await memory_service.store_message(
        message_id=assistant_msg.id,
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        language=language,
    )

    # ── Step 7: Convert response to audio ─────────────────────────────────────
    audio_file_name = "no_audio"
    if tts_service.is_available():
        try:
            audio_path = await tts_service.speak(ai_response)
            audio_file_name = audio_path.name
        except Exception as e:
            logger.warning("TTS failed, returning text only: %s", e)

    logger.info(
        "Voice chat completed | conversation=%s | lang=%s",
        conversation.id,
        language,
    )

    return VoiceChatResponse(
        transcribed_text=user_text,
        response_text=ai_response,
        conversation_id=conversation.id,
        audio_file=audio_file_name,
        language=language,
    )