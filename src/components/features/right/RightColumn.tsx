import React from 'react';
import './RightColumn.css';

const RightColumn: React.FC = () => {
  return (
    <div className="right-column-container">
      {/* 1. TELEMETRY CARD */}
      <div className="drishti-card" style={{ flex: '1' }}>
        <div className="drishti-card-header">
          <span>📡 TELEMETRY</span>
          <span style={{ color: '#00F0FF', fontSize: '9px' }}>LIVE (10s) ▾</span>
        </div>
        <div className="drishti-card-body">
          {/* Memory RSS */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', fontWeight: 700 }}>
              <span style={{ color: '#64748B' }}>MEMORY RSS (MB)</span>
              <span style={{ color: '#00F0FF' }}>312.6 MB <span style={{ color: '#64748B' }}>MAX 512.0 MB</span></span>
            </div>
            {/* SVG Sparkline Graph */}
            <svg width="100%" height="45" style={{ marginTop: '4px' }}>
              <path
                d="M 0 25 Q 40 15 80 28 T 160 20 T 240 25 T 300 22 L 300 45 L 0 45 Z"
                fill="rgba(0, 240, 255, 0.15)"
                stroke="#00F0FF"
                strokeWidth="1.5"
              />
            </svg>
          </div>

          {/* CPU Utilization */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', fontWeight: 700 }}>
              <span style={{ color: '#64748B' }}>CPU UTILIZATION (%)</span>
              <span style={{ color: '#00FF9D' }}>18.0 % <span style={{ color: '#64748B' }}>MAX 72%</span></span>
            </div>
            {/* SVG Line Graph */}
            <svg width="100%" height="40" style={{ marginTop: '4px' }}>
              <path
                d="M 0 30 L 30 20 L 60 35 L 90 15 L 120 28 L 150 18 L 180 32 L 210 12 L 240 25 L 270 20 L 300 28"
                fill="none"
                stroke="#00FF9D"
                strokeWidth="1.5"
              />
              <circle cx="300" cy="28" r="3" fill="#00FF9D" />
            </svg>
          </div>

          {/* Telemetry Stats Grid */}
          <div className="telemetry-grid">
            <div className="telemetry-stat-item">
              <span className="label">OPEN FILE DESCRIPTORS</span>
              <span className="val">📁 128</span>
            </div>
            <div className="telemetry-stat-item">
              <span className="label">THREADS</span>
              <span className="val">⚙ 18</span>
            </div>
            <div className="telemetry-stat-item">
              <span className="label">IO READ (kB/s)</span>
              <span className="val" style={{ color: '#00F0FF' }}>312.4</span>
            </div>
            <div className="telemetry-stat-item">
              <span className="label">IO WRITE (kB/s)</span>
              <span className="val" style={{ color: '#00FF9D' }}>1024.8</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. MEMORY GOVERNANCE CARD */}
      <div className="drishti-card" style={{ flex: '1.4' }}>
        <div className="drishti-card-header">
          <span>🛡️ MEMORY GOVERNANCE</span>
          <button className="drishti-btn">DETAILS</button>
        </div>
        <div className="drishti-card-body">
          <div style={{ fontSize: '8.5px', color: '#64748B', fontWeight: 700 }}>CONTEXT WINDOW STATUS: <span style={{ color: '#00F0FF' }}>128K TOKENS</span></div>

          {/* Radial Donut Ring Gauge */}
          <div className="donut-gauge-wrapper">
            <svg width="120" height="120" viewBox="0 0 120 120">
              {/* Background Ring */}
              <circle cx="60" cy="60" r="48" fill="none" stroke="#0E1A38" strokeWidth="10" />
              {/* Segmented Ring fill (85%) */}
              <circle
                cx="60" cy="60" r="48"
                fill="none"
                stroke="#FFB800"
                strokeWidth="10"
                strokeDasharray="255 301"
                strokeDashoffset="0"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div className="donut-center-text">
              <div className="pct">85%</div>
              <div className="sub">109,240 / 128,000</div>
              <div className="sub" style={{ fontSize: '7px' }}>TOKENS USED</div>
            </div>
          </div>

          {/* Breakdown Table */}
          <table className="breakdown-table">
            <tbody>
              <tr>
                <td><span className="dot" style={{ background: '#00F0FF' }}></span>SYSTEM PROMPT</td>
                <td className="val">8,192 (6.4%)</td>
              </tr>
              <tr>
                <td><span className="dot" style={{ background: '#00FF9D' }}></span>MEMORY</td>
                <td className="val">28,672 (22.4%)</td>
              </tr>
              <tr>
                <td><span className="dot" style={{ background: '#38BDF8' }}></span>TASK CONTEXT</td>
                <td className="val">42,813 (33.5%)</td>
              </tr>
              <tr>
                <td><span className="dot" style={{ background: '#A855F7' }}></span>TOOL OUTPUTS</td>
                <td className="val">18,947 (14.8%)</td>
              </tr>
              <tr>
                <td><span className="dot" style={{ background: '#E2E8F0' }}></span>HISTORY</td>
                <td className="val">10,616 (8.3%)</td>
              </tr>
              <tr>
                <td><span className="dot" style={{ background: '#334155' }}></span>RESERVED</td>
                <td className="val">- (14.6%)</td>
              </tr>
            </tbody>
          </table>

          {/* Compacting Alert Banner */}
          <div className="compacting-banner">
            <span style={{ fontSize: '14px' }}>⚠️</span>
            <div>
              <div>COMPACTING</div>
              <div style={{ fontSize: '8.5px', color: '#94A3B8', fontWeight: 500 }}>Stage 2 compaction in progress</div>
            </div>
          </div>

          {/* Governance Policy */}
          <div className="policy-list">
            <div className="policy-item"><span>COMPACTION THRESHOLD:</span><span className="val">80%</span></div>
            <div className="policy-item"><span>HARD LIMIT:</span><span className="val" style={{ color: '#FF3366' }}>95%</span></div>
            <div className="policy-item"><span>AUTO COMPACTION:</span><span className="val" style={{ color: '#00FF9D' }}>ENABLED</span></div>
            <div className="policy-item"><span>ORPHAN TOKENS:</span><span className="val">0</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RightColumn;
