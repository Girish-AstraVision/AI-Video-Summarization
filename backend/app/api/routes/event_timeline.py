import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.event_timeline import EventTimelineResponse, TimelineRequest
from app.services.event_timeline_service import (
    EventTimelineError,
    InvalidTimelineRequestError,
    MissingTimelineDataError,
    create_event_timeline,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["event-timeline"])


@router.post("/{video_id}/timeline", status_code=status.HTTP_200_OK, response_model=EventTimelineResponse)
async def create_event_timeline_route(video_id: str, payload: TimelineRequest | None = None) -> dict:
    request = payload or TimelineRequest()
    try:
        result = create_event_timeline(
            video_id=video_id,
            include_visual=request.include_visual,
            include_speech=request.include_speech,
            include_moderation=request.include_moderation,
            include_keyframes=request.include_keyframes,
            include_chapters=request.include_chapters,
        )
        return result
    except MissingTimelineDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidTimelineRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EventTimelineError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected timeline generation error for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected timeline generation error: {exc}",
        ) from exc
