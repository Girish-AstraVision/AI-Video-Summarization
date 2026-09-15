import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import cv2

from app.services.video_service import get_upload_directory

logger = logging.getLogger(__name__)


class PreprocessingError(RuntimeError):
    """Base exception for preprocessing failures."""


class MissingVideoError(PreprocessingError):
    """Raised when the target video cannot be found."""


class InvalidVideoError(PreprocessingError):
    """Raised when the video file is unreadable or corrupted."""


class FFprobeError(PreprocessingError):
    """Raised when FFprobe fails to inspect the media."""


class FFmpegError(PreprocessingError):
    """Raised when FFmpeg fails to process media."""


class OpenCVError(PreprocessingError):
    """Raised when OpenCV cannot process the video frames."""


class VideoWithoutAudioError(PreprocessingError):
    """Raised when the input video does not contain audio."""


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_output_directory(video_id: str) -> Path:
    output_dir = get_project_root() / "outputs" / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_video_path_by_id(video_id: str) -> Path:
    upload_dir = get_upload_directory()
    candidates = sorted(upload_dir.glob(f"{video_id}.*"))
    if not candidates:
        raise MissingVideoError(f"No uploaded video found for video_id '{video_id}'.")

    video_path = candidates[0]
    if not video_path.is_file() or not video_path.exists():
        raise MissingVideoError(f"Uploaded video not found or not readable: {video_path}")

    return video_path


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output received."
        stdout = exc.stdout.strip() if exc.stdout else "No standard output received."
        raise FFprobeError(f"Command failed: {' '.join(command)}\nSTDOUT: {stdout}\nSTDERR: {stderr}") from exc


def get_video_metadata(video_path: Path) -> dict[str, Any]:
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate",
        "-of",
        "json",
        str(video_path),
    ]

    result = _run_command(ffprobe_cmd)
    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FFprobeError(f"FFprobe output could not be parsed as JSON for: {video_path}") from exc

    streams = probe_data.get("streams", [])
    format_data = probe_data.get("format", {})

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise InvalidVideoError(f"No video stream found in file: {video_path}")

    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fps_value = video_stream.get("avg_frame_rate")
    fps = 0.0
    if fps_value and fps_value != "0/0":
        try:
            numerator, denominator = fps_value.split("/")
            numerator_value = float(numerator)
            denominator_value = float(denominator)
            fps = numerator_value / denominator_value if denominator_value else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    metadata = {
        "duration": float(format_data.get("duration", 0.0) or 0.0),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "fps": fps,
        "video_codec": video_stream.get("codec_name"),
        "audio_present": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
    }

    return metadata


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "audio.wav"

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output received."
        stdout = exc.stdout.strip() if exc.stdout else "No standard output received."
        if "Output file #0 does not contain any stream" in stderr or "Stream map" in stderr:
            raise VideoWithoutAudioError(f"The video has no audio stream: {video_path}")
        raise FFmpegError(f"FFmpeg audio extraction failed for {video_path}\nSTDOUT: {stdout}\nSTDERR: {stderr}") from exc

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise FFmpegError(f"Audio extraction did not produce a valid output file: {audio_path}")

    return audio_path


def extract_frames(video_path: Path, output_dir: Path, frame_interval_seconds: float = 5.0) -> list[dict[str, Any]]:
    if frame_interval_seconds <= 0:
        raise ValueError("Frame interval must be greater than zero seconds.")

    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise InvalidVideoError(f"OpenCV could not open video: {video_path}")

    extracted: list[dict[str, Any]] = []
    frame_number = 0
    next_sample_time = 0.0

    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 1.0

        while True:
            success, frame = capture.read()
            if not success:
                break

            timestamp = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if timestamp >= next_sample_time:
                frame_number += 1
                file_name = f"frame_{frame_number:06d}.jpg"
                frame_path = frame_dir / file_name

                success_write = cv2.imwrite(str(frame_path), frame)
                if not success_write or not frame_path.exists() or frame_path.stat().st_size == 0:
                    raise OpenCVError(f"Failed to write extracted frame: {frame_path}")

                extracted.append(
                    {
                        "frame_number": frame_number,
                        "timestamp": round(float(timestamp), 4),
                        "image_path": str(frame_path),
                    }
                )
                next_sample_time += frame_interval_seconds

        if not extracted:
            raise OpenCVError(f"No frames could be extracted from video: {video_path}")

        return extracted
    except cv2.error as exc:
        raise OpenCVError(f"OpenCV frame extraction failed for {video_path}: {exc}") from exc
    finally:
        capture.release()


def preprocess_video(video_id: str, frame_interval_seconds: float = 5.0) -> dict[str, Any]:
    logger.info("Starting preprocessing for video_id=%s with frame interval %.2f seconds", video_id, frame_interval_seconds)

    video_path: Path | None = None
    try:
        video_path = get_video_path_by_id(video_id)
        if not video_path.exists() or not video_path.is_file():
            raise MissingVideoError(f"Video file is missing or unreadable: {video_path}")

        metadata = get_video_metadata(video_path)
        output_dir = get_output_directory(video_id)

        audio_path: Path | None = None
        warnings: list[str] = []
        if metadata.get("audio_present"):
            audio_path = extract_audio(video_path, output_dir)
        else:
            warnings.append("Video has no audio stream; no WAV file was generated.")
            logger.warning("Video %s does not contain audio stream.", video_id)

        frames = extract_frames(video_path, output_dir, frame_interval_seconds=frame_interval_seconds)

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps({"video_id": video_id, "metadata": metadata}, indent=2),
            encoding="utf-8",
        )

        result = {
            "video_id": video_id,
            "video_path": str(video_path),
            "metadata": metadata,
            "audio_path": str(audio_path) if audio_path else None,
            "extracted_frame_directory": str(output_dir / "frames"),
            "frame_timestamps": [frame["timestamp"] for frame in frames],
            "frame_count": len(frames),
            "preprocessing_status": "completed",
            "warnings": warnings,
            "details": {
                "frame_interval_seconds": frame_interval_seconds,
                "output_directory": str(output_dir),
                "metadata_path": str(metadata_path),
            },
        }

        logger.info("Preprocessing completed for video_id=%s, extracted %d frames", video_id, len(frames))
        return result
    except (MissingVideoError, InvalidVideoError, FFprobeError, FFmpegError, OpenCVError, VideoWithoutAudioError, ValueError) as exc:
        logger.exception("Preprocessing failed for video_id=%s", video_id)
        return {
            "video_id": video_id,
            "video_path": str(video_path) if video_path else None,
            "metadata": {},
            "audio_path": None,
            "extracted_frame_directory": None,
            "frame_timestamps": [],
            "frame_count": 0,
            "preprocessing_status": "failed",
            "warnings": [str(exc)],
            "details": {"error": str(exc)},
        }
    except Exception as exc:
        logger.exception("Unexpected preprocessing failure for video_id=%s", video_id)
        return {
            "video_id": video_id,
            "video_path": str(video_path) if video_path else None,
            "metadata": {},
            "audio_path": None,
            "extracted_frame_directory": None,
            "frame_timestamps": [],
            "frame_count": 0,
            "preprocessing_status": "failed",
            "warnings": [f"Unexpected preprocessing error: {exc}"],
            "details": {"error": str(exc)},
        }
