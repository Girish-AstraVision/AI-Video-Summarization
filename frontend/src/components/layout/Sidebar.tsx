type NavItem = {
  label: string;
  active?: boolean;
};

const navItems: NavItem[] = [
  { label: 'Dashboard', active: true },
  { label: 'Video Analysis' },
  { label: 'Summarization' },
  { label: 'Chapters' },
  { label: 'Key Frames' },
  { label: 'Moderation' },
  { label: 'Event Timeline' },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav" aria-label="Sidebar navigation">
        {navItems.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`nav-item ${item.active ? 'active' : ''}`}
            aria-current={item.active ? 'page' : undefined}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
