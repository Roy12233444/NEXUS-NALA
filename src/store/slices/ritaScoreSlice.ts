import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface RitaScoreState {
  current: number; // 0.0 to 1.0
  history: number[]; // recent values for trending
  maxHistoryLength: number;
  average: number;
  lastUpdated: number; // timestamp
}

const initialState: RitaScoreState = {
  current: 0.5,
  history: [],
  maxHistoryLength: 50,
  average: 0.5,
  lastUpdated: Date.now(),
};

export const ritaScoreSlice = createSlice({
  name: 'ritaScore',
  initialState,
  reducers: {
    setRitaScore: (state, action: PayloadAction<number>) => {
      // Clamp value between 0 and 1
      const clamped = Math.max(0, Math.min(1, action.payload));
      state.current = clamped;
      state.history.push(clamped);
      state.lastUpdated = Date.now();

      // Keep history at max length
      if (state.history.length > state.maxHistoryLength) {
        state.history.shift();
      }

      // Recalculate average
      const sum = state.history.reduce((acc, val) => acc + val, 0);
      state.average = state.history.length > 0 ? sum / state.history.length : 0;
    },
    resetRitaScore: (state) => {
      state.current = 0.5;
      state.history = [];
      state.average = 0.5;
      state.lastUpdated = Date.now();
    },
    setRitaScoreHistory: (state, action: PayloadAction<number[]>) => {
      state.history = action.payload.slice(-state.maxHistoryLength); // Keep only latest
      state.lastUpdated = Date.now();

      // Recalculate average
      const sum = state.history.reduce((acc, val) => acc + val, 0);
      state.average = state.history.length > 0 ? sum / state.history.length : 0;

      // Set current to last value if history exists
      if (state.history.length > 0) {
        state.current = state.history[state.history.length - 1];
      }
    },
  },
});

export const { setRitaScore, resetRitaScore, setRitaScoreHistory } = ritaScoreSlice.actions;
export default ritaScoreSlice.reducer;