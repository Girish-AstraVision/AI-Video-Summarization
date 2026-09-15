export function Header() {
  return (
    <header className="topbar">
      <div className="brand-block">
        <div className="brand-mark">A</div>
        <div>
          <div className="brand-name">AstraVision</div>
          <div className="brand-subtitle">AI Video Intelligence Platform</div>
        </div>
      </div>

      <div className="status-indicator" aria-label="System status">
        <span className="status-dot" />
        System Ready
      </div>
    </header>
  );
}
