import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.event_timeline_service import (
    InvalidTimelineRequestError,
    MissingTimelineDataError,
    create_event_timeline,
)


def _write_timeline_fixture(tmp_path: Path, video_id: str) -> None:
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "visual_detection.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "detections": [
                    {"frame_filename": "frame_000001.jpg", "timestamp": 10.0, "label": "person", "confidence": 0.91},
                    {"frame_filename": "frame_000002.jpg", "timestamp": 10.0, "label": "person", "confidence": 0.88},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 15.0, "label": "person", "confidence": 0.87},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 20.0, "label": "car", "confidence": 0.82},
                    {"frame_filename": "frame_000011.jpg", "timestamp": 20.5, "label": "car", "confidence": 0.81},
                ],
            }
        ),
        encoding="utf-8",
    )

    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "segments": [
                    {"start": 9.0, "end": 13.0, "text": "A person is visible."},
                    {"start": 19.0, "end": 24.0, "text": "A car is moving on the road."},
                ],
            }
        ),
        encoding="utf-8",
    )

    (output_dir / "moderation.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "moderation_events": [
                    {"timestamp": 20.0, "end_time": 22.0, "category": "offensive_language", "severity": "medium", "confidence": 0.75, "message": "Contains mild profanity."},
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
                    {"frame_filename": "frame_000001.jpg", "timestamp": 10.0, "importance_score": 7.8, "detected_objects": ["person"]},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 20.0, "importance_score": 8.1, "detected_objects": ["car"]},
                ],
            }
        ),
        encoding="utf-8",
    )

    (output_dir / "chapters.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "chapters": [
                    {"chapter_number": 1, "start_time": 0.0, "end_time": 15.0, "title": "Introduction", "summary": "Initial activity and presence."},
                    {"chapter_number": 2, "start_time": 15.0, "end_time": 30.0, "title": "Vehicle Activity", "summary": "Vehicle movement continues."},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_create_event_timeline_includes_all_sources(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    assert result["video_id"] == video_id
    assert result["total_events"] > 0
    assert {event["event_type"] for event in result["events"]} >= {"visual", "speech", "moderation", "key_frame", "chapter"}
    assert all(result["events"][index]["timestamp"] <= result["events"][index + 1]["timestamp"] for index in range(len(result["events"]) - 1))


def test_create_event_timeline_visual_events_are_normalized(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    visual_events = [event for event in result["events"] if event["event_type"] == "visual"]
    assert visual_events
    assert all("person" in event["description"].lower() or "car" in event["description"].lower() for event in visual_events)


def test_create_event_timeline_speech_events_are_normalized(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    speech_events = [event for event in result["events"] if event["event_type"] == "speech"]
    assert speech_events
    assert any("person" in event["description"].lower() for event in speech_events)


def test_create_event_timeline_moderation_events_are_normalized(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    moderation_events = [event for event in result["events"] if event["event_type"] == "moderation"]
    assert moderation_events
    assert moderation_events[0]["metadata"]["category"] == "offensive_language"


def test_create_event_timeline_keyframe_events_are_normalized(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    keyframe_events = [event for event in result["events"] if event["event_type"] == "key_frame"]
    assert keyframe_events
    assert all("frame" in event["description"].lower() for event in keyframe_events)


def test_create_event_timeline_chapter_events_are_normalized(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    chapter_events = [event for event in result["events"] if event["event_type"] == "chapter"]
    assert chapter_events
    assert any("Introduction" in event["description"] or "Vehicle" in event["description"] for event in chapter_events)


def test_create_event_timeline_sorts_chronologically_and_keeps_timestamps(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    timestamps = [event["timestamp"] for event in result["events"]]
    assert timestamps == sorted(timestamps)
    assert any(timestamp == 10.0 for timestamp in timestamps)
    assert any(timestamp == 20.0 for timestamp in timestamps)


def test_create_event_timeline_handles_duplicate_visual_events(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    visual_events = [event for event in result["events"] if event["event_type"] == "visual"]
    assert visual_events
    assert len(visual_events) <= 4


def test_create_event_timeline_builds_multimodal_fusion(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id)

    assert any(event["event_type"] == "multimodal" for event in result["events"])


def test_create_event_timeline_respects_include_filters(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id, include_visual=False, include_speech=False, include_moderation=False, include_keyframes=False, include_chapters=False)

    assert result["events"] == []
    assert result["total_events"] == 0


def test_create_event_timeline_all_filters_disabled_returns_empty(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        result = create_event_timeline(video_id=video_id, include_visual=False, include_speech=False, include_moderation=False, include_keyframes=False, include_chapters=False)

    assert result["total_events"] == 0
    assert result["events"] == []


def test_create_event_timeline_missing_required_data(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        with pytest.raises(MissingTimelineDataError, match="Visual detection data"):
            create_event_timeline(video_id=video_id)


def test_create_event_timeline_is_deterministic(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_timeline_fixture(tmp_path, video_id)

    with patch("app.services.event_timeline_service.get_project_root", return_value=tmp_path):
        first = create_event_timeline(video_id=video_id)
        second = create_event_timeline(video_id=video_id)

    assert first == second


def test_create_event_timeline_rejects_invalid_video_id() -> None:
    with pytest.raises(InvalidTimelineRequestError, match="video_id"):
        create_event_timeline(video_id="  ")
