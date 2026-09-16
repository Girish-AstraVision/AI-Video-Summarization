import type { TimelineEvent } from '../../types/api';

type EventTimelineProps = {
  events: TimelineEvent[];
  onTimestampClick: (timestamp: number) => void;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void | Promise<void>;
};

function formatTimestamp(seconds: number | null): string {
  if (typeof seconds !== 'number' || Number.isNaN(seconds)) {
    return '00:00';
  }

  const safeSeconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const secs = safeSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function getEventTypeLabel(eventType: string): string {
  const normalized = eventType.trim().toLowerCase();

  switch (normalized) {
    case 'visual':
      return 'Visual';
    case 'speech':
      return 'Speech';
    case 'moderation':
      return 'Moderation';
    case 'key_frame':
      return 'Key Frame';
    case 'chapter':
      return 'Chapter';
    case 'fusion':
      return 'Multimodal Fusion';
    default:
      return normalized
        .split('_')
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
  }
}

function getEventTypeClass(eventType: string): string {
  const normalized = eventType.trim().toLowerCase();

  switch (normalized) {
    case 'visual':
      return 'visual';
    case 'speech':
      return 'speech';
    case 'moderation':
      return 'moderation';
    case 'key_frame':
      return 'key-frame';
    case 'chapter':
      return 'chapter';
    default:
      return 'visual';
  }
}

export function EventTimeline({ events, onTimestampClick, isLoading = false, error = null, onRefresh }: EventTimelineProps) {
  return (
    <section className="panel">
      <div className="panel-heading" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <h3>Multimodal Event Timeline</h3>
        {onRefresh ? (
          <button type="button" className="secondary-button" onClick={() => { void onRefresh(); }} disabled={isLoading}>
            {isLoading ? 'Refreshing...' : 'Refresh Timeline'}
          </button>
        ) : null}
      </div>

      {error ? <div className="upload-message error-message">{error}</div> : null}

      {isLoading ? <div className="upload-message">Loading event timeline...</div> : null}

      {!isLoading && !error && events.length === 0 ? (
        <div className="upload-message">No timeline events are available yet for this video.</div>
      ) : null}

      {!isLoading && !error && events.length > 0 ? (
        <div className="timeline-list" aria-label="Multimodal event timeline">
          {events.map((event) => (
            <button
              key={event.event_id}
              type="button"
              className="timeline-item timeline-clickable"
              onClick={() => onTimestampClick(event.timestamp)}
              aria-label={`Jump to ${formatTimestamp(event.timestamp)} ${getEventTypeLabel(event.event_type)}`}
            >
              <div className="timeline-marker">
                <span className={`timeline-dot ${getEventTypeClass(event.event_type)}`} />
              </div>
              <div className="timeline-body">
                <div className="timeline-meta">
                  <span className="timeline-time">{formatTimestamp(event.timestamp)}</span>
                  <span className="timeline-type">{getEventTypeLabel(event.event_type)}</span>
                </div>
                <p>{event.description}</p>
                <div className="timeline-footer">
                  <span className="timeline-source">{event.source}</span>
                  {event.end_time != null ? <span className="timeline-range">{formatTimestamp(event.end_time)}</span> : null}
                </div>
                {(event.confidence != null || event.importance_score != null) ? (
                  <div className="timeline-metrics">
                    {event.confidence != null ? <span>Confidence: {(event.confidence * 100).toFixed(0)}%</span> : null}
                    {event.importance_score != null ? <span>Importance: {event.importance_score.toFixed(2)}</span> : null}
                  </div>
                ) : null}
              </div>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
