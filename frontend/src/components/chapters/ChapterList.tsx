import type { ChapterResponse } from '../../types/api';

type ChapterListProps = {
  result: ChapterResponse;
  onTimestampClick: (timestamp: number) => void;
  isVisible: boolean;
};

function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

export function ChapterList({ result, onTimestampClick, isVisible }: ChapterListProps) {
  if (!isVisible) {
    return null;
  }

  const chapters = [...result.chapters].sort((a, b) => a.start_time - b.start_time);

  return (
    <section className="panel">
      <div className="panel-heading inline-heading">
        <h3>Chapters</h3>
      </div>

      <div className="visual-summary-grid">
        <div className="metric-item">
          <span className="metric-label">Generated</span>
          <strong>{result.number_of_chapters}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Processing time</span>
          <strong>{result.processing_time.toFixed(2)}s</strong>
        </div>
      </div>

      <div className="chapter-table-wrap">
        {chapters.length === 0 ? (
          <div className="visual-empty-state">No chapters were generated for this video.</div>
        ) : (
          <table className="chapter-table">
            <thead>
              <tr>
                <th>Start</th>
                <th>End</th>
                <th>Chapter</th>
                <th>Summary</th>
                <th>Objects</th>
              </tr>
            </thead>
            <tbody>
              {chapters.map((chapter) => (
                <tr key={`${chapter.chapter_number}-${chapter.start_time}-${chapter.end_time}`}>
                  <td>
                    <button type="button" className="speech-timestamp-button" onClick={() => onTimestampClick(chapter.start_time)}>
                      {formatTimestamp(chapter.start_time)}
                    </button>
                  </td>
                  <td>{formatTimestamp(chapter.end_time)}</td>
                  <td>
                    <strong>{chapter.title}</strong>
                    <div className="speech-segment-text">#{chapter.chapter_number}</div>
                  </td>
                  <td className="speech-segment-text">{chapter.summary}</td>
                  <td className="speech-segment-text">
                    {chapter.important_objects.length > 0
                      ? chapter.important_objects.map((item) => `${item.label} (${item.confidence.toFixed(2)})`).join(', ')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
