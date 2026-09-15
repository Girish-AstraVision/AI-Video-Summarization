import type { ModerationItem } from '../../types/dashboard';

type ModerationPanelProps = {
  items: ModerationItem[];
};

export function ModerationPanel({ items }: ModerationPanelProps) {
  const severityMap: Record<ModerationItem['severity'], string> = {
    Low: 'low',
    Medium: 'medium',
    High: 'high',
  };

  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Content Moderation</h3>
      </div>

      <div className="moderation-grid">
        {items.map((item) => (
          <article key={`${item.timestamp}-${item.event}`} className={`moderation-card ${item.status.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="moderation-topline">
              <span className="moderation-status">{item.status}</span>
              <span className={`severity-pill ${severityMap[item.severity]}`}>{item.severity}</span>
            </div>
            <div className="moderation-time">{item.timestamp}</div>
            <div className="moderation-event">{item.event}</div>
          </article>
        ))}
      </div>
    </section>
  );
}
