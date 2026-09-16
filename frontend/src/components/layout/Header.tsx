export function Header() {
  return (
    <header className="topbar">
      <div className="topbar-title-wrap">
        <p className="eyebrow subtle-eyebrow">AI Video Analysis</p>
        <h2 className="topbar-title">Multimodal Research Dashboard</h2>
      </div>

      <div className="status-indicator" aria-label="System status">
        <span className="status-dot" />
        System Ready
      </div>
    </header>
  );
}
