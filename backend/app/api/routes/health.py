from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "AI Video Summarization API",
        "version": "0.1.0",
    }
