from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.video_service import save_uploaded_video

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
