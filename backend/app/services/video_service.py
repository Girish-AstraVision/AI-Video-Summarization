import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def get_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "uploads").exists() or (parent / "outputs").exists():
            return parent
    return current.parents[2]


def get_upload_directory() -> Path:
    project_root = get_project_root()
    uploads_dir = project_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def get_video_path_by_id(video_id: str) -> Path:
    upload_dir = get_upload_directory()
    matches = sorted(upload_dir.glob(f"{video_id}.*"))
    logger.info(
        "video lookup: video_id=%s cwd=%s upload_dir=%s matches=%s exists=%s",
        video_id,
        Path.cwd(),
        upload_dir,
        [str(item.name) for item in matches],
        any(item.exists() for item in matches),
    )
    if not matches:
        raise FileNotFoundError(f"No uploaded video found for video_id '{video_id}'.")
    return matches[0]


def validate_video_extension(filename: str) -> str:
    if not filename:
        raise ValueError("No file name provided.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(
            "Unsupported file format. Allowed formats are: MP4, MOV, AVI, MKV."
        )

    return extension


async def save_uploaded_video(file: UploadFile) -> dict[str, Any]:
    original_filename = file.filename or "uploaded_video"
    extension = validate_video_extension(original_filename)

    file_content = await file.read()
    if not file_content:
        raise ValueError("Uploaded file is empty.")

    video_id = uuid4().hex
    saved_filename = f"{video_id}{extension}"
    upload_directory = get_upload_directory()
    destination = upload_directory / saved_filename

    try:
        with destination.open("wb") as file_object:
            file_object.write(file_content)
    except OSError as exc:
        raise OSError("Failed to save the uploaded video file.") from exc

    return {
        "video_id": video_id,
        "original_filename": original_filename,
        "saved_filename": saved_filename,
        "file_size": len(file_content),
        "status": "uploaded",
    }
