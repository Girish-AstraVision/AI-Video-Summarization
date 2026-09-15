import type { KeyFrameItem } from '../../types/dashboard';

type KeyFrameGalleryProps = {
  items: KeyFrameItem[];
};

export function KeyFrameGallery({ items }: KeyFrameGalleryProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Key Frames</h3>
      </div>

      <div className="keyframe-grid">
        {items.map((item) => (
          <article key={`${item.timestamp}-${item.title}`} className="keyframe-card">
            <div className="keyframe-visual" aria-label={`Key frame at ${item.timestamp}`}>
              <span className="keyframe-badge">{item.importance}</span>
            </div>
            <div className="keyframe-meta">
              <div className="keyframe-time">{item.timestamp}</div>
              <div className="keyframe-title">{item.title}</div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
