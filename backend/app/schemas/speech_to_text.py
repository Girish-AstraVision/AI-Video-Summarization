from pydantic import BaseModel, Field


class SpeechSegment(BaseModel):
    segment_number: int
    start: float
    end: float
    text: str


class SpeechToTextResult(BaseModel):
    video_id: str
    audio_path: str
    model_name: str
    detected_language: str | None = None
    language_probability: float = 0.0
    number_of_segments: int = 0
    segments: list[SpeechSegment] = Field(default_factory=list)
    processing_time: float = 0.0
