import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.summarization import SummarizeVideoRequest, VideoSummaryResponse
from app.services.summarization_service import (
    InvalidSummaryRequestError,
    MissingSummaryDataError,
    SummarizationError,
    summarize_video,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["summarization"])


@router.post("/{video_id}/summarize", status_code=status.HTTP_200_OK, response_model=VideoSummaryResponse)
async def summarize_video_route(video_id: str, payload: SummarizeVideoRequest | None = None) -> dict:
    request = payload or SummarizeVideoRequest()
    try:
        if request.summary_length is None:
            request.summary_length = "medium"
        validate_length = str(request.summary_length).strip().lower()
        if validate_length not in {"short", "medium", "long"}:
            raise InvalidSummaryRequestError(
                "summary_length must be one of: short, medium, long."
            )

        if request.target_duration is not None:
            if request.target_duration <= 0:
                raise InvalidSummaryRequestError("target_duration must be greater than 0 seconds.")
            if request.target_duration > 3600:
                raise InvalidSummaryRequestError("target_duration must be less than or equal to 3600 seconds.")

        result = summarize_video(
            video_id=video_id,
            summary_length=validate_length,
            target_duration=request.target_duration,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except MissingSummaryDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidSummaryRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SummarizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected summarization error for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected summarization error: {exc}",
        ) from exc
