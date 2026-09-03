import React from 'react';
import { useAppState } from '../../../hooks/useAppState';
import './SystemMetrics.css';

const SystemMetrics: React.FC = () => {
  const { getCurrentMode, getTimeInCurrentMode, isInTransition, getPreparationPhase,
          getVivekaStrictness, getVivekaAdaptiveLearning, getVivekaConfidenceCalibration,
          getSatyaTruthfulnessScore, getSatyaConsistencyRate, getSatyaContradictionCount,
          getSatyaLatencyMs, getSatyaTruthfulnessLevel, isSystemHealthy,
          isSystemDegraded, isSystemCritical,
          getCurrentRitaScore, getRitaScoreHistory, getRitaScoreAverage,
          getActivePramana, getPramanaConfidence, getPramanaReasoningChain,
          getTranscendentIndicators } = useAppState();

  const currentMode = getCurrentMode();
  const timeInMode = getTimeInCurrentMode();
  const isTransitioning = isInTransition();
  const preparationPhase = getPreparationPhase();
  const vivekaStrictness = getVivekaStrictness();
  const vivekaAdaptiveLearning = getVivekaAdaptiveLearning();
  const vivekaConfidenceCalibration = getVivekaConfidenceCalibration();
  const satyaTruthfulness = getSatyaTruthfulnessScore();
  const satyaConsistency = getSatyaConsistencyRate();
  const satyaContradictions = getSatyaContradictionCount();
  const satyaLatency = getSatyaLatencyMs();
  const satyaLevel = getSatyaTruthfulnessLevel();
  const isHealthy = isSystemHealthy();
  const isDegraded = isSystemDegraded();
  const isCritical = isSystemCritical();
  const ritaScore = getCurrentRitaScore();
  const ritaAverage = getRitaScoreAverage();
  const ritaHistory = getRitaScoreHistory();
  const activePramana = getActivePramana();
  const pramanaConfidence = getPramanaConfidence();
  const pramanaReasoning = getPramanaReasoningChain();
  const transcendentIndicators = getTranscendentIndicators();

  // Format time helper
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="system-metrics">
      <h2 className="section-title">System Metrics Dashboard</h2>
      <div className="metrics-grid">
        {/* Operation Mode */}
        <div className="metric-card">
          <h3>Operation Mode</h3>
          <div className="metric-item">
            <span className="metric-label">Current Mode:</span>
            <span className="metric-value mode-${currentMode.toLowerCase()}">${currentMode}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Time in Mode:</span>
            <span className="metric-value">${formatTime(timeInMode)}</span>
          </div>
          {isTransitioning && (
            <div className="metric-item transition-warning">
              <span className="metric-label">Transition:</span>
              <span className="metric-value">In Progress → ${preparationPhase || 'Unknown'}</span>
            </div>
          )}
          {!isTransitioning && (
            <div className="metric-item">
              <span className="metric-label">Stability:</span>
              <span className="metric-value stable">Stable</span>
            </div>
          )}
        </div>

        {/* Safety Metrics */}
        <div className="metric-card">
          <h3>Safety Metrics</h3>
          <div className="metric-item">
            <span className="metric-label">Viveka Strictness:</span>
            <span className="metric-value">${vivekaStrictness}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Adaptive Learning:</span>
            <span className="metric-value">${vivekaAdaptiveLearning ? 'ON' : 'OFF'}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Confidence Calibration:</span>
            <span className="metric-value">${(vivekaConfidenceCalibration * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Overall Health:</span>
            <span className="metric-value health-${isHealthy ? 'healthy' : isDegraded ? 'degraded' : 'critical'}">
              ${isHealthy ? 'Healthy' : isDegraded ? 'Degraded' : 'Critical'}
            </span>
          </div>
        </div>

        {/* Truthfulness Metrics */}
        <div className="metric-card">
          <h3>Truthfulness Metrics</h3>
          <div className="metric-item">
            <span className="metric-label">Truthfulness Score:</span>
            <span className="metric-value">${(satyaTruthfulness * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Consistency Rate:</span>
            <span className="metric-value">${(satyaConsistency * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Contradiction Count:</span>
            <span className="metric-value">${satyaContradictions}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Fact Check Latency:</span>
            <span className="metric-value">${satyaLatency}ms</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Truthfulness Level:</span>
            <span className="metric-value">${satyaLevel}</span>
          </div>
        </div>

        {/* Ṛta-Score Metrics */}
        <div className="metric-card">
          <h3>Ṛta-Score Metrics</h3>
          <div className="metric-item">
            <span className="metric-label">Current Score:</span>
            <span className="metric-value rita-score-${ritaScore >= 0.8 ? 'high' : ritaScore >= 0.6 ? 'medium' : 'low'}">
              ${(ritaScore * 100).toFixed(1)}%
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Average Score:</span>
            <span className="metric-value">${(ritaAverage * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Trend:</span>
            <span className="metric-value trend-${ritaHistory.length > 1 ? (ritaHistory[ritaHistory.length - 1].score > ritaHistory[ritaHistory.length - 2].score ? 'up' : 'down') : 'stable'}">
              ${ritaHistory.length > 1
                ? ((ritaHistory[ritaHistory.length - 1].score - ritaHistory[ritaHistory.length - 2].score) * 100).toFixed(1) + '%'
                : 'N/A'}
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">History Points:</span>
            <span className="metric-value">${ritaHistory.length}</span>
          </div>
        </div>

        {/* Transcendent Metrics */}
        <div className="metric-card">
          <h3>Transcendent Metrics</h3>
          <div className="metric-item">
            <span className="metric-label">Active Pramāṇa:</span>
            <span className="metric-value">${activePramana || 'None'}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Pramāṇa Confidence:</span>
            <span className="metric-value pramana-confidence-${pramanaConfidence >= 0.8 ? 'high' : pramanaConfidence >= 0.6 ? 'medium' : 'low'}">
              ${(pramanaConfidence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Reasoning Chain:</span>
            <span className="metric-value">${pramanaReasoning.length > 0 ? pramanaReasoning.join(' → ') : 'None'}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Awareness Level:</span>
            <span className="metric-value">${(transcendentIndicators.awarenessLevel * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Coherence Score:</span>
            <span className="metric-value">${(transcendentIndicators.coherenceScore * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Insight Depth:</span>
            <span className="metric-value">${(transcendentIndicators.insightDepth * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Pattern Recognition:</span>
            <span className="metric-value">${(transcendentIndicators.patternRecognition * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemMetrics;