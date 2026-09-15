from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_summary_route_returns_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "summary_length": "medium",
        "target_duration": 30,
        "actual_summary_duration": 12.5,
        "summary_text": "A person walks near a car. A truck moves quickly.",
        "number_of_segments": 2,
        "segments": [
            {"start_time": 0.0, "end_time": 5.0, "text": "A person walks near a car.", "importance_score": 5.4},
            {"start_time": 12.0, "end_time": 16.0, "text": "A truck moves quickly.", "importance_score": 6.6},
        ],
        "key_frames": [
            {"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 8.1, "detected_objects": ["person", "car"]}
        ],
        "processing_time": 0.05,
        "important_events": [{"timestamp": 0.0, "label": "speech-highlight", "description": "A person walks near a car.", "severity": "medium"}],
    }

    with patch("app.api.routes.summarization.summarize_video", return_value=mocked_result) as mock_service:
        response = client.post(
            "/api/videos/demo_video/summarize",
            json={"summary_length": "medium", "target_duration": 30},
        )

    assert response.status_code == 200
    assert response.json()["video_id"] == "demo_video"
    assert response.json()["summary_length"] == "medium"
    assert response.json()["number_of_segments"] == 2
    mock_service.assert_called_once_with(video_id="demo_video", summary_length="medium", target_duration=30)


def test_summary_route_validates_summary_length() -> None:
    response = client.post("/api/videos/demo_video/summarize", json={"summary_length": "tiny"})

    assert response.status_code == 400
    assert "summary_length" in response.json()["detail"]


def test_summary_route_validates_target_duration() -> None:
    response = client.post("/api/videos/demo_video/summarize", json={"summary_length": "medium", "target_duration": 0})

    assert response.status_code == 400
    assert "target_duration" in response.json()["detail"]


def test_summary_route_handles_missing_data() -> None:
    with patch(
        "app.api.routes.summarization.summarize_video",
        side_effect=RuntimeError("Transcript data not found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/summarize", json={"summary_length": "medium"})

    assert response.status_code == 500
    assert "Transcript data not found" in response.json()["detail"]


def test_summary_route_handles_service_failure() -> None:
    with patch("app.api.routes.summarization.summarize_video", side_effect=RuntimeError("Unexpected summary failure")):
        response = client.post("/api/videos/demo_video/summarize", json={"summary_length": "short"})

    assert response.status_code == 500
    assert "Unexpected summary failure" in response.json()["detail"]


def test_summary_route_response_schema() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "summary_length": "short",
        "target_duration": None,
        "actual_summary_duration": 3.0,
        "summary_text": "Important event captured.",
        "number_of_segments": 1,
        "segments": [
            {"start_time": 10.0, "end_time": 15.0, "text": "Important event captured.", "importance_score": 8.0}
        ],
        "key_frames": [
            {"frame_filename": "frame_000010.jpg", "timestamp": 10.0, "importance_score": 8.0, "detected_objects": ["person"]}
        ],
        "processing_time": 0.1,
        "important_events": [{"timestamp": 10.0, "label": "speech-highlight", "description": "Important event captured.", "severity": "medium"}],
    }

    with patch("app.api.routes.summarization.summarize_video", return_value=mocked_result):
        response = client.post("/api/videos/demo_video/summarize", json={"summary_length": "short"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) >= {"video_id", "summary_length", "actual_summary_duration", "summary_text", "segments", "key_frames"}
    assert payload["segments"][0]["importance_score"] == 8.0
