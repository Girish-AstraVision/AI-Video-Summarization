import type { SpeechToTextResult } from '../../types/api';

type SpeechTranscriptPanelProps = {
  result: SpeechToTextResult;
  onTimestampClick: (timestamp: number) => void;
  isVisible: boolean;
};

function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

export function SpeechTranscriptPanel({ result, onTimestampClick, isVisible }: SpeechTranscriptPanelProps) {
  if (!isVisible) {
    return null;
  }

  const segments = [...result.segments].sort((a, b) => a.start - b.start);

  return (
    <section className="panel speech-transcript-panel" aria-live="polite">
      <div className="panel-heading inline-heading">
        <h3>Speech Transcript</h3>
      </div>

      <div className="visual-summary-grid">
        <div className="metric-item">
          <span className="metric-label">Number of segments</span>
          <strong>{result.number_of_segments}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Detected language</span>
          <strong>{result.detected_language}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Language probability</span>
          <strong>{result.language_probability.toFixed(2)}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Processing time</span>
          <strong>{result.processing_time.toFixed(2)}s</strong>
        </div>
      </div>

      <div className="speech-transcript-meta" aria-label="Speech model metadata">
        <span className="meta-label">Model</span>
        <strong>{result.model_name}</strong>
      </div>

      <div className="speech-segment-list" aria-label="Speech transcript segments">
        {segments.length === 0 ? (
          <div className="visual-empty-state">No speech segments were detected.</div>
        ) : (
          segments.map((segment) => (
            <article key={segment.segment_number} className="speech-segment-item">
              <button
                type="button"
                className="speech-timestamp-button"
                onClick={() => onTimestampClick(segment.start)}
                aria-label={`Seek to ${formatTimestamp(segment.start)}`}
              >
                {formatTimestamp(segment.start)} → {formatTimestamp(segment.end)}
              </button>
              <p className="speech-segment-text">{segment.text}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
