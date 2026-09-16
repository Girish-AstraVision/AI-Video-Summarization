import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from app.services.keyframe_service import MissingKeyframeDataError, select_keyframes_for_video
from app.services.speech_to_text_service import transcribe_video_audio
from app.services.video_service import get_project_root
from app.services.visual_detection_service import process_video_visual_detection

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHAPTERS = 5
MIN_MAX_CHAPTERS = 1
MAX_MAX_CHAPTERS = 10
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "her",
    "his",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
    "will",
    "you",
    "your",
    "we",
    "they",
    "them",
    "our",
    "into",
    "about",
    "near",
    "while",
    "after",
    "before",
    "through",
    "during",
    "across",
    "without",
    "shows",
    "show",
    "appears",
    "activity",
    "segment",
    "scene",
    "summary",
    "chapter",
    "main",
    "conclusion",
    "introduction",
}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


class ChapterError(RuntimeError):
    """Base exception for chapter generation failures."""


class InvalidChapterRequestError(ChapterError):
    """Raised when the request is invalid."""


class MissingChapterDataError(ChapterError):
    """Raised when required transcript or visual data is absent."""


def validate_max_chapters(max_chapters: int | None) -> int:
    if max_chapters is None:
        return DEFAULT_MAX_CHAPTERS
    if isinstance(max_chapters, bool) or not isinstance(max_chapters, int):
        raise InvalidChapterRequestError("max_chapters must be an integer between 1 and 10.")
    if max_chapters < MIN_MAX_CHAPTERS or max_chapters > MAX_MAX_CHAPTERS:
        raise InvalidChapterRequestError(
            f"max_chapters must be between {MIN_MAX_CHAPTERS} and {MAX_MAX_CHAPTERS}."
        )
    return max_chapters


def _read_json(path: Path, description: str, video_id: str) -> dict[str, Any]:
    if not path.exists():
        raise MissingChapterDataError(f"{description} not found for video_id '{video_id}'.")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MissingChapterDataError(f"Could not parse {description} for video_id '{video_id}'.") from exc

    if not isinstance(payload, dict):
        raise MissingChapterDataError(f"{description} for video_id '{video_id}' is not a valid JSON object.")

    return payload


def load_transcript_data(video_id: str) -> list[dict[str, Any]]:
    transcript_path = get_project_root() / "outputs" / video_id / "transcript.json"
    if transcript_path.exists():
        payload = _read_json(transcript_path, "Transcript data", video_id)
        segments = payload.get("segments") or payload.get("transcript_segments") or []
        if not isinstance(segments, list) or not segments:
            raise MissingChapterDataError(f"Transcript segments are missing for video_id '{video_id}'.")
        return segments

    logger.info(
        "Transcript artifact missing for video_id=%s; generating from speech service. cwd=%s transcript_path=%s",
        video_id,
        Path.cwd(),
        transcript_path,
    )
    try:
        transcript_payload = transcribe_video_audio(video_id=video_id)
    except Exception as exc:
        raise MissingChapterDataError(f"Transcript data not found for video_id '{video_id}'.") from exc

    segments = transcript_payload.get("segments") or []
    if not isinstance(segments, list) or not segments:
        raise MissingChapterDataError(f"Transcript segments are missing for video_id '{video_id}'.")
    return segments


def load_visual_detection_data(video_id: str) -> list[dict[str, Any]]:
    detection_path = get_project_root() / "outputs" / video_id / "visual_detection.json"
    if detection_path.exists():
        payload = _read_json(detection_path, "Visual detection data", video_id)
        detections = payload.get("detections", [])
        if not isinstance(detections, list) or not detections:
            raise MissingChapterDataError(f"RT-DETR detection data is missing for video_id '{video_id}'.")
        return detections

    logger.info(
        "Visual detection artifact missing for video_id=%s; generating from detection service. cwd=%s detection_path=%s",
        video_id,
        Path.cwd(),
        detection_path,
    )
    try:
        detection_payload = process_video_visual_detection(video_id=video_id)
    except Exception as exc:
        raise MissingChapterDataError(f"Visual detection data is missing for video_id '{video_id}'.") from exc

    detections = detection_payload.get("detections", [])
    if not isinstance(detections, list) or not detections:
        raise MissingChapterDataError(f"RT-DETR detection data is missing for video_id '{video_id}'.")
    return detections


def load_keyframe_data(video_id: str) -> list[dict[str, Any]]:
    keyframe_path = get_project_root() / "outputs" / video_id / "keyframes.json"
    if keyframe_path.exists():
        payload = _read_json(keyframe_path, "Key-frame data", video_id)
        frames = payload.get("selected_frames") or payload.get("key_frames") or []
        if isinstance(frames, list) and frames:
            return frames

    try:
        keyframe_payload = select_keyframes_for_video(video_id=video_id, num_keyframes=10)
    except (MissingKeyframeDataError, ValueError) as exc:
        logger.warning("Key-frame data unavailable for video_id=%s; continuing with empty key-frame list. Reason: %s", video_id, exc)
        return []

    frames = keyframe_payload.get("selected_frames") or []
    if not isinstance(frames, list):
        return []
    return frames


def load_summary_data(video_id: str) -> list[dict[str, Any]]:
    summary_path = get_project_root() / "outputs" / video_id / "summary.json"
    if not summary_path.exists():
        return []

    payload = _read_json(summary_path, "Summary data", video_id)
    segments = payload.get("segments", [])
    if not isinstance(segments, list):
        return []
    return segments


def _keyword_words(text: str) -> list[str]:
    cleaned = _normalize_text(text)
    if not cleaned:
        return []

    words = [word.lower() for word in re.findall(r"[A-Za-z]+", cleaned)]
    filtered = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    return filtered


def _dominant_labels(detections: list[dict[str, Any]], start_time: float, end_time: float) -> list[str]:
    label_counts: dict[str, int] = {}
    for detection in detections:
        try:
            timestamp = float(detection.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        if start_time <= timestamp <= end_time:
            label = str(detection.get("label") or "").strip()
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1

    return [label for label, _ in sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))]


def _segment_importance(segment: dict[str, Any], detections: list[dict[str, Any]], keyframes: list[dict[str, Any]]) -> float:
    text = str(segment.get("text") or "")
    words = _keyword_words(text)
    keyword_score = len(words) * 0.8
    duration_score = max(0.0, float(segment.get("end", 0.0) or 0.0) - float(segment.get("start", 0.0) or 0.0)) * 0.15

    event_label_score = 0.0
    for detection in detections:
        try:
            timestamp = float(detection.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        start_time = float(segment.get("start", 0.0) or 0.0)
        end_time = float(segment.get("end", start_time) or start_time)
        if start_time <= timestamp <= end_time:
            event_label_score += float(detection.get("confidence", 0.0) or 0.0)

    keyframe_score = 0.0
    for keyframe in keyframes:
        try:
            keyframe_time = float(keyframe.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        start_time = float(segment.get("start", 0.0) or 0.0)
        end_time = float(segment.get("end", start_time) or start_time)
        if start_time <= keyframe_time <= end_time:
            keyframe_score += float(keyframe.get("importance_score", 0.0) or 0.0)

    return round(keyword_score + duration_score + event_label_score + keyframe_score, 4)


def _merge_adjacent_groups(groups: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    merged: list[list[dict[str, Any]]] = []
    for group in groups:
        if not group:
            continue
        if not merged:
            merged.append(group)
            continue

        previous = merged[-1]
        previous_start = float(previous[0].get("start", 0.0) or 0.0)
        previous_end = float(previous[-1].get("end", previous_start) or previous_start)
        group_start = float(group[0].get("start", 0.0) or 0.0)
        gap = max(0.0, group_start - previous_end)

        if gap <= 2.0:
            prev_words = set(_keyword_words(str(previous[-1].get("text") or "")))
            curr_words = set(_keyword_words(str(group[0].get("text") or "")))
            prev_labels = _dominant_labels(group, previous_start, previous_end)
            curr_labels = _dominant_labels(group, group_start, float(group[-1].get("end", group_start) or group_start))
            if prev_words and curr_words and prev_words.intersection(curr_words):
                merged[-1].extend(group)
                continue
            if prev_labels and curr_labels and set(prev_labels).intersection(set(curr_labels)):
                merged[-1].extend(group)
                continue

        merged.append(group)
    return merged


def _should_break(previous: dict[str, Any], current: dict[str, Any], detections: list[dict[str, Any]]) -> bool:
    previous_end = float(previous.get("end", 0.0) or 0.0)
    current_start = float(current.get("start", 0.0) or 0.0)
    gap = max(0.0, current_start - previous_end)

    if gap >= 4.0:
        return True

    prev_words = set(_keyword_words(str(previous.get("text") or "")))
    curr_words = set(_keyword_words(str(current.get("text") or "")))
    if prev_words and curr_words:
        meaningful_prev = prev_words - STOP_WORDS
        meaningful_curr = curr_words - STOP_WORDS
        if meaningful_prev and meaningful_curr and not meaningful_prev.intersection(meaningful_curr):
            return True

    prev_labels = _dominant_labels(detections, float(previous.get("start", 0.0) or 0.0), float(previous.get("end", 0.0) or 0.0))
    curr_labels = _dominant_labels(detections, float(current.get("start", 0.0) or 0.0), float(current.get("end", 0.0) or 0.0))
    if prev_labels and curr_labels and not set(prev_labels).intersection(set(curr_labels)):
        return True

    return False


def _build_groups(segments: list[dict[str, Any]], detections: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not segments:
        return []

    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = [segments[0]]

    for segment in segments[1:]:
        if _should_break(current_group[-1], segment, detections):
            groups.append(current_group)
            current_group = [segment]
        else:
            current_group.append(segment)

    groups.append(current_group)
    return _merge_adjacent_groups(groups)


def _group_importance(group: list[dict[str, Any]], detections: list[dict[str, Any]], keyframes: list[dict[str, Any]]) -> float:
    return sum(_segment_importance(segment, detections, keyframes) for segment in group)


def _limit_groups(groups: list[list[dict[str, Any]]], max_chapters: int, detections: list[dict[str, Any]], keyframes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(groups) <= max_chapters:
        return groups

    while len(groups) > max_chapters:
        best_index = 0
        best_score = float("inf")
        for idx in range(len(groups) - 1):
            combined_score = _group_importance(groups[idx], detections, keyframes) + _group_importance(groups[idx + 1], detections, keyframes)
            if combined_score < best_score:
                best_score = combined_score
                best_index = idx

        groups[best_index] = groups[best_index] + groups[best_index + 1]
        groups.pop(best_index + 1)

    return groups


def _extract_title(chapter_text: str, object_labels: list[str], chapter_number: int, total_chapters: int) -> str:
    normalized = _normalize_text(chapter_text)
    if not normalized:
        if chapter_number == 1:
            return "Introduction"
        if chapter_number == total_chapters:
            return "Conclusion"
        return f"Chapter {chapter_number}"

    lowered = normalized.lower()
    if any(token in lowered for token in ["warning", "danger", "alert", "incident", "accident", "emergency", "fire"]):
        return "Important Event"
    if any(token in lowered for token in ["person", "people", "crowd", "man", "woman", "group"]):
        return "People and Objects"
    if any(token in lowered for token in ["car", "truck", "bus", "vehicle", "road", "traffic"]):
        return "Vehicle Activity"

    if object_labels:
        labels = object_labels[:2]
        if len(labels) == 2:
            return " and ".join(label.title() for label in labels)
        return labels[0].title()

    keywords = _keyword_words(normalized)
    if keywords:
        top_words = keywords[:3]
        return " ".join(word.title() for word in top_words)

    return f"Chapter {chapter_number}"


def _chapter_summary(chapter_text: str, object_labels: list[str]) -> str:
    normalized = _normalize_text(chapter_text)
    if normalized:
        # deterministic summary: keep the first sentence-like chunk from the chapter.
        phrase = re.split(r"(?<=[.!?])\s+", normalized)[0]
        if len(phrase) > 220:
            return phrase[:217].rstrip() + "..."
        return phrase

    if object_labels:
        return "Detected objects included: " + ", ".join(object_labels[:3]) + "."

    return "Visual activity recorded during this chapter."


def _chapter_keyframes(keyframes: list[dict[str, Any]], start_time: float, end_time: float, limit: int = 3) -> list[dict[str, Any]]:
    if not keyframes:
        return []

    in_range: list[dict[str, Any]] = []
    for keyframe in keyframes:
        try:
            timestamp = float(keyframe.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if start_time <= timestamp <= end_time:
            in_range.append(keyframe)

    if in_range:
        ranked = sorted(in_range, key=lambda item: (-float(item.get("importance_score", 0.0) or 0.0), float(item.get("timestamp", 0.0) or 0.0)))
        selected = ranked[:limit]
        return [
            {
                "frame_filename": str(item.get("frame_filename") or ""),
                "timestamp": float(item.get("timestamp", 0.0) or 0.0),
                "importance_score": float(item.get("importance_score", 0.0) or 0.0),
            }
            for item in selected
            if str(item.get("frame_filename") or "")
        ]

    midpoint = (start_time + end_time) / 2.0 if end_time >= start_time else start_time
    ranked = sorted(
        keyframes,
        key=lambda item: abs(float(item.get("timestamp", 0.0) or 0.0) - midpoint),
    )
    return [
        {
            "frame_filename": str(item.get("frame_filename") or ""),
            "timestamp": float(item.get("timestamp", 0.0) or 0.0),
            "importance_score": float(item.get("importance_score", 0.0) or 0.0),
        }
        for item in ranked[:limit]
        if str(item.get("frame_filename") or "")
    ]


def _collect_important_objects(detections: list[dict[str, Any]], start_time: float, end_time: float) -> list[dict[str, Any]]:
    object_scores: dict[str, float] = {}
    object_count: dict[str, int] = {}

    for detection in detections:
        try:
            timestamp = float(detection.get("timestamp", 0.0) or 0.0)
            confidence = float(detection.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        if start_time <= timestamp <= end_time:
            label = str(detection.get("label") or "").strip()
            if not label:
                continue
            object_scores[label] = object_scores.get(label, 0.0) + confidence
            object_count[label] = object_count.get(label, 0) + 1

    items: list[dict[str, Any]] = []
    for label, conf_total in sorted(object_scores.items(), key=lambda item: (-item[1], item[0]))[:5]:
        items.append({
            "label": label,
            "confidence": round(conf_total / max(object_count[label], 1), 4),
        })
    return items


def _chapter_segments_to_time_range(group: list[dict[str, Any]]) -> tuple[float, float]:
    if not group:
        return 0.0, 0.0
    start_time = float(group[0].get("start", 0.0) or 0.0)
    end_time = float(group[-1].get("end", start_time) or start_time)
    return start_time, end_time


def generate_chapters(
    video_id: str,
    max_chapters: int = DEFAULT_MAX_CHAPTERS,
    transcript: list[dict[str, Any]] | None = None,
    detections: list[dict[str, Any]] | None = None,
    keyframes: list[dict[str, Any]] | None = None,
    summary_segments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not video_id or not video_id.strip():
        raise InvalidChapterRequestError("video_id must not be empty.")

    resolved_max = validate_max_chapters(max_chapters)
    transcript_segments = transcript or []
    detection_data = detections or []
    keyframe_data = keyframes or []
    summary_segment_data = summary_segments or []

    if not transcript_segments:
        raise MissingChapterDataError(f"Transcript segments are missing for video_id '{video_id}'.")

    if not detection_data:
        raise MissingChapterDataError(f"Visual detection data is missing for video_id '{video_id}'.")

    chapter_groups = _build_groups(transcript_segments, detection_data)
    chapter_groups = _limit_groups(chapter_groups, resolved_max, detection_data, keyframe_data)

    if not chapter_groups:
        chapter_groups = [transcript_segments]

    chapter_results: list[dict[str, Any]] = []
    for chapter_index, group in enumerate(chapter_groups, start=1):
        start_time, end_time = _chapter_segments_to_time_range(group)
        chapter_text = " ".join(_normalize_text(segment.get("text") or "") for segment in group if _normalize_text(segment.get("text") or ""))
        object_labels = _dominant_labels(detection_data, start_time, end_time)
        title = _extract_title(chapter_text, object_labels, chapter_index, len(chapter_groups))
        summary = _chapter_summary(chapter_text, object_labels)
        frames = _chapter_keyframes(keyframe_data, start_time, end_time)
        important_objects = _collect_important_objects(detection_data, start_time, end_time)

        chapter_results.append(
            {
                "chapter_number": chapter_index,
                "start_time": round(start_time, 4),
                "end_time": round(end_time, 4),
                "title": title,
                "summary": summary,
                "key_frames": frames,
                "important_objects": important_objects,
            }
        )

    # Preserve original timeline and disallow overlap.
    if chapter_results:
        for index in range(1, len(chapter_results)):
            previous = chapter_results[index - 1]
            current = chapter_results[index]
            if current["start_time"] < previous["end_time"]:
                current["start_time"] = previous["end_time"]
            if current["start_time"] >= current["end_time"]:
                current["end_time"] = current["start_time"] + 1.0

    return chapter_results


def create_video_chapters(video_id: str, max_chapters: int = DEFAULT_MAX_CHAPTERS) -> dict[str, Any]:
    validate_max_chapters(max_chapters)
    start_time = time.perf_counter()
    transcript_segments = load_transcript_data(video_id)
    detection_data = load_visual_detection_data(video_id)
    keyframe_data = load_keyframe_data(video_id)
    summary_data = load_summary_data(video_id)

    chapters = generate_chapters(
        video_id=video_id,
        max_chapters=max_chapters,
        transcript=transcript_segments,
        detections=detection_data,
        keyframes=keyframe_data,
        summary_segments=summary_data,
    )

    result = {
        "video_id": video_id,
        "number_of_chapters": len(chapters),
        "chapters": chapters,
        "processing_time": round(time.perf_counter() - start_time, 4),
    }

    logger.info(
        "Created %d chapter(s) for video_id=%s in %.4f seconds",
        len(chapters),
        video_id,
        result["processing_time"],
    )
    return result
