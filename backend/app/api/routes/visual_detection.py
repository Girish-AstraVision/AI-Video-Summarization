import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.services.visual_detection_service import (
    ModelLoadError,
    VideoFrameDetectionError,
    process_video_visual_detection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["visual-detection"])


@router.post("/{video_id}/detect", status_code=status.HTTP_200_OK)
async def detect_visual_objects(
    video_id: str,
    confidence_threshold: float = Query(default=0.5, ge=0.0, le=1.0),
) -> dict:
    try:
        result = process_video_visual_detection(
            video_id=video_id,
            confidence_threshold=confidence_threshold,
        )
        return result
    except (VideoFrameDetectionError, ValueError) as exc:
        detail = str(exc)
        if "confidence_threshold" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        ) from exc
    except ModelLoadError as exc:
        logger.exception("RT-DETR model load failed for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected API error while detecting frame objects for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected visual detection error: {exc}",
        ) from exc
