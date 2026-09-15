import logging

from fastapi import APIRouter, HTTPException, status

from app.services.preprocessing_service import preprocess_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["preprocessing"])


@router.post("/{video_id}/preprocess", status_code=status.HTTP_200_OK)
async def preprocess_video_route(video_id: str) -> dict:
    try:
        result = preprocess_video(video_id)
        if result.get("preprocessing_status") == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("warnings", ["Video preprocessing failed."])[0],
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard for unexpected failures
        logger.exception("Unexpected error while preprocessing video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected preprocessing error: {exc}",
        ) from exc
