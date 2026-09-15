from pydantic import BaseModel, Field


class ChapterKeyFrame(BaseModel):
    frame_filename: str
    timestamp: float
    importance_score: float


class ImportantObject(BaseModel):
    label: str
    confidence: float


class ChapterItem(BaseModel):
    chapter_number: int
    start_time: float
    end_time: float
    title: str
    summary: str
    key_frames: list[ChapterKeyFrame] = Field(default_factory=list)
    important_objects: list[ImportantObject] = Field(default_factory=list)


class ChapterRequest(BaseModel):
    max_chapters: int = 5


class ChapterResponse(BaseModel):
    video_id: str
    number_of_chapters: int = 0
    chapters: list[ChapterItem] = Field(default_factory=list)
    processing_time: float = 0.0
