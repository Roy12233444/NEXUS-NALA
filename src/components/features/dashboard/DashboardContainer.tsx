import React from 'react';
import SafetyGauges from './SafetyGauges';
import ToolActivityPanel from './ToolActivityPanel';
import SystemMetrics from './SystemMetrics';
import TranscendentPanel from './TranscendentPanel';
import './DashboardContainer.css';

const DashboardContainer: React.FC = () => {
  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>NALΑ Transcendent Reasoning Engine</h1>
        <p>System Dashboard & Analytics</p>
      </div>

      <div className="dashboard-grid">
        {/* Top Row - Safety Gauges */}
        <div className="dashboard-item full-width">
          <SafetyGauges />
        </div>

        {/* Middle Row - Tool Activity and System Metrics */}
        <div className="dashboard-item half-width">
          <ToolActivityPanel />
        </div>
        <div className="dashboard-item half-width">
          <SystemMetrics />
        </div>

        {/* Bottom Row - Transcendent Panel (full width) */}
        <div className="dashboard-item full-width">
          <TranscendentPanel />
        </div>
      </div>
    </div>
  );
};

export default DashboardContainer;