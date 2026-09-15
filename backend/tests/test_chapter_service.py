import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.chapter_service import (
    InvalidChapterRequestError,
    MissingChapterDataError,
    create_video_chapters,
    generate_chapters,
)


def _write_fixture(tmp_path: Path, video_id: str) -> None:
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "segments": [
                    {"start": 0.0, "end": 7.0, "text": "Introduction: a person walks near a car and traffic."},
                    {"start": 8.0, "end": 18.0, "text": "Main activity: a truck moves through the road with vehicles."},
                    {"start": 19.0, "end": 24.0, "text": "Important event: warning sign and emergency alert."},
                    {"start": 25.0, "end": 33.0, "text": "Conclusion: crowd and people gather near the station."},
                ],
            }
        ),
        encoding="utf-8",
    )

    (output_dir / "visual_detection.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "detections": [
                    {"frame_filename": "frame_000001.jpg", "timestamp": 2.0, "label": "person", "confidence": 0.9},
                    {"frame_filename": "frame_000001.jpg", "timestamp": 2.0, "label": "car", "confidence": 0.88},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 12.0, "label": "truck", "confidence": 0.96},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 20.0, "label": "warning", "confidence": 0.82},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 28.0, "label": "person", "confidence": 0.9},
                ],
            }
        ),
        encoding="utf-8",
    )

    (output_dir / "keyframes.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "selected_frames": [
                    {"frame_filename": "frame_000001.jpg", "timestamp": 2.0, "importance_score": 8.1, "detected_objects": ["person", "car"]},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 12.0, "importance_score": 7.9, "detected_objects": ["truck"]},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 20.0, "importance_score": 9.0, "detected_objects": ["warning"]},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 28.0, "importance_score": 6.6, "detected_objects": ["person"]},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_generate_chapters_normal_case(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 7.0, "text": "Introduction: a person walks near a car and traffic."},
        {"start": 8.0, "end": 18.0, "text": "Main activity: a truck moves through the road with vehicles."},
        {"start": 19.0, "end": 24.0, "text": "Important event: warning sign and emergency alert."},
        {"start": 25.0, "end": 33.0, "text": "Conclusion: crowd and people gather near the station."},
    ]
    detections = [
        {"timestamp": 2.0, "label": "person", "confidence": 0.9},
        {"timestamp": 12.0, "label": "truck", "confidence": 0.96},
        {"timestamp": 20.0, "label": "warning", "confidence": 0.82},
        {"timestamp": 28.0, "label": "person", "confidence": 0.9},
    ]
    keyframes = [
        {"frame_filename": "frame_000001.jpg", "timestamp": 2.0, "importance_score": 8.1},
        {"frame_filename": "frame_000003.jpg", "timestamp": 12.0, "importance_score": 7.9},
        {"frame_filename": "frame_000005.jpg", "timestamp": 20.0, "importance_score": 9.0},
    ]

    result = generate_chapters(video_id, max_chapters=5, transcript=transcript, detections=detections, keyframes=keyframes)

    assert result
    assert all(chapter["start_time"] < chapter["end_time"] for chapter in result)
    assert all(result[index]["chapter_number"] == index + 1 for index in range(len(result)))
    assert result[0]["title"]
    assert result[0]["summary"]


def test_generate_chapters_respects_max_chapters(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 5.0, "text": "One"},
        {"start": 5.0, "end": 10.0, "text": "Two"},
        {"start": 10.0, "end": 15.0, "text": "Three"},
        {"start": 15.0, "end": 20.0, "text": "Four"},
        {"start": 20.0, "end": 25.0, "text": "Five"},
    ]
    detections = [
        {"timestamp": 2.0, "label": "person", "confidence": 0.8},
        {"timestamp": 7.0, "label": "person", "confidence": 0.8},
        {"timestamp": 12.0, "label": "car", "confidence": 0.8},
        {"timestamp": 17.0, "label": "car", "confidence": 0.8},
        {"timestamp": 22.0, "label": "truck", "confidence": 0.8},
    ]

    result = generate_chapters(video_id, max_chapters=2, transcript=transcript, detections=detections, keyframes=[])

    assert len(result) <= 2


def test_generate_chapters_returns_fewer_when_data_is_sparse(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [{"start": 0.0, "end": 9.0, "text": "Only one meaningful section."}]
    detections = [{"timestamp": 4.0, "label": "person", "confidence": 0.9}]

    result = generate_chapters(video_id, max_chapters=5, transcript=transcript, detections=detections, keyframes=[])

    assert len(result) == 1


def test_generate_chapters_handles_short_video(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [{"start": 0.0, "end": 3.0, "text": "Short scene."}]
    detections = [{"timestamp": 1.0, "label": "person", "confidence": 0.8}]

    result = generate_chapters(video_id, max_chapters=5, transcript=transcript, detections=detections, keyframes=[])

    assert len(result) == 1
    assert result[0]["start_time"] == 0.0
    assert result[0]["end_time"] >= 3.0


def test_generate_chapters_uses_transcript_gaps(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 5.0, "text": "First segment."},
        {"start": 20.0, "end": 25.0, "text": "Second segment after a large gap."},
    ]
    detections = [
        {"timestamp": 2.0, "label": "person", "confidence": 0.8},
        {"timestamp": 22.0, "label": "vehicle", "confidence": 0.8},
    ]

    result = generate_chapters(video_id, max_chapters=5, transcript=transcript, detections=detections, keyframes=[])

    assert len(result) >= 2


def test_generate_chapters_tracks_visual_changes(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 10.0, "text": "Person appears."},
        {"start": 11.0, "end": 20.0, "text": "Vehicle appears."},
    ]
    detections = [
        {"timestamp": 2.0, "label": "person", "confidence": 0.9},
        {"timestamp": 15.0, "label": "truck", "confidence": 0.8},
    ]

    result = generate_chapters(video_id, max_chapters=5, transcript=transcript, detections=detections, keyframes=[])

    assert len(result) >= 2
    assert any("Person" in chapter["title"] or "Vehicle" in chapter["title"] for chapter in result)


def test_generate_chapters_includes_keyframe_integration(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [{"start": 0.0, "end": 10.0, "text": "Key segment with person and car."}]
    detections = [{"timestamp": 2.0, "label": "person", "confidence": 0.8}, {"timestamp": 3.0, "label": "car", "confidence": 0.9}]
    keyframes = [{"frame_filename": "frame_000001.jpg", "timestamp": 2.0, "importance_score": 8.7}]

    result = generate_chapters(video_id, max_chapters=2, transcript=transcript, detections=detections, keyframes=keyframes)

    assert result[0]["key_frames"]
    assert result[0]["key_frames"][0]["frame_filename"] == "frame_000001.jpg"


def test_generate_chapters_uses_summary_integration(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 6.0, "text": "Summary chapter one."},
        {"start": 7.0, "end": 14.0, "text": "Summary chapter two."},
    ]
    detections = [{"timestamp": 2.0, "label": "person", "confidence": 0.8}, {"timestamp": 9.0, "label": "car", "confidence": 0.8}]
    keyframes = []

    result = generate_chapters(video_id, max_chapters=2, transcript=transcript, detections=detections, keyframes=keyframes)

    assert len(result) == 2
    assert all(chapter["summary"] for chapter in result)


def test_generate_chapters_are_deterministic(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)
    transcript = [
        {"start": 0.0, "end": 5.0, "text": "Alpha beta gamma."},
        {"start": 6.0, "end": 10.0, "text": "Alpha beta gamma."},
        {"start": 11.0, "end": 15.0, "text": "Delta epsilon."},
    ]
    detections = [
        {"timestamp": 2.0, "label": "person", "confidence": 0.8},
        {"timestamp": 7.0, "label": "person", "confidence": 0.8},
        {"timestamp": 12.0, "label": "vehicle", "confidence": 0.9},
    ]

    result_a = generate_chapters(video_id, max_chapters=3, transcript=transcript, detections=detections, keyframes=[])
    result_b = generate_chapters(video_id, max_chapters=3, transcript=transcript, detections=detections, keyframes=[])

    assert result_a == result_b


def test_create_video_chapters_preserves_timestamp_integrity(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)

    with patch("app.services.chapter_service.get_project_root", return_value=tmp_path):
        result = create_video_chapters(video_id, max_chapters=3)

    assert result["video_id"] == video_id
    assert result["number_of_chapters"] >= 1
    assert all(chapter["start_time"] < chapter["end_time"] for chapter in result["chapters"])
    assert all(chapter["end_time"] >= chapter["start_time"] for chapter in result["chapters"])


def test_create_video_chapters_missing_required_data(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "transcript.json").write_text(json.dumps({"segments": []}), encoding="utf-8")

    with patch("app.services.chapter_service.get_project_root", return_value=tmp_path):
        with pytest.raises(MissingChapterDataError, match="Transcript"):
            create_video_chapters(video_id)


def test_create_video_chapters_invalid_max_chapters(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_fixture(tmp_path, video_id)

    with patch("app.services.chapter_service.get_project_root", return_value=tmp_path):
        with pytest.raises(InvalidChapterRequestError, match="max_chapters"):
            create_video_chapters(video_id, max_chapters=0)

        with pytest.raises(InvalidChapterRequestError, match="max_chapters"):
            create_video_chapters(video_id, max_chapters=11)
