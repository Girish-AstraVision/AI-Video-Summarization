from pydantic import BaseModel, Field


class SummarySegment(BaseModel):
    start_time: float
    end_time: float
    text: str
    importance_score: float


class SummaryKeyFrame(BaseModel):
    frame_filename: str
    timestamp: float
    importance_score: float
    detected_objects: list[str] = Field(default_factory=list)


class ImportantEvent(BaseModel):
    timestamp: float
    label: str
    description: str
    severity: str = "medium"


class SummarizeVideoRequest(BaseModel):
    summary_length: str = "medium"
    target_duration: float | None = None


class VideoSummaryResponse(BaseModel):
    video_id: str
    summary_length: str
    target_duration: float | None = None
    actual_summary_duration: float = 0.0
    summary_text: str
    number_of_segments: int = 0
    segments: list[SummarySegment] = Field(default_factory=list)
    key_frames: list[SummaryKeyFrame] = Field(default_factory=list)
    processing_time: float = 0.0
    important_events: list[ImportantEvent] = Field(default_factory=list)
