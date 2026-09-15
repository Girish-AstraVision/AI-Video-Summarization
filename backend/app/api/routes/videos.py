import mimetypes

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.responses import FileResponse

from app.services.video_service import get_video_path_by_id, save_uploaded_video

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...)) -> dict:
    try:
        result = await save_uploaded_video(file)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{video_id}/stream")
async def stream_video(video_id: str) -> FileResponse:
    try:
        video_path = get_video_path_by_id(video_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' was not found.",
        ) from exc

    media_type = mimetypes.guess_type(video_path.name)[0] or "application/octet-stream"
    return FileResponse(path=video_path, media_type=media_type, filename=video_path.name)
