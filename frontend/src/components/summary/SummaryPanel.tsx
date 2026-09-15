export function SummaryPanel() {
  return (
    <section className="panel summary-panel">
      <div className="panel-heading">
        <h3>AI Summary</h3>
        <button type="button" className="secondary-button">
          Generate Summary
        </button>
      </div>

      <p className="summary-text">
        The clip focuses on a guided product presentation, highlighting the primary subject in the
        foreground while discussing usage, key benefits, and operational details. The transcript and
        visual cues indicate a structured walkthrough with a moderate number of object mentions and a
        clear emphasis on the featured device and supporting scene transitions.
      </p>

      <div className="summary-options" aria-label="Summary length">
        {['Short', 'Medium', 'Long'].map((option, index) => (
          <button
            key={option}
            type="button"
            className={`summary-option ${index === 1 ? 'active' : ''}`}
          >
            {option}
          </button>
        ))}
      </div>
    </section>
  );
}
