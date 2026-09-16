import { API_BASE_URL } from '../../config/env';
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
      <div className="panel-heading keyframe-header">
        <div>
          <p className="eyebrow subtle-eyebrow">Key Frame Selection</p>
          <h3>Key Frame Selection</h3>
          <p className="keyframe-subtitle">Important frames extracted from your video using visual and content analysis</p>
        </div>

        <button type="button" className="secondary-button" onClick={() => onTimestampClick(frames[0]?.timestamp ?? 0)}>
          Select Key Frames
        </button>
      </div>

      <div className="keyframe-stat-grid">
        <div className="metric-item">
          <span className="metric-label">Total Frames Analyzed</span>
          <strong>{result.total_frames_analyzed}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Key Frames Selected</span>
          <strong>{result.number_selected}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Average / Top Importance</span>
          <strong>{frames.length > 0 ? formatScore(frames.reduce((sum, frame) => sum + frame.importance_score, 0) / frames.length) : '0.00'}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Processing Time</span>
          <strong>{result.processing_time.toFixed(2)}s</strong>
        </div>
      </div>

      <div className="keyframe-grid">
        {frames.length === 0 ? (
          <div className="visual-empty-state">No key frames were returned for this video.</div>
        ) : (
          frames.map((frame) => {
            const imageUrl = `${API_BASE_URL}/api/videos/${encodeURIComponent(result.video_id)}/frames/${encodeURIComponent(frame.frame_filename)}`;

            return (
              <article key={`${frame.frame_filename}-${frame.timestamp}`} className="keyframe-card">
                <div className="keyframe-media" aria-label={`Key frame at ${formatTimestamp(frame.timestamp)}`}>
                  <img
                    src={imageUrl}
                    alt={frame.frame_filename}
                    className="keyframe-image"
                    loading="lazy"
                    onError={(event) => {
                      const element = event.currentTarget;
                      element.style.display = 'none';
                      const parent = element.parentElement;
                      if (parent) {
                        parent.classList.add('fallback-media');
                      }
                    }}
                  />
                  <span className="keyframe-badge">{formatTimestamp(frame.timestamp)}</span>
                </div>

                <div className="keyframe-meta">
                  <div className="keyframe-filename">{frame.frame_filename}</div>

                  <div className="keyframe-score-row">
                    <span className="meta-label">Importance Score</span>
                    <strong>{formatScore(frame.importance_score)}</strong>
                  </div>

                  {frame.detected_objects.length > 0 ? (
                    <div className="keyframe-object-list" aria-label="Detected objects in key frame">
                      {frame.detected_objects.map((objectLabel) => (
                        <span key={`${frame.frame_filename}-${objectLabel}`} className="keyframe-pill">
                          {objectLabel}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <button
                    type="button"
                    className="keyframe-timestamp-button"
                    onClick={() => onTimestampClick(frame.timestamp)}
                    aria-label={`Seek to ${formatTimestamp(frame.timestamp)}`}
                  >
                    ▶ Go to Timestamp
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
