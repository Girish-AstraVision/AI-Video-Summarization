import json
import logging
import time
from pathlib import Path
from typing import Any

from app.services.video_service import get_project_root
from app.services.visual_detection_service import VideoFrameDetectionError, process_video_visual_detection

logger = logging.getLogger(__name__)

DEFAULT_KEYFRAME_COUNT = 5
MIN_KEYFRAME_COUNT = 1
MAX_KEYFRAME_COUNT = 20
MIN_TIME_GAP_SECONDS = 1.0


class KeyframeError(RuntimeError):
    """Base exception for key frame selection errors."""


class MissingKeyframeDataError(KeyframeError):
    """Raised when preprocessing or detection data is missing."""


class VisualDetectionRequiredError(KeyframeError):
    """Raised when RT-DETR results are required before key-frame selection."""


class InvalidKeyframeRequestError(KeyframeError):
    """Raised when a key-frame request is invalid."""


def _read_metadata(video_id: str) -> dict[str, Any]:
    metadata_path = get_project_root() / "outputs" / video_id / "metadata.json"
    if not metadata_path.exists():
        raise MissingKeyframeDataError(f"Preprocessing metadata not found for video_id '{video_id}'.")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MissingKeyframeDataError(f"Could not parse metadata.json for video_id '{video_id}'.") from exc

    return metadata


def _read_detection_results(video_id: str) -> dict[str, Any]:
    visual_detection_json = get_project_root() / "outputs" / video_id / "visual_detection.json"
    if visual_detection_json.exists():
        try:
            return json.loads(visual_detection_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MissingKeyframeDataError(f"Could not parse visual detection output for video_id '{video_id}'.") from exc

    try:
        return process_video_visual_detection(video_id=video_id)
    except (VideoFrameDetectionError, ValueError) as exc:
        raise VisualDetectionRequiredError(
            f"RT-DETR visual detection must be run before selecting key frames for video_id '{video_id}'."
        ) from exc


def _frame_rankings_by_filename(detections: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    frame_summary: dict[str, dict[str, Any]] = {}

    for detection in detections:
        frame_filename = detection.get("frame_filename")
        if not frame_filename:
            continue

        frame_entry = frame_summary.setdefault(
            frame_filename,
            {
                "frame_filename": frame_filename,
                "count": 0,
                "total_confidence": 0.0,
                "labels": set(),
            },
        )
        frame_entry["count"] += 1
        frame_entry["total_confidence"] += float(detection.get("confidence", 0.0) or 0.0)
        label = detection.get("label")
        if label:
            frame_entry["labels"].add(str(label))

    return frame_summary


def _compute_frame_importance(frame_filename: str, frame_timestamp: float, frame_summary: dict[str, Any]) -> float:
    if not frame_summary:
        return 0.0

    count = float(frame_summary.get("count", 0))
    average_confidence = float(frame_summary.get("total_confidence", 0.0) / max(count, 1))
    unique_labels = len(frame_summary.get("labels", set()))

    # Heuristic visual importance score; this is not an ML probability.
    score = (count * 1.5) + (average_confidence * 3.0) + (unique_labels * 1.25)
    if frame_timestamp is not None:
        score += 0.05 * max(0.0, 60.0 - abs(frame_timestamp))
    return round(score, 4)


def select_keyframes_for_video(
    video_id: str,
    num_keyframes: int = DEFAULT_KEYFRAME_COUNT,
) -> dict[str, Any]:
    if not video_id or not video_id.strip():
        raise InvalidKeyframeRequestError("video_id must not be empty.")
    if not isinstance(num_keyframes, int):
        raise InvalidKeyframeRequestError("num_keyframes must be an integer.")
    if num_keyframes < MIN_KEYFRAME_COUNT or num_keyframes > MAX_KEYFRAME_COUNT:
        raise InvalidKeyframeRequestError(
            f"num_keyframes must be between {MIN_KEYFRAME_COUNT} and {MAX_KEYFRAME_COUNT}."
        )

    start_time = time.perf_counter()

    try:
        metadata = _read_metadata(video_id)
        detections_result = _read_detection_results(video_id)
    except (MissingKeyframeDataError, VisualDetectionRequiredError):
        raise
    except Exception as exc:
        logger.exception("Failed to load preprocessing or detection data for video_id=%s", video_id)
        raise MissingKeyframeDataError(f"Key-frame data is missing or unreadable for video_id '{video_id}'.") from exc

    frame_details = metadata.get("frame_details") or metadata.get("frame_timestamps")
    if not isinstance(frame_details, list) or not frame_details:
        raise MissingKeyframeDataError(f"Preprocessing metadata for video_id '{video_id}' does not contain frame data.")

    detections = detections_result.get("detections", [])
    if not isinstance(detections, list) or not detections:
        raise VisualDetectionRequiredError(
            f"RT-DETR visual detection results are missing for video_id '{video_id}'. Run detection before selecting key frames."
        )

    frame_summary = _frame_rankings_by_filename(detections)
    candidate_frames: list[dict[str, Any]] = []

    for item in frame_details:
        if not isinstance(item, dict):
            continue

        frame_filename = item.get("frame_filename") or item.get("image_path")
        if not frame_filename:
            continue
        if isinstance(frame_filename, str):
            frame_name = Path(frame_filename).name
        else:
            frame_name = str(frame_filename)

        if not frame_name:
            continue

        timestamp = item.get("timestamp")
        score = _compute_frame_importance(frame_name, float(timestamp) if timestamp is not None else 0.0, frame_summary.get(frame_name))
        detected_objects = sorted(frame_summary.get(frame_name, {}).get("labels", set()))

        candidate_frames.append(
            {
                "frame_filename": frame_name,
                "timestamp": float(timestamp) if timestamp is not None else 0.0,
                "importance_score": score,
                "detected_objects": detected_objects,
            }
        )

    if not candidate_frames:
        raise MissingKeyframeDataError(f"No frame metadata available for video_id '{video_id}'.")

    ranked = sorted(candidate_frames, key=lambda item: (-item["importance_score"], item["timestamp"]))
    selected: list[dict[str, Any]] = []

    for candidate in ranked:
        if not selected:
            selected.append(candidate)
            continue

        if all(abs(candidate["timestamp"] - selected_item["timestamp"]) >= MIN_TIME_GAP_SECONDS for selected_item in selected):
            selected.append(candidate)

        if len(selected) >= num_keyframes:
            break

    if not selected:
        selected = [ranked[0]]

    if len(selected) < num_keyframes:
        for candidate in ranked:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) >= num_keyframes:
                break

    selected = selected[:num_keyframes]
    result = {
        "video_id": video_id,
        "total_frames_analyzed": len(candidate_frames),
        "selected_frames": selected,
        "number_selected": len(selected),
        "processing_time": round(time.perf_counter() - start_time, 4),
    }

    logger.info(
        "Selected %d key frames for video_id=%s from %d analyzed frames in %.4f seconds",
        len(selected),
        video_id,
        len(candidate_frames),
        result["processing_time"],
    )
    return result
