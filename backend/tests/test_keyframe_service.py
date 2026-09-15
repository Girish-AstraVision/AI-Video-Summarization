from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.keyframe_service import (
    InvalidKeyframeRequestError,
    MissingKeyframeDataError,
    VisualDetectionRequiredError,
    select_keyframes_for_video,
)


def test_select_keyframes_for_video_returns_ranked_frames(tmp_path: Path) -> None:
    video_id = "demo_video"
    outputs_dir = tmp_path / "outputs" / video_id
    frames_dir = outputs_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    (outputs_dir / "metadata.json").write_text(
        __import__("json").dumps(
            {
                "video_id": video_id,
                "frame_details": [
                    {"frame_filename": "frame_000001.jpg", "timestamp": 0.0},
                    {"frame_filename": "frame_000002.jpg", "timestamp": 5.0},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 10.0},
                    {"frame_filename": "frame_000004.jpg", "timestamp": 15.0},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 20.0},
                ],
            }
        ),
        encoding="utf-8",
    )

    detection_result = {
        "detections": [
            {"frame_filename": "frame_000001.jpg", "label": "car", "confidence": 0.9},
            {"frame_filename": "frame_000001.jpg", "label": "car", "confidence": 0.8},
            {"frame_filename": "frame_000003.jpg", "label": "truck", "confidence": 0.95},
            {"frame_filename": "frame_000003.jpg", "label": "person", "confidence": 0.7},
            {"frame_filename": "frame_000005.jpg", "label": "bus", "confidence": 0.8},
        ]
    }

    with patch("app.services.keyframe_service.get_project_root", return_value=tmp_path):
        with patch("app.services.keyframe_service._read_detection_results", return_value=detection_result):
            result = select_keyframes_for_video(video_id, num_keyframes=3)

    assert result["video_id"] == video_id
    assert result["number_selected"] == 3
    assert result["selected_frames"][0]["frame_filename"] == "frame_000003.jpg"
    assert result["selected_frames"][0]["timestamp"] == 10.0
    assert result["selected_frames"][0]["detected_objects"] == ["person", "truck"]


def test_select_keyframes_for_video_raises_if_visual_detection_missing(tmp_path: Path) -> None:
    video_id = "demo_video"
    outputs_dir = tmp_path / "outputs" / video_id
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "metadata.json").write_text(
        __import__("json").dumps({"video_id": video_id, "frame_details": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0}]}),
        encoding="utf-8",
    )

    with patch("app.services.keyframe_service.get_project_root", return_value=tmp_path):
        with patch("app.services.keyframe_service._read_detection_results", side_effect=VisualDetectionRequiredError("Run detection first")):
            with pytest.raises(VisualDetectionRequiredError, match="Run detection first"):
                select_keyframes_for_video(video_id)


def test_select_keyframes_for_video_rejects_invalid_keyframe_count(tmp_path: Path) -> None:
    with pytest.raises(InvalidKeyframeRequestError, match="num_keyframes"):
        select_keyframes_for_video("demo_video", num_keyframes=0)

    with pytest.raises(InvalidKeyframeRequestError, match="num_keyframes"):
        select_keyframes_for_video("demo_video", num_keyframes=21)


def test_select_keyframes_for_video_raises_for_missing_frame_metadata(tmp_path: Path) -> None:
    video_id = "demo_video"
    outputs_dir = tmp_path / "outputs" / video_id
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "metadata.json").write_text(__import__("json").dumps({"video_id": video_id}), encoding="utf-8")

    with patch("app.services.keyframe_service.get_project_root", return_value=tmp_path):
        with patch("app.services.keyframe_service._read_detection_results", return_value={"detections": [{"frame_filename": "frame_000001.jpg", "label": "car", "confidence": 0.9}]}):
            with pytest.raises(MissingKeyframeDataError, match="does not contain frame data"):
                select_keyframes_for_video(video_id)


def test_select_keyframes_for_video_prefers_time_gap_when_selecting(tmp_path: Path) -> None:
    video_id = "demo_video"
    outputs_dir = tmp_path / "outputs" / video_id
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "metadata.json").write_text(
        __import__("json").dumps(
            {
                "video_id": video_id,
                "frame_details": [
                    {"frame_filename": "frame_000001.jpg", "timestamp": 0.0},
                    {"frame_filename": "frame_000002.jpg", "timestamp": 0.5},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 5.0},
                    {"frame_filename": "frame_000004.jpg", "timestamp": 10.0},
                ],
            }
        ),
        encoding="utf-8",
    )

    detection_result = {
        "detections": [
            {"frame_filename": "frame_000001.jpg", "label": "car", "confidence": 0.8},
            {"frame_filename": "frame_000003.jpg", "label": "truck", "confidence": 0.9},
            {"frame_filename": "frame_000004.jpg", "label": "person", "confidence": 0.7},
        ]
    }

    with patch("app.services.keyframe_service.get_project_root", return_value=tmp_path):
        with patch("app.services.keyframe_service._read_detection_results", return_value=detection_result):
            result = select_keyframes_for_video(video_id, num_keyframes=2)

    timestamps = [frame["timestamp"] for frame in result["selected_frames"]]
    assert len(timestamps) == 2
    assert 5.0 in timestamps
    assert abs(timestamps[0] - timestamps[1]) >= 1.0
