import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type PramanaType =
  | 'PRATYAKSHA' // Direct perception
  | 'ANUMANA'    // Inference
  | 'UPAMANA'    // Comparison/Analogy
  | 'ARTHAPATTI' // Postulation
  | 'ANUPALABDHI' // Non-apprehension
  | 'SHABDA';    // Verbal testimony

interface PramanaRouterState {
  activePramana: PramanaType | null;
  confidence: number; // 0.0 to 1.0
  lastUpdated: number;
  reasoningChain: PramanaType[]; // Sequence of pramanas used
}

interface RtaScoreHistory {
  timestamp: number;
  score: number; // 0.0 to 1.0
  contributingFactors: Record<string, number>; // Factors contributing to the score
}

interface TranscendentIndicators {
  awarenessLevel: number; // 0.0 to 1.0
  coherenceScore: number; // 0.0 to 1.0
  insightDepth: number; // 0.0 to 1.0
  patternRecognition: number; // 0.0 to 1.0
  lastUpdated: number;
}

interface TranscendentState {
  pramanaRouter: PramanaRouterState;
  rtaScoreHistory: RtaScoreHistory[];
  maxHistoryLength: number;
  transcendentIndicators: TranscendentIndicators;
  lastFullUpdate: number;
}

const initialState: TranscendentState = {
  pramanaRouter: {
    activePramana: null,
    confidence: 0.5,
    lastUpdated: Date.now(),
    reasoningChain: [],
  },
  rtaScoreHistory: [],
  maxHistoryLength: 50,
  transcendentIndicators: {
    awarenessLevel: 0.5,
    coherenceScore: 0.5,
    insightDepth: 0.5,
    patternRecognition: 0.5,
    lastUpdated: Date.now(),
  },
  lastFullUpdate: Date.now(),
};

export const transcendentSlice = createSlice({
  name: 'transcendent',
  initialState,
  reducers: {
    setActivePramana: (state, action: PayloadAction<{ pramana: PramanaType; confidence: number }>) => {
      state.pramanaRouter.activePramana = action.payload.pramana;
      state.pramanaRouter.confidence = action.payload.confidence;
      state.pramanaRouter.lastUpdated = Date.now();
      // Add to reasoning chain (avoid duplicates)
      if (!state.pramanaRouter.reasoningChain.includes(action.payload.pramana)) {
        state.pramanaRouter.reasoningChain.push(action.payload.pramana);
        // Keep only last 5 in chain
        if (state.pramanaRouter.reasoningChain.length > 5) {
          state.pramanaRouter.reasoningChain.shift();
        }
      }
    },
    clearPramanaReasoning: (state) => {
      state.pramanaRouter.reasoningChain = [];
    },
    updatePramanaConfidence: (state, action: PayloadAction<number>) => {
      state.pramanaRouter.confidence = Math.max(0, Math.min(1, action.payload));
      state.pramanaRouter.lastUpdated = Date.now();
    },
    addRtaScore: (state, action: PayloadAction<{ score: number; contributingFactors: Record<string, number> }>) => {
      const scoreEntry: RtaScoreHistory = {
        timestamp: Date.now(),
        score: Math.max(0, Math.min(1, action.payload.score)),
        contributingFactors: action.payload.contributingFactors,
      };

      state.rtaScoreHistory.push(scoreEntry);

      // Keep history at max length
      if (state.rtaScoreHistory.length > state.maxHistoryLength) {
        state.rtaScoreHistory.shift();
      }
    },
    resetRtaScoreHistory: (state) => {
      state.rtaScoreHistory = [];
    },
    setTranscendentIndicators: (state, action: PayloadAction<Partial<TranscendentIndicators>>) => {
      state.transcendentIndicators = {
        ...state.transcendentIndicators,
        ...action.payload,
        lastUpdated: Date.now(),
      };
    },
    setTranscendentAwareness: (state, action: PayloadAction<number>) => {
      state.transcendentIndicators.awarenessLevel = Math.max(0, Math.min(1, action.payload));
      state.transcendentIndicators.lastUpdated = Date.now();
    },
    setTranscendentCoherence: (state, action: PayloadAction<number>) => {
      state.transcendentIndicators.coherenceScore = Math.max(0, Math.min(1, action.payload));
      state.transcendentIndicators.lastUpdated = Date.now();
    },
    setTranscendentInsightDepth: (state, action: PayloadAction<number>) => {
      state.transcendentIndicators.insightDepth = Math.max(0, Math.min(1, action.payload));
      state.transcendentIndicators.lastUpdated = Date.now();
    },
    setTranscendentPatternRecognition: (state, action: PayloadAction<number>) => {
      state.transcendentIndicators.patternRecognition = Math.max(0, Math.min(1, action.payload));
      state.transcendentIndicators.lastUpdated = Date.now();
    },
    setTranscendentState: (state, action: PayloadAction<Partial<TranscendentState>>) => {
      return { ...state, ...action.payload, lastFullUpdate: Date.now() };
    },
    resetTranscendentState: (state) => {
      state.pramanaRouter = {
        activePramana: null,
        confidence: 0.5,
        lastUpdated: Date.now(),
        reasoningChain: [],
      };
      state.rtaScoreHistory = [];
      state.transcendentIndicators = {
        awarenessLevel: 0.5,
        coherenceScore: 0.5,
        insightDepth: 0.5,
        patternRecognition: 0.5,
        lastUpdated: Date.now(),
      };
      state.lastFullUpdate = Date.now();
    },
  },
});

export const {
  setActivePramana,
  clearPramanaReasoning,
  updatePramanaConfidence,
  addRtaScore,
  resetRtaScoreHistory,
  setTranscendentIndicators,
  setTranscendentAwareness,
  setTranscendentCoherence,
  setTranscendentInsightDepth,
  setTranscendentPatternRecognition,
  setTranscendentState,
  resetTranscendentState,
} = transcendentSlice.actions;
export default transcendentSlice.reducer;