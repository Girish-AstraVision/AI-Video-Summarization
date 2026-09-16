import type { ModerationResult } from '../../types/api';

type ModerationPanelProps = {
  result: ModerationResult;
  onTimestampClick: (timestamp: number) => void;
  isVisible: boolean;
};

function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function ModerationPanel({ result, onTimestampClick, isVisible }: ModerationPanelProps) {
  if (!isVisible) {
    return null;
  }

  const events = [...result.moderation_events].sort((a, b) => a.timestamp - b.timestamp);
  const highSeverityEvents = events.filter((event) => event.severity.toLowerCase() === 'high').length;

  return (
    <section className="panel moderation-panel" aria-live="polite">
      <div className="panel-heading inline-heading">
        <h3>Content Moderation</h3>
      </div>

      <div className="visual-summary-grid">
        <div className="metric-item">
          <span className="metric-label">Total events</span>
          <strong>{result.total_events}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">High severity</span>
          <strong>{highSeverityEvents}</strong>
        </div>
      </div>

      <div className="moderation-grid">
        {events.length === 0 ? (
          <div className="visual-empty-state">No content moderation events were detected for this transcript.</div>
        ) : (
          events.map((event) => {
            const severityClass = event.severity.toLowerCase();
            const toneClass = event.severity.toLowerCase() === 'high' ? 'flagged-content' : event.severity.toLowerCase() === 'medium' ? 'review-required' : 'safe-content';

            return (
              <button
                key={`${event.video_id}-${event.timestamp}-${event.category}-${event.text}`}
                type="button"
                className={`moderation-card ${toneClass}`}
                onClick={() => onTimestampClick(event.timestamp)}
              >
                <div className="moderation-topline">
                  <span className="moderation-status">{event.category.replace(/_/g, ' ')}</span>
                  <span className={`severity-pill ${severityClass}`}>{event.severity}</span>
                </div>
                <div className="moderation-time">{formatTimestamp(event.timestamp)}</div>
                <div className="moderation-event">{event.message}</div>
                <div className="speech-segment-text">{event.text}</div>
                <div className="moderation-time">Confidence: {formatConfidence(event.confidence)}</div>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
