import React, { useState } from 'react';
import './RunLogs.css';

const sampleLogs = [
  { time: '10:32:41', level: 'INFO', msg: 'Checkpoint 000150 created (LSN advanced)' },
  { time: '10:32:39', level: 'INFO', msg: 'Step 2.3 completed: Baseline run finished (acc=0.842)' },
  { time: '10:32:38', level: 'INFO', msg: 'Evaluation completed on CLRS validation set' },
  { time: '10:31:12', level: 'INFO', msg: 'Started baseline run: GPT-4o, top-k=5, temp=0.2' },
  { time: '10:31:11', level: 'DEBUG', msg: 'Retrieved 128 documents (top-k=5)' },
  { time: '10:31:10', level: 'INFO', msg: 'Tool: Vector DB query' },
  { time: '10:31:09', level: 'INFO', msg: 'Tool: File read results/config.json' },
  { time: '10:31:09', level: 'INFO', msg: 'Step 2.3 started: Run baseline experiment' },
];

const RunLogs: React.FC = () => {
  const [autoScroll, setAutoScroll] = useState(true);

  return (
    <div className="run-logs-card">
      <div className="logs-top-bar">
        <span className="logs-title">Run Logs</span>
        <div className="logs-controls">
          <select style={{ background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '11px', padding: '2px 6px', borderRadius: '4px' }}>
            <option>All Levels</option>
            <option>INFO</option>
            <option>DEBUG</option>
          </select>
          <input type="text" className="logs-search" placeholder="Search logs..." />
          <button style={{ background: 'var(--bg-input)', border: '1px solid var(--border-subtle)', color: '#94A3B8', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer' }}>⏸</button>
        </div>
      </div>

      <div className="logs-console">
        {sampleLogs.map((log, idx) => (
          <div key={idx} className="log-entry">
            <span className="log-time">{log.time}</span>
            <span className={`log-level ${log.level}`}>{log.level}</span>
            <span className="log-msg">{log.msg}</span>
          </div>
        ))}
      </div>

      <div className="logs-footer">
        <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981' }}></span>
          Streaming...
        </span>
        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
          <span>Auto-scroll</span>
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
        </label>
      </div>
    </div>
  );
};

export default RunLogs;
