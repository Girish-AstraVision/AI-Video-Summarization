from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_detect_route_returns_detection_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "frames_processed": 1,
        "number_of_detections": 1,
        "detections": [
            {
                "frame_number": 1,
                "frame_filename": "frame_000001.jpg",
                "timestamp": 0.0,
                "label": "truck",
                "confidence": 0.9,
                "bounding_box": [10.0, 20.0, 30.0, 40.0],
            }
        ],
        "processing_time": 0.12,
        "model_name": "PekingU/rtdetr_r50vd_coco_o365",
    }

    with patch("app.api.routes.visual_detection.process_video_visual_detection", return_value=mocked_result) as mock_service:
        response = client.post("/api/videos/demo_video/detect", params={"confidence_threshold": 0.5})

    assert response.status_code == 200
    assert response.json()["video_id"] == "demo_video"
    assert response.json()["number_of_detections"] == 1
    mock_service.assert_called_once_with(video_id="demo_video", confidence_threshold=0.5)


def test_detect_route_rejects_invalid_confidence_threshold() -> None:
    response = client.post("/api/videos/demo_video/detect", params={"confidence_threshold": 2.0})

    assert response.status_code == 422


def test_detect_route_handles_missing_video() -> None:
    with patch(
        "app.api.routes.visual_detection.process_video_visual_detection",
        side_effect=ValueError("No processed frames found for video_id 'missing_video'."),
    ):
        response = client.post("/api/videos/missing_video/detect")

    assert response.status_code == 404
    assert "No processed frames found" in response.json()["detail"]


def test_detect_route_handles_model_load_error() -> None:
    with patch(
        "app.api.routes.visual_detection.process_video_visual_detection",
        side_effect=RuntimeError("Failed to load RT-DETR model 'PekingU/rtdetr_r50vd_coco_o365'."),
    ):
        response = client.post("/api/videos/demo_video/detect")

    assert response.status_code == 500
    assert "Failed to load RT-DETR model" in response.json()["detail"]
