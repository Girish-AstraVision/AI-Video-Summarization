import type { KeyFrameSelectionResult } from '../../types/api';

type KeyFrameGalleryProps = {
  result: KeyFrameSelectionResult;
  onTimestampClick: (timestamp: number) => void;
  isVisible: boolean;
};

function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatScore(score: number): string {
  return score.toFixed(2);
}

export function KeyFrameGallery({ result, onTimestampClick, isVisible }: KeyFrameGalleryProps) {
  if (!isVisible) {
    return null;
  }

  const frames = [...result.selected_frames].sort((a, b) => a.timestamp - b.timestamp);

  return (
    <section className="panel keyframe-panel" aria-live="polite">
      <div className="panel-heading inline-heading">
        <h3>Key Frames</h3>
      </div>

      <div className="visual-summary-grid">
        <div className="metric-item">
          <span className="metric-label">Frames analyzed</span>
          <strong>{result.total_frames_analyzed}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Selected</span>
          <strong>{result.number_selected}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Processing time</span>
          <strong>{result.processing_time.toFixed(2)}s</strong>
        </div>
      </div>

      <div className="keyframe-grid">
        {frames.length === 0 ? (
          <div className="visual-empty-state">No key frames were returned for this video.</div>
        ) : (
          frames.map((frame) => (
            <button
              key={`${frame.frame_filename}-${frame.timestamp}`}
              type="button"
              className="keyframe-card"
              onClick={() => onTimestampClick(frame.timestamp)}
              aria-label={`Seek to ${formatTimestamp(frame.timestamp)}`}
            >
              <div className="keyframe-visual" aria-label={`Key frame at ${formatTimestamp(frame.timestamp)}`}>
                <span className="keyframe-badge">{formatScore(frame.importance_score)}</span>
              </div>
              <div className="keyframe-meta">
                <div className="keyframe-time">{formatTimestamp(frame.timestamp)}</div>
                <div className="keyframe-title">{frame.frame_filename}</div>
                <div className="speech-segment-text">Importance score: {formatScore(frame.importance_score)}</div>
                <div className="speech-segment-text">
                  {frame.detected_objects.length > 0 ? `Objects: ${frame.detected_objects.join(', ')}` : 'No detected objects recorded'}
                </div>
              </div>
            </button>
          ))
        )}
      </div>

      <div className="visual-detection-meta" aria-label="Key-frame image availability note">
        <span className="meta-label">Frame image source</span>
        <strong>Stored on disk by the backend; no direct HTTP image endpoint is currently exposed.</strong>
      </div>
    </section>
  );
}
