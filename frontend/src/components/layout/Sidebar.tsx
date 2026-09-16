type NavItem = {
  label: string;
  id: string;
};

const navItems: NavItem[] = [
  { label: 'Dashboard', id: 'dashboard' },
  { label: 'Video Analysis', id: 'video-analysis' },
  { label: 'Summarization', id: 'summarization' },
  { label: 'Chapters', id: 'chapters' },
  { label: 'Key Frames', id: 'key-frames' },
  { label: 'Moderation', id: 'moderation' },
  { label: 'Event Timeline', id: 'event-timeline' },
];

type SidebarProps = {
  activeSection: string;
  onNavigate: (sectionId: string) => void;
};

export function Sidebar({ activeSection, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav" aria-label="Sidebar navigation">
        {navItems.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
            aria-current={activeSection === item.id ? 'page' : undefined}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
