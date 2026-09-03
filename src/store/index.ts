import { configureStore } from '@reduxjs/toolkit';
import connectionReducer from './slices/connectionSlice';
import modeReducer from './slices/modeSlice';
import ritaScoreReducer from './slices/ritaScoreSlice';
import safetyReducer from './slices/safetySlice';
import toolsReducer from './slices/toolsSlice';
import transcendentReducer from './slices/transcendentSlice';

export const store = configureStore({
  reducer: {
    connection: connectionReducer,
    mode: modeReducer,
    ritaScore: ritaScoreReducer,
    safety: safetyReducer,
    tools: toolsReducer,
    transcendent: transcendentReducer,
  },
  devTools: process.env.NODE_ENV !== 'production',
});

// Infer types for use in components
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Re-export all slice actions
export * from './slices/connectionSlice';
export * from './slices/modeSlice';
export * from './slices/ritaScoreSlice';
export * from './slices/safetySlice';
export * from './slices/toolsSlice';
export * from './slices/transcendentSlice';