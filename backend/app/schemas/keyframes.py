from pydantic import BaseModel, Field


class SelectedFrame(BaseModel):
    frame_filename: str
    timestamp: float
    importance_score: float
    detected_objects: list[str] = Field(default_factory=list)


class KeyframeSelectionResult(BaseModel):
    video_id: str
    total_frames_analyzed: int
    selected_frames: list[SelectedFrame] = Field(default_factory=list)
    number_selected: int
    processing_time: float
