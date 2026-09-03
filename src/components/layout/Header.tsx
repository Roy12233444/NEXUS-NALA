import React, { useState, useEffect } from 'react';

interface HeaderProps {
  onBackToWebsite?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onBackToWebsite }) => {
  const [elapsed, setElapsed] = useState('04:23:17');

  useEffect(() => {
    let seconds = 15797; // 4h 23m 17s
    const timer = setInterval(() => {
      seconds += 1;
      const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
      const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
      const s = String(seconds % 60).padStart(2, '0');
      setElapsed(`${h}:${m}:${s}`);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="v2-top-header">
      {/* Left: Mission & Run Status */}
      <div className="header-left-group">
        <div className="run-status-pill">
          <span className="status-pulse-dot"></span>
          <span>RUNNING</span>
        </div>

        <div className="header-divider"></div>

        <div className="mission-info-box">
          <span className="mission-label">CURRENT MISSION</span>
          <span className="mission-text">Replicate & extend key results from Brown et al. (2024)</span>
        </div>
      </div>

      {/* Center: Live Telemetry */}
      <div className="header-center-metrics">
        <div className="header-metric">
          <span className="metric-tag">ELAPSED</span>
          <span className="metric-value">{elapsed}</span>
        </div>
        <div className="header-metric">
          <span className="metric-tag">AGENT</span>
          <span className="metric-value">NALA v1.3</span>
        </div>
        <div className="header-metric">
          <span className="metric-tag">MODE</span>
          <span className="metric-value highlight">AUTONOMOUS</span>
        </div>
      </div>

      {/* Right: Action Buttons */}
      <div className="header-right-actions">
        <button className="btn-header-website" onClick={onBackToWebsite}>
          <span>🌐</span>
          <span>Back to Website</span>
        </button>
        <button className="btn-header-secondary">⏸ Pause</button>
        <button className="btn-header-danger">⛔ Stop</button>
      </div>
    </header>
  );
};

export default Header;