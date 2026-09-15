import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.speech_to_text import SpeechToTextResult
from app.services.speech_to_text_service import (
    AudioNotFoundError,
    InvalidAudioError,
    SpeechTranscriptionError,
    WhisperModelLoadError,
    transcribe_video_audio,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["speech-to-text"])


@router.post("/{video_id}/transcribe", status_code=status.HTTP_200_OK, response_model=SpeechToTextResult)
async def transcribe_video_route(video_id: str) -> dict:
    try:
        result = transcribe_video_audio(video_id=video_id)
        return result
    except (AudioNotFoundError, InvalidAudioError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (SpeechTranscriptionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except WhisperModelLoadError as exc:
        logger.exception("Whisper model loading failed for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected ASR API error while transcribing video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected transcription error: {exc}",
        ) from exc
