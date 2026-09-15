from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.content_moderation_service import (
    InvalidModerationInputError,
    MissingTranscriptError,
)

client = TestClient(app)


def test_moderate_route_returns_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "total_events": 1,
        "moderation_events": [
            {
                "video_id": "demo_video",
                "timestamp": 10.0,
                "start_time": 10.0,
                "end_time": 12.5,
                "category": "offensive_language",
                "severity": "low",
                "confidence": 0.72,
                "text": "damn",
                "message": "Contains mild profanity.",
            }
        ],
    }

    with patch("app.api.routes.content_moderation.moderate_video", return_value=mocked_result) as mock_service:
        response = client.post("/api/videos/demo_video/moderate")

    assert response.status_code == 200
    assert response.json()["video_id"] == "demo_video"
    assert response.json()["total_events"] == 1
    mock_service.assert_called_once_with(video_id="demo_video")


def test_moderate_route_handles_missing_transcript() -> None:
    with patch(
        "app.api.routes.content_moderation.moderate_video",
        side_effect=MissingTranscriptError("Transcript/audio not found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/moderate")

    assert response.status_code == 404
    assert "Transcript/audio not found" in response.json()["detail"]


def test_moderate_route_handles_invalid_input() -> None:
    with patch(
        "app.api.routes.content_moderation.moderate_video",
        side_effect=InvalidModerationInputError("video_id must not be empty."),
    ):
        response = client.post("/api/videos/ /moderate")

    assert response.status_code == 400
    assert "video_id" in response.json()["detail"]


def test_moderate_route_handles_unexpected_service_failure() -> None:
    with patch(
        "app.api.routes.content_moderation.moderate_video",
        side_effect=RuntimeError("Unexpected moderation error"),
    ):
        response = client.post("/api/videos/demo_video/moderate")

    assert response.status_code == 500
    assert "Unexpected moderation error" in response.json()["detail"]
