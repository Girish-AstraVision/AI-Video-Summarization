import type { TimelineEvent } from '../../types/dashboard';

type EventTimelineProps = {
  events: TimelineEvent[];
};

export function EventTimeline({ events }: EventTimelineProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Multimodal Event Timeline</h3>
      </div>

      <div className="timeline-list" aria-label="Multimodal event timeline">
        {events.map((event) => (
          <div key={`${event.timestamp}-${event.type}-${event.description}`} className="timeline-item">
            <div className="timeline-marker">
              <span className={`timeline-dot ${event.type.toLowerCase().replace(/\s+/g, '-')}`} />
            </div>
            <div className="timeline-body">
              <div className="timeline-meta">
                <span className="timeline-time">{event.timestamp}</span>
                <span className="timeline-type">{event.type}</span>
              </div>
              <p>{event.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
