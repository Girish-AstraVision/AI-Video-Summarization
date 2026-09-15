from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.visual_detection_service import (
    ModelLoadError,
    VideoFrameDetectionError,
    process_video_visual_detection,
)


def test_process_video_visual_detection_uses_exact_preprocessing_timestamps(tmp_path: Path) -> None:
    project_root = tmp_path / "outputs"
    video_dir = project_root / "demo_video"
    frames_dir = video_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "metadata.json").write_text(
        __import__("json").dumps({
            "video_id": "demo_video",
            "metadata": {"fps": 30.0},
            "frame_details": [
                {"frame_filename": "frame_000001.jpg", "timestamp": 0.0},
                {"frame_filename": "frame_000002.jpg", "timestamp": 5.0},
                {"frame_filename": "frame_000003.jpg", "timestamp": 10.0},
            ],
        }),
        encoding="utf-8",
    )

    for idx in range(1, 4):
        (frames_dir / f"frame_{idx:06d}.jpg").write_bytes(b"fake-image")

    fake_processor = MagicMock()
    fake_model = MagicMock()
    fake_model.config.id2label = {1: "truck"}
    fake_result = {
        "scores": [MagicMock(item=lambda: 0.9)],
        "labels": [MagicMock(item=lambda: 1)],
        "boxes": [MagicMock(tolist=lambda: [10, 20, 30, 40])],
    }
    fake_processor.post_process_object_detection.return_value = [fake_result]

    with patch("app.services.visual_detection_service.get_project_root", return_value=tmp_path):
        with patch("app.services.visual_detection_service._load_model_and_processor", return_value=(fake_processor, fake_model)):
            with patch("app.services.visual_detection_service.Image.open") as mocked_image_open:
                mock_image = MagicMock()
                mock_image.size = (640, 480)
                mock_image.convert.return_value = mock_image
                mocked_image_open.return_value.__enter__.return_value = mock_image

                result = process_video_visual_detection("demo_video")

    assert result["detections"][0]["timestamp"] == 0.0
    assert result["detections"][1]["timestamp"] == 5.0
    assert result["detections"][2]["timestamp"] == 10.0


def test_process_video_visual_detection_raises_for_missing_frame_timestamp_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "outputs"
    video_dir = project_root / "demo_video"
    frames_dir = video_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "metadata.json").write_text(__import__("json").dumps({"video_id": "demo_video", "metadata": {"fps": 30.0}}), encoding="utf-8")
    (frames_dir / "frame_000001.jpg").write_bytes(b"fake-image")

    with patch("app.services.visual_detection_service.get_project_root", return_value=tmp_path):
        with pytest.raises(VideoFrameDetectionError, match="Frame timestamp metadata is missing"):
            process_video_visual_detection("demo_video")


def test_process_video_visual_detection_raises_for_missing_video_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "outputs"
    project_root.mkdir(parents=True, exist_ok=True)

    with patch("app.services.visual_detection_service.get_project_root", return_value=tmp_path):
        with pytest.raises(VideoFrameDetectionError, match="No processed frames found"):
            process_video_visual_detection("missing_video")


def test_process_video_visual_detection_raises_for_missing_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "outputs"
    video_dir = project_root / "demo_video"
    frames_dir = video_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    (frames_dir / "frame_000001.jpg").write_bytes(b"fake-image")

    with patch("app.services.visual_detection_service.get_project_root", return_value=tmp_path):
        with pytest.raises(VideoFrameDetectionError, match="Missing metadata file"):
            process_video_visual_detection("demo_video")


def test_process_video_visual_detection_uses_mocked_model_and_detects_objects(tmp_path: Path) -> None:
    project_root = tmp_path / "outputs"
    video_dir = project_root / "demo_video"
    frames_dir = video_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "video_id": "demo_video",
        "metadata": {"fps": 10.0},
        "frame_details": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0}],
    }
    (video_dir / "metadata.json").write_text(__import__("json").dumps(metadata), encoding="utf-8")

    fake_image = Path(frames_dir / "frame_000001.jpg")
    fake_image.write_bytes(b"fake-image")

    fake_processor = MagicMock()
    fake_model = MagicMock()
    fake_model.config.id2label = {1: "truck"}

    fake_result = {
        "scores": [MagicMock(item=lambda: 0.9)],
        "labels": [MagicMock(item=lambda: 1)],
        "boxes": [MagicMock(tolist=lambda: [10, 20, 30, 40])],
    }
    fake_processor.post_process_object_detection.return_value = [fake_result]

    with patch("app.services.visual_detection_service.get_project_root", return_value=tmp_path):
        with patch("app.services.visual_detection_service._load_model_and_processor", return_value=(fake_processor, fake_model)):
            with patch("app.services.visual_detection_service.Image.open") as mocked_image_open:
                mock_image = MagicMock()
                mock_image.size = (640, 480)
                mock_image.convert.return_value = mock_image
                mocked_image_open.return_value.__enter__.return_value = mock_image

                result = process_video_visual_detection("demo_video", confidence_threshold=0.5)

    assert result["video_id"] == "demo_video"
    assert result["frames_processed"] == 1
    assert result["number_of_detections"] == 1
    assert result["detections"][0]["label"] == "truck"
    assert result["detections"][0]["confidence"] == 0.9
    assert result["detections"][0]["timestamp"] == 0.0
    assert result["model_name"]


def test_process_video_visual_detection_raises_for_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        process_video_visual_detection("demo_video", confidence_threshold=1.5)


def test_load_model_raises_model_load_error() -> None:
    import app.services.visual_detection_service as visual_detection_service

    visual_detection_service._processor_instance = None
    visual_detection_service._model_instance = None

    with patch("app.services.visual_detection_service.RTDetrImageProcessor.from_pretrained", side_effect=Exception("fail")):
        with patch("app.services.visual_detection_service.RTDetrForObjectDetection.from_pretrained", side_effect=Exception("fail")):
            with pytest.raises(ModelLoadError):
                visual_detection_service._load_model_and_processor()
