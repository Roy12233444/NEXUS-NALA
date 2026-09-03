import { io, Socket } from 'socket.io-client';
import { store } from '../store';
import {
  setAmpStatus,
  setFleetCoordinatorStatus,
  setSafetyGatesStatus,
  setKnowledgeBaseStatus,
} from '../store/slices/connectionSlice';
import {
  setCurrentMode,
  setTransitionInProgress,
  setPreparationPhase,
  incrementTimeInMode,
  resetTimeInMode,
} from '../store/slices/modeSlice';
import { setRitaScore } from '../store/slices/ritaScoreSlice';
import {
  setVivekaStrictness,
  setVivekaAdaptiveLearning,
  setVivekaConfidenceCalibration,
  addVivekaTransitionOutcome,
  setSatyaScores,
  setSatyaLatency,
  setSatyaTruthfulnessLevel,
  setOverallHealth,
} from '../store/slices/safetySlice';
import {
  setToolPredictions,
  warmTool,
  coolTool,
  setToolReady,
  updateToolUsage,
} from '../store/slices/toolsSlice';
import {
  setActivePramana,
  clearPramanaReasoning,
  updatePramanaConfidence,
  addRtaScore,
  resetRtaScoreHistory,
  setTranscendentAwareness,
  setTranscendentCoherence,
  setTranscendentInsightDepth,
  setTranscendentPatternRecognition,
} from '../store/slices/transcendentSlice';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 2000; // 2 seconds
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectedState = false;

  constructor() {
    this.connect();
  }

  public connect() {
    try {
      const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
      const url = (typeof process !== 'undefined' && process.env?.REACT_APP_WS_URL) || `http://${host}:3001`;

      if (this.socket && this.socket.connected) return;

      this.socket = io(url, {
        transports: ['websocket', 'polling'],
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
      });

      this.setupEventListeners();
    } catch (error) {
      console.error('Failed to initialize WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected to NALA Server on port 3001');
      this.connectedState = true;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.reconnectAttempts = 0;
      this.startHeartbeat();

      // Update connection status in Redux
      store.dispatch(setAmpStatus('connected'));
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.connectedState = false;
      this.stopHeartbeat();

      // Update connection status in Redux
      store.dispatch(setAmpStatus('disconnected'));

      if (reason !== 'io server disconnect') {
        this.scheduleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.connectedState = false;
      store.dispatch(setAmpStatus('disconnected'));
    });

    // AMP (AMP-Enabled) connection status
    this.socket.on('amp-status', (status: 'connected' | 'disconnected' | 'connecting') => {
      store.dispatch(setAmpStatus(status));
    });

    // Fleet Coordinator status
    this.socket.on('fleet-coordinator-status', (status: 'synced' | 'outOfSync' | 'syncing') => {
      store.dispatch(setFleetCoordinatorStatus(status));
    });

    // Safety Gates status
    this.socket.on('safety-gates-status', (status: 'online' | 'degraded' | 'offline') => {
      store.dispatch(setSafetyGatesStatus(status));
    });

    // Knowledge Base status
    this.socket.on('knowledge-base-status', (status: 'loaded' | 'loading' | 'error') => {
      store.dispatch(setKnowledgeBaseStatus(status));
    });

    // Operation Mode updates
    this.socket.on('operation-mode', (mode: string) => {
      store.dispatch(setCurrentMode(mode as any));
    });

    this.socket.on('transition-in-progress', (inProgress: boolean) => {
      store.dispatch(setTransitionInProgress(inProgress));
    });

    this.socket.on('preparation-phase', (phase: string | null) => {
      store.dispatch(setPreparationPhase(phase as any));
    });

    this.socket.on('time-in-mode', (seconds: number) => {
      store.dispatch(incrementTimeInMode());
      // Optionally reset if needed based on server logic
    });

    // Ṛta-Score updates
    this.socket.on('rita-score-update', (score: number) => {
      store.dispatch(setRitaScore(score));
    });

    // Viveka Gate updates
    this.socket.on('viveka-strictness', (strictness: string) => {
      store.dispatch(setVivekaStrictness(strictness as any));
    });

    this.socket.on('viveka-adaptive-learning', (enabled: boolean) => {
      store.dispatch(setVivekaAdaptiveLearning(enabled));
    });

    this.socket.on('viveka-confidence-calibration', (score: number) => {
      store.dispatch(setVivekaConfidenceCalibration(score));
    });

    this.socket.on('viveka-transition-outcome', (outcome: { timestamp: number; wasValid: boolean; issues: string[] }) => {
      store.dispatch(addVivekaTransitionOutcome(outcome));
    });

    // Satya Layer updates
    this.socket.on('satya-scores', (data: { truthfulnessScore: number; consistencyRate: number; contradictionCount: number }) => {
      store.dispatch(setSatyaScores(data));
    });

    this.socket.on('satya-latency', (latencyMs: number) => {
      store.dispatch(setSatyaLatency(latencyMs));
    });

    this.socket.on('satya-truthfulness-level', (level: string) => {
      store.dispatch(setSatyaTruthfulnessLevel(level as any));
    });

    // Overall health
    this.socket.on('overall-health', (health: 'HEALTHY' | 'DEGRADED' | 'CRITICAL') => {
      store.dispatch(setOverallHealth(health));
    });

    // Tool predictions and status
    this.socket.on('tool-predictions', (predictions: Array<{
      toolName: string;
      confidence: number;
      reasoning: string[];
      estimatedLatencyReduction: number;
      safetyChecked: boolean;
    }>) => {
      store.dispatch(setToolPredictions(
        predictions.map(p => ({
          ...p,
          lastUpdated: Date.now(),
        }))
      ));
    });

    this.socket.on('tool-warmed', (data: { toolName: string; instanceId: string }) => {
      store.dispatch(warmTool(data));
    });

    this.socket.on('tool-cooled', (data: { toolName: string; instanceId: string }) => {
      store.dispatch(coolTool(data));
    });

    this.socket.on('tool-ready', (data: { toolName: string; instanceId: string; ready: boolean }) => {
      store.dispatch(setToolReady(data));
    });

    this.socket.on('tool-usage-update', (data: { toolName: string; latency: number }) => {
      store.dispatch(updateToolUsage(data));
    });

    // Transcendent layer updates
    this.socket.on('pramana-active', (data: { pramana: string; confidence: number }) => {
      store.dispatch(setActivePramana(data.pramana as any));
      store.dispatch(updatePramanaConfidence(data.confidence));
    });

    this.socket.on('pramana-reasoning-clear', () => {
      store.dispatch(clearPramanaReasoning());
    });

    this.socket.on('rta-score-history', (data: { score: number; contributingFactors: Record<string, number> }[]) => {
      // Clear existing history and add new entries
      store.dispatch(resetRtaScoreHistory());
      data.forEach(entry => {
        store.dispatch(addRtaScore(entry));
      });
    });

    this.socket.on('transcendent-awareness', (level: number) => {
      store.dispatch(setTranscendentAwareness(level));
    });

    this.socket.on('transcendent-coherence', (score: number) => {
      store.dispatch(setTranscendentCoherence(score));
    });

    this.socket.on('transcendent-insight-depth', (depth: number) => {
      store.dispatch(setTranscendentInsightDepth(depth));
    });

    this.socket.on('transcendent-pattern-recognition', (pattern: number) => {
      store.dispatch(setTranscendentPatternRecognition(pattern));
    });

    // Safety metrics updates
    this.socket.on('safety-metrics-update', (data: {
      viveka: {
        validationStrictness: string;
        confidenceCalibrationScore: number;
      };
      satya: {
        truthfulnessScore: number;
        consistencyRate: number;
        contradictionCount: number;
        factCheckLatencyMs: number;
        truthfulnessLevel: string;
      };
      overallHealth: string;
    }) => {
      // Update Viveka metrics
      store.dispatch(setVivekaStrictness(data.viveka.validationStrictness as any));
      store.dispatch(setVivekaConfidenceCalibration(data.viveka.confidenceCalibrationScore));

      // Update Satya metrics
      store.dispatch(setSatyaScores({
        truthfulnessScore: data.satya.truthfulnessScore,
        consistencyRate: data.satya.consistencyRate,
        contradictionCount: data.satya.contradictionCount,
      }));
      store.dispatch(setSatyaLatency(data.satya.factCheckLatencyMs));
      store.dispatch(setSatyaTruthfulnessLevel(data.satya.truthfulnessLevel as any));

      // Update overall health
      store.dispatch(setOverallHealth(data.overallHealth as any));
    });
  }

  private startHeartbeat() {
    if (this.heartbeatInterval) return;

    this.heartbeatInterval = setInterval(() => {
      if (this.socket && this.socket.connected) {
        this.socket.emit('heartbeat', { timestamp: Date.now() });
      }
    }, 30000); // 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached. Giving up.');
      return;
    }

    this.reconnectAttempts++;
    setTimeout(() => {
      console.log(`Reconnection attempt ${this.reconnectAttempts}`);
      this.connect();
    }, this.reconnectDelay * this.reconnectAttempts);
  }

  // Public methods for emitting events to server
  public emit(event: string, data?: any) {
    if (this.socket && this.socket.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn(`WebSocket not connected. Cannot emit event: ${event}`);
    }
  }

  public on(event: string, callback: (...args: any[]) => void) {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  public off(event: string, callback?: (...args: any[]) => void) {
    if (this.socket) {
      this.socket.off(event, callback);
    }
  }

  public disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.stopHeartbeat();
    }
  }

  public isConnected(): boolean {
    return Boolean(this.socket && this.socket.connected);
  }
}

// Export a singleton instance
export const websocketService = new WebSocketService();