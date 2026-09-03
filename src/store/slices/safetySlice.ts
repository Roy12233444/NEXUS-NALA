import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type ValidationStrictness = 'MINIMAL' | 'STANDARD' | 'MAXIMUM';

interface VivekaMetrics {
  validationStrictness: ValidationStrictness;
  lastValidationTime: number;
  transitionOutcomes: Array<{
    timestamp: number;
    wasValid: boolean;
    issues: string[];
  }>;
  // Additional metrics from Viveka gate
  adaptiveLearningEnabled: boolean;
  confidenceCalibrationScore: number; // 0-1
}

interface SatyaMetrics {
  truthfulnessScore: number; // 0.0-1.0 running average
  consistencyRate: number; // 0.0-1.0
  factCheckLatencyMs: number;
  contradictionCount: number;
  lastUpdated: number;
  truthfulnessLevel: 'MINIMAL' | 'STANDARD' | 'RIGOROUS' | 'TRANSCENDENT';
}

interface SafetyState {
  viveka: VivekaMetrics;
  satya: SatyaMetrics;
  overallHealth: 'HEALTHY' | 'DEGRADED' | 'CRITICAL'; // Derived metric
  lastFullUpdate: number;
}

const initialState: SafetyState = {
  viveka: {
    validationStrictness: 'STANDARD',
    lastValidationTime: Date.now(),
    transitionOutcomes: [],
    adaptiveLearningEnabled: true,
    confidenceCalibrationScore: 1.0,
  },
  satya: {
    truthfulnessScore: 1.0,
    consistencyRate: 1.0,
    factCheckLatencyMs: 0,
    contradictionCount: 0,
    lastUpdated: Date.now(),
    truthfulnessLevel: 'STANDARD',
  },
  overallHealth: 'HEALTHY',
  lastFullUpdate: Date.now(),
};

export const safetySlice = createSlice({
  name: 'safety',
  initialState,
  reducers: {
    // Viveka updates
    setVivekaStrictness: (state, action: PayloadAction<ValidationStrictness>) => {
      state.viveka.validationStrictness = action.payload;
      state.viveka.lastValidationTime = Date.now();
    },
    addVivekaTransitionOutcome: (state, action: PayloadAction<{
      timestamp: number;
      wasValid: boolean;
      issues: string[];
    }>) => {
      state.viveka.transitionOutcomes.push(action.payload);
      // Keep only last 50 outcomes
      if (state.viveka.transitionOutcomes.length > 50) {
        state.viveka.transitionOutcomes.shift();
      }
    },
    setVivekaAdaptiveLearning: (state, action: PayloadAction<boolean>) => {
      state.viveka.adaptiveLearningEnabled = action.payload;
    },
    setVivekaConfidenceCalibration: (state, action: PayloadAction<number>) => {
      state.viveka.confidenceCalibrationScore = Math.max(0, Math.min(1, action.payload));
    },

    // Satya updates
    setSatyaScores: (state, action: PayloadAction<{
      truthfulnessScore: number;
      consistencyRate: number;
      contradictionCount: number;
    }>) => {
      state.satya.truthfulnessScore = Math.max(0, Math.min(1, action.payload.truthfulnessScore));
      state.satya.consistencyRate = Math.max(0, Math.min(1, action.payload.consistencyRate));
      state.satya.contradictionCount = action.payload.contradictionCount;
      state.satya.lastUpdated = Date.now();
    },
    setSatyaLatency: (state, action: PayloadAction<number>) => {
      state.satya.factCheckLatencyMs = action.payload;
      state.satya.lastUpdated = Date.now();
    },
    setSatyaTruthfulnessLevel: (state, action: PayloadAction<'MINIMAL' | 'STANDARD' | 'RIGOROUS' | 'TRANSCENDENT'>) => {
      state.satya.truthfulnessLevel = action.payload;
    },

    // Overall health
    setOverallHealth: (state, action: PayloadAction<'HEALTHY' | 'DEGRADED' | 'CRITICAL'>) => {
      state.overallHealth = action.payload;
      state.lastFullUpdate = Date.now();
    },

    // Bulk update
    setSafetyState: (state, action: PayloadAction<Partial<SafetyState>>) => {
      return { ...state, ...action.payload, lastFullUpdate: Date.now() };
    },
  },
});

export const {
  setVivekaStrictness,
  addVivekaTransitionOutcome,
  setVivekaAdaptiveLearning,
  setVivekaConfidenceCalibration,
  setSatyaScores,
  setSatyaLatency,
  setSatyaTruthfulnessLevel,
  setOverallHealth,
  setSafetyState,
} = safetySlice.actions;
export default safetySlice.reducer;