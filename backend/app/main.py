from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.content_moderation import router as content_moderation_router
from app.api.routes.health import router as health_router
from app.api.routes.preprocessing import router as preprocessing_router
from app.api.routes.speech_to_text import router as speech_to_text_router
from app.api.routes.videos import router as videos_router
from app.api.routes.visual_detection import router as visual_detection_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Academic project backend for AI-based multimodal video summarization and content moderation.",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(videos_router)
app.include_router(preprocessing_router)
app.include_router(visual_detection_router)
app.include_router(speech_to_text_router)
app.include_router(content_moderation_router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Welcome to the AI Video Summarization API",
        "version": settings.app_version,
    }
