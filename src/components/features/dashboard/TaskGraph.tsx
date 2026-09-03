import React from 'react';
import './TaskGraph.css';

const TaskGraph: React.FC = () => {
  return (
    <div className="task-graph-card">
      <div className="graph-top-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '14px', color: '#111827' }}>
          <span>Task Pipeline Graph</span>
          <span style={{ fontSize: '11px', color: 'rgba(17, 24, 39, 0.4)' }}>ⓘ</span>
        </div>
        <div className="graph-legend-group">
          <span><span className="legend-dot" style={{ background: '#059669' }}></span>Completed</span>
          <span><span className="legend-dot" style={{ background: '#E8791A' }}></span>In Progress</span>
          <span><span className="legend-dot" style={{ background: 'rgba(17, 24, 39, 0.3)' }}></span>Pending</span>
          <span><span className="legend-dot" style={{ background: '#DC2626' }}></span>Blocked</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={{ background: '#FAF9F6', border: '1px solid rgba(17, 24, 39, 0.12)', color: '#111827', fontSize: '11px', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>Fit</button>
          <button style={{ background: '#FAF9F6', border: '1px solid rgba(17, 24, 39, 0.12)', color: '#111827', fontSize: '11px', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>🔍+</button>
          <button style={{ background: '#FAF9F6', border: '1px solid rgba(17, 24, 39, 0.12)', color: '#111827', fontSize: '11px', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>🔍-</button>
          <button style={{ background: '#FAF9F6', border: '1px solid rgba(17, 24, 39, 0.12)', color: '#111827', fontSize: '11px', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}>Expand</button>
        </div>
      </div>

      <div className="graph-flow-container">
        {/* Main Phase Line */}
        <div className="graph-main-row">
          <div className="v2-node completed">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Phase 1</span>
            <span>Setup</span>
            <span style={{ fontSize: '10px', fontWeight: 700, marginTop: '2px' }}>6 / 6 ✓</span>
          </div>

          <span className="v2-arrow active">➔</span>

          <div className="v2-node in-progress">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Phase 2</span>
            <span>Replication</span>
            <span style={{ fontSize: '10px', fontWeight: 700, marginTop: '2px' }}>3 / 6</span>
          </div>

          <span className="v2-arrow">➔</span>

          <div className="v2-node pending">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Phase 3</span>
            <span>Ablations</span>
            <span style={{ fontSize: '10px', marginTop: '2px' }}>0 / 9</span>
          </div>

          <span className="v2-arrow">➔</span>

          <div className="v2-node pending">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Phase 4</span>
            <span>Analysis</span>
            <span style={{ fontSize: '10px', marginTop: '2px' }}>0 / 6</span>
          </div>

          <span className="v2-arrow">➔</span>

          <div className="v2-node pending">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Phase 5</span>
            <span>Report</span>
            <span style={{ fontSize: '10px', marginTop: '2px' }}>0 / 4</span>
          </div>
        </div>

        {/* Branch Pipeline Line */}
        <div className="graph-branch-row">
          <span className="v2-arrow active" style={{ transform: 'rotate(90deg)', marginRight: '8px' }}>↳</span>
          <div className="v2-node in-progress">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Baseline Runs</span>
            <span style={{ fontSize: '10px', fontWeight: 700, marginTop: '2px' }}>3 / 6</span>
          </div>

          <span className="v2-arrow">➔</span>

          <div className="v2-node pending">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Results Aggregation</span>
            <span style={{ fontSize: '10px', marginTop: '2px' }}>0 / 2</span>
          </div>

          <span className="v2-arrow">➔</span>

          <div className="v2-node pending">
            <span style={{ fontSize: '13px', fontWeight: 700 }}>Sanity Checks</span>
            <span style={{ fontSize: '10px', marginTop: '2px' }}>0 / 2</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskGraph;
