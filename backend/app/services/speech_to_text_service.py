import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

DEFAULT_MODEL_SIZE = "tiny"
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"

_model_instance: WhisperModel | None = None


class SpeechToTextError(RuntimeError):
    """Base exception for speech-to-text failures."""


class AudioNotFoundError(SpeechToTextError):
    """Raised when the expected audio file for a video is missing."""


class InvalidAudioError(SpeechToTextError):
    """Raised when the expected audio is unreadable or empty."""


class WhisperModelLoadError(SpeechToTextError):
    """Raised when the Whisper model cannot be initialized."""


class SpeechTranscriptionError(SpeechToTextError):
    """Raised when audio transcription fails."""


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_audio_path_for_video(video_id: str) -> Path:
    audio_path = get_project_root() / "outputs" / video_id / "audio" / "audio.wav"
    if not audio_path.exists() or not audio_path.is_file():
        raise AudioNotFoundError(f"Audio file not found for video_id '{video_id}': {audio_path}")
    if audio_path.stat().st_size <= 0:
        raise InvalidAudioError(f"Audio file is empty for video_id '{video_id}': {audio_path}")
    return audio_path


def _load_model(
    model_size: str = DEFAULT_MODEL_SIZE,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> WhisperModel:
    global _model_instance

    if _model_instance is None:
        try:
            logger.info(
                "Loading Whisper model '%s' on device '%s' with compute type '%s'",
                model_size,
                device,
                compute_type,
            )
            _model_instance = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as exc:  # pragma: no cover - exercised through unit tests with mocks
            raise WhisperModelLoadError(
                f"Failed to load Whisper model '{model_size}' on device '{device}'."
            ) from exc

    return _model_instance


def transcribe_video_audio(
    video_id: str,
    model_size: str = DEFAULT_MODEL_SIZE,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> dict[str, Any]:
    start_time = time.perf_counter()
    audio_path = get_audio_path_for_video(video_id)

    try:
        model = _load_model(model_size=model_size, device=device, compute_type=compute_type)
        logger.info("Starting transcription for video_id=%s using %s", video_id, model_size)

        segments, info = model.transcribe(str(audio_path), beam_size=5)
        segment_list = list(segments)

        structured_segments = [
            {
                "segment_number": index + 1,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": str(segment.text).strip(),
            }
            for index, segment in enumerate(segment_list)
        ]

        processing_time = time.perf_counter() - start_time
        result = {
            "video_id": video_id,
            "audio_path": str(audio_path),
            "model_name": model_size,
            "detected_language": getattr(info, "language", None),
            "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
            "number_of_segments": len(structured_segments),
            "segments": structured_segments,
            "processing_time": round(processing_time, 4),
        }

        logger.info(
            "Completed transcription for video_id=%s in %.4f seconds with %d segments",
            video_id,
            processing_time,
            len(structured_segments),
        )
        return result
    except (AudioNotFoundError, InvalidAudioError, WhisperModelLoadError):
        logger.exception("Speech-to-text failed for video_id=%s", video_id)
        raise
    except Exception as exc:
        logger.exception("Unexpected speech transcription failure for video_id=%s", video_id)
        raise SpeechTranscriptionError(f"Failed to transcribe audio for video_id '{video_id}'.") from exc
