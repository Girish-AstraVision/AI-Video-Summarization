from pydantic import BaseModel, Field


class DetectionRecord(BaseModel):
    frame_number: int
    frame_filename: str
    timestamp: float
    label: str
    confidence: float
    bounding_box: list[float] = Field(default_factory=list)


class VisualDetectionResult(BaseModel):
    video_id: str
    frames_processed: int
    number_of_detections: int
    detections: list[DetectionRecord] = Field(default_factory=list)
    processing_time: float
    model_name: str
