import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.content_moderation import ModerationResult
from app.services.content_moderation_service import (
    ContentModerationError,
    InvalidModerationInputError,
    MissingTranscriptError,
    moderate_video,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["content-moderation"])


@router.post("/{video_id}/moderate", status_code=status.HTTP_200_OK, response_model=ModerationResult)
async def moderate_video_route(video_id: str) -> dict:
    try:
        result = moderate_video(video_id=video_id)
        return result
    except MissingTranscriptError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidModerationInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ContentModerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected moderation error for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected moderation error: {exc}",
        ) from exc
