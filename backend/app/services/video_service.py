from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def get_upload_directory() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    uploads_dir = project_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


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
