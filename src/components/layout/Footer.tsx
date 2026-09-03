import React from 'react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="drishti-footer">
      <div className="footer-item">
        <span className="icon">📋</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">SESSION ID</span>
          <span className="val" style={{ color: '#00F0FF' }}>550e8400-e29b-4d4a-a716-446655440007</span>
        </div>
      </div>

      <div className="footer-item">
        <span className="icon">🚀</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">SPAWN REASON</span>
          <span className="val">fresh_initial</span>
        </div>
      </div>

      <div className="footer-item">
        <span className="icon">💾</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">CHECKPOINT DIR</span>
          <span className="val">./checkpoints</span>
        </div>
      </div>

      <div className="footer-item">
        <span className="icon">⚙</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">CONFIG</span>
          <span className="val">soak_config.yaml</span>
        </div>
      </div>

      <div className="footer-item">
        <span className="icon">🔒</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">LOG LEVEL</span>
          <span className="val" style={{ color: '#00FF9D' }}>INFO</span>
        </div>
      </div>

      <div className="footer-item">
        <span className="icon">♥</span>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="label">HEARTBEAT</span>
          <span className="val" style={{ color: '#00FF9D' }}>21:45:01 100%</span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;