import React from 'react';

interface SidebarProps {
  onBackToWebsite?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onBackToWebsite }) => {
  return (
    <aside className="v2-sidebar">
      <div className="sidebar-top">
        <div
          className="sidebar-brand"
          style={{ cursor: 'pointer' }}
          onClick={onBackToWebsite}
          title="Click to go back to NALA Research Website"
        >
          <div className="brand-title">
            <span>NALA</span>
            <span className="brand-title-dot"></span>
          </div>
          <div className="brand-sub">Sovereign Control Center</div>
        </div>

        {/* Back to Website Button */}
        <button
          onClick={onBackToWebsite}
          style={{
            background: 'var(--color-saffron)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            align-items: 'center',
            justify-content: 'center',
            gap: '6px',
            transition: 'all 0.2s ease',
            marginBottom: '4px',
            boxShadow: '0 2px 8px rgba(232, 121, 26, 0.2)',
          }}
        >
          <span>← Back to NALA Website</span>
        </button>

        <nav className="sidebar-menu">
          {/* Dashboard */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
            </svg>
            <span>Dashboard</span>
          </div>

          {/* Chat (Active) */}
          <div className="menu-item active">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>Chat</span>
          </div>

          {/* Runs */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <circle cx="12" cy="12" r="10"/>
              <polygon points="10 8 16 12 10 16 10 8" fill="currentColor"/>
            </svg>
            <span>Runs</span>
          </div>

          {/* Tasks */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
            <span>Tasks</span>
          </div>

          {/* Tools */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            <span>Tools</span>
          </div>

          {/* Memory */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M6 19v-3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v3"/>
              <path d="M6 5v3a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V5"/>
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
            </svg>
            <span>Memory</span>
          </div>

          {/* Checkpoints */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            <span>Checkpoints</span>
          </div>

          {/* Safety */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            <span>Safety</span>
          </div>

          {/* Evaluations */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <line x1="18" y1="20" x2="18" y2="10"/>
              <line x1="12" y1="20" x2="12" y2="4"/>
              <line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
            <span>Evaluations</span>
          </div>

          {/* Alerts */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>Alerts</span>
          </div>

          {/* Settings */}
          <div className="menu-item">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>Settings</span>
          </div>
        </nav>
      </div>

      <div className="sidebar-bottom">
        <div className="version-tag">
          <span className="version-dot"></span>
          <span>NALA Core v1.3.2</span>
        </div>

        <div className="profile-card">
          <div className="profile-avatar">AR</div>
          <div className="profile-info">
            <span className="profile-name">A. Researcher</span>
            <span className="profile-role">admin</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
