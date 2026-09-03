import React from 'react';
import { useAppState } from '../../../hooks/useAppState';
import './SafetyGauges.css';

const SafetyGauges: React.FC = () => {
  const { getVivekaStrictness, getVivekaAdaptiveLearning, getVivekaConfidenceCalibration,
          getVivekaTransitionOutcomes, getSatyaTruthfulnessScore, getSatyaConsistencyRate,
          getSatyaContradictionCount, getSatyaLatencyMs, getSatyaTruthfulnessLevel,
          isSystemHealthy, isSystemDegraded, isSystemCritical } = useAppState();

  const vivekaStrictness = getVivekaStrictness();
  const vivekaAdaptiveLearning = getVivekaAdaptiveLearning();
  const vivekaConfidenceCalibration = getVivekaConfidenceCalibration();
  const vivekaOutcomes = getVivekaTransitionOutcomes();
  const satyaTruthfulness = getSatyaTruthfulnessScore();
  const satyaConsistency = getSatyaConsistencyRate();
  const satyaContradictions = getSatyaContradictionCount();
  const satyaLatency = getSatyaLatencyMs();
  const satyaLevel = getSatyaTruthfulnessLevel();
  const isHealthy = isSystemHealthy();
  const isDegraded = isSystemDegraded();
  const isCritical = isSystemCritical();

  // Calculate recent validity rate from outcomes
  const recentOutcomes = vivekaOutcomes.slice(-10); // Last 10 outcomes
  const recentValidityRate = recentOutcomes.length > 0
    ? (recentOutcomes.filter(o => o.wasValid).length / recentOutcomes.length) * 100
    : 100;

  return (
    <div className="safety-gauges">
      <h2 className="section-title">Safety & Validation Gauges</h2>
      <div className="gauges-grid">
        {/* Viveka Gauges */}
        <div className="gauge-card">
          <h3>Viveka Gate</h3>
          <div className="gauge-item">
            <span className="gauge-label">Validation Strictness:</span>
            <span className="gauge-value">{vivekaStrictness}</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Adaptive Learning:</span>
            <span className="gauge-value">{vivekaAdaptiveLearning ? 'Enabled' : 'Disabled'}</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Confidence Calibration:</span>
            <span className="gauge-value">${(vivekaConfidenceCalibration * 100).toFixed(1)}%</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Recent Validity Rate:</span>
            <span className="gauge-value">${recentValidityRate.toFixed(1)}%</span>
          </div>
        </div>

        {/* Satya Gauges */}
        <div className="gauge-card">
          <h3>Satya Layer</h3>
          <div className="gauge-item">
            <span className="gauge-label">Truthfulness Score:</span>
            <span className="gauge-value">${(satyaTruthfulness * 100).toFixed(1)}%</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Consistency Rate:</span>
            <span className="gauge-value">${(satyaConsistency * 100).toFixed(1)}%</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Contradiction Count:</span>
            <span className="gauge-value">${satyaContradictions}</span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Fact Check Latency:</span>
            <span className="gauge-value">${satyaLatency}ms</span>
          </div>
        </div>

        {/* Overall Health */}
        <div className="gauge-card health-status">
          <h3>System Health</h3>
          <div className={`health-indicator ${isHealthy ? 'healthy' : isDegraded ? 'degraded' : 'critical'}`}>
            <span className="health-dot"></span>
            <span className="health-text">
              {isHealthy ? 'HEALTHY' : isDegraded ? 'DEGRADED' : 'CRITICAL'}
            </span>
          </div>
          <div className="gauge-item">
            <span className="gauge-label">Truthfulness Level:</span>
            <span className="gauge-value">${satyaLevel}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SafetyGauges;