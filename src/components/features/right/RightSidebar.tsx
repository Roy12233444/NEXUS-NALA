import React from 'react';
import './RightSidebar.css';

const RightSidebar: React.FC = () => {
  return (
    <aside className="right-telemetry-sidebar">
      {/* 1. SAFETY GATES CARD */}
      <div className="v2-card">
        <div className="v2-card-header">
          <span>Safety Gates</span>
          <span className="v2-card-link">View All</span>
        </div>

        <div className="speedometer-grid">
          {/* Gauge 1 */}
          <div className="speedometer-item">
            <svg width="44" height="26" viewBox="0 0 50 30">
              <path d="M 5 25 A 20 20 0 0 1 45 25" fill="none" stroke="#1C2B3E" strokeWidth="5" />
              <path d="M 5 25 A 20 20 0 0 1 43 23" fill="none" stroke="#10B981" strokeWidth="5" />
            </svg>
            <span className="speedometer-label">Policy Compliance</span>
            <span className="speedometer-val">0.98</span>
            <span className="speedometer-badge ok">OK</span>
          </div>

          {/* Gauge 2 */}
          <div className="speedometer-item">
            <svg width="44" height="26" viewBox="0 0 50 30">
              <path d="M 5 25 A 20 20 0 0 1 45 25" fill="none" stroke="#1C2B3E" strokeWidth="5" />
              <path d="M 5 25 A 20 20 0 0 1 42 22" fill="none" stroke="#10B981" strokeWidth="5" />
            </svg>
            <span className="speedometer-label">Data Safety</span>
            <span className="speedometer-val">0.97</span>
            <span className="speedometer-badge ok">OK</span>
          </div>

          {/* Gauge 3 */}
          <div className="speedometer-item">
            <svg width="44" height="26" viewBox="0 0 50 30">
              <path d="M 5 25 A 20 20 0 0 1 45 25" fill="none" stroke="#1C2B3E" strokeWidth="5" />
              <path d="M 5 25 A 20 20 0 0 1 35 15" fill="none" stroke="#F59E0B" strokeWidth="5" />
            </svg>
            <span className="speedometer-label">Tool Risk</span>
            <span className="speedometer-val">0.84</span>
            <span className="speedometer-badge warn">WARN</span>
          </div>

          {/* Gauge 4 */}
          <div className="speedometer-item">
            <svg width="44" height="26" viewBox="0 0 50 30">
              <path d="M 5 25 A 20 20 0 0 1 45 25" fill="none" stroke="#1C2B3E" strokeWidth="5" />
              <path d="M 5 25 A 20 20 0 0 1 41 21" fill="none" stroke="#10B981" strokeWidth="5" />
            </svg>
            <span className="speedometer-label">Output Safety</span>
            <span className="speedometer-val">0.96</span>
            <span className="speedometer-badge ok">OK</span>
          </div>
        </div>
      </div>

      {/* 2. SYSTEM METRICS GRID (RTA Score, Context Budget, Checkpoint LSN, Handoff Ready) */}
      <div className="four-metrics-grid">
        {/* RTA Score */}
        <div className="metric-card-box">
          <div className="title"><span>RTA Score</span><span>ⓘ</span></div>
          <div className="big-val" style={{ color: '#00F2FE' }}>0.91</div>
          <div className="sub">High Reliability</div>
          <svg width="100%" height="18" style={{ marginTop: '2px' }}>
            <path d="M 0 12 L 15 5 L 30 14 L 45 8 L 60 12 L 75 4 L 90 15 L 105 7 L 120 10" fill="none" stroke="#00F2FE" strokeWidth="1.5" />
          </svg>
        </div>

        {/* Context Budget */}
        <div className="metric-card-box">
          <div className="title"><span>Context Budget</span></div>
          <div className="big-val" style={{ color: '#00F2FE' }}>68%</div>
          <div style={{ fontSize: '9px', color: '#64748B' }}>68,342 / 100,000 tokens</div>
        </div>

        {/* Checkpoint LSN */}
        <div className="metric-card-box">
          <div className="title"><span>Checkpoint LSN</span></div>
          <div className="big-val">000150</div>
          <div style={{ fontSize: '9px', color: '#64748B' }}>3m ago · Auto Every 5m</div>
        </div>

        {/* Handoff Ready */}
        <div className="metric-card-box">
          <div className="title"><span>Handoff Ready</span></div>
          <div className="big-val" style={{ color: '#10B981' }}>✓</div>
          <div className="sub">Ready · All criteria met</div>
        </div>
      </div>

      {/* 3. CHECKPOINTS TIMELINE CARD */}
      <div className="v2-card">
        <div className="v2-card-header">
          <span>Checkpoints</span>
          <span className="v2-card-link">View All</span>
        </div>

        <div className="checkpoint-timeline">
          <div className="timeline-item">
            <div className="timeline-left">
              <span className="timeline-dot"></span>
              <span style={{ color: '#00F2FE', fontWeight: 700 }}>000150</span>
              <span style={{ color: '#64748B' }}>10:32:41 AM</span>
            </div>
            <span style={{ color: '#94A3B8' }}>1.2 GB</span>
          </div>

          <div className="timeline-item">
            <div className="timeline-left">
              <span className="timeline-dot"></span>
              <span style={{ color: '#00F2FE', fontWeight: 700 }}>000145</span>
              <span style={{ color: '#64748B' }}>10:27:41 AM</span>
            </div>
            <span style={{ color: '#94A3B8' }}>1.1 GB</span>
          </div>

          <div className="timeline-item">
            <div className="timeline-left">
              <span className="timeline-dot"></span>
              <span style={{ color: '#00F2FE', fontWeight: 700 }}>000140</span>
              <span style={{ color: '#64748B' }}>10:22:41 AM</span>
            </div>
            <span style={{ color: '#94A3B8' }}>1.0 GB</span>
          </div>

          <div className="timeline-item">
            <div className="timeline-left">
              <span className="timeline-dot"></span>
              <span style={{ color: '#00F2FE', fontWeight: 700 }}>000135</span>
              <span style={{ color: '#64748B' }}>10:17:41 AM</span>
            </div>
            <span style={{ color: '#94A3B8' }}>980 MB</span>
          </div>
        </div>
      </div>

      {/* 4. TOOL ACTIVITY & SPARKLINES CARD */}
      <div className="v2-card">
        <div className="v2-card-header">
          <span>Tool Activity</span>
          <span className="v2-card-link">View All</span>
        </div>

        <div className="tool-telemetry-list">
          {/* Python REPL */}
          <div className="tool-telemetry-item">
            <div className="tool-info-left">
              <span>&lt;/&gt;</span>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 600, color: '#F1F5F9' }}>Python REPL</span>
                <span style={{ fontSize: '9px', color: '#64748B' }}>Code execution</span>
              </div>
            </div>
            <span style={{ fontSize: '9px', fontWeight: 700, color: '#10B981' }}>ACTIVE</span>
            <svg width="45" height="15"><path d="M 0 8 Q 10 2 20 10 T 40 4 L 45 8" fill="none" stroke="#00F2FE" strokeWidth="1.5" /></svg>
          </div>

          {/* File System */}
          <div className="tool-telemetry-item">
            <div className="tool-info-left">
              <span>📁</span>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 600, color: '#F1F5F9' }}>File System</span>
                <span style={{ fontSize: '9px', color: '#64748B' }}>Read/Write</span>
              </div>
            </div>
            <span style={{ fontSize: '9px', fontWeight: 700, color: '#10B981' }}>ACTIVE</span>
            <svg width="45" height="15"><path d="M 0 10 L 10 3 L 20 12 L 30 5 L 45 9" fill="none" stroke="#00F2FE" strokeWidth="1.5" /></svg>
          </div>

          {/* Search */}
          <div className="tool-telemetry-item">
            <div className="tool-info-left">
              <span>🔍</span>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 600, color: '#F1F5F9' }}>Search</span>
                <span style={{ fontSize: '9px', color: '#64748B' }}>Web / Docs</span>
              </div>
            </div>
            <span style={{ fontSize: '9px', fontWeight: 700, color: '#64748B' }}>IDLE</span>
            <svg width="45" height="15"><path d="M 0 10 L 45 10" fill="none" stroke="#64748B" strokeWidth="1.5" /></svg>
          </div>

          {/* Vector DB */}
          <div className="tool-telemetry-item">
            <div className="tool-info-left">
              <span>🛢️</span>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 600, color: '#F1F5F9' }}>Vector DB</span>
                <span style={{ fontSize: '9px', color: '#64748B' }}>Retrieval</span>
              </div>
            </div>
            <span style={{ fontSize: '9px', fontWeight: 700, color: '#10B981' }}>ACTIVE</span>
            <svg width="45" height="15"><path d="M 0 5 L 12 12 L 25 3 L 38 10 L 45 6" fill="none" stroke="#00F2FE" strokeWidth="1.5" /></svg>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default RightSidebar;
