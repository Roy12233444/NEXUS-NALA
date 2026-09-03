import React from 'react';
import './CenterColumn.css';

const CenterColumn: React.FC = () => {
  return (
    <div className="command-center-container">
      {/* COMMAND CENTER CARD */}
      <div className="drishti-card" style={{ flex: 1 }}>
        <div className="drishti-card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🎯 COMMAND CENTER</span>
            <span style={{ color: '#64748B' }}>|</span>
            <span style={{ color: '#94A3B8' }}>LIVE TASK GRAPH (GEN-07)</span>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button className="drishti-btn">AUTO-FIT</button>
            <button className="drishti-btn">⤢</button>
          </div>
        </div>

        <div className="drishti-card-body" style={{ padding: '8px' }}>
          {/* Legend Filter Bar */}
          <div className="graph-legend-bar">
            <span className="legend-item pending">○ PENDING</span>
            <span className="legend-item running">◎ RUNNING</span>
            <span className="legend-item success">● SUCCESS</span>
            <span className="legend-item failed">⊗ FAILED</span>
            <span className="legend-item handoff">◇ HANDOFF POINT</span>
          </div>

          {/* Graph Canvas */}
          <div className="graph-canvas-area">
            <div className="node-flow-wrapper">
              {/* Node 1 */}
              <div className="node-box success">
                <span>✓ soak_step_0838</span>
                <span style={{ fontSize: '8.5px' }}>SUCCESS</span>
              </div>
              <div className="connector-line active"></div>

              {/* Node 2 */}
              <div className="node-box success">
                <span>✓ soak_step_0839</span>
                <span style={{ fontSize: '8.5px' }}>SUCCESS</span>
              </div>
              <div className="connector-line active"></div>

              {/* Node 3 */}
              <div className="node-box running">
                <span>C soak_step_0840</span>
                <span style={{ fontSize: '8.5px' }}>RUNNING</span>
              </div>
              <div className="connector-line active"></div>

              {/* Branch Row */}
              <div className="node-row-branch">
                <div className="node-box success" style={{ minWidth: '130px' }}>
                  <span>✓ soak_step_0841</span>
                </div>
                <div className="node-box running" style={{ minWidth: '130px' }}>
                  <span>C soak_step_0842</span>
                </div>
                <div className="node-box success" style={{ minWidth: '130px' }}>
                  <span>✓ soak_step_0843</span>
                </div>
              </div>
              <div className="connector-line"></div>

              {/* Diamond Join */}
              <div className="node-diamond">
                <span>☍</span>
              </div>
              <span style={{ fontSize: '8px', color: '#64748B', fontWeight: 700, marginTop: '-6px' }}>join_0844 PENDING</span>
              <div className="connector-line"></div>

              {/* Node Pending 1 */}
              <div className="node-box pending" style={{ minWidth: '140px' }}>
                <span>⊗ soak_step_0845</span>
                <span style={{ fontSize: '8.5px' }}>PENDING</span>
              </div>

              {/* Node Pending 2 */}
              <div className="node-box pending" style={{ minWidth: '140px' }}>
                <span>○ soak_step_0846</span>
                <span style={{ fontSize: '8.5px' }}>PENDING</span>
              </div>
            </div>

            {/* Bottom Floating Minimap & Inspector */}
            <div className="graph-bottom-widgets">
              {/* Minimap */}
              <div className="minimap-box">
                <div style={{ fontSize: '7.5px', color: '#64748B', fontWeight: 700 }}>GRAPH OVERVIEW</div>
                <div style={{ border: '1px solid #00F0FF', width: '100%', height: '40px', marginTop: '4px', background: 'rgba(0, 240, 255, 0.05)', borderRadius: '2px' }}></div>
              </div>

              {/* Step Details Inspector */}
              <div className="inspector-box">
                <div style={{ color: '#00F0FF', fontWeight: 800, borderBottom: '1px solid #1E3A5F', paddingBottom: '4px', marginBottom: '4px' }}>
                  STEP DETAILS
                </div>
                <div className="inspector-row"><span>Step ID:</span><span className="val" style={{ color: '#00F0FF' }}>soak_step_0842</span></div>
                <div className="inspector-row"><span>Status:</span><span className="val" style={{ color: '#00F0FF' }}>RUNNING</span></div>
                <div className="inspector-row"><span>Start Time:</span><span className="val">21:44:59</span></div>
                <div className="inspector-row"><span>Duration:</span><span className="val">00:00:02</span></div>
                <div className="inspector-row"><span>Phase:</span><span className="val">3</span></div>
                <div className="inspector-row"><span>Tokens In:</span><span className="val">12,431</span></div>
                <div className="inspector-row"><span>Tokens Out:</span><span className="val">8,192</span></div>
                <div className="inspector-row"><span>Cost (USD):</span><span className="val" style={{ color: '#00FF9D' }}>$0.01247</span></div>
                <button className="drishti-btn" style={{ marginTop: '6px', justifyContent: 'center' }}>VIEW FULL CONTEXT ↗</button>
              </div>
            </div>
          </div>

          {/* Bottom Tasks Queue Ribbon */}
          <div className="queue-ribbon">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📦 TASKS IN QUEUE: <span style={{ color: '#00F0FF' }}>8</span></span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: '#94A3B8' }}>
              <span>COMPACT MODE: <span style={{ color: '#00FF9D' }}>STAGE 2</span></span>
              <span>LAST COMPACTION: <span>21:44:56</span></span>
              <span>NEXT ETA: <span style={{ color: '#FFB800' }}>~ 02:15</span></span>
            </div>
            <button className="drishti-btn">FORCE COMPACTION</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CenterColumn;
