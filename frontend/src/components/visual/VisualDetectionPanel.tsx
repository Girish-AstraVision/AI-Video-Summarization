import type { VisualDetectionResult } from '../../types/api';

type VisualDetectionPanelProps = {
  result: VisualDetectionResult;
  onTimestampClick: (timestamp: number) => void;
  isVisible: boolean;
};

function formatTimestamp(timestamp: number): string {
  const totalSeconds = Math.max(0, Math.round(timestamp));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function VisualDetectionPanel({ result, onTimestampClick, isVisible }: VisualDetectionPanelProps) {
  if (!isVisible) {
    return null;
  }

  const detections = [...result.detections].sort((a, b) => a.timestamp - b.timestamp);
  const uniqueClasses = new Set(detections.map((detection) => detection.label)).size;

  return (
    <section className="panel visual-detection-panel" aria-live="polite">
      <div className="panel-heading inline-heading">
        <h3>RT-DETR Visual Detection Results</h3>
      </div>

      <div className="visual-summary-grid">
        <div className="metric-item">
          <span className="metric-label">Total detections</span>
          <strong>{result.number_of_detections}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Unique classes</span>
          <strong>{uniqueClasses}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Frames processed</span>
          <strong>{result.frames_processed}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Processing time</span>
          <strong>{result.processing_time.toFixed(2)}s</strong>
        </div>
      </div>

      <div className="visual-detection-list" aria-label="Visual detection list">
        {detections.length === 0 ? (
          <div className="visual-empty-state">No objects detected above the selected confidence threshold.</div>
        ) : (
          detections.map((detection) => (
            <button
              key={`${detection.frame_number}-${detection.label}-${detection.timestamp}-${detection.frame_filename}`}
              type="button"
              className="visual-detection-row"
              onClick={() => onTimestampClick(detection.timestamp)}
            >
              <span className="visual-detection-time" role="button" tabIndex={0}>
                {formatTimestamp(detection.timestamp)}
              </span>
              <span className="visual-detection-label">{detection.label}</span>
              <span className="visual-detection-confidence">{formatConfidence(detection.confidence)}</span>
              <span className="visual-detection-frame">{detection.frame_filename}</span>
            </button>
          ))
        )}
      </div>

      <div className="visual-detection-meta" aria-label="Model information">
        <div>
          <span className="meta-label">Model</span>
          <strong>{result.model_name}</strong>
        </div>
      </div>
    </section>
  );
}
