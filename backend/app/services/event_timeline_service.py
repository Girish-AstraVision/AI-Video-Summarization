import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_VISUAL_WINDOW_SECONDS = 3.0
DEFAULT_FUSION_WINDOW_SECONDS = 2.5


class EventTimelineError(RuntimeError):
    """Base exception for event timeline errors."""


class InvalidTimelineRequestError(EventTimelineError):
    """Raised when request data is invalid."""


class MissingTimelineDataError(EventTimelineError):
    """Raised when required analysis data is missing."""


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path, description: str, video_id: str) -> dict[str, Any]:
    if not path.exists():
        raise MissingTimelineDataError(f"{description} not found for video_id '{video_id}'.")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MissingTimelineDataError(f"Could not parse {description} for video_id '{video_id}'.") from exc

    if not isinstance(payload, dict):
        raise MissingTimelineDataError(f"{description} for video_id '{video_id}' is not a valid JSON object.")

    return payload


def load_visual_detection_data(video_id: str) -> list[dict[str, Any]]:
    detection_path = get_project_root() / "outputs" / video_id / "visual_detection.json"
    payload = _read_json(detection_path, "Visual detection data", video_id)
    detections = payload.get("detections", [])
    if not isinstance(detections, list) or not detections:
        raise MissingTimelineDataError(f"RT-DETR visual detection data is missing for video_id '{video_id}'.")
    return detections


def load_transcript_data(video_id: str) -> list[dict[str, Any]]:
    transcript_path = get_project_root() / "outputs" / video_id / "transcript.json"
    payload = _read_json(transcript_path, "Transcript data", video_id)
    segments = payload.get("segments") or payload.get("transcript_segments") or []
    if not isinstance(segments, list) or not segments:
        raise MissingTimelineDataError(f"Whisper transcript data is missing for video_id '{video_id}'.")
    return segments


def load_moderation_data(video_id: str) -> list[dict[str, Any]]:
    moderation_path = get_project_root() / "outputs" / video_id / "moderation.json"
    if not moderation_path.exists():
        return []

    payload = _read_json(moderation_path, "Moderation data", video_id)
    events = payload.get("moderation_events") or payload.get("events") or []
    if not isinstance(events, list):
        return []
    return events


def load_keyframe_data(video_id: str) -> list[dict[str, Any]]:
    keyframe_path = get_project_root() / "outputs" / video_id / "keyframes.json"
    if not keyframe_path.exists():
        return []

    payload = _read_json(keyframe_path, "Key-frame data", video_id)
    frames = payload.get("selected_frames") or payload.get("key_frames") or []
    if not isinstance(frames, list):
        return []
    return frames


def load_chapter_data(video_id: str) -> list[dict[str, Any]]:
    chapter_path = get_project_root() / "outputs" / video_id / "chapters.json"
    if not chapter_path.exists():
        return []

    payload = _read_json(chapter_path, "Chapter data", video_id)
    chapters = payload.get("chapters", [])
    if not isinstance(chapters, list):
        return []
    return chapters


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-")
    return value.lower() if value else "event"


def _normalize_visual_events(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    grouped: dict[tuple[str, float], dict[str, Any]] = {}

    for detection in detections:
        if not isinstance(detection, dict):
            continue

        timestamp = _safe_float(detection.get("timestamp"), 0.0)
        label = str(detection.get("label") or "object").strip() or "object"
        confidence = _safe_float(detection.get("confidence"), 0.0)

        key = (label.lower(), round(timestamp, 3))
        if key not in grouped:
            grouped[key] = {
                "timestamp": timestamp,
                "end_time": timestamp,
                "event_type": "visual",
                "source": "visual_detection",
                "description": f"{label.title()} detected",
                "confidence": min(max(confidence, 0.0), 1.0),
                "importance_score": round(confidence * 2.5, 4),
                "metadata": {"label": label, "frame_filename": detection.get("frame_filename"), "raw_confidence": confidence},
            }
        else:
            current = grouped[key]
            current["end_time"] = timestamp
            current["confidence"] = max(current["confidence"], confidence)
            current["importance_score"] = round(max(current["importance_score"], confidence * 2.5), 4)
            current["metadata"]["frame_filename"] = detection.get("frame_filename") or current["metadata"].get("frame_filename")

    for value in grouped.values():
        events.append(value)

    return sorted(events, key=lambda item: (item["timestamp"], item["source"], item["description"]))


def _normalize_speech_events(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue

        start_time = _safe_float(segment.get("start"), 0.0)
        end_time = _safe_float(segment.get("end"), start_time)
        text = str(segment.get("text") or "Speech segment").strip() or "Speech segment"
        confidence = 0.8
        description = text if len(text) <= 140 else text[:137] + "..."

        events.append(
            {
                "timestamp": start_time,
                "end_time": end_time,
                "event_type": "speech",
                "source": "speech_to_text",
                "description": description,
                "confidence": confidence,
                "importance_score": round(min(max(len(text.split()) / 18.0, 0.0), 3.0), 4),
                "metadata": {"segment_number": segment.get("segment_number"), "start": start_time, "end": end_time},
            }
        )
    return sorted(events, key=lambda item: (item["timestamp"], item["source"]))


def _normalize_moderation_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue

        timestamp = _safe_float(event.get("timestamp", event.get("start_time")), 0.0)
        end_time = _safe_float(event.get("end_time"), timestamp)
        label = str(event.get("category") or "moderation").strip() or "moderation"
        message = str(event.get("message") or event.get("text") or "Potentially inappropriate language detected").strip()
        confidence = _safe_float(event.get("confidence"), 0.5)
        severity = str(event.get("severity") or "medium").strip().lower()

        normalized.append(
            {
                "timestamp": timestamp,
                "end_time": end_time,
                "event_type": "moderation",
                "source": "content_moderation",
                "description": message or f"{label.title()} detected",
                "confidence": min(max(confidence, 0.0), 1.0),
                "importance_score": round((confidence * 2.5) + ({"low": 0.5, "medium": 1.0, "high": 1.5}.get(severity, 1.0)), 4),
                "metadata": {
                    "category": label,
                    "severity": severity,
                    "message": message,
                    "start_time": timestamp,
                    "end_time": end_time,
                },
            }
        )
    return sorted(normalized, key=lambda item: (item["timestamp"], item["source"], item["description"]))


def _normalize_keyframe_events(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            continue

        timestamp = _safe_float(frame.get("timestamp"), 0.0)
        importance = _safe_float(frame.get("importance_score"), 0.0)
        frame_filename = str(frame.get("frame_filename") or "frame")
        detected = frame.get("detected_objects") or []
        metadata = {
            "frame_filename": frame_filename,
            "detected_objects": list(detected) if isinstance(detected, list) else [str(detected)],
            "importance_score": importance,
        }

        events.append(
            {
                "timestamp": timestamp,
                "end_time": timestamp,
                "event_type": "key_frame",
                "source": "keyframe_selection",
                "description": f"Important visual frame selected: {frame_filename}",
                "confidence": 0.75,
                "importance_score": importance,
                "metadata": metadata,
            }
        )
    return sorted(events, key=lambda item: (item["timestamp"], item["importance_score"], item["description"]))


def _normalize_chapter_events(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue

        start_time = _safe_float(chapter.get("start_time"), 0.0)
        end_time = _safe_float(chapter.get("end_time"), start_time)
        title = str(chapter.get("title") or "Chapter").strip() or "Chapter"
        summary = str(chapter.get("summary") or "").strip() or "Chapter activity recorded."

        events.append(
            {
                "timestamp": start_time,
                "end_time": end_time,
                "event_type": "chapter",
                "source": "chapter_generation",
                "description": f"Chapter: {title}",
                "confidence": 0.73,
                "importance_score": round(max(0.0, (end_time - start_time) / 10.0), 4),
                "metadata": {"chapter_number": chapter.get("chapter_number"), "title": title, "summary": summary},
            }
        )
    return sorted(events, key=lambda item: (item["timestamp"], item["source"]))


def _group_duplicate_visual_events(events: list[dict[str, Any]], max_gap_seconds: float = DEFAULT_VISUAL_WINDOW_SECONDS) -> list[dict[str, Any]]:
    if not events:
        return []

    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = [events[0]]

    for event in events[1:]:
        previous = current_group[-1]
        if event["description"].lower() == previous["description"].lower() and abs(event["timestamp"] - previous["timestamp"]) <= max_gap_seconds:
            current_group.append(event)
        else:
            groups.append(current_group)
            current_group = [event]

    groups.append(current_group)

    merged: list[dict[str, Any]] = []
    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        earliest = min(group, key=lambda item: item["timestamp"])
        latest = max(group, key=lambda item: item["timestamp"])
        merged.append(
            {
                "timestamp": earliest["timestamp"],
                "end_time": latest["timestamp"],
                "event_type": "visual",
                "source": "visual_detection",
                "description": earliest["description"],
                "confidence": max(item["confidence"] for item in group),
                "importance_score": round(sum(item["importance_score"] for item in group) / len(group), 4),
                "metadata": {
                    "grouped_event_count": len(group),
                    "labels": [item["metadata"].get("label") for item in group if item["metadata"].get("label")],
                    "frame_filenames": [item["metadata"].get("frame_filename") for item in group if item["metadata"].get("frame_filename")],
                },
            }
        )

    return sorted(merged, key=lambda item: (item["timestamp"], item["source"], item["description"]))


def _temporal_fusion(events: list[dict[str, Any]], fusion_window_seconds: float = DEFAULT_FUSION_WINDOW_SECONDS) -> list[dict[str, Any]]:
    if not events:
        return []

    fused: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: (item["timestamp"], item["event_type"])):
        if not fused:
            fused.append(event)
            continue

        previous = fused[-1]
        if (
            event["event_type"] != previous["event_type"]
            and abs(float(event["timestamp"]) - float(previous["timestamp"])) <= fusion_window_seconds
            and abs(float(event["timestamp"]) - float(previous["timestamp"])) >= 0.0
        ):
            fused.append(
                {
                    "timestamp": min(float(previous["timestamp"]), float(event["timestamp"])),
                    "end_time": max(
                        float(previous.get("end_time", previous["timestamp"]) or previous["timestamp"]),
                        float(event.get("end_time", event["timestamp"]) or event["timestamp"]),
                    ),
                    "event_type": "multimodal",
                    "source": "multimodal_fusion",
                    "description": (
                        f"Multimodal activity: {previous['description']} and {event['description']}"
                    ),
                    "confidence": round(
                        max(float(previous.get("confidence", 0.0) or 0.0), float(event.get("confidence", 0.0) or 0.0)),
                        4,
                    ),
                    "importance_score": round(
                        max(float(previous.get("importance_score", 0.0) or 0.0), float(event.get("importance_score", 0.0) or 0.0)) + 0.5,
                        4,
                    ),
                    "metadata": {
                        "related_events": [
                            {
                                "event_type": previous["event_type"],
                                "timestamp": float(previous["timestamp"]),
                                "description": previous["description"],
                            },
                            {
                                "event_type": event["event_type"],
                                "timestamp": float(event["timestamp"]),
                                "description": event["description"],
                            },
                        ]
                    },
                }
            )

        fused.append(event)

    return fused


def _sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        events,
        key=lambda item: (
            float(item.get("timestamp", 0.0) or 0.0),
            str(item.get("event_type") or ""),
            str(item.get("source") or ""),
            str(item.get("description") or ""),
        ),
    )


def build_event_timeline(
    video_id: str,
    include_visual: bool = True,
    include_speech: bool = True,
    include_moderation: bool = True,
    include_keyframes: bool = True,
    include_chapters: bool = True,
) -> list[dict[str, Any]]:
    if not video_id or not video_id.strip():
        raise InvalidTimelineRequestError("video_id must not be empty.")

    if not any([include_visual, include_speech, include_moderation, include_keyframes, include_chapters]):
        return []

    events: list[dict[str, Any]] = []

    if include_visual:
        visual_events = _normalize_visual_events(load_visual_detection_data(video_id))
        events.extend(_group_duplicate_visual_events(visual_events))

    if include_speech:
        speech_events = _normalize_speech_events(load_transcript_data(video_id))
        events.extend(speech_events)

    if include_moderation:
        moderation_events = _normalize_moderation_events(load_moderation_data(video_id))
        events.extend(moderation_events)

    if include_keyframes:
        keyframe_events = _normalize_keyframe_events(load_keyframe_data(video_id))
        events.extend(keyframe_events)

    if include_chapters:
        chapter_events = _normalize_chapter_events(load_chapter_data(video_id))
        events.extend(chapter_events)

    if not events:
        return []

    fused_events = _temporal_fusion(_sort_events(events))
    return _sort_events(fused_events)


def create_event_timeline(
    video_id: str,
    include_visual: bool = True,
    include_speech: bool = True,
    include_moderation: bool = True,
    include_keyframes: bool = True,
    include_chapters: bool = True,
) -> dict[str, Any]:
    start_time = time.perf_counter()
    event_list = build_event_timeline(
        video_id=video_id,
        include_visual=include_visual,
        include_speech=include_speech,
        include_moderation=include_moderation,
        include_keyframes=include_keyframes,
        include_chapters=include_chapters,
    )

    result = {
        "video_id": video_id,
        "total_events": len(event_list),
        "events": [
            {
                "event_id": _slugify(f"{event['event_type']}-{event['source']}-{event['timestamp']}-{index}"),
                "timestamp": float(event.get("timestamp", 0.0) or 0.0),
                "end_time": float(event.get("end_time", event.get("timestamp", 0.0) or 0.0) or 0.0),
                "event_type": str(event.get("event_type") or "event"),
                "source": str(event.get("source") or "unknown"),
                "description": str(event.get("description") or ""),
                "confidence": float(event.get("confidence", 0.0) or 0.0),
                "importance_score": float(event.get("importance_score", 0.0) or 0.0),
                "metadata": event.get("metadata") or {},
            }
            for index, event in enumerate(event_list)
        ],
        "processing_time": 0.0,
    }

    logger.info(
        "Created %d timeline event(s) for video_id=%s in %.4f seconds",
        result["total_events"],
        video_id,
        result["processing_time"],
    )
    return result
