from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.speech_to_text_service import (
    AudioNotFoundError,
    SpeechTranscriptionError,
)

client = TestClient(app)


def test_transcribe_route_returns_transcript_result() -> None:
    mocked_result = {
        "video_id": "demo_video",
        "audio_path": "/tmp/demo_video/audio/audio.wav",
        "model_name": "tiny",
        "detected_language": "en",
        "language_probability": 0.97,
        "number_of_segments": 2,
        "segments": [
            {
                "segment_number": 1,
                "start": 0.0,
                "end": 2.5,
                "text": "Hello world",
            },
            {
                "segment_number": 2,
                "start": 2.5,
                "end": 6.1,
                "text": "Second sentence",
            },
        ],
        "processing_time": 0.12,
    }

    with patch("app.api.routes.speech_to_text.transcribe_video_audio", return_value=mocked_result) as mock_service:
        response = client.post("/api/videos/demo_video/transcribe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["video_id"] == "demo_video"
    assert payload["number_of_segments"] == 2
    assert payload["segments"][0]["text"] == "Hello world"
    mock_service.assert_called_once_with(video_id="demo_video")


def test_transcribe_route_handles_missing_audio() -> None:
    with patch(
        "app.api.routes.speech_to_text.transcribe_video_audio",
        side_effect=AudioNotFoundError("Audio file not found for video_id 'missing_video': /tmp/missing_video/audio/audio.wav"),
    ):
        response = client.post("/api/videos/missing_video/transcribe")

    assert response.status_code == 404
    assert "Audio file not found" in response.json()["detail"]


def test_transcribe_route_handles_transcription_failure() -> None:
    with patch(
        "app.api.routes.speech_to_text.transcribe_video_audio",
        side_effect=SpeechTranscriptionError("Failed to transcribe audio for video_id 'demo_video'."),
    ):
        response = client.post("/api/videos/demo_video/transcribe")

    assert response.status_code == 400
    assert "Failed to transcribe audio" in response.json()["detail"]


def test_transcribe_route_handles_model_load_error() -> None:
    with patch(
        "app.api.routes.speech_to_text.transcribe_video_audio",
        side_effect=RuntimeError("Failed to load Whisper model 'tiny' on device 'cpu'."),
    ):
        response = client.post("/api/videos/demo_video/transcribe")

    assert response.status_code == 500
    assert "Failed to load Whisper model" in response.json()["detail"]
