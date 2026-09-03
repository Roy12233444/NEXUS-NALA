import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export enum ToolType {
  SRUTI = 'sruti',
  SMRITI = 'smriti',
  ANUBHAVA = 'anubhava',
}

export interface ToolSpec {
  name: string;
  toolType: ToolType;
  allowedReadPaths: string[];
  allowedWritePaths: string[];
  allowedNetworkEndpoints: string[];
  spawnsProcesses: boolean;
  requiresRoot: boolean;
  isDeterministic: boolean;
  estimatedInitTime: number;
  resourceProfile: {
    cpu: number;
    memory: number;
    disk: number;
  };
  description: string;
  tags: string[];
}

interface ToolPrediction {
  toolName: string;
  confidence: number; // 0.0 to 1.0
  reasoning: string[];
  estimatedLatencyReduction: number; // in seconds
  safetyChecked: boolean;
  lastUpdated: number;
}

interface WarmedTool {
  toolName: string;
  instanceId: string;
  warmedAt: number;
  ready: boolean;
}

interface ToolsState {
  predictions: ToolPrediction[];
  warmedTools: Record<string, WarmedTool[]>; // toolName -> array of instances
  toolUsageStats: Record<string, {
    count: number;
    lastUsed: number;
    totalLatency: number;
  }>;
  lastPredictionUpdate: number;
}

const initialState: ToolsState = {
  predictions: [],
  warmedTools: {},
  toolUsageStats: {},
  lastPredictionUpdate: 0,
};

export const toolsSlice = createSlice({
  name: 'tools',
  initialState,
  reducers: {
    setToolPredictions: (state, action: PayloadAction<ToolPrediction[]>) => {
      state.predictions = action.payload;
      state.lastPredictionUpdate = Date.now();
    },
    addToolPrediction: (state, action: PayloadAction<ToolPrediction>) => {
      // Replace if exists, otherwise add
      const index = state.predictions.findIndex(p => p.toolName === action.payload.toolName);
      if (index >= 0) {
        state.predictions[index] = action.payload;
      } else {
        state.predictions.push(action.payload);
      }
      state.predictions.sort((a, b) => b.confidence - a.confidence); // Sort by confidence descending
      state.lastPredictionUpdate = Date.now();
    },
    clearToolPredictions: (state) => {
      state.predictions = [];
      state.lastPredictionUpdate = Date.now();
    },
    warmTool: (state, action: PayloadAction<{ toolName: string; instanceId: string }>) => {
      if (!state.warmedTools[action.payload.toolName]) {
        state.warmedTools[action.payload.toolName] = [];
      }
      state.warmedTools[action.payload.toolName].push({
        toolName: action.payload.toolName,
        instanceId: action.payload.instanceId,
        warmedAt: Date.now(),
        ready: true,
      });
    },
    coolTool: (state, action: PayloadAction<{ toolName: string; instanceId: string }>) => {
      const toolInstances = state.warmedTools[action.payload.toolName] || [];
      const index = toolInstances.findIndex(t => t.instanceId === action.payload.instanceId);
      if (index >= 0) {
        toolInstances.splice(index, 1);
        // Clean up empty arrays
        if (toolInstances.length === 0) {
          delete state.warmedTools[action.payload.toolName];
        }
      }
    },
    setToolReady: (state, action: PayloadAction<{ toolName: string; instanceId: string; ready: boolean }>) => {
      const toolInstances = state.warmedTools[action.payload.toolName] || [];
      const instance = toolInstances.find(t => t.instanceId === action.payload.instanceId);
      if (instance) {
        instance.ready = action.payload.ready;
      }
    },
    updateToolUsage: (state, action: PayloadAction<{
      toolName: string;
      latency: number;
    }>) => {
      if (!state.toolUsageStats[action.payload.toolName]) {
        state.toolUsageStats[action.payload.toolName] = {
          count: 0,
          lastUsed: 0,
          totalLatency: 0,
        };
      }
      const stats = state.toolUsageStats[action.payload.toolName];
      stats.count += 1;
      stats.lastUsed = Date.now();
      stats.totalLatency += action.payload.latency;
    },
    resetToolsState: (state) => {
      state.predictions = [];
      state.warmedTools = {};
      state.toolUsageStats = {};
      state.lastPredictionUpdate = 0;
    },
  },
});

export const {
  setToolPredictions,
  addToolPrediction,
  clearToolPredictions,
  warmTool,
  coolTool,
  setToolReady,
  updateToolUsage,
  resetToolsState,
} = toolsSlice.actions;
export default toolsSlice.reducer;