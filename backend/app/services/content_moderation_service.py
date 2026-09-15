import logging
import re
from typing import Any

from app.services.speech_to_text_service import AudioNotFoundError, transcribe_video_audio

logger = logging.getLogger(__name__)

DEFAULT_MODERATION_RULES: dict[str, dict[str, Any]] = {
    "damn": {
        "category": "offensive_language",
        "severity": "low",
        "confidence": 0.72,
        "message": "Contains mild profanity.",
    },
    "hell": {
        "category": "offensive_language",
        "severity": "low",
        "confidence": 0.68,
        "message": "Contains profanity.",
    },
    "crap": {
        "category": "inappropriate_language",
        "severity": "medium",
        "confidence": 0.8,
        "message": "Contains inappropriate language.",
    },
    "idiot": {
        "category": "inappropriate_language",
        "severity": "high",
        "confidence": 0.9,
        "message": "Contains insulting language.",
    },
    "stupid": {
        "category": "inappropriate_language",
        "severity": "medium",
        "confidence": 0.84,
        "message": "Contains insulting language.",
    },
}


class ContentModerationError(RuntimeError):
    """Base exception for text moderation failures."""


class MissingTranscriptError(ContentModerationError):
    """Raised when the video transcript is missing or unreadable."""


class InvalidModerationInputError(ContentModerationError):
    """Raised when moderation input is missing or invalid."""


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _compile_rule(pattern: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(pattern)}(?!\w)", re.IGNORECASE)


def _match_rule(text: str, rule: dict[str, Any]) -> bool:
    if not text:
        return False

    pattern = rule.get("pattern")
    if pattern:
        return bool(_compile_rule(pattern).search(text))

    return False


def moderate_video(video_id: str, moderation_rules: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    if not video_id or not video_id.strip():
        raise InvalidModerationInputError("video_id must not be empty.")

    rules = moderation_rules or DEFAULT_MODERATION_RULES
    try:
        transcript = transcribe_video_audio(video_id=video_id)
    except AudioNotFoundError as exc:
        raise MissingTranscriptError(f"Transcript/audio not found for video_id '{video_id}'.") from exc
    except ValueError as exc:
        raise InvalidModerationInputError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected transcription error while moderating video_id=%s", video_id)
        raise ContentModerationError(f"Failed to read transcript for video_id '{video_id}'.") from exc

    segments = transcript.get("segments", [])
    events: list[dict[str, Any]] = []

    for segment in segments:
        segment_text = str(segment.get("text", "")).strip()
        if not segment_text:
            continue

        normalized_text = _normalize_text(segment_text)
        for keyword, config in rules.items():
            if not isinstance(config, dict):
                continue

            if _match_rule(normalized_text, {"pattern": keyword}):
                start_time = float(segment.get("start", 0.0) or 0.0)
                end_time = float(segment.get("end", 0.0) or 0.0)
                event = {
                    "video_id": video_id,
                    "timestamp": start_time,
                    "start_time": start_time,
                    "end_time": end_time,
                    "category": config.get("category", "inappropriate_language"),
                    "severity": config.get("severity", "medium"),
                    "confidence": float(config.get("confidence", 0.5)),
                    "text": segment_text,
                    "message": config.get("message", "Potentially inappropriate content detected."),
                }
                events.append(event)
                break

    result = {
        "video_id": video_id,
        "total_events": len(events),
        "moderation_events": events,
    }

    logger.info("Moderation completed for video_id=%s with %d event(s)", video_id, len(events))
    return result
