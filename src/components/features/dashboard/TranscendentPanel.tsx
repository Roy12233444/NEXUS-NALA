import React from 'react';
import { useAppState } from '../../../hooks/useAppState';
import './TranscendentPanel.css';

const TranscendentPanel: React.FC = () => {
  const { getActivePramana, getPramanaConfidence, getPramanaReasoningChain,
          getRtaScoreHistory, getTranscendentIndicators } = useAppState();

  const activePramana = getActivePramana();
  const pramanaConfidence = getPramanaConfidence();
  const pramanaReasoning = getPramanaReasoningChain();
  const rtaScoreHistory = getRtaScoreHistory();
  const transcendentIndicators = getTranscendentIndicators();

  // Calculate average Ṛta-Score from history
  const averageRtaScore = rtaScoreHistory.length > 0
    ? rtaScoreHistory.reduce((sum, entry) => sum + entry.score, 0) / rtaScoreHistory.length
    : 0.5;

  // Get latest Ṛta-Score
  const latestRtaScore = rtaScoreHistory.length > 0
    ? rtaScoreHistory[rtaScoreHistory.length - 1].score
    : 0.5;

  // Calculate trend
  const rtaScoreTrend = rtaScoreHistory.length >= 2
    ? rtaScoreHistory[rtaScoreHistory.length - 1].score - rtaScoreHistory[rtaScoreHistory.length - 2].score
    : 0;

  return (
    <div className="transcendent-panel">
      <h2 className="section-title">Transcendent Awareness Panel</h2>
      <div className="transcendent-content">
        {/* Current Pramāṇa State */}
        <div className="insight-section">
          <h3>Current Pramāṇa State</h3>
          <div className="pramana-display">
            <div className="pramana-symbol">
              {getPramanaSymbol(activePramana)}
            </div>
            <div className="pramana-info">
              <div className="pramana-name">{getPramanaName(activePramana)}</div>
              <div className="pramana-confidence">
                Confidence: <span className="confidence-value">${(pramanaConfidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          {pramanaReasoning.length > 0 && (
            <div className="reasoning-chain">
              <span className="reasoning-label">Reasoning Chain:</span>
              <span className="reasoning-sequence">
                {pramanaReasoning.map((p, index) => (
                  <span key={index} className="pramana-step">
                    {getPramanaSymbol(p)} {getPramanaName(p)}
                    {index < pramanaReasoning.length - 1 ? ' → ' : ''}
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>

        {/* Ṛta-Score Tracking */}
        <div className="insight-section">
          <h3>Ṛta-Score Tracking</h3>
          <div className="rta-score-display">
            <div className="rta-score-value">
              ${(latestRtaScore * 100).toFixed(1)}%
            </div>
            <div className="rta-score-label">Current Ṛta-Score</div>
            <div className="rta-score-trend">
              {rtaScoreTrend !== 0 ? (
                <span className={`trend-indicator ${rtaScoreTrend > 0 ? 'trend-up' : 'trend-down'}`}>
                  {rtaScoreTrend > 0 ? '▲' : '▼'} ${Math.abs(rtaScoreTrend * 100).toFixed(2)}%
                </span>
              ) : (
                <span className="trend-indicator trend-stable">● Stable</span>
              )}
            </div>
            <div className="rta-score-average">
              Average (last ${rtaScoreHistory.length}): ${(averageRtaScore * 100).toFixed(1)}%
            </div>
          </div>

          {/* Mini sparkline chart */}
          {rtaScoreHistory.length > 0 && (
            <div className="rta-score-chart">
              <svg width="100%" height="60" className="rta-svg">
                <polyline
                  points={getRtaScorePoints(rtaScoreHistory)}
                  fill="none"
                  stroke="url(#rtaGradient)"
                  stroke-width="2"
                />
              </svg>
              <defs>
                <linearGradient id="rtaGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" style="stop-color:${getRtaScoreColor(latestRtaScore)};stop-opacity:1" />
                  <stop offset="100%" style="stop-color:#ff9a9e;stop-opacity:1" />
                </linearGradient>
              </defs>
            </div>
          )}
        </div>

        {/* Transcendent Indicators */}
        <div className="insight-section">
          <h3>Transcendent Indicators</h3>
          <div className="indicators-grid">
            <div className="indicator-item">
              <div className="indicator-label">Awareness Level</div>
              <div className="indicator-value">${(transcendentIndicators.awarenessLevel * 100).toFixed(1)}%</div>
              <div className="indicator-bar">
                <div className="indicator-fill" style={{ width: `${transcendentIndicators.awarenessLevel * 100}%` }}></div>
              </div>
            </div>

            <div className="indicator-item">
              <div className="indicator-label">Coherence Score</div>
              <div className="indicator-value">${(transcendentIndicators.coherenceScore * 100).toFixed(1)}%</div>
              <div className="indicator-bar">
                <div className="indicator-fill" style={{ width: `${transcendentIndicators.coherenceScore * 100}%` }}></div>
              </div>
            </div>

            <div className="indicator-item">
              <div className="indicator-label">Insight Depth</div>
              <div className="indicator-value">${(transcendentIndicators.insightDepth * 100).toFixed(1)}%</div>
              <div className="indicator-bar">
                <div className="indicator-fill" style={{ width: `${transcendentIndicators.insightDepth * 100}%` }}></div>
              </div>
            </div>

            <div className="indicator-item">
              <div className="indicator-label">Pattern Recognition</div>
              <div className="indicator-value">${(transcendentIndicators.patternRecognition * 100).toFixed(1)}%</div>
              <div className="indicator-bar">
                <div className="indicator-fill" style={{ width: `${transcendentIndicators.patternRecognition * 100}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper functions
const getPramanaSymbol = (pramana: string | null): string => {
  const symbols: { [key: string]: string } = {
    'PRATYAKSHA': '👁️',  // Direct perception
    'ANUMANA': '🔬',     // Inference
    'UPAMANA': '🔄',     // Comparison/Analogy
    'ARTHAPATTI': '🧠',  // Postulation
    'ANUPALABDHI': '🚫', // Non-apprehension
    'SHABDA': '📚',      // Verbal testimony
  };
  return symbols[pramana] || '❓';
};

const getPramanaName = (pramana: string | null): string => {
  const names: { [key: string]: string } = {
    'PRATYAKSHA': 'Direct Perception',
    'ANUMANA': 'Inference',
    'UPAMANA': 'Comparison',
    'ARTHAPATTI': 'Postulation',
    'ANUPALABDHI': 'Non-apprehension',
    'SHABDA': 'Verbal Testimony',
  };
  return names[pramana] || 'Unknown';
};

const getRtaScorePoints = (history: any[]): string => {
  if (history.length === 0) return '';

  const points = history.map((point, index) => {
    const x = (index / Math.max(history.length - 1, 1)) * 100;
    const y = 100 - (point.score * 80); // Invert and scale for SVG
    return `${x},${y}`;
  });

  return points.join(' ');
};

const getRtaScoreColor = (score: number): string => {
  if (score >= 0.8) return '#22c55e'; // Green
  if (score >= 0.6) return '#eab308'; // Yellow
  return '#ef4444'; // Red
};

export default TranscendentPanel;