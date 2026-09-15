import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.preprocessing_service import preprocess_video


def configure_test_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.services.preprocessing_service.get_upload_directory", lambda: uploads_dir)
    monkeypatch.setattr("app.services.preprocessing_service.get_project_root", lambda: tmp_path)
    return uploads_dir, outputs_dir


def create_synthetic_video(
    video_path: Path,
    *,
    width: int = 320,
    height: int = 240,
    fps: int = 10,
    duration: float = 1.5,
    with_audio: bool = True,
) -> None:
    if with_audio:
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size={width}x{height}:rate={fps}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1000:duration={duration}",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(video_path),
        ]
    else:
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size={width}x{height}:rate={fps}",
            "-t",
            str(duration),
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            str(video_path),
        ]

    subprocess.run(command, check=True, capture_output=True, text=True)


def test_preprocess_video_returns_failure_for_missing_video_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configure_test_runtime(monkeypatch, tmp_path)

    result = preprocess_video("missing_video_id_123")

    assert result["video_id"] == "missing_video_id_123"
    assert result["preprocessing_status"] == "failed"
    assert result["frame_count"] == 0
    assert result["warnings"]
    assert "No uploaded video found" in result["warnings"][0]


def test_preprocess_video_handles_corrupted_video(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    corrupted_video = uploads_dir / "corrupted.mp4"
    corrupted_video.write_bytes(b"this is not a valid video file")

    result = preprocess_video("corrupted")

    assert result["video_id"] == "corrupted"
    assert result["preprocessing_status"] == "failed"
    assert result["frame_count"] == 0
    assert result["warnings"]


def test_preprocess_video_extracts_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    video_path = uploads_dir / "metadata_test.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, duration=1.5, with_audio=True)

    result = preprocess_video(video_path.stem, frame_interval_seconds=0.5)

    assert result["preprocessing_status"] == "completed"
    metadata = result["metadata"]
    assert metadata["audio_present"] is True
    assert metadata["width"] == 320
    assert metadata["height"] == 240
    assert metadata["fps"] > 0
    assert metadata["video_codec"] == "h264"
    assert metadata["audio_codec"] == "aac"
    assert metadata["duration"] > 0


def test_preprocess_video_extracts_audio_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    video_path = uploads_dir / "audio_test.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=12, duration=1.0, with_audio=True)

    result = preprocess_video(video_path.stem, frame_interval_seconds=1.0)

    assert result["preprocessing_status"] == "completed"
    assert result["audio_path"] is not None
    audio_path = Path(result["audio_path"])
    assert audio_path.exists()
    assert audio_path.name == "audio.wav"

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=sample_rate,channels,codec_name",
            "-of",
            "json",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    probe_data = json.loads(probe.stdout)
    assert probe_data["streams"][0]["sample_rate"] == "16000"
    assert probe_data["streams"][0]["channels"] == 1


def test_preprocess_video_without_audio_returns_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    video_path = uploads_dir / "silent_test.mp4"
    create_synthetic_video(video_path, width=240, height=180, fps=8, duration=1.0, with_audio=False)

    result = preprocess_video(video_path.stem, frame_interval_seconds=0.5)

    assert result["preprocessing_status"] == "completed"
    assert result["metadata"]["audio_present"] is False
    assert result["audio_path"] is None
    assert result["warnings"]
    assert "no audio" in " ".join(result["warnings"]).lower()


def test_preprocess_video_extracts_frames_and_timestamps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    video_path = uploads_dir / "frame_test.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, duration=1.0, with_audio=True)

    result = preprocess_video(video_path.stem, frame_interval_seconds=0.5)

    assert result["preprocessing_status"] == "completed"
    assert result["frame_count"] > 0
    assert result["frame_timestamps"]
    assert result["frame_timestamps"] == sorted(result["frame_timestamps"])

    frames_dir = Path(result["extracted_frame_directory"])
    assert frames_dir.exists()
    assert len(list(frames_dir.glob("*.jpg"))) == result["frame_count"]


def test_preprocess_video_creates_expected_output_structure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    uploads_dir, _ = configure_test_runtime(monkeypatch, tmp_path)

    video_path = uploads_dir / "output_structure_test.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, duration=1.0, with_audio=True)

    result = preprocess_video(video_path.stem, frame_interval_seconds=0.5)
    output_root = Path(result["details"]["output_directory"])

    assert output_root.exists()
    assert (output_root / "audio").is_dir()
    assert (output_root / "frames").is_dir()
    assert (output_root / "metadata.json").exists()
    assert (output_root / "audio" / "audio.wav").exists()


def test_preprocess_api_successful_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configure_test_runtime(monkeypatch, tmp_path)
    client = TestClient(app)

    uploads_dir = tmp_path / "uploads"
    video_path = uploads_dir / "api_success.mp4"
    create_synthetic_video(video_path, width=320, height=240, fps=10, duration=1.0, with_audio=True)

    response = client.post(f"/api/videos/{video_path.stem}/preprocess")

    assert response.status_code == 200
    payload = response.json()
    assert payload["video_id"] == video_path.stem
    assert payload["preprocessing_status"] == "completed"
    assert payload["frame_count"] > 0


def test_preprocess_api_missing_video_returns_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configure_test_runtime(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post("/api/videos/missing_video_test/preprocess")

    assert response.status_code == 400
    payload = response.json()
    assert "detail" in payload
    assert "No uploaded video found" in payload["detail"]
