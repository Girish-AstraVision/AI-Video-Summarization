from typing import Any

from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_present: bool = False
    audio_codec: str | None = None


class PreprocessingResult(BaseModel):
    video_id: str
    video_path: str
    metadata: VideoMetadata
    audio_path: str | None = None
    extracted_frame_directory: str
    frame_timestamps: list[float] = Field(default_factory=list)
    frame_count: int = 0
    preprocessing_status: str = "completed"
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
