from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chapter_route_returns_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "number_of_chapters": 2,
        "chapters": [
            {
                "chapter_number": 1,
                "start_time": 0.0,
                "end_time": 10.0,
                "title": "Introduction",
                "summary": "Initial activity in the scene.",
                "key_frames": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 8.0}],
                "important_objects": [{"label": "person", "confidence": 0.9}],
            },
            {
                "chapter_number": 2,
                "start_time": 10.0,
                "end_time": 20.0,
                "title": "Vehicle Activity",
                "summary": "Vehicle movement dominates the later action.",
                "key_frames": [{"frame_filename": "frame_000010.jpg", "timestamp": 12.0, "importance_score": 6.0}],
                "important_objects": [{"label": "truck", "confidence": 0.86}],
            },
        ],
        "processing_time": 0.09,
    }

    with patch("app.api.routes.chapters.create_video_chapters", return_value=mocked_result) as mock_service:
        response = client.post("/api/videos/demo_video/chapters", json={"max_chapters": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["video_id"] == "demo_video"
    assert payload["number_of_chapters"] == 2
    mock_service.assert_called_once_with(video_id="demo_video", max_chapters=2)


def test_chapter_route_validates_max_chapters() -> None:
    response = client.post("/api/videos/demo_video/chapters", json={"max_chapters": 0})

    assert response.status_code == 400
    assert "max_chapters" in response.json()["detail"]


def test_chapter_route_handles_missing_data() -> None:
    with patch(
        "app.api.routes.chapters.create_video_chapters",
        side_effect=RuntimeError("Transcript data not found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/chapters", json={"max_chapters": 3})

    assert response.status_code == 500
    assert "Transcript data not found" in response.json()["detail"]


def test_chapter_route_handles_service_failure() -> None:
    with patch("app.api.routes.chapters.create_video_chapters", side_effect=RuntimeError("Unexpected chapter failure")):
        response = client.post("/api/videos/demo_video/chapters", json={"max_chapters": 5})

    assert response.status_code == 500
    assert "Unexpected chapter failure" in response.json()["detail"]


def test_chapter_route_response_schema() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "number_of_chapters": 1,
        "chapters": [
            {
                "chapter_number": 1,
                "start_time": 0.0,
                "end_time": 8.0,
                "title": "Introduction",
                "summary": "Scene activity begins.",
                "key_frames": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 6.5}],
                "important_objects": [{"label": "person", "confidence": 0.8}],
            }
        ],
        "processing_time": 0.05,
    }

    with patch("app.api.routes.chapters.create_video_chapters", return_value=mocked_result):
        response = client.post("/api/videos/demo_video/chapters", json={"max_chapters": 5})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) >= {"video_id", "number_of_chapters", "chapters", "processing_time"}
    assert payload["chapters"][0]["title"] == "Introduction"
