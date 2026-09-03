import React from 'react';
import './LeftColumn.css';

const generationsData = [
  { gen: 'GEN-07', live: true, session: '550e8400-e29b...', range: '14848 +', steps: 842, status: 'RUNNING', pill: 'running' },
  { gen: 'GEN-06', live: false, session: '550e8400-e29b...', range: '12801-14847', steps: 1046, status: 'SUCCESS', pill: 'success' },
  { gen: 'GEN-05', live: false, session: '550e8400-e29b...', range: '8961-12800', steps: 1180, status: 'SUCCESS', pill: 'success' },
  { gen: 'GEN-04', live: false, session: '550e8400-e29b...', range: '5121-8960', steps: 1840, status: 'HANDOFF', pill: 'handoff' },
  { gen: 'GEN-03', live: false, session: '550e8400-e29b...', range: '2561-5120', steps: 1260, status: 'SUCCESS', pill: 'success' },
  { gen: 'GEN-02', live: false, session: '550e8400-e29b...', range: '1201-2560', steps: 1360, status: 'HANDOFF', pill: 'handoff' },
  { gen: 'GEN-01', live: false, session: '550e8400-e29b...', range: '1-1200', steps: 1200, status: 'SUCCESS', pill: 'success' },
];

const eventLogs = [
  { time: '21:44:59', type: 'STEP STARTED', typeCls: 'running', icon: '▶', details: 'soak_step_0842' },
  { time: '21:44:59', type: 'METRICS SAMPLE', typeCls: 'running', icon: '📈', details: 'RSS: 312.6 MB | CPU: 18%' },
  { time: '21:44:58', type: 'CHECKPOINT WRITTEN', typeCls: 'success', icon: '✓', details: 'LSN 14847' },
  { time: '21:44:58', type: 'STEP SUCCESS', typeCls: 'success', icon: '✓', details: 'soak_step_0841' },
  { time: '21:44:56', type: 'COMPACTION TRIGGERED', typeCls: 'warning', icon: '⚙', details: 'Stage 2 Compaction' },
  { time: '21:44:55', type: 'MEMORY WARNING', typeCls: 'warning', icon: '⚠', details: 'Context 85%' },
  { time: '21:44:54', type: 'HANDOFF COMPLETE', typeCls: 'running', icon: '🚀', details: 'To GEN-07' },
  { time: '21:44:50', type: 'GENERATION SPAWNED', typeCls: 'success', icon: '⚡', details: 'GEN-07 (fresh_initial)' },
  { time: '21:44:50', type: 'SUPERVISOR HEARTBEAT', typeCls: 'success', icon: '♥', details: 'All systems nominal' },
  { time: '21:44:48', type: 'LOCKS RESOLVED', typeCls: 'success', icon: '🔒', details: 'Stale locks: 2' },
];

const LeftColumn: React.FC = () => {
  return (
    <div className="left-column-container">
      {/* 1. GENERATION LEDGER CARD */}
      <div className="drishti-card" style={{ flex: '1.2' }}>
        <div className="drishti-card-header">
          <span>❖ GENERATION LEDGER</span>
        </div>
        <div className="drishti-card-body">
          {/* Summary Pills */}
          <div className="ledger-summary">
            <div className="summary-stat">
              <span className="label">TOTAL GENERATIONS</span>
              <span className="val">7</span>
            </div>
            <div className="summary-stat">
              <span className="label">SUCCESSFUL</span>
              <span className="val" style={{ color: '#00FF9D' }}>5</span>
            </div>
            <div className="summary-stat">
              <span className="label">HANDOFFS</span>
              <span className="val" style={{ color: '#FFB800' }}>4</span>
            </div>
          </div>

          {/* Table */}
          <table className="ledger-table">
            <thead>
              <tr>
                <th>GENERATION</th>
                <th>LSN RANGE</th>
                <th>STEPS</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {generationsData.map((row) => (
                <tr key={row.gen}>
                  <td>
                    <span className={`gen-tag ${row.live ? 'live' : ''}`}>
                      ● {row.gen}
                    </span>
                  </td>
                  <td style={{ color: '#94A3B8' }}>{row.range}</td>
                  <td>{row.steps}</td>
                  <td>
                    <span className={`status-pill ${row.pill}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. EVENT LOG CARD */}
      <div className="drishti-card" style={{ flex: '1' }}>
        <div className="drishti-card-header">
          <span>⚡ EVENT LOG (CHRONOLOGICAL)</span>
          <span style={{ color: '#00FF9D', fontSize: '9px' }}>● LIVE</span>
        </div>
        <div className="drishti-card-body">
          <div className="event-log-list">
            {eventLogs.map((log, idx) => (
              <div key={idx} className="event-log-item">
                <span className="time">{log.time}</span>
                <span className={`type ${log.typeCls}`}>
                  <span>{log.icon}</span> {log.type}
                </span>
                <span className="details">{log.details}</span>
              </div>
            ))}
          </div>
          <button className="drishti-btn" style={{ marginTop: 'auto', width: '100%', justifyContent: 'center' }}>
            VIEW FULL LOGS ↗
          </button>
        </div>
      </div>
    </div>
  );
};

export default LeftColumn;
