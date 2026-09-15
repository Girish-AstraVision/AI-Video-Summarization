from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.keyframe_service import MissingKeyframeDataError, VisualDetectionRequiredError

client = TestClient(app)


def test_keyframe_route_returns_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "total_frames_analyzed": 10,
        "selected_frames": [
            {
                "frame_filename": "frame_000003.jpg",
                "timestamp": 10.0,
                "importance_score": 7.28,
                "detected_objects": ["car", "person"],
            }
        ],
        "number_selected": 1,
        "processing_time": 0.12,
    }

    with patch("app.api.routes.keyframes.select_keyframes_for_video", return_value=mocked_result) as mock_service:
        response = client.post("/api/videos/demo_video/keyframes", params={"num_keyframes": 1})

    assert response.status_code == 200
    assert response.json()["video_id"] == "demo_video"
    assert response.json()["number_selected"] == 1
    mock_service.assert_called_once_with(video_id="demo_video", num_keyframes=1)


def test_keyframe_route_handles_missing_data() -> None:
    with patch(
        "app.api.routes.keyframes.select_keyframes_for_video",
        side_effect=MissingKeyframeDataError("Preprocessing metadata not found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/keyframes")

    assert response.status_code == 404
    assert "Preprocessing metadata not found" in response.json()["detail"]


def test_keyframe_route_handles_visual_detection_required() -> None:
    with patch(
        "app.api.routes.keyframes.select_keyframes_for_video",
        side_effect=VisualDetectionRequiredError("RT-DETR visual detection must be run before selecting key frames for video_id 'demo_video'."),
    ):
        response = client.post("/api/videos/demo_video/keyframes")

    assert response.status_code == 404
    assert "visual detection must be run" in response.json()["detail"].lower()


def test_keyframe_route_rejects_invalid_keyframe_count() -> None:
    response = client.post("/api/videos/demo_video/keyframes", params={"num_keyframes": 0})

    assert response.status_code == 422
