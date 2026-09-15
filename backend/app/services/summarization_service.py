import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from app.services.keyframe_service import MissingKeyframeDataError, select_keyframes_for_video

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_LENGTH = "medium"
VALID_SUMMARY_LENGTHS = {
    "short": {"target_segments": 2, "max_segments": 3, "min_gap_seconds": 6.0},
    "medium": {"target_segments": 4, "max_segments": 6, "min_gap_seconds": 4.0},
    "long": {"target_segments": 6, "max_segments": 9, "min_gap_seconds": 3.0},
}
MIN_TARGET_DURATION_SECONDS = 1.0
MAX_TARGET_DURATION_SECONDS = 3600.0
IMPORTANT_KEYWORDS = {
    "important",
    "warning",
    "danger",
    "safety",
    "security",
    "fire",
    "accident",
    "traffic",
    "vehicle",
    "person",
    "crowd",
    "incident",
    "emergency",
    "road",
    "police",
    "alert",
    "critical",
    "inspection",
}


class SummarizationError(RuntimeError):
    """Base exception for summarization failures."""


class InvalidSummaryRequestError(SummarizationError):
    """Raised when input for summarization is invalid."""


class MissingSummaryDataError(SummarizationError):
    """Raised when required speech or visual data is absent."""


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_summary_length(summary_length: str | None) -> str:
    if summary_length is None:
        return DEFAULT_SUMMARY_LENGTH

    normalized = str(summary_length).strip().lower()
    if normalized not in VALID_SUMMARY_LENGTHS:
        allowed = ", ".join(sorted(VALID_SUMMARY_LENGTHS))
        raise InvalidSummaryRequestError(
            f"summary_length must be one of: {allowed}. Received '{summary_length}'."
        )
    return normalized


def validate_target_duration(target_duration: float | int | None) -> float | None:
    if target_duration is None:
        return None

    if isinstance(target_duration, bool) or not isinstance(target_duration, (int, float)):
        raise InvalidSummaryRequestError("target_duration must be a positive number of seconds.")

    duration_value = float(target_duration)
    if duration_value <= 0:
        raise InvalidSummaryRequestError("target_duration must be greater than 0 seconds.")
    if duration_value > MAX_TARGET_DURATION_SECONDS:
        raise InvalidSummaryRequestError(
            f"target_duration must be less than or equal to {MAX_TARGET_DURATION_SECONDS} seconds."
        )
    return duration_value


def _read_json(path: Path, description: str, video_id: str) -> dict[str, Any]:
    if not path.exists():
        raise MissingSummaryDataError(f"{description} not found for video_id '{video_id}'.")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MissingSummaryDataError(f"Could not parse {description} for video_id '{video_id}'.") from exc

    if not isinstance(payload, dict):
        raise MissingSummaryDataError(f"{description} for video_id '{video_id}' is not a valid JSON object.")

    return payload


def load_transcript_data(video_id: str) -> dict[str, Any]:
    transcript_path = get_project_root() / "outputs" / video_id / "transcript.json"
    transcript = _read_json(transcript_path, "Transcript data", video_id)
    segments = transcript.get("segments") or transcript.get("transcript_segments") or []
    if not isinstance(segments, list) or not segments:
        raise MissingSummaryDataError(f"Transcript segments are missing for video_id '{video_id}'.")
    return transcript


def load_visual_detection_data(video_id: str) -> list[dict[str, Any]]:
    detection_path = get_project_root() / "outputs" / video_id / "visual_detection.json"
    detection_payload = _read_json(detection_path, "Visual detection data", video_id)
    detections = detection_payload.get("detections", [])
    if not isinstance(detections, list) or not detections:
        raise MissingSummaryDataError(
            f"RT-DETR visual detection data is missing for video_id '{video_id}'."
        )
    return detections


def load_keyframe_data(video_id: str) -> list[dict[str, Any]]:
    keyframe_path = get_project_root() / "outputs" / video_id / "keyframes.json"
    if keyframe_path.exists():
        payload = _read_json(keyframe_path, "Key-frame data", video_id)
        selected_frames = payload.get("selected_frames") or payload.get("key_frames") or []
        if isinstance(selected_frames, list) and selected_frames:
            return selected_frames

    try:
        keyframe_payload = select_keyframes_for_video(video_id=video_id, num_keyframes=10)
    except (MissingKeyframeDataError, ValueError) as exc:
        raise MissingSummaryDataError(f"Key-frame data is missing or invalid for video_id '{video_id}'.") from exc

    selected_frames = keyframe_payload.get("selected_frames") or []
    if not isinstance(selected_frames, list) or not selected_frames:
        raise MissingSummaryDataError(f"Key-frame data is missing for video_id '{video_id}'.")
    return selected_frames


def load_moderation_events(video_id: str) -> list[dict[str, Any]]:
    moderation_path = get_project_root() / "outputs" / video_id / "moderation.json"
    if not moderation_path.exists():
        return []

    payload = _read_json(moderation_path, "Moderation events", video_id)
    events = payload.get("moderation_events") or payload.get("events") or []
    if not isinstance(events, list):
        return []
    return events


def _conversation_score(text: str) -> float:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return 0.0

    words = re.findall(r"[A-Za-z0-9']+", cleaned.lower())
    keyword_hits = sum(1 for word in words if word in IMPORTANT_KEYWORDS)
    word_count = max(len(words), 1)
    length_score = min(word_count / 12.0, 2.5)
    keyword_score = keyword_hits * 2.0
    return round(length_score + keyword_score, 4)


def _keyframe_timeline_boost(segment_start: float, segment_end: float, keyframes: list[dict[str, Any]]) -> float:
    if not keyframes:
        return 0.0

    boost = 0.0
    window = max(10.0, (segment_end - segment_start) + 5.0)
    midpoint = (segment_start + segment_end) / 2.0
    for keyframe in keyframes:
        try:
            timestamp = float(keyframe.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        distance = min(abs(timestamp - segment_start), abs(timestamp - segment_end), abs(timestamp - midpoint))
        if distance <= window:
            importance = float(keyframe.get("importance_score", 0.0) or 0.0)
            boost += importance * max(0.0, 1.0 - (distance / window))
    return round(boost, 4)


def _visual_detection_boost(segment_start: float, segment_end: float, detections: list[dict[str, Any]]) -> float:
    if not detections:
        return 0.0

    midpoint = (segment_start + segment_end) / 2.0
    boost = 0.0
    seen_labels: set[str] = set()
    confidence_total = 0.0
    count = 0

    for detection in detections:
        try:
            timestamp = float(detection.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        if timestamp < segment_start - 3.0 or timestamp > segment_end + 3.0:
            continue

        label = str(detection.get("label") or "").strip()
        if label:
            seen_labels.add(label)

        confidence = float(detection.get("confidence", 0.0) or 0.0)
        confidence_total += confidence
        count += 1
        boost += confidence * 1.5

    if count:
        boost += (confidence_total / max(count, 1)) * 1.25
        boost += len(seen_labels) * 0.75
        if abs(midpoint - 0.0) > 0.0:
            boost += 0.2

    return round(boost, 4)


def _moderation_boost(segment_start: float, segment_end: float, moderation_events: list[dict[str, Any]]) -> float:
    if not moderation_events:
        return 0.0

    boost = 0.0
    for event in moderation_events:
        try:
            event_time = float(event.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        if segment_start <= event_time <= segment_end:
            boost += 3.0
    return round(boost, 4)


def _temporal_position_score(segment_start: float, segment_end: float, video_duration: float) -> float:
    if video_duration <= 0:
        return 0.0

    midpoint = (segment_start + segment_end) / 2.0
    relative = midpoint / video_duration
    return round(max(0.0, 1.0 - abs(relative - 0.5) * 2.0) * 0.5, 4)


def _compute_segment_importance(
    segment: dict[str, Any],
    keyframes: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    moderation_events: list[dict[str, Any]],
    video_duration: float,
) -> float:
    start_time = float(segment.get("start", 0.0) or 0.0)
    end_time = float(segment.get("end", 0.0) or start_time)
    text = str(segment.get("text") or "")

    text_score = _conversation_score(text)
    keyframe_score = _keyframe_timeline_boost(start_time, end_time, keyframes)
    detection_score = _visual_detection_boost(start_time, end_time, detections)
    moderation_score = _moderation_boost(start_time, end_time, moderation_events)
    temporal_score = _temporal_position_score(start_time, end_time, video_duration)

    total_score = text_score + keyframe_score + detection_score + moderation_score + temporal_score
    return round(total_score, 4)


def _segment_duration(segment: dict[str, Any]) -> float:
    start_time = float(segment.get("start", 0.0) or 0.0)
    end_time = float(segment.get("end", start_time) or start_time)
    return max(0.0, end_time - start_time)


def _select_summary_segments(
    segments: list[dict[str, Any]],
    summary_length: str,
    target_duration: float | None,
    keyframes: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    moderation_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    if not segments:
        return [], 0.0

    config = VALID_SUMMARY_LENGTHS[summary_length]
    max_segments = config["max_segments"]
    min_gap_seconds = config["min_gap_seconds"]
    target_count = config["target_segments"]

    video_duration = max((segment.get("end", 0.0) or 0.0) for segment in segments)
    scored_segments: list[dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start_time = float(segment.get("start", 0.0) or 0.0)
        end_time = float(segment.get("end", start_time) or start_time)
        text = str(segment.get("text") or "").strip()
        if not text:
            continue

        importance = _compute_segment_importance(segment, keyframes, detections, moderation_events, video_duration)
        scored_segments.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
                "importance_score": importance,
            }
        )

    if not scored_segments:
        return [], 0.0

    scored_segments.sort(key=lambda item: (-item["importance_score"], item["start_time"]))
    selected: list[dict[str, Any]] = []

    for candidate in scored_segments:
        if any(abs(candidate["start_time"] - existing["start_time"]) < min_gap_seconds for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max_segments:
            break

    if len(selected) < target_count:
        for candidate in scored_segments:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) >= target_count:
                break

    if target_duration is not None:
        selected_duration = sum(_segment_duration(item) for item in selected)
        if selected_duration < target_duration * 0.9:
            for candidate in scored_segments:
                if candidate not in selected:
                    if all(abs(candidate["start_time"] - existing["start_time"]) >= min_gap_seconds for existing in selected):
                        selected.append(candidate)
                if len(selected) >= max_segments:
                    break
                if sum(_segment_duration(item) for item in selected) >= target_duration:
                    break

    selected.sort(key=lambda item: item["start_time"])
    actual_duration = 0.0
    if selected:
        coverage_end = -1.0
        for segment in selected:
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            if start_time > coverage_end:
                actual_duration += max(0.0, end_time - start_time)
                coverage_end = end_time
            else:
                actual_duration += max(0.0, end_time - coverage_end)
                coverage_end = max(coverage_end, end_time)

    return selected, round(actual_duration, 4)


def _select_summary_keyframes(keyframes: list[dict[str, Any]], selected_segments: list[dict[str, Any]], summary_length: str) -> list[dict[str, Any]]:
    desired_count = {"short": 2, "medium": 3, "long": 5}[summary_length]
    ranked = sorted(
        keyframes,
        key=lambda item: (-float(item.get("importance_score", 0.0) or 0.0), float(item.get("timestamp", 0.0) or 0.0)),
    )

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for keyframe in ranked:
        frame_filename = str(keyframe.get("frame_filename") or "")
        if not frame_filename or frame_filename in seen:
            continue

        timestamp = float(keyframe.get("timestamp", 0.0) or 0.0)
        if any(abs(timestamp - segment["start_time"]) <= 5.0 for segment in selected_segments):
            selected.append(keyframe)
            seen.add(frame_filename)
        if len(selected) >= desired_count:
            break

    if not selected:
        selected = ranked[:desired_count]

    return [
        {
            "frame_filename": str(item.get("frame_filename") or ""),
            "timestamp": float(item.get("timestamp", 0.0) or 0.0),
            "importance_score": float(item.get("importance_score", 0.0) or 0.0),
            "detected_objects": list(item.get("detected_objects") or []),
        }
        for item in selected[:desired_count]
    ]


def _render_summary_text(selected_segments: list[dict[str, Any]]) -> str:
    if not selected_segments:
        return "No significant segments were selected for this video summary."

    text_parts = [segment["text"] for segment in selected_segments]
    return " ".join(part.strip() for part in text_parts if part and part.strip())


def _important_events(selected_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for segment in sorted(selected_segments, key=lambda item: (-item["importance_score"], item["start_time"]))[:3]:
        events.append(
            {
                "timestamp": segment["start_time"],
                "label": "speech-highlight",
                "description": segment["text"],
                "severity": "medium",
            }
        )
    return events


def summarize_video(
    video_id: str,
    summary_length: str = DEFAULT_SUMMARY_LENGTH,
    target_duration: float | int | None = None,
) -> dict[str, Any]:
    if not video_id or not video_id.strip():
        raise InvalidSummaryRequestError("video_id must not be empty.")

    normalized_length = _normalize_summary_length(summary_length)
    validated_duration = validate_target_duration(target_duration)

    start_time = time.perf_counter()
    transcript = load_transcript_data(video_id)
    detection_data = load_visual_detection_data(video_id)
    keyframe_data = load_keyframe_data(video_id)
    moderation_events = load_moderation_events(video_id)

    segments = transcript.get("segments") or transcript.get("transcript_segments") or []
    selected_segments, actual_duration = _select_summary_segments(
        segments=segments,
        summary_length=normalized_length,
        target_duration=validated_duration,
        keyframes=keyframe_data,
        detections=detection_data,
        moderation_events=moderation_events,
    )

    final_segments = [
        {
            "start_time": float(segment["start_time"]),
            "end_time": float(segment["end_time"]),
            "text": str(segment["text"]),
            "importance_score": float(segment["importance_score"]),
        }
        for segment in selected_segments
    ]

    final_keyframes = _select_summary_keyframes(keyframe_data, selected_segments, normalized_length)
    summary_text = _render_summary_text(selected_segments)
    important_events = _important_events(selected_segments)

    result = {
        "video_id": video_id,
        "summary_length": normalized_length,
        "target_duration": validated_duration,
        "actual_summary_duration": actual_duration,
        "summary_text": summary_text,
        "number_of_segments": len(final_segments),
        "segments": final_segments,
        "key_frames": final_keyframes,
        "processing_time": round(time.perf_counter() - start_time, 4),
        "important_events": important_events,
    }

    logger.info(
        "Generated %s summary for video_id=%s with %d segments in %.4f seconds",
        normalized_length,
        video_id,
        len(final_segments),
        result["processing_time"],
    )
    return result
