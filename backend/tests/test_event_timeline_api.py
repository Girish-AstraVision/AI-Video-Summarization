from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.event_timeline_service import EventTimelineError, MissingTimelineDataError

client = TestClient(app)


def test_event_timeline_route_returns_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "total_events": 2,
        "events": [
            {
                "event_id": "visual-visual_detection-10.0-0",
                "timestamp": 10.0,
                "end_time": 10.0,
                "event_type": "visual",
                "source": "visual_detection",
                "description": "Person detected",
                "confidence": 0.9,
                "importance_score": 2.25,
                "metadata": {"label": "person"},
            },
            {
                "event_id": "speech-speech_to_text-12.0-1",
                "timestamp": 12.0,
                "end_time": 13.0,
                "event_type": "speech",
                "source": "speech_to_text",
                "description": "A person is visible.",
                "confidence": 0.8,
                "importance_score": 1.2,
                "metadata": {"segment_number": 1},
            },
        ],
        "processing_time": 0.05,
    }

    with patch("app.api.routes.event_timeline.create_event_timeline", return_value=mocked_result) as mock_service:
        response = client.post(
            "/api/videos/demo_video/timeline",
            json={"include_visual": True, "include_speech": True, "include_moderation": True, "include_keyframes": True, "include_chapters": True},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["video_id"] == "demo_video"
    assert payload["total_events"] == 2
    mock_service.assert_called_once_with(
        video_id="demo_video",
        include_visual=True,
        include_speech=True,
        include_moderation=True,
        include_keyframes=True,
        include_chapters=True,
    )


def test_event_timeline_route_filters() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "total_events": 1,
        "events": [
            {
                "event_id": "speech-speech_to_text-12.0-0",
                "timestamp": 12.0,
                "end_time": 13.0,
                "event_type": "speech",
                "source": "speech_to_text",
                "description": "A person is visible.",
                "confidence": 0.8,
                "importance_score": 1.2,
                "metadata": {"segment_number": 1},
            }
        ],
        "processing_time": 0.0,
    }

    with patch("app.api.routes.event_timeline.create_event_timeline", return_value=mocked_result):
        response = client.post(
            "/api/videos/demo_video/timeline",
            json={"include_visual": False, "include_speech": True, "include_moderation": False, "include_keyframes": False, "include_chapters": False},
        )

    assert response.status_code == 200
    assert response.json()["events"][0]["event_type"] == "speech"


def test_event_timeline_route_validation_error() -> None:
    response = client.post("/api/videos/demo_video/timeline", json={"include_visual": "yes"})

    assert response.status_code == 422


def test_event_timeline_route_handles_missing_data() -> None:
    with patch(
        "app.api.routes.event_timeline.create_event_timeline",
        side_effect=MissingTimelineDataError("Visual detection data not found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/timeline")

    assert response.status_code == 404
    assert "Visual detection data not found" in response.json()["detail"]


def test_event_timeline_route_handles_service_failure() -> None:
    with patch("app.api.routes.event_timeline.create_event_timeline", side_effect=EventTimelineError("Unexpected timeline failure")):
        response = client.post("/api/videos/demo_video/timeline")

    assert response.status_code == 500
    assert "Unexpected timeline failure" in response.json()["detail"]


def test_event_timeline_route_response_schema() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "total_events": 1,
        "events": [
            {
                "event_id": "chapter-chapter_generation-0.0-0",
                "timestamp": 0.0,
                "end_time": 5.0,
                "event_type": "chapter",
                "source": "chapter_generation",
                "description": "Chapter: Introduction",
                "confidence": 0.73,
                "importance_score": 0.5,
                "metadata": {"chapter_number": 1},
            }
        ],
        "processing_time": 0.01,
    }

    with patch("app.api.routes.event_timeline.create_event_timeline", return_value=mocked_result):
        response = client.post("/api/videos/demo_video/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][0]["event_type"] == "chapter"
    assert payload["total_events"] == 1
