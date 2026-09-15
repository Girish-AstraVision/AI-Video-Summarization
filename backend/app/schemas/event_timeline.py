from pydantic import BaseModel, Field, StrictBool


class TimelineRequest(BaseModel):
    include_visual: StrictBool = True
    include_speech: StrictBool = True
    include_moderation: StrictBool = True
    include_keyframes: StrictBool = True
    include_chapters: StrictBool = True


class TimelineEvent(BaseModel):
    event_id: str
    timestamp: float
    end_time: float | None = None
    event_type: str
    source: str
    description: str
    confidence: float | None = None
    importance_score: float | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class EventTimelineResponse(BaseModel):
    video_id: str
    total_events: int = 0
    events: list[TimelineEvent] = Field(default_factory=list)
    processing_time: float = 0.0
