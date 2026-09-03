import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ConnectionState {
  amp: 'connected' | 'disconnected' | 'connecting';
  fleetCoordinator: 'synced' | 'outOfSync' | 'syncing';
  safetyGates: 'online' | 'degraded' | 'offline';
  knowledgeBase: 'loaded' | 'loading' | 'error';
}

const initialState: ConnectionState = {
  amp: 'disconnected',
  fleetCoordinator: 'outOfSync',
  safetyGates: 'offline',
  knowledgeBase: 'loading',
};

export const connectionSlice = createSlice({
  name: 'connection',
  initialState,
  reducers: {
    setAmpStatus: (state, action: PayloadAction<'connected' | 'disconnected' | 'connecting'>) => {
      state.amp = action.payload;
    },
    setFleetCoordinatorStatus: (state, action: PayloadAction<'synced' | 'outOfSync' | 'syncing'>) => {
      state.fleetCoordinator = action.payload;
    },
    setSafetyGatesStatus: (state, action: PayloadAction<'online' | 'degraded' | 'offline'>) => {
      state.safetyGates = action.payload;
    },
    setKnowledgeBaseStatus: (state, action: PayloadAction<'loaded' | 'loading' | 'error'>) => {
      state.knowledgeBase = action.payload;
    },
  },
});

export const {
  setAmpStatus,
  setFleetCoordinatorStatus,
  setSafetyGatesStatus,
  setKnowledgeBaseStatus,
} = connectionSlice.actions;
export default connectionSlice.reducer;