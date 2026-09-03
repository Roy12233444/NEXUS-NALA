import React from 'react';
import { useAppState } from '../../../hooks/useAppState';
import './ToolActivityPanel.css';

const ToolActivityPanel: React.FC = () => {
  const { getToolPredictions, getToolWarmingStatus, getToolUsageStats } = useAppState();

  const toolPredictions = getToolPredictions();
  const toolWarmingStatus = getToolWarmingStatus();
  const toolUsageStats = getToolUsageStats();

  return (
    <div className="tool-activity-panel">
      <h2 className="section-title">Tool Activity & Predictions</h2>
      <div className="tool-activity-content">
        {/* Tool Predictions */}
        <div className="activity-section">
          <h3>Top Predictions</h3>
          {toolPredictions.length > 0 ? (
            <ul className="predictions-list">
              {toolPredictions.slice(0, 5).map((pred, index) => (
                <li key={pred.toolName + index} className="prediction-item">
                  <div className="prediction-info">
                    <span className="tool-name">{pred.toolName}</span>
                    <span className={`confidence-badge confidence-${Math.floor(pred.confidence * 100)}`}>
                      {(pred.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="prediction-details">
                    <span className="latency-reduction">-{pred.estimatedLatencyReduction.toFixed(1)}s latency</span>
                    {pred.reasoning.length > 0 && (
                      <span className="reasoning-tag"> {pred.reasoning[0]}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-data">No predictions available</p>
          )}
        </div>

        {/* Tool Warming Status */}
        <div className="activity-section">
          <h3>Tool Warming Status</h3>
          {Object.keys(toolWarmingStatus).length > 0 ? (
            <div className="warming-status-grid">
              {Object.entries(toolWarmingStatus).map(([toolName, instances]) => (
                <div key={toolName} className="tool-warming-status">
                  <div className="tool-header">
                    <span className="tool-name">{toolName}</span>
                    <span className="instance-count">({instances.length} instances)</span>
                  </div>
                  <div className="instances-list">
                    {instances.map((instance) => (
                      <div key={instance.instanceId} className={`instance-status ${instance.ready ? 'ready' : 'warming'}`}>
                        <span className="instance-id">{instance.instanceId.slice(-8)}</span>
                        <span className={`status-dot ${instance.ready ? 'ready' : 'warming'}`}></span>
                        <span className="status-text">{instance.ready ? 'Ready' : 'Warming...'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No tools in warming status</p>
          )}
        </div>

        {/* Tool Usage Statistics */}
        <div className="activity-section">
          <h3>Usage Statistics</h3>
          {Object.keys(toolUsageStats).length > 0 ? (
            <ul className="usage-stats-list">
              {Object.entries(toolUsageStats).map(([toolName, stats]) => (
                <li key={toolName} className="usage-stat-item">
                  <span className="tool-name">{toolName}</span>
                  <span className="usage-count">{stats.count} uses</span>
                  {stats.totalLatency > 0 && (
                    <span className="avg-latency"> (avg: {(stats.totalLatency / stats.count).toFixed(1)}ms)</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-data">No usage statistics available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ToolActivityPanel;