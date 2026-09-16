import json
import logging
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

from app.services.video_service import get_project_root

logger = logging.getLogger(__name__)

MODEL_NAME = "PekingU/rtdetr_r50vd_coco_o365"

_model_instance: RTDetrForObjectDetection | None = None
_processor_instance: RTDetrImageProcessor | None = None


class VisualDetectionError(RuntimeError):
    """Base exception for visual detection errors."""


class ModelLoadError(VisualDetectionError):
    """Raised when the model or processor cannot be loaded."""


class VideoFrameDetectionError(VisualDetectionError):
    """Raised when frame detection fails for a video."""


def _get_device() -> torch.device:
    return torch.device("cpu")


def _load_model_and_processor() -> tuple[RTDetrImageProcessor, RTDetrForObjectDetection]:
    global _model_instance, _processor_instance

    if _processor_instance is None or _model_instance is None:
        try:
            logger.info("Loading RT-DETR model and processor from Hugging Face: %s", MODEL_NAME)
            processor = RTDetrImageProcessor.from_pretrained(MODEL_NAME)
            model = RTDetrForObjectDetection.from_pretrained(MODEL_NAME)
        except Exception as exc:  # pragma: no cover - exercises model-loading failure path only in tests
            raise ModelLoadError(f"Failed to load RT-DETR model '{MODEL_NAME}'.") from exc

        device = _get_device()
        model.to(device)
        model.eval()

        _processor_instance = processor
        _model_instance = model

    return _processor_instance, _model_instance


def _read_metadata(video_dir: Path) -> dict[str, Any]:
    metadata_path = video_dir / "metadata.json"
    if not metadata_path.exists():
        raise VideoFrameDetectionError(f"Missing metadata file for video directory: {video_dir}")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VideoFrameDetectionError(f"Could not parse metadata JSON for video directory: {video_dir}") from exc

    return metadata


def _frame_timestamps_from_metadata(frame_paths: list[Path], metadata: dict[str, Any]) -> list[float]:
    if isinstance(metadata.get("frame_timestamps"), list):
        explicit_timestamps = [float(value) for value in metadata["frame_timestamps"]]
        if len(explicit_timestamps) != len(frame_paths):
            raise VideoFrameDetectionError(
                "Frame timestamp metadata length does not match extracted frame count. "
                f"Expected {len(frame_paths)} timestamps, found {len(explicit_timestamps)}."
            )
        return explicit_timestamps

    frame_details = metadata.get("frame_details")
    if isinstance(frame_details, list) and frame_details:
        filename_to_timestamp: dict[str, float] = {}
        for item in frame_details:
            if not isinstance(item, dict):
                continue
            frame_filename = item.get("frame_filename") or (Path(str(item.get("image_path", ""))).name if item.get("image_path") else None)
            if not frame_filename:
                continue
            if "timestamp" not in item:
                raise VideoFrameDetectionError(f"Frame timestamp metadata is missing for frame '{frame_filename}'.")
            filename_to_timestamp[frame_filename] = float(item["timestamp"])

        if not filename_to_timestamp:
            raise VideoFrameDetectionError(
                "Frame timestamp metadata is missing from metadata.json. "
                "Add frame_details entries with frame_filename and timestamp values."
            )

        missing_frames = [path.name for path in frame_paths if path.name not in filename_to_timestamp]
        if missing_frames:
            raise VideoFrameDetectionError(
                "Frame timestamp metadata is incomplete for frames: " + ", ".join(missing_frames)
            )

        return [filename_to_timestamp[path.name] for path in frame_paths]

    raise VideoFrameDetectionError(
        "Frame timestamp metadata is missing from metadata.json. "
        "Add frame_details entries with frame_filename and timestamp values."
    )


def _detect_objects_in_frame(
    image: Image.Image,
    processor: RTDetrImageProcessor,
    model: RTDetrForObjectDetection,
    confidence_threshold: float,
) -> list[dict[str, Any]]:
    device = _get_device()
    inputs = processor(images=image, return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]], device=device)
    results = processor.post_process_object_detection(
        outputs,
        target_sizes=target_sizes,
        threshold=confidence_threshold,
    )[0]

    detections: list[dict[str, Any]] = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        detections.append(
            {
                "label": model.config.id2label.get(label.item(), str(label.item())),
                "confidence": float(score.item()),
                "bounding_box": [float(value) for value in box.tolist()],
            }
        )

    return detections


def process_video_visual_detection(video_id: str, confidence_threshold: float = 0.5) -> dict[str, Any]:
    if confidence_threshold < 0 or confidence_threshold > 1:
        raise ValueError("confidence_threshold must be between 0 and 1.")

    start_time = time.perf_counter()
    logger.info("Starting visual detection for video_id=%s with threshold %.2f", video_id, confidence_threshold)

    outputs_root = get_project_root() / "outputs"
    video_dir = outputs_root / video_id
    frames_dir = video_dir / "frames"

    if not video_dir.exists() or not frames_dir.exists():
        raise VideoFrameDetectionError(f"No processed frames found for video_id '{video_id}'.")

    try:
        metadata = _read_metadata(video_dir)
        frame_paths = sorted(frames_dir.glob("*.jpg"))
        if not frame_paths:
            raise VideoFrameDetectionError(f"No JPG frames found in {frames_dir} for video '{video_id}'.")

        processor, model = _load_model_and_processor()
        all_detections: list[dict[str, Any]] = []
        timestamps = _frame_timestamps_from_metadata(frame_paths, metadata)

        for frame_index, frame_path in enumerate(frame_paths, start=1):
            try:
                image = Image.open(frame_path).convert("RGB")
                detections = _detect_objects_in_frame(
                    image=image,
                    processor=processor,
                    model=model,
                    confidence_threshold=confidence_threshold,
                )

                for detection in detections:
                    all_detections.append(
                        {
                            "frame_number": frame_index,
                            "frame_filename": frame_path.name,
                            "timestamp": timestamps[frame_index - 1],
                            "label": detection["label"],
                            "confidence": detection["confidence"],
                            "bounding_box": detection["bounding_box"],
                        }
                    )
            except Exception as exc:  # pragma: no cover - defensive guard for a single frame failure
                logger.warning("Skipping frame %s for video_id=%s due to detection error: %s", frame_path.name, video_id, exc)
                continue

        total_time = time.perf_counter() - start_time
        result = {
            "video_id": video_id,
            "frames_processed": len(frame_paths),
            "number_of_detections": len(all_detections),
            "detections": all_detections,
            "processing_time": round(total_time, 4),
            "model_name": MODEL_NAME,
        }

        logger.info(
            "Completed visual detection for video_id=%s in %.4f seconds; %d detections across %d frames",
            video_id,
            total_time,
            len(all_detections),
            len(frame_paths),
        )
        return result
    except (VisualDetectionError, ValueError):
        logger.exception("Visual detection failed for video_id=%s", video_id)
        raise
    except Exception as exc:
        logger.exception("Unexpected visual detection failure for video_id=%s", video_id)
        raise VideoFrameDetectionError(f"Unexpected visual detection failure for video_id '{video_id}'.") from exc
