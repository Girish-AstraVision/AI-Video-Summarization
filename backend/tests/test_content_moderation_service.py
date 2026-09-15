from unittest.mock import patch

import pytest

from app.services.content_moderation_service import (
    ContentModerationError,
    InvalidModerationInputError,
    MissingTranscriptError,
    moderate_video,
)


def test_moderate_video_returns_events_for_matching_keywords() -> None:
    transcript = {
        "video_id": "demo_video",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "This is damn bad"},
            {"start": 5.0, "end": 8.0, "text": "You are stupid"},
            {"start": 10.0, "end": 12.0, "text": "No issue here"},
        ],
    }

    with patch("app.services.content_moderation_service.transcribe_video_audio", return_value=transcript):
        result = moderate_video("demo_video")

    assert result["video_id"] == "demo_video"
    assert result["total_events"] == 2
    assert result["moderation_events"][0]["category"] == "offensive_language"
    assert result["moderation_events"][0]["severity"] == "low"
    assert result["moderation_events"][1]["category"] == "inappropriate_language"
    assert result["moderation_events"][1]["text"] == "You are stupid"


def test_moderate_video_raises_for_missing_transcript() -> None:
    with patch(
        "app.services.content_moderation_service.transcribe_video_audio",
        side_effect=Exception("missing transcript"),
    ):
        with pytest.raises(ContentModerationError, match="Failed to read transcript"):
            moderate_video("missing_video")


def test_moderate_video_raises_for_empty_video_id() -> None:
    with pytest.raises(InvalidModerationInputError, match="video_id"):
        moderate_video("   ")


def test_moderate_video_ignores_non_matching_segments() -> None:
    transcript = {
        "video_id": "demo_video",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Good morning everyone"}],
    }

    with patch("app.services.content_moderation_service.transcribe_video_audio", return_value=transcript):
        result = moderate_video("demo_video")

    assert result["total_events"] == 0
    assert result["moderation_events"] == []


def test_moderate_video_returns_confidence_and_timestamp_details() -> None:
    transcript = {
        "video_id": "demo_video",
        "segments": [{"start": 21.1, "end": 24.5, "text": "idiot behavior"}],
    }

    with patch("app.services.content_moderation_service.transcribe_video_audio", return_value=transcript):
        result = moderate_video("demo_video")

    event = result["moderation_events"][0]
    assert event["timestamp"] == 21.1
    assert event["start_time"] == 21.1
    assert event["end_time"] == 24.5
    assert event["category"] == "inappropriate_language"
    assert event["severity"] == "high"
    assert event["confidence"] == 0.9
