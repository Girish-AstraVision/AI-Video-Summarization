import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.chapters import ChapterRequest, ChapterResponse
from app.services.chapter_service import (
    ChapterError,
    InvalidChapterRequestError,
    MissingChapterDataError,
    create_video_chapters,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["chapters"])


@router.post("/{video_id}/chapters", status_code=status.HTTP_200_OK, response_model=ChapterResponse)
async def create_chapters_route(video_id: str, payload: ChapterRequest | None = None) -> dict:
    request = payload or ChapterRequest()
    try:
        max_chapters = request.max_chapters
        if max_chapters is not None:
            from app.services.chapter_service import validate_max_chapters

            validate_max_chapters(max_chapters)
        logger.info(
            "chapter route: video_id=%s cwd=%s upload_dir=%s resolved_matches=%s",
            video_id,
            __import__('pathlib').Path.cwd(),
            __import__('app.services.video_service', fromlist=['get_upload_directory']).get_upload_directory(),
            sorted(str(p.name) for p in __import__('app.services.video_service', fromlist=['get_upload_directory']).get_upload_directory().glob(f"{video_id}.*")),
        )
        result = create_video_chapters(video_id=video_id, max_chapters=max_chapters)
        return result
    except MissingChapterDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidChapterRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ChapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected chapter-generation error for video_id=%s", video_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected chapter generation error: {exc}",
        ) from exc
