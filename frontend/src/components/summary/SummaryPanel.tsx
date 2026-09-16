import type { PreprocessingState, SummarizeVideoResponse } from '../../types/api';

interface SummaryPanelProps {
  videoId: string | null;
  result: SummarizeVideoResponse | null;
  error: string | null;
  state: PreprocessingState;
  selectedLength: 'short' | 'medium' | 'long';
  onGenerate: (length: 'short' | 'medium' | 'long') => void;
}

const summaryLengths = ['short', 'medium', 'long'] as const;

export function SummaryPanel({ videoId, result, error, state, selectedLength, onGenerate }: SummaryPanelProps) {
  const isBusy = state === 'in-progress';

  return (
    <section className="panel summary-panel">
      <div className="panel-heading">
        <h3>AI Summary</h3>
        <button
          type="button"
          className="secondary-button"
          onClick={() => onGenerate(selectedLength)}
          disabled={!videoId || isBusy}
        >
          {isBusy ? 'Generating...' : 'Generate Summary'}
        </button>
      </div>

      <p className="summary-text">
        {result?.summary_text ?? 'Upload a video and generate a summary using the backend summarization service.'}
      </p>

      {result ? (
        <div className="summary-meta" style={{ marginTop: '0.75rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <span>Length: {result.summary_length}</span>
          <span>Segments: {result.number_of_segments}</span>
          <span>Actual duration: {result.actual_summary_duration}s</span>
        </div>
      ) : null}

      {error ? <div className="upload-message error-message" style={{ marginTop: '0.75rem' }}>{error}</div> : null}

      <div className="summary-options" aria-label="Summary length">
        {summaryLengths.map((option) => (
          <button
            key={option}
            type="button"
            className={`summary-option ${selectedLength === option ? 'active' : ''}`}
            onClick={() => onGenerate(option)}
            disabled={!videoId || isBusy}
          >
            {option.charAt(0).toUpperCase() + option.slice(1)}
          </button>
        ))}
      </div>
    </section>
  );
}
