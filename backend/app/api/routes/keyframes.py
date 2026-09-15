import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.keyframes import KeyframeSelectionResult
from app.services.keyframe_service import (
    InvalidKeyframeRequestError,
    KeyframeError,
    MissingKeyframeDataError,
    VisualDetectionRequiredError,
    select_keyframes_for_video,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["keyframes"])


@router.post("/{video_id}/keyframes", status_code=status.HTTP_200_OK, response_model=KeyframeSelectionResult)
async def select_keyframes_route(
    video_id: str,
    num_keyframes: int = Query(default=5, ge=1, le=20),
) -> dict:
    try:
        result = select_keyframes_for_video(video_id=video_id, num_keyframes=num_keyframes)
        return result
    except MissingKeyframeDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (InvalidKeyframeRequestError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (VisualDetectionRequiredError, KeyframeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected key-frame selection error for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected key-frame selection error: {exc}",
        ) from exc
