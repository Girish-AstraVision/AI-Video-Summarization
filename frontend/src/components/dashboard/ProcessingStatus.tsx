import type { ProcessingStep } from '../../types/dashboard';

type ProcessingStatusProps = {
  steps: ProcessingStep[];
};

export function ProcessingStatus({ steps }: ProcessingStatusProps) {
  return (
    <section className="panel status-panel">
      <div className="panel-heading inline-heading">
        <h3>Processing Status</h3>
      </div>

      <div className="processing-steps" aria-label="Pipeline status">
        {steps.map((step) => (
          <div key={step.name} className="processing-step">
            <div className="step-indicator-group">
              <span className={`step-dot ${step.status.toLowerCase().replace(/\s+/g, '-')}`} />
              <div className="step-line" />
            </div>
            <div className="step-content">
              <div className="step-name-row">
                <span>{step.name}</span>
                <span className={`step-state ${step.status.toLowerCase().replace(/\s+/g, '-')}`}>
                  {step.status}
                </span>
              </div>
              <div className="step-track">
                <span style={{ width: `${step.value}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
