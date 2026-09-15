from pydantic import BaseModel, Field


class ModerationEvent(BaseModel):
    video_id: str
    timestamp: float
    start_time: float
    end_time: float
    category: str
    severity: str
    confidence: float
    text: str
    message: str


class ModerationResult(BaseModel):
    video_id: str
    total_events: int = 0
    moderation_events: list[ModerationEvent] = Field(default_factory=list)
