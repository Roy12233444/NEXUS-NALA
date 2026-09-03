import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from '../store';
import { setSatyaScores, setSatyaLatency } from '../store/slices/safetySlice';
import { addRtaScore } from '../store/slices/transcendentSlice';

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

export const useAppState = () => {
  const dispatch = useAppDispatch();

  const connection = useAppSelector((state) => state.connection);
  const mode = useAppSelector((state) => state.mode);
  const ritaScore = useAppSelector((state) => state.ritaScore);
  const safety = useAppSelector((state) => state.safety);
  const tools = useAppSelector((state) => state.tools);
  const transcendent = useAppSelector((state) => state.transcendent);

  // Helper selectors
  const getConnectionStatus = () => {
    if (!connection) return 'disconnected';
    return connection.amp === 'connected' ? 'connected' : 'disconnected';
  };

  const getCurrentMode = () => {
    return mode?.currentMode || 'AUTONOMOUS';
  };

  const isSystemHealthy = () => {
    return (
      connection?.amp === 'connected' &&
      safety?.satyaLayer?.truthfulnessScore > 0.8
    );
  };

  const isSystemDegraded = () => {
    return (
      safety?.satyaLayer?.truthfulnessScore <= 0.8 &&
      safety?.satyaLayer?.truthfulnessScore > 0.5
    );
  };

  const isSystemCritical = () => {
    return safety?.satyaLayer?.truthfulnessScore <= 0.5;
  };

  const getVivekaMetrics = () => {
    return safety?.vivekaGate || {
      truthfulnessLevel: 0.95,
      validationStrictness: 0.9,
      adaptivationRate: 0.85,
    };
  };

  const getSatyaMetrics = () => {
    return safety?.satyaLayer || {
      truthfulnessScore: 0.92,
      consistencyRate: 0.96,
      contradictionCount: 0,
      averageLatency: 45,
    };
  };

  const getToolPredictions = () => {
    return tools?.predictions || [];
  };

  const getToolWarmingStatus = () => {
    return tools?.warmingStatus || {};
  };

  const getToolUsageStats = () => {
    return tools?.usageStats || {};
  };

  const getModeState = () => {
    return mode || {
      currentMode: 'AUTONOMOUS',
      transitionInProgress: false,
      preparationPhase: null,
      timeInCurrentMode: 0,
    };
  };

  const getSafetyState = () => {
    return safety || {};
  };

  const getTruthfulnessMetrics = () => {
    return {
      truthfulnessScore: safety?.satyaLayer?.truthfulnessScore || 0.92,
      truthfulnessLevel: safety?.vivekaGate?.truthfulnessLevel || 0.95,
    };
  };

  const getRtaScore = () => {
    if (typeof ritaScore === 'number') return ritaScore;
    return (ritaScore as any)?.currentScore || 0.95;
  };

  const getRtaScoreHistory = () => {
    return transcendent?.rtaScoreHistory || [];
  };

  const getTranscendentIndicators = () => {
    return transcendent?.transcendentIndicators || {
      awarenessLevel: 0.88,
      coherenceScore: 0.94,
      insightDepth: 0.82,
      patternRecognition: 0.91,
      lastUpdated: Date.now(),
    };
  };

  const getPramanaRouter = () => {
    return transcendent?.pramanaRouter || {
      activePramana: 'PRATYAKSHA',
      confidence: 0.95,
      lastUpdated: Date.now(),
      reasoningChain: ['PRATYAKSHA', 'ANUMANA'],
    };
  };

  return {
    dispatch,
    connection,
    mode,
    ritaScore,
    safety,
    tools,
    transcendent,
    getConnectionStatus,
    getCurrentMode,
    isSystemHealthy,
    isSystemDegraded,
    isSystemCritical,
    getVivekaMetrics,
    getSatyaMetrics,
    getToolPredictions,
    getToolWarmingStatus,
    getToolUsageStats,
    getModeState,
    getSafetyState,
    getTruthfulnessMetrics,
    getRtaScore,
    getRtaScoreHistory,
    getTranscendentIndicators,
    getPramanaRouter,
    updateSatyaScores: (scores: any) => dispatch(setSatyaScores(scores)),
    updateSatyaLatency: (latency: number) => dispatch(setSatyaLatency(latency)),
    updateRitaScore: (data: any) => dispatch(addRtaScore(data)),
  };
};
