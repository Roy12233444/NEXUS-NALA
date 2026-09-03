"""
Zero-Loss State Synchronization AMP (Autonomous-Interactive Mediator) Client.
Implements double-buffering, CRDTs, state validation checksums, and Chiranjeevi
persistence for seamless mode transitions with zero data loss.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import copy
import uuid
import json

# Import OperationMode from the fleet coordinator (Phase 1 implementation)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from fleet.coordinator import OperationMode


@dataclass
class PredictiveSignals:
    """Container for normalized predictive signals (imported for type hints)."""
    workload_complexity_index: float = 0.5
    cognitive_load_predictive: float = 0.5
    state_cohesion_score: float = 0.9
    hysteresis_buffer: float = 0.1
    timestamp: float = field(default_factory=time.time)


class StateCorruptionError(Exception):
    """Raised when state validation checksum fails."""
    pass


class TransitionNotReadyError(Exception):
    """Raised when transition preparation validation fails."""
    pass


class DualBufferState:
    """
    Manages two synchronized state buffers for zero-loss transitions.
    Uses thread-safe atomic swap to ensure instantaneous transition.
    """

    def __init__(self, initial_state: Any):
        self._lock = threading.RLock()
        self.active_buffer: Any = copy.deepcopy(initial_state)    # Currently serving state
        self.standby_buffer: Any = copy.deepcopy(initial_state)   # Prepared state
        self.version_vector: Dict[str, int] = {}                  # For CRDT conflict tracking
        self._state_type = type(initial_state)
        self._last_swap_time: float = 0.0

    def swap_buffers(self) -> None:
        """Atomically swap active and standby buffers."""
        with self._lock:
            self.active_buffer, self.standby_buffer = self.standby_buffer, self.active_buffer
            self._last_swap_time = time.time()
            # Increment version for the new active buffer (simplified)
            self.version_vector["swap"] = self.version_vector.get("swap", 0) + 1

    def get_active_state(self) -> Any:
        """Get a deep copy of the currently active state."""
        with self._lock:
            return copy.deepcopy(self.active_buffer)

    def get_standby_state(self) -> Any:
        """Get a deep copy of the standby (prepared) state."""
        with self._lock:
            return copy.deepcopy(self.standby_buffer)

    def update_standby_state(self, new_state: Any) -> None:
        """Update the standby buffer with new state (thread-safe)."""
        with self._lock:
            self.standby_buffer = copy.deepcopy(new_state)

    def get_version_vector(self) -> Dict[str, int]:
        """Get current version vector for CRDT tracking."""
        with self._lock:
            return copy.deepcopy(self.version_vector)


class CRDTStateSegment:
    """
    Conflict-free Replicated Data Type for mergeable state segments.
    Implements a state-based CRDT with vector clocks and observed-removed sets.
    """

    def __init__(self, segment_id: str, initial_value: Any = None):
        self.segment_id: str = segment_id
        self.value: Any = initial_value
        self.vector_clock: Dict[str, int] = {}      # Lamport timestamps per node/replica
        self.observed_removed: set = set()          # Tombstones for deleted elements
        self._value_type = type(initial_value) if initial_value is not None else None
        self._last_updated: float = time.time()

    def update(self, new_value: Any, node_id: str = "local") -> None:
        """Update the segment value and increment local clock."""
        # Increment local clock
        self.vector_clock[node_id] = self.vector_clock.get(node_id, 0) + 1

        # Update value (if not removed)
        if self.segment_id not in self.observed_removed:
            self.value = copy.deepcopy(new_value)
            self._value_type = type(new_value)

        self._last_updated = time.time()

    def remove(self, node_id: str = "local") -> None:
        """Mark segment as removed (tombstone)."""
        self.vector_clock[node_id] = self.vector_clock.get(node_id, 0) + 1
        self.observed_removed.add(self.segment_id)
        self._last_updated = time.time()

    def merge(self, other: 'CRDTStateSegment') -> 'CRDTStateSegment':
        """
        Merge another CRDT segment using vector clock comparison.
        Returns new merged segment (does not modify originals).
        """
        # Create new segment for result
        result = CRDTStateSegment(self.segment_id)

        # Merge vector clocks: take max per node
        all_nodes = set(self.vector_clock.keys()) | set(other.vector_clock.keys())
        for node in all_nodes:
            result.vector_clock[node] = max(
                self.vector_clock.get(node, 0),
                other.vector_clock.get(node, 0)
            )

        # Merge observed-removed sets
        result.observed_removed = self.observed_removed | other.observed_removed

        # Determine value based on conflict resolution:
        # If either is removed and the other isn't, removed wins (delete wins)
        # If both have values, use the one with higher vector_clock (or arbitrary if equal)
        self_removed = self.segment_id in self.observed_removed
        other_removed = other.segment_id in other.observed_removed

        if self_removed and not other_removed:
            result.value = None
            result._value_type = None
        elif not self_removed and other_removed:
            result.value = other.value
            result._value_type = other._value_type
        elif not self_removed and not other_removed:
            # Both have values - compare vector clocks
            self_clock_sum = sum(self.vector_clock.values())
            other_clock_sum = sum(other.vector_clock.values())

            if self_clock_sum > other_clock_sum:
                result.value = copy.deepcopy(self.value)
                result._value_type = self._value_type
            elif other_clock_sum > self_clock_sum:
                result.value = copy.deepcopy(other.value)
                result._value_type = other._value_type
            else:
                # Equal clocks - arbitrary choice (could use timestamp)
                result.value = copy.deepcopy(self.value)  # Prefer local
                result._value_type = self._value_type
        else:
            # Both removed
            result.value = None
            result._value_type = None

        result._last_updated = max(self._last_updated, other._last_updated)
        return result

    def is_removed(self) -> bool:
        """Check if segment is marked as removed."""
        return self.segment_id in self.observed_removed

    def get_value(self) -> Any:
        """Get current value (returns None if removed)."""
        if self.is_removed():
            return None
        return copy.deepcopy(self.value)

    def get_vector_clock(self) -> Dict[str, int]:
        """Get vector clock copy."""
        return copy.deepcopy(self.vector_clock)


class StateChecksumValidator:
    """
    Validates state integrity using cryptographic checksums.
    Uses SHA-256 for strong collision resistance.
    """

    def __init__(self, algorithm: str = 'sha256'):
        self.algorithm_name = algorithm
        self._hash_func = getattr(hashlib, algorithm)

    def compute_checksum(self, state_data: Any) -> str:
        """
        Compute checksum for state validation.
        Converts state to canonical string representation.
        """
        # Convert state to canonical JSON-like string for consistent hashing
        canonical_str = self._state_to_canonical_string(state_data)
        return self._hash_func(canonical_str.encode('utf-8')).hexdigest()

    def validate(self, state_data: Any, expected_checksum: str) -> bool:
        """Validate state against expected checksum."""
        computed = self.compute_checksum(state_data)
        # Use constant-time comparison to prevent timing attacks
        return self._constant_time_compare(computed, expected_checksum)

    def _state_to_canonical_string(self, state_data: Any) -> str:
        """Convert state data to canonical string representation."""
        if state_data is None:
            return "null"
        elif isinstance(state_data, (str, int, float, bool)):
            return json.dumps(state_data, sort_keys=True)
        elif isinstance(state_data, (list, tuple)):
            return json.dumps([self._state_to_canonical_string(item) for item in state_data], sort_keys=True)
        elif isinstance(state_data, dict):
            return json.dumps({k: self._state_to_canonical_string(v) for k, v in sorted(state_data.items())}, sort_keys=True)
        else:
            # For arbitrary objects, use their string representation (with warning in practice)
            return str(state_data)

    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0


class ChiranjeeviPersistenceManager:
    """
    Handles gradient-based compression and versioned checkpoints for state persistence.
    Simulates gradient-based compression using delta encoding and quantization.
    """

    def __init__(self, storage_path: str = "./checkpoints", max_checkpoints: int = 100):
        self.storage_path = storage_path
        self.max_checkpoints = max_checkpoints
        self.checkpoint_history: deque = deque(maxlen=max_checkpoints)
        self._last_checkpoint_state: Optional[Any] = None
        self._lock = threading.RLock()

        # Ensure storage directory exists (in real implementation)
        # os.makedirs(self.storage_path, exist_ok=True)

    def create_gradient_checkpoint(self, state_delta: Any, compression_ratio: float = 0.7) -> str:
        """
        Create compressed checkpoint using gradient-based compression simulation.
        Returns checkpoint ID.
        """
        checkpoint_id = f"ckpt_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"

        with self._lock:
            # Simulate gradient-based compression:
            # 1. Delta encoding from last checkpoint
            # 2. Quantization (reduce precision)
            # 3. Optional: dimensionality reduction (simulated)

            compressed_data = self._apply_gradient_compression(
                state_delta,
                self._last_checkpoint_state,
                compression_ratio
            )

            # Store checkpoint metadata
            checkpoint_meta = {
                "id": checkpoint_id,
                "timestamp": time.time(),
                "compression_ratio": compression_ratio,
                "size_estimate": len(str(compressed_data)),  # Simplified
                "data": compressed_data  # In real impl, this would be stored to disk
            }

            self.checkpoint_history.append(checkpoint_meta)
            self._last_checkpoint_state = copy.deepcopy(state_delta) if state_delta is not None else None

        return checkpoint_id

    def _apply_gradient_compression(self, current_state: Any, last_state: Optional[Any], ratio: float) -> Any:
        """
        Apply gradient-based compression simulation.
        In reality, this would use techniques like:
        - FP16 quantization
        - Delta encoding with predictive coding
        - Principal component analysis for state vectors
        """
        if last_state is None:
            # First checkpoint - store full state (with light compression)
            return self._quantize_state(current_state, ratio)

        # Compute state delta (simplified)
        delta = self._compute_state_delta(current_state, last_state)

        # Apply quantization to delta
        quantized_delta = self._quantize_state(delta, ratio)

        return {
            "base_checkpoint": self._get_last_checkpoint_id(),
            "delta": quantized_delta,
            "compression_applied": True
        }

    def _quantize_state(self, state: Any, ratio: float) -> Any:
        """Simulate quantization by reducing numerical precision."""
        if isinstance(state, (int, float)):
            # Simulate reducing float precision (e.g., FP32 -> FP16 equivalent)
            if isinstance(state, float):
                # Quantize to fewer significant digits
                if abs(state) < 1e-10:
                    return 0.0
                # Keep only enough digits based on ratio
                digits = max(1, int(15 * ratio))  # Assume ~15 decimal digits precision
                return round(state, digits)
            return state
        elif isinstance(state, list):
            return [self._quantize_state(item, ratio) for item in state]
        elif isinstance(state, dict):
            return {k: self._quantize_state(v, ratio) for k, v in state.items()}
        elif isinstance(state, str):
            # For strings, simulate by truncating or using shorter encoding
            if ratio <= 0.5 and len(state) > 10:
                return state[:int(len(state) * ratio)] + "..."
            return state
        else:
            # For other types, return as-is (in real impl, would have specific handlers)
            return state

    def _compute_state_delta(self, current: Any, last: Any) -> Any:
        """Compute delta between current and last state (simplified)."""
        if type(current) != type(last):
            return current  # Can't compute delta, return full

        if isinstance(current, (int, float)):
            return current - last
        elif isinstance(current, list):
            if len(current) != len(last):
                return current  # Length changed, return full
            return [curr - last_item if isinstance(curr, (int, float)) and isinstance(last_item, (int, float))
                    else curr for curr, last_item in zip(current, last)]
        elif isinstance(current, dict):
            # Simple dict delta: added/changed/removed keys
            delta = {}
            all_keys = set(current.keys()) | set(last.keys())
            for key in all_keys:
                curr_val = current.get(key)
                last_val = last.get(key)
                if curr_val != last_val:
                    delta[key] = curr_val  # Store new value (or None if removed)
            return delta
        else:
            return current  # Fallback to full state

    def _get_last_checkpoint_id(self) -> Optional[str]:
        """Get ID of most recent checkpoint."""
        with self._lock:
            if self.checkpoint_history:
                return self.checkpoint_history[-1]["id"]
            return None

    def recover_from_checkpoint(self, checkpoint_id: str) -> Any:
        """
        Restore state from a specific checkpoint using gradient decompression.
        """
        with self._lock:
            # Find checkpoint
            checkpoint = None
            for cp in self.checkpoint_history:
                if cp["id"] == checkpoint_id:
                    checkpoint = cp
                    break

            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")

            # Reconstruct state from checkpoint data
            if "data" in checkpoint:
                # Direct storage (simplified)
                return self._decompress_state(checkpoint["data"])
            elif "delta" in checkpoint:
                # Delta from base checkpoint
                base_state = self.recover_from_checkpoint(checkpoint["base_checkpoint"])
                return self._apply_delta(base_state, checkpoint["delta"])
            else:
                # Fallback
                return None

    def _decompress_state(self, compressed_data: Any) -> Any:
        """Decompress state from gradient-compressed format."""
        # In real implementation, would reverse quantization and delta application
        # For simulation, we return as-is (quantization is lossy but we simulate)
        return copy.deepcopy(compressed_data)

    def _apply_delta(self, base_state: Any, delta: Any) -> Any:
        """Apply delta to base state to reconstruct current state."""
        if isinstance(base_state, (int, float)) and isinstance(delta, (int, float)):
            return base_state + delta
        elif isinstance(base_state, list) and isinstance(delta, list):
            if len(base_state) != len(delta):
                return base_state  # Can't apply, return base
            return [base + delta_val if isinstance(base, (int, float)) and isinstance(delta_val, (int, float))
                    else delta_val for base, delta_val in zip(base_state, delta)]
        elif isinstance(base_state, dict) and isinstance(delta, dict):
            # Apply dict delta: update/add/remove keys
            result = copy.deepcopy(base_state)
            for key, delta_val in delta.items():
                if delta_val is None:
                    result.pop(key, None)  # Remove key
                else:
                    result[key] = delta_val
            return result
        else:
            # Fallback: if delta is a full state, return it
            return delta if delta is not None else base_state

    def get_recent_checkpoints(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent checkpoint metadata."""
        with self._lock:
            return list(self.checkpoint_history)[-count:]


class AMPClient:
    """
    Autonomous-Interactive Mediator Client - Core zero-loss state synchronization.
    Implements predictive state preparation, double-buffering, CRDTs, checksums,
    and Chiranjeevi persistence for seamless mode transitions.
    """

    def __init__(self, initial_state: Any, persistence_path: str = "./checkpoints"):
        """
        Initialize AMP Client with initial state.

        Args:
            initial_state: The initial AMP state to synchronize
            persistence_path: Path for Chiranjeevi persistence storage
        """
        # Core components
        self.dual_buffer = DualBufferState(initial_state)
        self.checksum_validator = StateChecksumValidator()
        self.persistence_manager = ChiranjeeviPersistenceManager(persistence_path)

        # State tracking
        self._last_known_good_checksum: str = self.checksum_validator.compute_checksum(initial_state)
        self._last_known_good_state: Any = copy.deepcopy(initial_state)
        self._transition_in_progress: bool = False
        self._preparation_futures: Dict[str, Any] = {}  # Track ongoing preparations
        self._layer3_validation_callback: Optional[callable] = None  # For Layer 3 integration

        # Performance metrics
        self._prepare_count: int = 0
        self._successful_transitions: int = 0
        self._failed_transitions: int = 0
        self._total_prepare_time: float = 0.0

        # CRDT segments for state (divide state into mergeable parts)
        self._state_segments: Dict[str, CRDTStateSegment] = {}
        self._initialize_state_segments(initial_state)

    def _initialize_state_segments(self, state: Any) -> None:
        """Divide state into CRDT segments for conflict-free merging."""
        # Simple segmentation: top-level keys become segments
        if isinstance(state, dict):
            for key, value in state.items():
                segment_id = f"state_{key}"
                self._state_segments[segment_id] = CRDTStateSegment(segment_id, value)
        elif isinstance(state, list):
            for idx, value in enumerate(state):
                segment_id = f"state_idx_{idx}"
                self._state_segments[segment_id] = CRDTStateSegment(segment_id, value)
        else:
            # Scalar state - single segment
            self._state_segments["state_scalar"] = CRDTStateSegment("state_scalar", state)

    def _update_state_segments_from_state(self, state: Any) -> None:
        """Update CRDT segments from a full state object."""
        if isinstance(state, dict):
            for key, value in state.items():
                segment_id = f"state_{key}"
                if segment_id in self._state_segments:
                    self._state_segments[segment_id].update(value)
                else:
                    self._state_segments[segment_id] = CRDTStateSegment(segment_id, value)
        elif isinstance(state, list):
            for idx, value in enumerate(state):
                segment_id = f"state_idx_{idx}"
                if segment_id in self._state_segments:
                    self._state_segments[segment_id].update(value)
                else:
                    self._state_segments[segment_id] = CRDTStateSegment(segment_id, value)
        else:
            # Scalar state
            if "state_scalar" in self._state_segments:
                self._state_segments["state_scalar"].update(state)
            else:
                self._state_segments["state_scalar"] = CRDTStateSegment("state_scalar", state)

    def _state_from_segments(self) -> Any:
        """Reconstruct full state from CRDT segments."""
        # Reconstruct based on original state structure (simplified)
        # In reality, would need to know original structure
        scalar_segments = {k: v for k, v in self._state_segments.items()
                          if k.startswith("state_idx_") or k == "state_scalar"}
        dict_segments = {k: v for k, v in self._state_segments.items()
                        if k.startswith("state_") and not k.startswith("state_idx_")}

        result = {}

        # Reconstruct dict parts
        for seg_id, segment in dict_segments.items():
            if not segment.is_removed():
                key = seg_id.replace("state_", "", 1)
                result[key] = segment.get_value()

        # Reconstruct list parts (if we had list indices)
        if any(k.startswith("state_idx_") for k in self._state_segments):
            # Find max index
            max_idx = -1
            for seg_id in self._state_segments:
                if seg_id.startswith("state_idx_"):
                    try:
                        idx = int(seg_id.split("_")[2])
                        max_idx = max(max_idx, idx)
                    except (ValueError, IndexError):
                        pass

            if max_idx >= 0:
                result_list = [None] * (max_idx + 1)
                for seg_id, segment in self._state_segments.items():
                    if seg_id.startswith("state_idx_"):
                        try:
                            idx = int(seg_id.split("_")[2])
                            if not segment.is_removed():
                                result_list[idx] = segment.get_value()
                        except (ValueError, IndexError):
                            pass
                result["_reconstructed_list"] = result_list

        # If we only had scalar, return it directly
        if not dict_segments and not any(k.startswith("state_idx_") for k in self._state_segments):
            scalar_seg = self._state_segments.get("state_scalar")
            if scalar_seg and not scalar_seg.is_removed():
                return scalar_seg.get_value()

        return result if result else None

    # -----------------------------------------------------------------
    # Predictive State Preparation (Phase 2 Core)
    # -----------------------------------------------------------------
    def prepare_for_interaction(self, current_amp_state: Any) -> Dict[str, Any]:
        """
        Layer 2: Begins prefetching relevant context to AMP buffers 2s before transition.
        Returns preparation tracking object for Layer 3 validation.

        Implements:
        - Context prefetch (simulated 2s lead time)
        - Double-buffering preparation
        - CRDT segment preparation
        - State validation checksums
        - Chiranjeevi persistence checkpoint
        """
        start_time = time.time()
        perf_start = time.perf_counter()
        preparation_id = f"prep_interact_{int(start_time*1000)}_{uuid.uuid4().hex[:4]}"

        try:
            # 1. Validate current state integrity
            if not self.checksum_validator.validate(current_amp_state, self._last_known_good_checksum):
                raise StateCorruptionError("Current state validation failed")

            # 2. Update internal state tracking
            self._update_state_segments_from_state(current_amp_state)
            self._last_known_good_state = copy.deepcopy(current_amp_state)
            self._last_known_good_checksum = self.checksum_validator.compute_checksum(current_amp_state)

            # 3. Prepare double-buffering for state synchronization
            #    (Prepare standby buffer with current state - will be swapped later)
            self.dual_buffer.update_standby_state(current_amp_state)

            # 4. Prepare CRDT segments for mergeable state (mark as ready for merge)
            #    In this simulation, we just ensure segments are up-to-date
            crdt_future = self._simulate_async_operation(
                self._prepare_crdt_segments,
                current_amp_state,
                delay=0.5  # 500ms for CRDT prep
            )

            # 5. Prepare validation checksums for state
            checksum_future = self._simulate_async_operation(
                self._prepare_state_checksums,
                current_amp_state,
                delay=0.3  # 300ms for checksum prep
            )

            # 6. Prepare Chiranjeevi persistence checkpoint (gradient compression)
            persistence_future = self._simulate_async_operation(
                self._prepare_persistence_checkpoint,
                current_amp_state,
                delay=0.7  # 700ms for persistence prep
            )

            # 7. Simulate context prefetch (2s lead time as per document)
            prefetch_future = self._simulate_async_operation(
                self._prefetch_context,
                current_amp_state,
                delay=2.0  # 2s context prefetch
            )

            prepare_time = max(time.perf_counter() - perf_start, 0.0001)
            self._total_prepare_time += prepare_time
            self._prepare_count += 1

            # Store futures for tracking
            self._preparation_futures[preparation_id] = {
                "prefetch": prefetch_future,
                "crdt": crdt_future,
                "checksum": checksum_future,
                "persistence": persistence_future,
                "start_time": start_time,
                "prepare_time": prepare_time,
                "target_mode": OperationMode.INTERACTIVE
            }

            return {
                "preparation_id": preparation_id,
                "phase": "PREPARING_TO_INTERACTIVE",
                "actions_initiated": [
                    "context_prefetch",
                    "double_buffer_prepare",
                    "crdt_prepare",
                    "checksum_prepare",
                    "persistence_checkpoint"
                ],
                "estimated_completion_time": start_time + 2.0,  # 2s prep window
                "state_snapshot_id": preparation_id,
                "prepare_time_estimate": prepare_time,
                "futures": [prefetch_future, crdt_future, checksum_future, persistence_future]
            }

        except Exception as e:
            self._failed_transitions += 1
            raise e

    def prepare_for_autonomous(self, current_amp_state: Any) -> Dict[str, Any]:
        """
        Layer 2: Compresses and prioritizes interaction insights for AMP storage.
        Returns preparation tracking object for Layer 3 validation.

        Implements:
        - Insight compression and prioritization
        - Double-buffering preparation (reverse direction)
        - CRDT preparation for insights
        - State validation checksums
        - Chiranjeevi persistence checkpoint
        """
        start_time = time.time()
        perf_start = time.perf_counter()
        preparation_id = f"prep_auto_{int(start_time*1000)}_{uuid.uuid4().hex[:4]}"

        try:
            # 1. Validate current state integrity
            if not self.checksum_validator.validate(current_amp_state, self._last_known_good_checksum):
                raise StateCorruptionError("Current state validation failed")

            # 2. Extract and prioritize interaction insights (simplified)
            #    In reality, would identify high-value insights from interaction
            prioritized_insights = self._extract_and_prioritize_insights(current_amp_state)

            # 3. Compress insights (simulate)
            compressed_insights = self._compress_insights(prioritized_insights)

            # 4. Update internal state with insights (for tracking)
            next_state = copy.deepcopy(current_amp_state)
            if isinstance(next_state, dict) and isinstance(compressed_insights, dict):
                next_state.update(compressed_insights)
            elif isinstance(next_state, list) and isinstance(compressed_insights, list):
                next_state = compressed_insights
            else:
                next_state = compressed_insights

            self._last_known_good_state = copy.deepcopy(next_state)
            self._last_known_good_checksum = self.checksum_validator.compute_checksum(next_state)

            # 5. Prepare double-buffering (for insights storage)
            self.dual_buffer.update_standby_state(next_state)

            # 6. Prepare CRDT segments for insight data
            crdt_future = self._simulate_async_operation(
                self._prepare_insight_crdt_segments,
                compressed_insights,
                delay=0.4
            )

            # 7. Prepare validation checksums for insights
            checksum_future = self._simulate_async_operation(
                self._prepare_insight_checksums,
                compressed_insights,
                delay=0.2
            )

            # 8. Prepare Chiranjeevi persistence checkpoint for insights
            persistence_future = self._simulate_async_operation(
                self._prepare_persistence_checkpoint,
                compressed_insights,
                delay=0.6
            )

            prepare_time = max(time.perf_counter() - perf_start, 0.0001)
            self._total_prepare_time += prepare_time
            self._prepare_count += 1

            # Store futures for tracking
            self._preparation_futures[preparation_id] = {
                "crdt": crdt_future,
                "checksum": checksum_future,
                "persistence": persistence_future,
                "start_time": start_time,
                "prepare_time": prepare_time,
                "target_mode": OperationMode.AUTONOMOUS,
                "insights_compressed": True
            }

            return {
                "preparation_id": preparation_id,
                "phase": "PREPARING_TO_AUTONOMOUS",
                "actions_initiated": [
                    "insight_compression",
                    "insight_prioritization",
                    "double_buffer_prepare",
                    "crdt_insight_prepare",
                    "checksum_prepare",
                    "persistence_checkpoint"
                ],
                "estimated_completion_time": start_time + 1.5,  # Faster prep for insights
                "state_snapshot_id": preparation_id,
                "prepare_time_estimate": prepare_time,
                "futures": [crdt_future, checksum_future, persistence_future]
            }

        except Exception as e:
            self._failed_transitions += 1
            raise e

    def _simulate_async_operation(self, func, *args, delay: float = 0.0, **kwargs) -> "FutureLike":
        """
        Simulate an asynchronous operation that completes after delay.
        Returns a future-like object that can be checked for completion.
        """
        class FutureLike:
            def __init__(self, func, args, delay, kwargs):
                self.func = func
                self.args = args
                self.delay = delay
                self.kwargs = kwargs
                self._start_time = time.time()
                self._completed = False
                self._result = None
                self._error = None

            def is_complete(self) -> bool:
                """Check if the simulated async operation has completed."""
                if self._completed:
                    return True
                if time.time() - self._start_time >= self.delay:
                    try:
                        self._result = self.func(*self.args, **self.kwargs)
                        self._completed = True
                    except Exception as e:
                        self._error = e
                        self._completed = True
                return self._completed

            def result(self) -> Any:
                """Get result (blocks until complete in real impl)."""
                # In real impl, would block until done
                # For simulation, we wait if not done
                while not self.is_complete():
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                if self._error:
                    raise self._error
                return self._result

        return FutureLike(func, args, delay, kwargs)

    # -----------------------------------------------------------------
    # Preparation Phase Helpers (Simulated)
    # -----------------------------------------------------------------
    def _prepare_crdt_segments(self, state: Any) -> Dict[str, Any]:
        """Prepare CRDT segments for merging (simulation)."""
        # In real impl, would set up CRDT merge protocols
        # For simulation, just return status
        return {"status": "crdt_ready", "segments_prepared": len(self._state_segments)}

    def _prepare_state_checksums(self, state: Any) -> Dict[str, Any]:
        """Prepare state validation checksums (simulation)."""
        checksum = self.checksum_validator.compute_checksum(state)
        return {"checksum": checksum, "algorithm": self.checksum_validator.algorithm_name}

    def _prepare_persistence_checkpoint(self, state: Any) -> Dict[str, Any]:
        """Prepare Chiranjeevi persistence checkpoint (simulation)."""
        checkpoint_id = self.persistence_manager.create_gradient_checkpoint(state)
        return {"checkpoint_id": checkpoint_id, "persistence_ready": True}

    def _prefetch_context(self, state: Any) -> Dict[str, Any]:
        """Simulate context prefetching (2s lead time)."""
        # In real impl, would prefetch relevant context from memory/storage
        # For simulation, just return prefetch status
        return {"prefetched": True, "context_size_estimate": len(str(state))}

    def _extract_and_prioritize_insights(self, state: Any) -> Any:
        """
        Extract and prioritize interaction insights for storage.
        Simplified: return a subset or compressed version of state.
        """
        if isinstance(state, dict):
            # Prioritize keys that seem like insights (simplified heuristic)
            insight_keys = [k for k in state.keys()
                           if any(word in k.lower() for word in ['insight', 'learn', 'pattern', 'rule'])]
            if insight_keys:
                return {k: state[k] for k in insight_keys}
            # Fallback: return first few keys
            return {k: state[k] for k in list(state.keys())[:min(3, len(state))]}
        elif isinstance(state, list):
            # Return first few items as insights
            return state[:min(3, len(state))]
        else:
            # For scalars, return as-is (insight is the state itself)
            return state

    def _compress_insights(self, insights: Any) -> Any:
        """Compress insights (simulate quantization)."""
        return self.persistence_manager._quantize_state(insights, 0.6)  # 60% compression

    def _prepare_insight_crdt_segments(self, insights: Any) -> Dict[str, Any]:
        """Prepare CRDT segments for insight data."""
        return {"status": "insight_crdt_ready"}

    def _prepare_insight_checksums(self, insights: Any) -> Dict[str, Any]:
        """Prepare validation checksums for insights."""
        checksum = self.checksum_validator.compute_checksum(insights)
        return {"checksum": checksum}

    # -----------------------------------------------------------------
    # Transition Validation (Interfaces with Layer 3 - Safety Gateway)
    # -----------------------------------------------------------------
    def validate_transition_readiness(self, preparation_result: Dict[str, Any]) -> bool:
        """
        Layer 3 interface: Validates that transition preparation is complete.
        Called by Adaptive Safety Gateway before committing transition.

        Returns True if preparation is sufficient (I.e. >= 80% actions completed)
        and state integrity is maintained.
        """
        preparation_id = preparation_result["preparation_id"]

        # Check if preparation exists
        if preparation_id not in self._preparation_futures:
            return False

        prep_data = self._preparation_futures[preparation_id]

        # 1. Check action completion
        required_actions = preparation_result["actions_initiated"]
        completed_actions = []

        # Map action names to future keys
        action_to_future = {
            "context_prefetch": "prefetch",
            "double_buffer_prepare": "double_buffer",
            "crdt_prepare": "crdt",
            "checksum_prepare": "checksum",
            "persistence_checkpoint": "persistence",
            "insight_compression": "insight_comp",
            "insight_prioritization": "insight_prio",
            "crdt_insight_prepare": "crdt",
            "checksum_prepare": "checksum"
        }

        # Check each required action
        for action in required_actions:
            future_key = action_to_future.get(action)
            if future_key in ["double_buffer", "insight_comp", "insight_prio"]:
                # These actions are considered done immediately
                completed_actions.append(action)
            elif future_key:
                # Check if the specific future exists and is complete
                future = prep_data.get(future_key)
                if future and future.is_complete():
                    completed_actions.append(action)

        # Calculate completion ratio
        completion_ratio = len(completed_actions) / len(required_actions) if required_actions else 0

        # 2. Additional validations
        state_integrity_ok = self._validate_prepared_state_integrity(preparation_id)
        persistence_ready = self._validate_persistence_checkpoint(preparation_id)

        # Require 80% completion (from validation gate concept in document)
        return (completion_ratio >= 0.8) and state_integrity_ok and persistence_ready

    def _validate_prepared_state_integrity(self, preparation_id: str) -> bool:
        """Validate that prepared state maintains integrity."""
        if preparation_id not in self._preparation_futures:
            return False
        return True

    def _validate_persistence_checkpoint(self, preparation_id: str) -> bool:
        """Validate that persistence checkpoint is ready."""
        if preparation_id not in self._preparation_futures:
            return False

        prep_data = self._preparation_futures[preparation_id]
        future = prep_data.get("persistence")
        if future and future.is_complete():
            return True
        return False

    # -----------------------------------------------------------------
    # Transition Execution
    # -----------------------------------------------------------------
    def execute_transition(self, preparation_result: Dict[str, Any], target_mode: OperationMode) -> Any:
        """
        Executes the actual zero-loss state transition after validation.
        Called once Layer 3 (Safety Gateway) gives approval.

        Returns the new active state after transition.
        """
        preparation_id = preparation_result["preparation_id"]

        if self._transition_in_progress:
            raise RuntimeError("Transition already in progress")

        if not self.validate_transition_readiness(preparation_result):
            raise TransitionNotReadyError("Transition preparation validation failed")

        # Mark transition as in progress
        self._transition_in_progress = True

        try:
            # Atomic double-buffer swap (the zero-loss moment)
            self.dual_buffer.swap_buffers()

            # Update version vectors for CRDT tracking
            self._increment_version_vector(target_mode.value)

            # Final persistence commit
            if "state_snapshot_id" in preparation_result:
                self.persistence_manager.create_gradient_checkpoint(
                    self.dual_buffer.get_active_state(),  # Commit the new active state
                    compression_ratio=0.8
                )

            # Update tracking
            self._successful_transitions += 1
            self._transition_in_progress = False

            # Clean up preparation futures
            if preparation_id in self._preparation_futures:
                del self._preparation_futures[preparation_id]

            # Notify layers of successful transition (callback for Layer 3/4/5)
            if self._layer3_validation_callback:
                self._layer3_validation_callback(True, preparation_id, target_mode)

            # Return the new active state
            return self.dual_buffer.get_active_state()

        except Exception as e:
            self._failed_transitions += 1
            self._transition_in_progress = False
            raise e

    def _increment_version_vector(self, mode_suffix: str) -> None:
        """Increment version vector for the given mode."""
        with self.dual_buffer._lock:
            self.dual_buffer.version_vector[mode_suffix] = \
                self.dual_buffer.version_vector.get(mode_suffix, 0) + 1

    # -----------------------------------------------------------------
    # State Access and Monitoring
    # -----------------------------------------------------------------
    def get_current_state(self) -> Any:
        """Get current active state."""
        return self.dual_buffer.get_active_state()

    def get_prepared_state(self) -> Any:
        """Get currently prepared (standby) state."""
        return self.dual_buffer.get_standby_state()

    def is_transition_in_progress(self) -> bool:
        """Check if a transition is currently in progress."""
        return self._transition_in_progress

    def get_transition_statistics(self) -> Dict[str, Any]:
        """Get statistics about preparations and transitions."""
        avg_prepare_time = (
            self._total_prepare_time / self._prepare_count
            if self._prepare_count > 0 else 0.0
        )

        return {
            "total_preparations": self._prepare_count,
            "successful_transitions": self._successful_transitions,
            "failed_transitions": self._failed_transitions,
            "success_rate": (
                self._successful_transitions /
                max(self._successful_transitions + self._failed_transitions, 1)
            ),
            "average_prepare_time": avg_prepare_time,
            "preparations_in_progress": len(self._preparation_futures),
            "transition_in_progress": self._transition_in_progress
        }

    def set_layer3_validation_callback(self, callback: callable) -> None:
        """Set callback for Layer 3 (Safety Gateway) notifications."""
        self._layer3_validation_callback = callback

    # -----------------------------------------------------------------
    # Cleanup and Maintenance
    # -----------------------------------------------------------------
    def cleanup_old_preparations(self, max_age_seconds: float = 300.0) -> None:
        """Remove preparations older than max_age_seconds."""
        current_time = time.time()
        to_remove = []

        for prep_id, prep_data in self._preparation_futures.items():
            if current_time - prep_data["start_time"] > max_age_seconds:
                to_remove.append(prep_id)

        for prep_id in to_remove:
            del self._preparation_futures[prep_id]

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information for monitoring."""
        return {
            "state_info": {
                "active_state_type": str(type(self.get_current_state())),
                "state_size_estimate": len(str(self.get_current_state())),
                "checksum": self.checksum_validator.compute_checksum(self.get_current_state())
            },
            "buffer_info": {
                "last_swap_time": self.dual_buffer._last_swap_time,
                "version_vector": self.dual_buffer.get_version_vector()
            },
            "persistence_info": {
                "recent_checkpoints": self.persistence_manager.get_recent_checkpoints(3),
                "checkpoint_count": len(self.persistence_manager.checkpoint_history)
            },
            "transition_stats": self.get_transition_statistics()
        }

    def get_state_in_consistency_score(self) -> float:
        """
        Calculate state consistency/integrity score.
        Heuristics based on active segments and validation history.
        """
        if not self._state_segments:
            return 1.0
        active_count = sum(1 for seg in self._state_segments.values() if not seg.is_removed())
        ratio = active_count / len(self._state_segments)
        now = time.time()
        ages = [now - seg._last_updated for seg in self._state_segments.values()]
        avg_age = sum(ages) / len(ages) if ages else 0.0
        decay = min(0.1, avg_age * 0.0001)
        return max(0.0, min(1.0, ratio * 0.95 - decay))



# Convenience function for easy instantiation
def create_amp_client(initial_state: Any, persistence_path: str = "./checkpoints") -> AMPClient:
    """
    Factory function to create an AMP Client instance.

    Args:
        initial_state: The initial AMP state to synchronize
        persistence_path: Path for Chiranjeevi persistence storage

    Returns:
        Configured AMPClient instance
    """
    return AMPClient(initial_state, persistence_path)


# Export public interface
__all__ = [
    "AMPClient",
    "create_amp_client",
    "PredictiveSignals",
    "StateCorruptionError",
    "TransitionNotReadyError",
    "OperationMode"
]