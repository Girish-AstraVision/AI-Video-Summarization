from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.speech_to_text_service import (
    AudioNotFoundError,
    SpeechTranscriptionError,
    WhisperModelLoadError,
    transcribe_video_audio,
)


def _create_audio_file(audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(b"fake-audio")


def _make_segment(start: float, end: float, text: str) -> MagicMock:
    segment = MagicMock()
    segment.start = start
    segment.end = end
    segment.text = text
    return segment


def test_transcribe_video_audio_successfully_returns_segments(tmp_path: Path) -> None:
    video_id = "demo_video"
    audio_path = tmp_path / "outputs" / video_id / "audio" / "audio.wav"
    _create_audio_file(audio_path)

    fake_segments = [
        _make_segment(0.0, 2.5, "Hello world"),
        _make_segment(2.5, 6.1, "Second sentence"),
    ]
    fake_info = SimpleNamespace(language="en", language_probability=0.97)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (fake_segments, fake_info)

    with patch("app.services.speech_to_text_service.get_project_root", return_value=tmp_path):
        with patch("app.services.speech_to_text_service._load_model", return_value=fake_model):
            result = transcribe_video_audio(video_id)

    assert result["video_id"] == video_id
    assert result["audio_path"] == str(audio_path)
    assert result["model_name"] == "tiny"
    assert result["detected_language"] == "en"
    assert result["language_probability"] == 0.97
    assert result["number_of_segments"] == 2
    assert result["segments"][0] == {
        "segment_number": 1,
        "start": 0.0,
        "end": 2.5,
        "text": "Hello world",
    }
    assert result["segments"][1]["segment_number"] == 2
    assert result["segments"][1]["start"] == 2.5
    assert result["segments"][1]["end"] == 6.1
    assert result["processing_time"] >= 0.0


def test_transcribe_video_audio_raises_for_missing_audio(tmp_path: Path) -> None:
    video_id = "missing_audio_video"
    with patch("app.services.speech_to_text_service.get_project_root", return_value=tmp_path):
        with pytest.raises(AudioNotFoundError, match="Audio file not found"):
            transcribe_video_audio(video_id)


def test_transcribe_video_audio_raises_for_transcription_failure(tmp_path: Path) -> None:
    video_id = "demo_video"
    audio_path = tmp_path / "outputs" / video_id / "audio" / "audio.wav"
    _create_audio_file(audio_path)

    fake_model = MagicMock()
    fake_model.transcribe.side_effect = RuntimeError("transcribe failed")

    with patch("app.services.speech_to_text_service.get_project_root", return_value=tmp_path):
        with patch("app.services.speech_to_text_service._load_model", return_value=fake_model):
            with pytest.raises(SpeechTranscriptionError, match="Failed to transcribe audio"):
                transcribe_video_audio(video_id)


def test_transcribe_video_audio_uses_metadata_timestamps_from_faster_whisper(tmp_path: Path) -> None:
    video_id = "timestamped_video"
    audio_path = tmp_path / "outputs" / video_id / "audio" / "audio.wav"
    _create_audio_file(audio_path)

    fake_segments = [
        _make_segment(0.0, 3.0, "first"),
        _make_segment(3.0, 6.0, "second"),
        _make_segment(6.0, 9.0, "third"),
    ]
    fake_info = SimpleNamespace(language="en", language_probability=0.99)
    fake_model = MagicMock()
    fake_model.transcribe.return_value = (fake_segments, fake_info)

    with patch("app.services.speech_to_text_service.get_project_root", return_value=tmp_path):
        with patch("app.services.speech_to_text_service._load_model", return_value=fake_model):
            result = transcribe_video_audio(video_id)

    timestamps = [(segment["start"], segment["end"]) for segment in result["segments"]]
    assert timestamps == [(0.0, 3.0), (3.0, 6.0), (6.0, 9.0)]
    assert result["segments"][0]["text"] == "first"
    assert result["segments"][1]["text"] == "second"
    assert result["segments"][2]["text"] == "third"


def test_transcribe_video_audio_reuses_loaded_model_instance(tmp_path: Path) -> None:
    video_id = "cached_video"
    audio_path = tmp_path / "outputs" / video_id / "audio" / "audio.wav"
    _create_audio_file(audio_path)

    fake_model = MagicMock()
    fake_model.transcribe.return_value = (
        [_make_segment(0.0, 1.0, "hello")],
        SimpleNamespace(language="en", language_probability=0.90),
    )

    with patch("app.services.speech_to_text_service.get_project_root", return_value=tmp_path):
        with patch("app.services.speech_to_text_service.WhisperModel", return_value=fake_model) as mock_whisper_model:
            import app.services.speech_to_text_service as speech_service

            speech_service._model_instance = None
            first = transcribe_video_audio(video_id)
            second = transcribe_video_audio(video_id)

    assert mock_whisper_model.call_count == 1
    assert first["number_of_segments"] == 1
    assert second["number_of_segments"] == 1


def test_load_model_raises_model_load_error_when_init_fails(tmp_path: Path) -> None:
    import app.services.speech_to_text_service as speech_service

    speech_service._model_instance = None

    with patch("app.services.speech_to_text_service.WhisperModel", side_effect=RuntimeError("boom")):
        with pytest.raises(WhisperModelLoadError, match="Failed to load Whisper model"):
            speech_service._load_model(model_size="tiny")
