import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type OperationMode =
  | 'AUTONOMOUS'
  | 'INTERACTIVE'
  | 'PREPARING_TO_INTERACTIVE'
  | 'PREPARING_TO_AUTONOMOUS'
  | 'SYNCING_STATE';

interface ModeState {
  currentMode: OperationMode;
  transitionInProgress: boolean;
  preparationPhase: OperationMode | null;
  timeInCurrentMode: number; // seconds
}

const initialState: ModeState = {
  currentMode: 'AUTONOMOUS',
  transitionInProgress: false,
  preparationPhase: null,
  timeInCurrentMode: 0,
};

export const modeSlice = createSlice({
  name: 'mode',
  initialState,
  reducers: {
    setCurrentMode: (state, action: PayloadAction<OperationMode>) => {
      state.currentMode = action.payload;
      // Reset timer when mode changes
      state.timeInCurrentMode = 0;
    },
    setTransitionInProgress: (state, action: PayloadAction<boolean>) => {
      state.transitionInProgress = action.payload;
    },
    setPreparationPhase: (state, action: PayloadAction<OperationMode | null>) => {
      state.preparationPhase = action.payload;
    },
    incrementTimeInMode: (state) => {
      state.timeInCurrentMode += 1;
    },
    resetTimeInMode: (state) => {
      state.timeInCurrentMode = 0;
    },
  },
});

export const {
  setCurrentMode,
  setTransitionInProgress,
  setPreparationPhase,
  incrementTimeInMode,
  resetTimeInMode,
} = modeSlice.actions;
export default modeSlice.reducer;