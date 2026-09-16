import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.summarization_service import (
    InvalidSummaryRequestError,
    MissingSummaryDataError,
    summarize_video,
)


def _write_summary_fixture(tmp_path: Path, video_id: str) -> None:
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "segments": [
                    {"start": 0.0, "end": 6.0, "text": "A person walks near a car and a traffic signal."},
                    {"start": 12.0, "end": 16.0, "text": "A truck is moving quickly on the road."},
                    {"start": 22.0, "end": 27.0, "text": "The warning system indicates danger in the area."},
                    {"start": 44.0, "end": 50.0, "text": "A crowd gathers near the station."},
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
                    {"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "label": "person", "confidence": 0.9},
                    {"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "label": "car", "confidence": 0.8},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 12.0, "label": "truck", "confidence": 0.96},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 22.0, "label": "warning", "confidence": 0.88},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 44.0, "label": "person", "confidence": 0.91},
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
                    {"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 8.1, "detected_objects": ["person", "car"]},
                    {"frame_filename": "frame_000003.jpg", "timestamp": 12.0, "importance_score": 7.6, "detected_objects": ["truck"]},
                    {"frame_filename": "frame_000005.jpg", "timestamp": 22.0, "importance_score": 9.3, "detected_objects": ["warning"]},
                    {"frame_filename": "frame_000010.jpg", "timestamp": 44.0, "importance_score": 6.7, "detected_objects": ["person"]},
                ],
            }
        )
    )


def test_summarization_service_short_summary(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="short")

    assert result["video_id"] == video_id
    assert result["summary_length"] == "short"
    assert result["number_of_segments"] <= 3
    assert result["summary_text"]
    assert result["segments"][0]["start_time"] <= result["segments"][-1]["start_time"]


def test_summarization_service_medium_summary(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="medium")

    assert result["summary_length"] == "medium"
    assert 1 <= result["number_of_segments"] <= 6
    assert result["actual_summary_duration"] >= 0.0
    assert any(segment["importance_score"] > 0 for segment in result["segments"])


def test_summarization_service_long_summary(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="long")

    assert result["summary_length"] == "long"
    assert result["number_of_segments"] >= 1
    assert result["key_frames"]


def test_summarization_service_respects_target_duration(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="medium", target_duration=25)

    assert result["target_duration"] == 25
    assert result["actual_summary_duration"] <= 25 + 1.0


def test_summarization_service_preserves_timestamp_integrity(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="long")

    assert any(segment["start_time"] == 22.0 for segment in result["segments"])
    assert any(keyframe["timestamp"] == 22.0 for keyframe in result["key_frames"])


def test_summarization_service_scores_importance_and_avoids_duplicates(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="medium")

    assert all(segment["importance_score"] >= 0 for segment in result["segments"])
    selected_starts = [segment["start_time"] for segment in result["segments"]]
    gaps = [abs(b - a) for a, b in zip(selected_starts, selected_starts[1:])]
    assert all(gap >= 3.0 for gap in gaps if gap)


def test_summarization_service_includes_keyframes_from_visual_data(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id, summary_length="medium")

    assert result["key_frames"]
    assert all("frame_filename" in keyframe for keyframe in result["key_frames"])
    assert all("detected_objects" in keyframe for keyframe in result["key_frames"])


def test_summarization_service_raises_for_missing_transcript(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "visual_detection.json").write_text(json.dumps({"detections": [{"timestamp": 1.0, "label": "car", "confidence": 0.8}]}), encoding="utf-8")
    (output_dir / "keyframes.json").write_text(json.dumps({"selected_frames": [{"frame_filename": "frame_001.jpg", "timestamp": 1.0, "importance_score": 4.0, "detected_objects": ["car"]}]}), encoding="utf-8")

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        with pytest.raises(MissingSummaryDataError, match="Transcript"):
            summarize_video(video_id=video_id)


def test_summarization_service_allows_fallback_when_keyframe_data_missing(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "transcript.json").write_text(json.dumps({"segments": [{"start": 0.0, "end": 2.0, "text": "Hello there."}]}), encoding="utf-8")
    (output_dir / "visual_detection.json").write_text(json.dumps({"detections": [{"timestamp": 1.0, "label": "car", "confidence": 0.8}]}), encoding="utf-8")

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        result = summarize_video(video_id=video_id)

    assert result["video_id"] == video_id
    assert result["summary_text"]


def test_summarization_service_rejects_invalid_summary_length(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)
    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        with pytest.raises(InvalidSummaryRequestError, match="summary_length"):
            summarize_video(video_id=video_id, summary_length="invalid")


def test_summarization_service_rejects_invalid_target_duration(tmp_path: Path) -> None:
    video_id = "demo_video"
    _write_summary_fixture(tmp_path, video_id)
    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        with pytest.raises(InvalidSummaryRequestError, match="target_duration"):
            summarize_video(video_id=video_id, target_duration=0)

        with pytest.raises(InvalidSummaryRequestError, match="target_duration"):
            summarize_video(video_id=video_id, target_duration=-1)

        with pytest.raises(InvalidSummaryRequestError, match="target_duration"):
            summarize_video(video_id=video_id, target_duration=5000)


def test_summarization_service_falls_back_to_transcription_when_transcript_missing(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "visual_detection.json").write_text(
        json.dumps(
            {"video_id": video_id, "detections": [{"timestamp": 0.0, "label": "person", "confidence": 0.9}]}
        ),
        encoding="utf-8",
    )
    (output_dir / "keyframes.json").write_text(
        json.dumps(
            {
                "video_id": video_id,
                "selected_frames": [
                    {
                        "frame_filename": "frame_000001.jpg",
                        "timestamp": 0.0,
                        "importance_score": 8.1,
                        "detected_objects": ["person"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "moderation.json").write_text(json.dumps({"moderation_events": []}), encoding="utf-8")

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path), patch(
        "app.services.summarization_service.transcribe_video_audio",
        return_value={
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "A person walks near a car and a warning sign."},
                {"start": 8.0, "end": 12.0, "text": "A truck is moving quickly on the road."},
            ]
        },
    ) as mock_transcribe:
        result = summarize_video(video_id=video_id, summary_length="short")

    assert result["video_id"] == video_id
    assert result["summary_length"] == "short"
    assert result["summary_text"]
    assert result["number_of_segments"] >= 1
    mock_transcribe.assert_called_once_with(video_id=video_id)


def test_summarization_service_rejects_unknown_video_id(tmp_path: Path) -> None:
    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            summarize_video(video_id="unknown_video")


def test_summarization_service_persists_transcript_after_fallback(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "visual_detection.json").write_text(
        json.dumps({"video_id": video_id, "detections": [{"timestamp": 0.0, "label": "person", "confidence": 0.9}]}),
        encoding="utf-8",
    )
    (output_dir / "keyframes.json").write_text(
        json.dumps({"video_id": video_id, "selected_frames": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 8.1, "detected_objects": ["person"]}]}),
        encoding="utf-8",
    )
    (output_dir / "moderation.json").write_text(json.dumps({"moderation_events": []}), encoding="utf-8")

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path), patch(
        "app.services.summarization_service.transcribe_video_audio",
        return_value={
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "A person walks near a car and a warning sign."},
            ]
        },
    ) as mock_transcribe:
        first = summarize_video(video_id=video_id, summary_length="short")
        second = summarize_video(video_id=video_id, summary_length="medium")

    assert first["summary_text"]
    assert second["summary_text"]
    assert (output_dir / "transcript.json").exists()
    assert (output_dir / "transcript.json").read_text(encoding="utf-8")
    assert mock_transcribe.call_count == 1


def test_summarization_service_reuses_cached_visual_detection_and_keyframes(tmp_path: Path) -> None:
    video_id = "demo_video"
    output_dir = tmp_path / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_payload = {
        "video_id": video_id,
        "segments": [
            {"start": 0.0, "end": 10.0, "text": "A person walks near a car and a warning signal."},
            {"start": 15.0, "end": 20.0, "text": "A truck moves quickly on the road."},
        ],
    }
    (output_dir / "transcript.json").write_text(json.dumps(transcript_payload), encoding="utf-8")
    detection_payload = {"video_id": video_id, "detections": [{"timestamp": 0.0, "label": "person", "confidence": 0.9}]}
    keyframe_payload = {"video_id": video_id, "selected_frames": [{"frame_filename": "frame_000001.jpg", "timestamp": 0.0, "importance_score": 8.1, "detected_objects": ["person"]}]}
    (output_dir / "visual_detection.json").write_text(json.dumps(detection_payload), encoding="utf-8")
    (output_dir / "keyframes.json").write_text(json.dumps(keyframe_payload), encoding="utf-8")

    with patch("app.services.summarization_service.get_project_root", return_value=tmp_path), patch(
        "app.services.summarization_service.process_video_visual_detection"
    ) as mock_detection, patch("app.services.summarization_service.select_keyframes_for_video") as mock_keyframes:
        summarize_video(video_id=video_id, summary_length="short")
        summarize_video(video_id=video_id, summary_length="long")

    mock_detection.assert_not_called()
    mock_keyframes.assert_not_called()
