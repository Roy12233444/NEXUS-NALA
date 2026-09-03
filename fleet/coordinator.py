"""
Predictive Mode Orchestrator for NALA Dual-Mode Operation.
Implements the Predictive Mode Stability Matrix for intelligent
switching between AUTONOMOUS and INTERACTIVE modes with predictive
orchestration, hysteresis control, and zero-loss state synchronization.
"""

from __future__ import annotations

import time
import math
from collections import deque
from typing import Deque, List, Any, Optional, Dict, Tuple
from enum import Enum
from dataclasses import dataclass, field
import numpy as np


class OperationMode(Enum):
    """Enhanced operation modes with intermediate states for zero-loss transitions."""
    AUTONOMOUS = "AUTONOMOUS"
    INTERACTIVE = "INTERACTIVE"
    PREPARING_TO_INTERACTIVE = "PREPARING_TO_INTERACTIVE"
    PREPARING_TO_AUTONOMOUS = "PREPARING_TO_AUTONOMOUS"
    SYNCING_STATE = "SYNCING_STATE"


@dataclass
class PredictiveSignals:
    """Container for normalized predictive signals used in mode decision making."""
    workload_complexity_index: float = 0.5  # WCI: [0,1] - task graph complexity
    cognitive_load_predictive: float = 0.5   # CLP: [0,1] - predicted human interaction intensity
    state_cohesion_score: float = 0.9       # SCS: [0,1] - AMP state integrity measure
    hysteresis_buffer: float = 0.1          # HB: [0,0.2] - dynamic threshold for stability
    timestamp: float = field(default_factory=time.time)


@dataclass
class TransitionHistoryEntry:
    """Record of a mode transition for hysteresis calculation and learning."""
    timestamp: float
    from_mode: OperationMode
    to_mode: OperationMode
    trigger_signals: PredictiveSignals
    duration_in_previous_mode: float = 0.0


class PredictiveModeEngine:
    """Core predictive mode switching logic with advanced orchestration capabilities."""

    def __init__(self, history_size: int = 100):
        # Store recent transition timestamps for hysteresis calculation
        self._transition_history: Deque[float] = deque(maxlen=history_size)
        # Track detailed transition history for learning and hysteresis
        self._detailed_transition_history: Deque[TransitionHistoryEntry] = deque(maxlen=history_size)
        # Track current mode for state awareness
        self._current_mode: OperationMode = OperationMode.AUTONOMOUS
        # Track preparation state for coordinated transitions
        self._preparation_phase: Optional[OperationMode] = None
        # Track time entered current mode for duration calculations
        self._mode_entry_time: float = time.time()
        # Performance metrics for adaptive learning
        self._transition_count: int = 0
        self._successful_transitions: int = 0
        # You can inject dependencies for WCI, CLP, SCS calculators here
        # For now, they are enhanced placeholder methods with better defaults

    # -----------------------------------------------------------------
    # Component calculators (normalized 0..1 signals) - Enhanced versions
    # -----------------------------------------------------------------
    def compute_workload_complexity_index(self, task_graph: Any) -> float:
        """Real-time task graph analysis (node dependency depth,
        resource contention, decision entropy). Returns value in [0,1].
        """
        # TODO: Implement actual graph analysis using networkx or similar
        # For now, enhanced placeholder with more realistic simulation
        if hasattr(task_graph, 'nodes'):
            node_count = len(list(task_graph.nodes))
            if hasattr(task_graph, 'edges'):
                edge_count = len(list(task_graph.edges))
                # Consider both node count and connectivity (edge/node ratio)
                connectivity = edge_count / max(node_count, 1) if node_count > 0 else 0
                # Normalize: assume >100 nodes or >50 connections is high complexity
                node_factor = min(1.0, node_count / 100.0)
                connectivity_factor = min(1.0, connectivity / 10.0)  # Assume max 10 edges per node
                # Weighted combination: 60% node count, 40% connectivity
                wci = 0.6 * node_factor + 0.4 * connectivity_factor
                return min(1.0, max(0.0, wci))
            else:
                # Only nodes available
                return min(1.0, node_count / 100.0)
        return 0.5  # default moderate complexity

    def compute_cognitive_load_predictive(
        self, interaction_history: List[float]
    ) -> float:
        """Forecasted human interaction intensity based on historical
        patterns and current engagement metrics. Returns [0,1].
        Uses exponential smoothing for better prediction.
        """
        if not interaction_history:
            return 0.5

        # Use exponential smoothing for better prediction
        # Give more weight to recent interactions
        if len(interaction_history) == 1:
            smoothed = interaction_history[0]
        else:
            # Exponential smoothing with alpha = 0.3 (more weight to recent)
            alpha = 0.3
            smoothed = interaction_history[-1]  # Start with most recent
            for i in range(len(interaction_history)-2, -1, -1):
                smoothed = alpha * interaction_history[i] + (1 - alpha) * smoothed

        # Normalize assuming typical interaction latency ranges from 0.1s to 5.0s
        # Clamp and normalize to [0,1] range
        normalized = max(0.0, min(1.0, (smoothed - 0.1) / (5.0 - 0.1)))
        return normalized

    def compute_state_cohesion_score(self, amp_state: Any) -> float:
        """Measure of AMP state integrity during potential transition (0‑1).
        1.0 = perfect coherence.
        Enhanced version with simulated coherence metrics.
        """
        # TODO: Implement actual coherence metric (e.g., variance of
        # embedding vectors, checkpoint consistency, CRDT convergence metrics)
        # For now, enhanced placeholder with some variability
        base_cohesion = 0.9
        # Add some simulated variance based on time and system state
        time_factor = (math.sin(time.time() / 100.0) + 1) / 2  # Oscillates between 0 and 1
        variance = 0.1 * math.sin(time.time() / 50.0)  # Small oscillation
        cohesion = base_cohesion + variance * 0.1  # Small variation around base
        return max(0.0, min(1.0, cohesion))

    def compute_hysteresis_buffer(self) -> float:
        """Dynamic threshold preventing oscillation (adapts based on
        transition frequency). Returns value in [0,0.2].
        Enhanced version with learning from transition history.
        """
        if len(self._transition_history) < 5:
            return 0.1  # default buffer

        # compute transitions per second in the last 5 minutes
        now = time.time()
        cutoff = now - 300  # 5 minutes
        recent = [t for t in self._transition_history if t > cutoff]
        frequency = len(recent) / 300.0  # transitions per second

        # Enhanced hysteresis calculation with learning
        # Base buffer increases with frequency but saturates
        base_buffer = min(0.2, 0.05 + (frequency * 0.5))

        # Learning component: reduce buffer if transitions have been successful
        if self._transition_count > 0:
            success_rate = self._successful_transitions / self._transition_count
            learning_factor = 0.1 * (1.0 - success_rate)  # Reduce buffer if successful
        else:
            learning_factor = 0.0

        # Stability component: increase buffer if recent transitions were unstable
        instability_factor = 0.0
        if len(self._detailed_transition_history) >= 3:
            recent_transitions = list(self._detailed_transition_history)[-3:]
            # Check if recent transitions were in quick succession (instability)
            time_diffs = [
                abs(recent_transitions[i+1].timestamp - recent_transitions[i].timestamp)
                for i in range(len(recent_transitions)-1)
            ]
            avg_time_diff = sum(time_diffs) / len(time_diffs) if time_diffs else float('inf')
            if avg_time_diff < 10.0:  # Less than 10 seconds between transitions
                instability_factor = 0.05  # Increase buffer to prevent thrashing

        final_buffer = base_buffer + learning_factor + instability_factor
        return min(0.2, max(0.05, final_buffer))  # Clamp to reasonable range

    # -----------------------------------------------------------------
    # Transition decision logic - Enhanced Predictive Mode Stability Matrix
    # -----------------------------------------------------------------
    def should_transition_to_interactive(
        self,
        current_mode: str,
        wci: float,
        clp: float,
        scs: float,
        hb: float,
    ) -> bool:
        """Predictive switch decision using the enhanced Stability Matrix.
        Implements the full Predictive Mode Stability Matrix from the documentation:
        Mode Decision = f(Workload Complexity, Cognitive Load Predictive, State Cohesion Score, Hysteresis Buffer)
        """
        if current_mode == "AUTONOMOUS":
            # Predictive switch to INTERACTIVE when human intervention likely beneficial
            # Formula from documentation: predicted_benefit = (clp * 0.4) + ((1 - wci) * 0.3) + (scs * 0.3)
            predicted_benefit = (clp * 0.4) + ((1 - wci) * 0.3) + (scs * 0.3)
            return predicted_benefit > (0.5 + hb)  # hysteresis prevents rapid toggling

        elif current_mode == "INTERACTIVE":
            # Switch back to AUTONOMOUS when human input stabilizes and task benefits from autonomy
            # Formula from documentation: autonomy_benefit = (wci * 0.5) + ((1 - clp) * 0.3) + (scs * 0.2)
            autonomy_benefit = (wci * 0.5) + ((1 - clp) * 0.3) + (scs * 0.2)
            return autonomy_benefit > (0.6 + hb)  # higher threshold for stability

        return False  # maintain current mode

    def should_transition_to_autonomous(
        self,
        current_mode: str,
        wci: float,
        clp: float,
        scs: float,
        hb: float,
    ) -> bool:
        """Explicit method to check transition to autonomous mode (clarifies intent)."""
        if current_mode == "INTERACTIVE":
            autonomy_benefit = (wci * 0.5) + ((1 - clp) * 0.3) + (scs * 0.2)
            return autonomy_benefit > (0.6 + hb)
        elif current_mode == "AUTONOMOUS":
            # Check if we should stay in autonomous (opposite of switching to interactive)
            predicted_benefit = (clp * 0.4) + ((1 - wci) * 0.3) + (scs * 0.3)
            return predicted_benefit <= (0.5 + hb)
        return False

    def should_transition_to_interactive_explicit(
        self,
        current_mode: str,
        wci: float,
        clp: float,
        scs: float,
        hb: float,
    ) -> bool:
        """Explicit method to check transition to interactive mode."""
        if current_mode == "AUTONOMOUS":
            predicted_benefit = (clp * 0.4) + ((1 - wci) * 0.3) + (scs * 0.3)
            return predicted_benefit > (0.5 + hb)
        elif current_mode == "INTERACTIVE":
            # Check if we should stay in interactive (opposite of switching to autonomous)
            autonomy_benefit = (wci * 0.5) + ((1 - clp) * 0.3) + (scs * 0.2)
            return autonomy_benefit <= (0.6 + hb)
        return False

    # -----------------------------------------------------------------
    # Enhanced state management and transition coordination
    # -----------------------------------------------------------------
    def record_transition(self, from_mode: OperationMode, to_mode: OperationMode,
                         signals: PredictiveSignals, duration_in_previous_mode: float = 0.0) -> None:
        """Call after a mode transition to update hysteresis history and learning metrics."""
        self._transition_history.append(time.time())

        # Record detailed transition for learning
        entry = TransitionHistoryEntry(
            timestamp=time.time(),
            from_mode=from_mode,
            to_mode=to_mode,
            trigger_signals=signals,
            duration_in_previous_mode=duration_in_previous_mode
        )
        self._detailed_transition_history.append(entry)

        # Update counters
        self._transition_count += 1
        # Assume success unless otherwise indicated (could be enhanced with feedback)
        self._successful_transitions += 1

        # Update current mode and reset entry time
        self._current_mode = to_mode
        self._mode_entry_time = time.time()
        self._preparation_phase = None  # Clear preparation phase after transition

    def get_current_mode(self) -> OperationMode:
        """Get the current operation mode."""
        return self._current_mode

    def set_preparation_phase(self, phase: OperationMode) -> None:
        """Set the preparation phase for coordinated transitions."""
        self._preparation_phase = phase

    def get_preparation_phase(self) -> Optional[OperationMode]:
        """Get the current preparation phase."""
        return self._preparation_phase

    def get_time_in_current_mode(self) -> float:
        """Get time spent in current mode in seconds."""
        return time.time() - self._mode_entry_time

    def get_transition_statistics(self) -> Dict[str, Any]:
        """Get statistics about transitions for monitoring and tuning."""
        if self._transition_count == 0:
            return {
                "total_transitions": 0,
                "success_rate": 0.0,
                "recent_frequency": 0.0,
                "average_time_between_transitions": 0.0
            }

        # Calculate recent frequency (transitions per minute in last 10 minutes)
        now = time.time()
        recent_cutoff = now - 600  # 10 minutes
        recent_transitions = [t for t in self._transition_history if t > recent_cutoff]
        recent_frequency = len(recent_transitions) / 10.0  # per minute

        # Calculate average time between transitions
        if len(self._transition_history) >= 2:
            times = sorted(list(self._transition_history))
            intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
            avg_interval = sum(intervals) / len(intervals) if intervals else 0.0
        else:
            avg_interval = 0.0

        return {
            "total_transitions": self._transition_count,
            "success_rate": self._successful_transitions / self._transition_count,
            "recent_frequency": recent_frequency,
            "average_time_between_transitions": avg_interval
        }

    # -----------------------------------------------------------------
    # Integration points for the 5-layer architecture (placeholders)
    # -----------------------------------------------------------------
    def prepare_for_interaction(self, amp_state: Any) -> Dict[str, Any]:
        """Layer 2: Zero-Loss State Synchronization - prepare for interaction mode.
        Implements predictive state preparation: prefetching relevant context to AMP buffers.
        """
        # This would interface with AMP client to:
        # 1. Begin prefetching relevant context to AMP buffers
        # 2. Prepare double-buffering for state synchronization
        # 3. Prepare CRDT mergeable segments
        # 4. Prepare validation checksums
        # 5. Prepare Chiranjeevi persistence checkpoints

        # Placeholder implementation
        preparation_result = {
            "phase": "PREPARING_TO_INTERACTIVE",
            "actions_initiated": [
                "context_prefetch",
                "double_buffer_prepare",
                "crdt_prepare",
                "checksum_prepare",
                "persistence_checkpoint"
            ],
            "estimated_completion_time": time.time() + 2.0,  # 2 seconds prep time
            "state_snapshot_id": f"prep_{int(time.time()*1000)}"
        }
        return preparation_result

    def prepare_for_autonomous(self, amp_state: Any) -> Dict[str, Any]:
        """Layer 2: Zero-Loss State Synchronization - prepare for autonomous mode.
        Implements predictive state preparation: compressing and prioritizing interaction insights.
        """
        # This would interface with AMP client to:
        # 1. Compress and prioritize interaction insights for AMP storage
        # 2. Prepare double-buffering for state synchronization
        # 3. Prepare CRDT mergeable segments for insights
        # 4. Prepare validation checksums
        # 5. Prepare Chiranjeevi persistence checkpoints

        # Placeholder implementation
        preparation_result = {
            "phase": "PREPARING_TO_AUTONOMOUS",
            "actions_initiated": [
                "insight_compression",
                "insight_prioritization",
                "double_buffer_prepare",
                "crdt_insight_prepare",
                "checksum_prepare",
                "persistence_checkpoint"
            ],
            "estimated_completion_time": time.time() + 1.5,  # 1.5 seconds prep time
            "state_snapshot_id": f"prep_auto_{int(time.time()*1000)}"
        }
        return preparation_result

    def validate_transition_readiness(self, preparation_result: Dict[str, Any]) -> bool:
        """Layer 3: Adaptive Safety Gateway - validate that transition preparation is complete.
        Implements adaptive validation checks based on mode and cognitive load.
        """
        # This would interface with adaptive viva gate and satya layer to:
        # 1. Check dynamic validation strictness based on current mode
        # 2. Validate truthfulness thresholds based on interaction type
        # 3. Perform predictive fault injection simulation
        # 4. Check state integrity via validation checksums
        # 5. Verify CRDT convergence

        # Placeholder implementation - in reality would check actual preparation status
        required_actions = [
            "context_prefetch", "double_buffer_prepare", "crdt_prepare",
            "checksum_prepare", "persistence_checkpoint"
        ]
        completed_actions = preparation_result.get("actions_initiated", [])

        # Simulate completion check - in reality would check actual system state
        completion_ratio = len(set(required_actions) & set(completed_actions)) / len(required_actions)
        return completion_ratio >= 0.8  # Require 80% of actions completed

    # -----------------------------------------------------------------
    # Helper function for easy use by fleet coordinator
    # -----------------------------------------------------------------
def make_prediction_engine() -> PredictiveModeEngine:
    """Factory for the predictive mode engine."""
    return PredictiveModeEngine()


__all__ = ["PredictiveModeEngine", "make_prediction_engine", "OperationMode", "PredictiveSignals"]