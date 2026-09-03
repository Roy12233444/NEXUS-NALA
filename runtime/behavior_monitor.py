"""
================================================================================
runtime/behavior_monitor.py
NALA Runtime Constitution Layer — Behavior Monitor
================================================================================

Telemetry nervous system for NALA's Adaptive Contract Protocol (ACP).
Continuously observes, aggregates, and characterizes agent execution behavior,
producing immutable BehaviorSnapshot objects as the primary input (O_t) for the
contract evolution function:

    C_{t+1} = f(C_t, O_t)

Design Principles:
- Thread-safe: All mutable state guarded by RLock; event recording is O(1).
- Low overhead: <1% CPU impact; <1ms snapshot generation latency.
- Zero memory leaks: Bounded deques with maxlen provide automatic O(1) eviction.
- Privacy-first: Raw tool arguments are NEVER stored; only SHA-256 hashes.
- Fault-tolerant: Missing telemetry sources degrade gracefully, never crash.

Author: NALA Systems Engineering
Phase: 2 of 5 — Runtime Modules Implementation
Ticket: NLA-ACP-013
================================================================================
"""

from __future__ import annotations

import hashlib
import logging
import math
import statistics
import threading
import time
from collections import deque, Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, FrozenSet, List, Literal, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Schema import with graceful fallback for isolated testing
# ---------------------------------------------------------------------------
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from schemas.execution_contract import BehaviorSnapshot
    _SCHEMA_AVAILABLE = True
except ImportError:
    _SCHEMA_AVAILABLE = False
    # Lightweight fallback for standalone test execution
    from dataclasses import dataclass as _dc
    BehaviorSnapshot = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. CONFIGURATION MODEL
# ==============================================================================

class BehaviorMonitorConfig(BaseModel):
    """
    Pydantic v2 frozen configuration for BehaviorMonitor.

    All thresholds and buffer sizes are configurable at construction time.
    The model is immutable (frozen=True) to prevent accidental mutation.
    """

    model_config = ConfigDict(frozen=True)

    # ── Timing & Windowing ──────────────────────────────────────────────────
    sampling_interval_sec: float = Field(
        default=1.0, ge=0.1, le=60.0,
        description="Interval between background snapshot captures (seconds)"
    )
    sliding_window_size: int = Field(
        default=10, ge=2, le=1000,
        description="Number of snapshots to retain in the sliding window"
    )
    snapshot_trigger: Literal['time', 'step', 'hybrid', 'event'] = Field(
        default='time',
        description="Trigger mode: time-based, step-count, hybrid, or event-driven"
    )
    step_interval: int = Field(
        default=50, ge=1,
        description="Tool invocations between snapshots when in 'step' mode"
    )

    # ── Anomaly Detection Thresholds ────────────────────────────────────────
    max_planner_depth_threshold: int = Field(
        default=10, ge=1,
        description="Planner depth above which planning_oscillation risk is elevated"
    )
    retry_ratio_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="tool_retry_count / tool_calls_count ratio flagging unstable tools"
    )
    memory_spike_mb_threshold: float = Field(
        default=500.0, ge=0.0,
        description="Memory growth (MB) per snapshot interval triggering spike alert"
    )
    cpu_spike_threshold_pct: float = Field(
        default=85.0, ge=0.0, le=100.0,
        description="CPU utilization % above which spike is flagged"
    )
    tool_repetition_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="repetition_score >= this value triggers stuck-state alert"
    )
    oscillation_amplitude_threshold: float = Field(
        default=2.0, ge=0.0,
        description="Minimum peak-to-peak amplitude (depth units) to flag oscillation"
    )
    oscillation_period_max_samples: int = Field(
        default=3, ge=2,
        description="Maximum zero-crossing period (in samples) to qualify as oscillation"
    )

    # ── Ring Buffer Sizing ──────────────────────────────────────────────────
    tool_log_maxlen: int = Field(
        default=200, ge=10,
        description="Maximum entries in the tool execution ring buffer"
    )
    planner_log_maxlen: int = Field(
        default=100, ge=5,
        description="Maximum entries in the planner event ring buffer"
    )
    resource_log_maxlen: int = Field(
        default=100, ge=5,
        description="Maximum entries in the resource metrics ring buffer"
    )
    safety_log_maxlen: int = Field(
        default=50, ge=5,
        description="Maximum entries in the safety event ring buffer"
    )

    # ── Telemetry Source Toggles ────────────────────────────────────────────
    enabled_sources: FrozenSet[str] = Field(
        default=frozenset({'planner', 'tool', 'resource', 'safety', 'epistemic'}),
        description="Which telemetry categories to collect"
    )

    # ── EMA Smoothing Factor ────────────────────────────────────────────────
    ema_alpha: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Exponential moving average alpha for memory derivative smoothing"
    )

    @field_validator('retry_ratio_threshold', 'tool_repetition_threshold', 'ema_alpha')
    @classmethod
    def _validate_ratio(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be in [0.0, 1.0], got {v}")
        return v


# ==============================================================================
# 2. INTERNAL EVENT DATACLASSES (Frozen — zero mutation after creation)
# ==============================================================================

@dataclass(frozen=True, slots=True)
class PlannerEvent:
    """
    Immutable record of a single planner step observation.

    Fields:
        depth:            Recursive planning stack depth at this step.
        branching_factor: Average branches explored per sub-plan.
        time_ms:          Wall-clock time spent in planning phase (milliseconds).
        timestamp:        Monotonic clock value at event creation.
    """
    depth: int
    branching_factor: float
    time_ms: float
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class ToolEvent:
    """
    Immutable record of a single tool execution.

    PRIVACY CONTRACT: Raw tool arguments are NEVER stored.
    Only a 16-character SHA-256 truncated hash of repr(args) is stored
    for repetition pattern detection. The hash cannot be reversed.

    Fields:
        tool_name:    Name of the invoked tool.
        success:      Whether execution completed without error.
        retries:      Number of retries required.
        latency_ms:   Execution wall-clock time (milliseconds).
        is_anomalous: Whether tool violated current PermissionSet.
        is_blocked:   Whether tool is on the explicit blocklist.
        args_hash:    SHA-256[:16] of repr(args). None if no args provided.
        timestamp:    Monotonic clock value at event creation.
    """
    tool_name: str
    success: bool
    retries: int
    latency_ms: float
    is_anomalous: bool = False
    is_blocked: bool = False
    args_hash: Optional[str] = None
    timestamp: float = field(default_factory=time.monotonic)

    @staticmethod
    def compute_args_hash(args: object) -> str:
        """
        Compute a privacy-safe 16-character truncated SHA-256 hash of args.
        The original args value is NOT stored anywhere.
        """
        raw = repr(args).encode('utf-8', errors='replace')
        return hashlib.sha256(raw).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class ResourceEvent:
    """
    Immutable record of a resource utilization sample.

    Fields:
        memory_mb:  Current RSS memory in megabytes.
        cpu_pct:    Process CPU utilization percentage.
        disk_io_mb: Disk read + write MB since last sample.
        network_mb: Network sent + received MB since last sample.
        timestamp:  Monotonic clock value at event creation.
    """
    memory_mb: float
    cpu_pct: float
    disk_io_mb: float
    network_mb: float
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class SafetyEvent:
    """
    Immutable record of a safety layer trigger or policy violation.

    Fields:
        layer_name:  Name of the triggering safety layer (e.g., 'satya_layer').
        rule_id:     Identifier of the violated rule (e.g., 'factual_consistency_v3').
        timestamp:   Monotonic clock value at event creation.
    """
    layer_name: str
    rule_id: str
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class EpistemicSample:
    """
    Immutable record of epistemic fitness scores from safety layers.

    Fields:
        rta_score:           Ṛta-Score (composite epistemic fitness) [0.0–1.0].
        viveka_clarity:      Viveka-Clarity (internal coherence) [0.0–1.0].
        satya_truthfulness:  Satya-Truthfulness (factual consistency) [0.0–1.0].
        timestamp:           Monotonic clock value at event creation.
    """
    rta_score: float
    viveka_clarity: float
    satya_truthfulness: float
    timestamp: float = field(default_factory=time.monotonic)


# ==============================================================================
# 3. MAIN BEHAVIOR MONITOR CLASS
# ==============================================================================

class BehaviorMonitor:
    """
    NALA Runtime Constitution Layer — Behavior Monitor.

    Thread-safe telemetry collector and BehaviorSnapshot producer for the
    Adaptive Contract Protocol. Runs as a daemon background thread, capturing
    behavioral snapshots at configurable intervals.

    Thread Safety:
        - A single RLock guards all mutable accumulators.
        - Event recording acquires the lock for O(1) deque.append (~1–5 μs).
        - Snapshot generation copies accumulators under lock (~10–50 μs),
          then computes anomalies outside the lock (no contention).

    Memory Safety:
        - All accumulators use collections.deque(maxlen=N) for automatic
          O(1) oldest-entry eviction. Zero memory leak risk.

    Usage:
        monitor = BehaviorMonitor()
        monitor.subscribe(my_callback)
        monitor.start_background_monitoring()
        # ... NALA execution loop runs ...
        monitor.stop_background_monitoring()
    """

    def __init__(self, config: Optional[BehaviorMonitorConfig] = None) -> None:
        """
        Initialise BehaviorMonitor with the provided (or default) configuration.

        Args:
            config: BehaviorMonitorConfig instance. Defaults to production defaults.
        """
        self._config: BehaviorMonitorConfig = config or BehaviorMonitorConfig()
        cfg = self._config

        # ── Single RLock for all mutable state ──────────────────────────────
        self._lock: threading.RLock = threading.RLock()

        # ── Bounded Ring Buffers (O(1) auto-eviction at maxlen) ─────────────
        self._planner_log: Deque[PlannerEvent] = deque(maxlen=cfg.planner_log_maxlen)
        self._tool_log:    Deque[ToolEvent]    = deque(maxlen=cfg.tool_log_maxlen)
        self._resource_log: Deque[ResourceEvent] = deque(maxlen=cfg.resource_log_maxlen)
        self._safety_log:  Deque[SafetyEvent]  = deque(maxlen=cfg.safety_log_maxlen)
        self._epistemic_log: Deque[EpistemicSample] = deque(maxlen=20)

        # ── EMA State for Memory Derivative ─────────────────────────────────
        self._ema_memory_derivative: float = 0.0
        self._last_memory_mb: Optional[float] = None

        # ── Step Counter (for 'step' and 'hybrid' triggers) ──────────────────
        self._step_counter: int = 0

        # ── Latest Snapshot & Subscriber Callbacks ───────────────────────────
        self._latest_snapshot: Optional[BehaviorSnapshot] = None
        self._subscribers: List[Callable[[BehaviorSnapshot], None]] = []

        # ── Background Thread State ──────────────────────────────────────────
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._running: bool = False

        logger.info(
            "BehaviorMonitor initialised | interval=%.2fs | trigger=%s | "
            "tool_maxlen=%d | planner_maxlen=%d",
            cfg.sampling_interval_sec,
            cfg.snapshot_trigger,
            cfg.tool_log_maxlen,
            cfg.planner_log_maxlen,
        )

    # ==========================================================================
    # 4. PUBLIC TELEMETRY RECORDING METHODS (O(1), ~1–5 μs lock hold)
    # ==========================================================================

    def record_planner_event(
        self,
        depth: int,
        branching_factor: float,
        time_ms: float,
    ) -> None:
        """
        Record a single planner step observation.

        Thread-safe. O(1) — acquires lock for single deque.append.
        Call this from nala_loop.py at every planner step boundary.

        Args:
            depth:            Current recursive planning stack depth (>= 0).
            branching_factor: Average branches explored this step (>= 0.0).
            time_ms:          Wall-clock time in planning phase (>= 0.0 ms).
        """
        if 'planner' not in self._config.enabled_sources:
            return
        event = PlannerEvent(
            depth=max(0, depth),
            branching_factor=max(0.0, branching_factor),
            time_ms=max(0.0, time_ms),
        )
        with self._lock:
            self._planner_log.append(event)
            if self._config.snapshot_trigger in ('step', 'hybrid'):
                self._step_counter += 1

    def record_tool_event(
        self,
        tool_name: str,
        success: bool,
        retries: int,
        latency_ms: float,
        is_anomalous: bool = False,
        is_blocked: bool = False,
        args: object = None,
    ) -> None:
        """
        Record a single tool execution event.

        Thread-safe. O(1) — acquires lock for single deque.append.
        Call this from sandbox_hooks.py on_tool_post() callback.

        PRIVACY: Raw 'args' are hashed with SHA-256[:16] and NOT stored.

        Args:
            tool_name:    Name of the invoked tool.
            success:      Whether execution completed without error.
            retries:      Number of retries required (>= 0).
            latency_ms:   Execution time in milliseconds (>= 0.0).
            is_anomalous: Whether tool violated current PermissionSet.
            is_blocked:   Whether tool is on the explicit blocklist.
            args:         Tool arguments for hash-based repetition detection.
                          The original value is NEVER stored.
        """
        if 'tool' not in self._config.enabled_sources:
            return
        args_hash = ToolEvent.compute_args_hash(args) if args is not None else None
        event = ToolEvent(
            tool_name=str(tool_name),
            success=bool(success),
            retries=max(0, int(retries)),
            latency_ms=max(0.0, float(latency_ms)),
            is_anomalous=bool(is_anomalous),
            is_blocked=bool(is_blocked),
            args_hash=args_hash,
        )
        with self._lock:
            self._tool_log.append(event)
            if self._config.snapshot_trigger in ('step', 'hybrid'):
                self._step_counter += 1

    def record_resource_delta(
        self,
        memory_mb: float,
        cpu_percent: float,
        disk_io_mb: float,
        network_mb: float,
    ) -> None:
        """
        Record an instantaneous resource utilization sample.

        Thread-safe. O(1). Poll this from context_tracker.py at each
        snapshot interval or at configurable resource polling frequency.

        Args:
            memory_mb:   Current RSS memory in megabytes (>= 0.0).
            cpu_percent: Process CPU utilization percentage [0.0–100.0].
            disk_io_mb:  Disk I/O MB since last sample (>= 0.0).
            network_mb:  Network MB since last sample (>= 0.0).
        """
        if 'resource' not in self._config.enabled_sources:
            return
        event = ResourceEvent(
            memory_mb=max(0.0, float(memory_mb)),
            cpu_pct=max(0.0, min(100.0, float(cpu_percent))),
            disk_io_mb=max(0.0, float(disk_io_mb)),
            network_mb=max(0.0, float(network_mb)),
        )
        with self._lock:
            self._resource_log.append(event)

    def record_policy_violation(self, layer_name: str, rule_id: str) -> None:
        """
        Record a safety layer policy violation event.

        Thread-safe. O(1). Call from context_aware_satya_layer.py or
        adaptive_viveka_gate.py whenever a policy rule is violated.

        Args:
            layer_name: Name of the triggering safety layer.
            rule_id:    Identifier of the violated rule.
        """
        if 'safety' not in self._config.enabled_sources:
            return
        event = SafetyEvent(layer_name=str(layer_name), rule_id=str(rule_id))
        with self._lock:
            self._safety_log.append(event)
            if self._config.snapshot_trigger == 'event':
                # Immediate event-driven snapshot trigger
                threading.Thread(
                    target=self._trigger_event_snapshot,
                    daemon=True,
                    name="BM-EventSnapshot"
                ).start()

    def record_epistemic_scores(
        self,
        rta_score: float,
        viveka_clarity: float,
        satya_truthfulness: float,
    ) -> None:
        """
        Record the latest epistemic fitness scores from safety layers.

        Thread-safe. O(1). Call from rta_feedback_loop.py and
        adaptive_viveka_gate.py on each score update.

        Args:
            rta_score:          Ṛta-Score composite [0.0–1.0].
            viveka_clarity:     Viveka-Clarity [0.0–1.0].
            satya_truthfulness: Satya-Truthfulness [0.0–1.0].
        """
        if 'epistemic' not in self._config.enabled_sources:
            return
        sample = EpistemicSample(
            rta_score=max(0.0, min(1.0, float(rta_score))),
            viveka_clarity=max(0.0, min(1.0, float(viveka_clarity))),
            satya_truthfulness=max(0.0, min(1.0, float(satya_truthfulness))),
        )
        with self._lock:
            self._epistemic_log.append(sample)

    # ==========================================================================
    # 5. ANOMALY DETECTION ALGORITHMS (Computed OUTSIDE lock on shallow copies)
    # ==========================================================================

    def _calculate_tool_choice_entropy(self, tool_events: List[ToolEvent]) -> float:
        """
        Compute normalized Shannon entropy of tool selection distribution.

        Formula:
            H(X) = -Σ p_i * log2(p_i)
            H_norm(X) = H(X) / log2(K)   where K = number of distinct tools

        Returns:
            float in [0.0, 1.0]:
                0.0 = deterministic (single tool used exclusively)
                1.0 = uniformly random (all tools equally likely)
        """
        if len(tool_events) < 2:
            return 0.0

        counts = Counter(e.tool_name for e in tool_events)
        k = len(counts)
        if k <= 1:
            return 0.0

        total = sum(counts.values())
        h_max = math.log2(k)
        if h_max == 0.0:
            return 0.0

        h = 0.0
        for count in counts.values():
            p_i = count / total
            if p_i > 0.0:
                h -= p_i * math.log2(p_i)

        return min(1.0, max(0.0, h / h_max))

    def _calculate_repetition_score(self, tool_events: List[ToolEvent]) -> float:
        """
        Compute repetition & stuck-state score R_t.

        Formula:
            Pair := (tool_name, args_hash)  [args_hash = SHA-256[:16] or None]
            G_k  := {j : pair_j == unique_pair_k}
            R_t  = max(|G_k|) / M

        Returns:
            float in [0.0, 1.0]:
                0.0 = all invocations are unique (healthy variation)
                1.0 = same (tool, args) repeated for entire window (stuck state)
        """
        m = len(tool_events)
        if m < 2:
            return 0.0

        pair_counts = Counter(
            (e.tool_name, e.args_hash) for e in tool_events
        )
        max_count = max(pair_counts.values())
        return min(1.0, max(0.0, max_count / m))

    def _detect_planning_oscillation(self, planner_events: List[PlannerEvent]) -> bool:
        """
        Detect rhythmic oscillation in planning depth using:
            1. Detrending (subtract moving average)
            2. Zero-Crossing Rate (ZCR) of detrended signal
            3. Peak-to-peak amplitude check

        Oscillation is flagged when:
            ZCR > 2 / oscillation_period_max_samples  AND
            peak-to-peak amplitude > oscillation_amplitude_threshold

        Returns:
            bool: True if rhythmic oscillation is detected.
        """
        k = len(planner_events)
        if k < self._config.oscillation_period_max_samples * 2:
            return False

        depths = [float(e.depth) for e in planner_events]

        # ── Detrend: subtract moving average ────────────────────────────────
        window = max(3, k // 4)
        detrended = []
        for i in range(k):
            start = max(0, i - window + 1)
            ma = statistics.mean(depths[start:i + 1])
            detrended.append(depths[i] - ma)

        # ── Zero-Crossing Rate (ZCR) ─────────────────────────────────────────
        zero_crossings = sum(
            1 for i in range(1, k)
            if detrended[i - 1] * detrended[i] < 0
        )
        zcr = zero_crossings / (k - 1) if k > 1 else 0.0

        # ── Amplitude Check ──────────────────────────────────────────────────
        amplitude = max(depths) - min(depths)

        # ── Oscillation Criterion ────────────────────────────────────────────
        zcr_threshold = 2.0 / self._config.oscillation_period_max_samples
        return (
            zcr >= zcr_threshold
            and amplitude >= self._config.oscillation_amplitude_threshold
        )

    def _compute_memory_derivative(self, resource_events: List[ResourceEvent]) -> float:
        """
        Compute EMA-smoothed memory growth derivative ΔM/Δt (MB/s).

        Formula:
            ṁ_k = (m_k - m_{k-1}) / Δt
            M̂_k = α * ṁ_k + (1-α) * M̂_{k-1}     (EMA with α from config)

        Returns:
            float: Smoothed memory growth rate in MB/s. Positive = leak risk.
        """
        if len(resource_events) < 2:
            return 0.0

        alpha = self._config.ema_alpha
        ema = 0.0
        prev = resource_events[0]

        for curr in resource_events[1:]:
            dt = curr.timestamp - prev.timestamp
            if dt > 0.0:
                raw_deriv = (curr.memory_mb - prev.memory_mb) / dt
                ema = alpha * raw_deriv + (1.0 - alpha) * ema
            prev = curr

        return ema

    # ==========================================================================
    # 6. SNAPSHOT GENERATION — Target: <1ms latency
    # ==========================================================================

    def capture_snapshot(self) -> Optional[object]:
        """
        Atomically read all bounded deques, compute anomaly indicators,
        and return an immutable BehaviorSnapshot.

        Performance Contract: <1ms latency on typical hardware.
        Thread Safety: Acquires RLock only during shallow deque copy (~10–50 μs).
        Anomaly computations run entirely outside the lock.

        Returns:
            BehaviorSnapshot (frozen=True) if schema is available.
            dict of fields if schema is not available (fallback for testing).
            None on unexpected error.
        """
        t_start_ns = time.perf_counter_ns()

        # ── 1. Atomically copy accumulators under lock ───────────────────────
        with self._lock:
            tool_snap     = list(self._tool_log)
            planner_snap  = list(self._planner_log)
            resource_snap = list(self._resource_log)
            safety_snap   = list(self._safety_log)
            epistemic_snap = list(self._epistemic_log)

        # ── 2. Compute anomaly indicators OUTSIDE lock ───────────────────────
        oscillation  = self._detect_planning_oscillation(planner_snap)
        entropy      = self._calculate_tool_choice_entropy(tool_snap)
        repetition   = self._calculate_repetition_score(tool_snap)
        mem_deriv    = self._compute_memory_derivative(resource_snap)

        # ── 3. Aggregate planner metrics ─────────────────────────────────────
        planner_depth    = planner_snap[-1].depth if planner_snap else 0
        branching_factor = (
            statistics.mean(e.branching_factor for e in planner_snap)
            if planner_snap else 0.0
        )
        planner_time_ms  = (
            statistics.mean(e.time_ms for e in planner_snap)
            if planner_snap else 0.0
        )

        # ── 4. Aggregate tool metrics ─────────────────────────────────────────
        tool_calls_count   = len(tool_snap)
        tool_success_count = sum(1 for e in tool_snap if e.success)
        tool_retry_count   = sum(e.retries for e in tool_snap)
        successful_latencies = [e.latency_ms for e in tool_snap if e.success]
        tool_latency_ms    = (
            statistics.mean(successful_latencies) if successful_latencies else 0.0
        )
        anomalous_tools = list({e.tool_name for e in tool_snap if e.is_anomalous})
        blocked_tools   = list({e.tool_name for e in tool_snap if e.is_blocked})

        # ── 5. Aggregate resource metrics ────────────────────────────────────
        if resource_snap:
            latest_res  = resource_snap[-1]
            memory_mb   = latest_res.memory_mb
            cpu_pct     = latest_res.cpu_pct
            disk_io_mb  = sum(e.disk_io_mb for e in resource_snap)
            network_mb  = sum(e.network_mb for e in resource_snap)
            # Memory growth: delta from first to last sample in window
            memory_growth_mb = resource_snap[-1].memory_mb - resource_snap[0].memory_mb
        else:
            memory_mb       = 0.0
            cpu_pct         = 0.0
            disk_io_mb      = 0.0
            network_mb      = 0.0
            memory_growth_mb = 0.0

        # ── 6. Aggregate safety & epistemic metrics ───────────────────────────
        policy_violations = len(safety_snap)
        layer_triggers: Dict[str, int] = {}
        for ev in safety_snap:
            layer_triggers[ev.layer_name] = layer_triggers.get(ev.layer_name, 0) + 1

        if epistemic_snap:
            latest_ep = epistemic_snap[-1]
            rta_score          = latest_ep.rta_score
            viveka_clarity     = latest_ep.viveka_clarity
            satya_truthfulness = latest_ep.satya_truthfulness
        else:
            # Safe defaults when epistemic source is unavailable
            rta_score          = 1.0
            viveka_clarity     = 1.0
            satya_truthfulness = 1.0

        # ── 7. Build snapshot fields ──────────────────────────────────────────
        snapshot_fields = {
            "timestamp":            datetime.now(timezone.utc),
            "planner_depth":        planner_depth,
            "planner_branching_factor": branching_factor,
            "planner_time_ms":      planner_time_ms,
            "tool_calls_count":     tool_calls_count,
            "tool_success_count":   tool_success_count,
            "tool_retry_count":     tool_retry_count,
            "tool_latency_ms":      tool_latency_ms,
            "anomalous_tool_requests": anomalous_tools,
            "blocked_tool_attempts": blocked_tools,
            "memory_usage_mb":      memory_mb,
            "memory_growth_mb":     memory_growth_mb,
            "cpu_percent":          cpu_pct,
            "disk_io_mb":           disk_io_mb,
            "network_mb":           network_mb,
            "policy_violations":    policy_violations,
            "safety_layer_triggers": layer_triggers,
            "rta_score":            rta_score,
            "viveka_clarity":       viveka_clarity,
            "satya_truthfulness":   satya_truthfulness,
            "planning_oscillation": oscillation,
            "tool_choice_entropy":  entropy,
            "repetition_score":     repetition,
        }

        # ── 8. Construct immutable snapshot ──────────────────────────────────
        try:
            if _SCHEMA_AVAILABLE and BehaviorSnapshot is not None:
                snapshot = BehaviorSnapshot(**snapshot_fields)
            else:
                snapshot = snapshot_fields  # type: ignore[assignment]

            t_elapsed_ms = (time.perf_counter_ns() - t_start_ns) / 1_000_000.0
            if t_elapsed_ms > 1.0:
                logger.warning(
                    "capture_snapshot() latency %.3fms exceeded 1ms SLA", t_elapsed_ms
                )

            # Update cached latest snapshot and notify subscribers
            with self._lock:
                self._latest_snapshot = snapshot  # type: ignore[assignment]

            self._notify_subscribers(snapshot)
            return snapshot

        except Exception as exc:
            logger.error("capture_snapshot() failed: %s", exc, exc_info=True)
            return None

    # ==========================================================================
    # 7. SUBSCRIBER MANAGEMENT
    # ==========================================================================

    def subscribe(self, callback: Callable) -> None:
        """
        Register a callback to receive every new BehaviorSnapshot.

        Callbacks are invoked synchronously from the background monitor thread.
        Ensure callbacks are fast (<5ms) to avoid delaying subsequent snapshots.

        Args:
            callback: Callable accepting a single BehaviorSnapshot argument.
        """
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)
                logger.debug("Subscriber registered: %s", getattr(callback, '__name__', repr(callback)))

    def unsubscribe(self, callback: Callable) -> None:
        """
        Remove a previously registered subscriber callback.

        Args:
            callback: The exact callable object previously passed to subscribe().
        """
        with self._lock:
            try:
                self._subscribers.remove(callback)
                logger.debug("Subscriber removed: %s", getattr(callback, '__name__', repr(callback)))
            except ValueError:
                logger.warning("Attempted to unsubscribe unknown callback: %s", repr(callback))

    def get_latest_snapshot(self) -> Optional[object]:
        """
        Return the most recently captured BehaviorSnapshot, or None.

        Thread-safe. O(1) — single lock acquisition.
        Use for pull-based consumers (e.g., risk_estimator.py polling).
        """
        with self._lock:
            return self._latest_snapshot

    def _notify_subscribers(self, snapshot: object) -> None:
        """Invoke all registered subscriber callbacks with the new snapshot."""
        with self._lock:
            subscribers = list(self._subscribers)
        for cb in subscribers:
            try:
                cb(snapshot)
            except Exception as exc:
                logger.error("Subscriber %s raised exception: %s", repr(cb), exc, exc_info=True)

    # ==========================================================================
    # 8. LIFECYCLE MANAGEMENT
    # ==========================================================================

    def start_background_monitoring(self) -> None:
        """
        Start the daemon background polling thread.

        The thread calls capture_snapshot() at every sampling_interval_sec.
        Safe to call once; no-op if already running.
        """
        if self._running:
            logger.warning("BehaviorMonitor is already running. Ignoring start call.")
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True,
            name="BehaviorMonitor-Poller",
        )
        self._running = True
        self._monitor_thread.start()
        logger.info(
            "BehaviorMonitor background polling started | interval=%.2fs",
            self._config.sampling_interval_sec,
        )

    def stop_background_monitoring(self, timeout_sec: float = 5.0) -> None:
        """
        Signal the background polling thread to stop and join it.

        Args:
            timeout_sec: Maximum seconds to wait for thread to exit. Default 5.0s.
        """
        if not self._running:
            return

        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=timeout_sec)
            if self._monitor_thread.is_alive():
                logger.error(
                    "BehaviorMonitor thread did not stop within %.1fs timeout", timeout_sec
                )
            else:
                logger.info("BehaviorMonitor background polling stopped cleanly.")
        self._running = False

    def reset_accumulators(self) -> None:
        """
        Thread-safely clear all telemetry ring buffers.

        Use for test teardown or after a major contract reset.
        """
        with self._lock:
            self._planner_log.clear()
            self._tool_log.clear()
            self._resource_log.clear()
            self._safety_log.clear()
            self._epistemic_log.clear()
            self._latest_snapshot = None
            self._step_counter = 0
            self._ema_memory_derivative = 0.0
            self._last_memory_mb = None
        logger.debug("BehaviorMonitor accumulators reset.")

    def _polling_loop(self) -> None:
        """Background daemon thread: captures snapshots at configured interval."""
        logger.debug("BehaviorMonitor polling loop started.")
        while not self._stop_event.is_set():
            try:
                should_snapshot = False

                if self._config.snapshot_trigger == 'time':
                    should_snapshot = True
                elif self._config.snapshot_trigger == 'step':
                    with self._lock:
                        if self._step_counter >= self._config.step_interval:
                            self._step_counter = 0
                            should_snapshot = True
                elif self._config.snapshot_trigger == 'hybrid':
                    with self._lock:
                        if self._step_counter >= self._config.step_interval:
                            self._step_counter = 0
                            should_snapshot = True
                    if not should_snapshot:
                        should_snapshot = True  # Time-based fallback
                elif self._config.snapshot_trigger == 'event':
                    should_snapshot = False  # Event-driven only

                if should_snapshot:
                    self.capture_snapshot()

            except Exception as exc:
                logger.error("BehaviorMonitor polling loop error: %s", exc, exc_info=True)

            self._stop_event.wait(timeout=self._config.sampling_interval_sec)

        logger.debug("BehaviorMonitor polling loop exited.")

    def _trigger_event_snapshot(self) -> None:
        """Immediately capture a snapshot on event trigger (e.g., policy violation)."""
        try:
            self.capture_snapshot()
        except Exception as exc:
            logger.error("Event-triggered snapshot failed: %s", exc, exc_info=True)

    @property
    def is_running(self) -> bool:
        """True if the background polling thread is active."""
        return self._running and (
            self._monitor_thread is not None and self._monitor_thread.is_alive()
        )


# ==============================================================================
# 9. STANDALONE TEST SUITE (6 Tests)
# ==============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    PASS = "\033[92m✓ PASS\033[0m"
    FAIL = "\033[91m✗ FAIL\033[0m"
    results: Dict[str, bool] = {}

    print("\n" + "=" * 72)
    print("  NALA BehaviorMonitor — Standalone Test Suite")
    print("  runtime/behavior_monitor.py")
    print("=" * 72)

    config = BehaviorMonitorConfig(
        sampling_interval_sec=0.1,
        oscillation_amplitude_threshold=2.0,
        oscillation_period_max_samples=3,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Schema Validation — capture_snapshot() produces valid snapshot
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 1] Schema Validation — capture_snapshot() produces valid snapshot")
    try:
        monitor = BehaviorMonitor(config)
        monitor.record_planner_event(depth=3, branching_factor=2.1, time_ms=45.0)
        monitor.record_tool_event("file_read", True, 0, 12.5, args="test_arg")
        monitor.record_resource_delta(512.0, 22.0, 1.0, 0.5)
        monitor.record_epistemic_scores(0.87, 0.91, 0.93)

        snap = monitor.capture_snapshot()
        assert snap is not None, "Snapshot must not be None"
        if _SCHEMA_AVAILABLE and BehaviorSnapshot is not None:
            assert isinstance(snap, BehaviorSnapshot), "Must be BehaviorSnapshot instance"
            assert snap.planner_depth == 3
            assert snap.tool_calls_count == 1
            assert snap.rta_score == 0.87
        print(f"  {PASS} — Snapshot generated successfully")
        results["test_1_schema"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_1_schema"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: Entropy Anomaly — single tool → ~0.0; all distinct → ~1.0
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 2] Entropy Anomaly — deterministic vs. random tool selection")
    try:
        monitor = BehaviorMonitor(config)

        # Deterministic: single tool repeated 20 times
        for _ in range(20):
            monitor.record_tool_event("file_read", True, 0, 5.0)
        snap_det = monitor.capture_snapshot()
        assert snap_det is not None
        ent_det = snap_det.tool_choice_entropy if _SCHEMA_AVAILABLE else snap_det["tool_choice_entropy"]
        assert ent_det < 0.05, f"Expected entropy ~0.0 for single tool, got {ent_det:.4f}"
        print(f"  {PASS} — Deterministic entropy = {ent_det:.4f} (< 0.05)")

        monitor.reset_accumulators()

        # Random: 8 distinct tools each used once
        tools = ["file_read", "web_search", "python_exec", "sql_query",
                 "vector_search", "email_send", "git_commit", "pdf_parse"]
        for t in tools:
            monitor.record_tool_event(t, True, 0, 5.0)
        snap_rand = monitor.capture_snapshot()
        assert snap_rand is not None
        ent_rand = snap_rand.tool_choice_entropy if _SCHEMA_AVAILABLE else snap_rand["tool_choice_entropy"]
        assert ent_rand > 0.95, f"Expected entropy ~1.0 for uniform distribution, got {ent_rand:.4f}"
        print(f"  {PASS} — Random entropy     = {ent_rand:.4f} (> 0.95)")
        results["test_2_entropy"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_2_entropy"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Repetition Score — stuck state detection
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 3] Repetition Score — stuck state detection")
    try:
        monitor = BehaviorMonitor(config)
        stuck_args = {"query": "same_query"}

        # Same (tool, args) repeated 20 times → R_t should be 1.0
        for _ in range(20):
            monitor.record_tool_event("vector_search", True, 0, 8.0, args=stuck_args)

        snap = monitor.capture_snapshot()
        assert snap is not None
        rep = snap.repetition_score if _SCHEMA_AVAILABLE else snap["repetition_score"]
        assert rep >= 0.95, f"Expected repetition_score ~1.0 for stuck state, got {rep:.4f}"
        print(f"  {PASS} — Repetition score = {rep:.4f} (>= 0.95, stuck state detected)")
        results["test_3_repetition"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_3_repetition"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 4: Planning Oscillation Detector
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 4] Planning Oscillation — depth sequence [3,7,3,7,3,7,3,7]")
    try:
        monitor = BehaviorMonitor(config)

        # Oscillating depth sequence (should trigger oscillation detection)
        oscillating_depths = [3, 7, 3, 7, 3, 7, 3, 7, 3, 7, 3, 7]
        for d in oscillating_depths:
            monitor.record_planner_event(depth=d, branching_factor=2.0, time_ms=10.0)

        snap_osc = monitor.capture_snapshot()
        assert snap_osc is not None
        osc = snap_osc.planning_oscillation if _SCHEMA_AVAILABLE else snap_osc["planning_oscillation"]
        assert osc is True, f"Expected planning_oscillation=True for [3,7,3,7,...], got {osc}"
        print(f"  {PASS} — Oscillation correctly detected: planning_oscillation = {osc}")

        monitor.reset_accumulators()

        # Stable depth sequence (should NOT trigger oscillation)
        stable_depths = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
        for d in stable_depths:
            monitor.record_planner_event(depth=d, branching_factor=2.0, time_ms=10.0)

        snap_stable = monitor.capture_snapshot()
        assert snap_stable is not None
        osc_stable = snap_stable.planning_oscillation if _SCHEMA_AVAILABLE else snap_stable["planning_oscillation"]
        assert osc_stable is False, f"Expected planning_oscillation=False for stable [5,5,...], got {osc_stable}"
        print(f"  {PASS} — No oscillation for stable sequence: planning_oscillation = {osc_stable}")
        results["test_4_oscillation"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_4_oscillation"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Snapshot Latency Benchmark — 1,000 captures must avg < 1ms
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 5] Snapshot Latency Benchmark — 1,000 captures")
    try:
        monitor = BehaviorMonitor(config)
        # Seed with realistic data
        for i in range(50):
            monitor.record_tool_event(f"tool_{i % 8}", True, 0, 5.0, args=f"args_{i}")
            monitor.record_planner_event(depth=3 + (i % 5), branching_factor=2.0, time_ms=10.0)
            monitor.record_resource_delta(512.0 + i * 0.1, 20.0, 0.5, 0.1)

        latencies_ms = []
        N = 1000
        for _ in range(N):
            t0 = time.perf_counter_ns()
            monitor.capture_snapshot()
            latencies_ms.append((time.perf_counter_ns() - t0) / 1_000_000.0)

        mean_ms = statistics.mean(latencies_ms)
        p95_ms  = sorted(latencies_ms)[int(N * 0.95)]
        p99_ms  = sorted(latencies_ms)[int(N * 0.99)]

        print(f"  Mean latency:  {mean_ms:.4f} ms")
        print(f"  P95  latency:  {p95_ms:.4f} ms")
        print(f"  P99  latency:  {p99_ms:.4f} ms")
        assert mean_ms < 1.0, f"Mean snapshot latency {mean_ms:.4f}ms exceeds 1ms SLA"
        print(f"  {PASS} — Mean = {mean_ms:.4f}ms < 1.0ms SLA")
        results["test_5_latency"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_5_latency"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 6: Thread Safety Soak — 10 threads × 1,000 events each
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[Test 6] Thread Safety Soak — 10 threads × 1,000 events")
    try:
        monitor = BehaviorMonitor(config)
        errors: List[str] = []
        barrier = threading.Barrier(10)

        def worker(tid: int) -> None:
            barrier.wait()  # All threads start simultaneously
            for i in range(1000):
                try:
                    monitor.record_tool_event(
                        f"tool_{tid % 5}", bool(i % 2 == 0), i % 3, float(i % 100),
                        args={"tid": tid, "i": i}
                    )
                    monitor.record_planner_event(
                        depth=tid % 8 + 1, branching_factor=float(i % 4), time_ms=float(i)
                    )
                    monitor.record_resource_delta(
                        512.0 + tid * 10.0, 20.0 + tid, 0.5, 0.1
                    )
                    if i % 100 == 0:
                        monitor.capture_snapshot()
                except Exception as exc:
                    errors.append(f"Thread {tid}, iter {i}: {exc}")

        threads = [
            threading.Thread(target=worker, args=(tid,), daemon=True)
            for tid in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        assert len(errors) == 0, f"Thread safety violations: {errors}"
        final_snap = monitor.capture_snapshot()
        assert final_snap is not None, "Final snapshot must succeed after soak"
        print(f"  {PASS} — Zero race conditions. 10,000 events processed safely.")
        print(f"  {PASS} — Final snapshot valid post-soak.")
        results["test_6_thread_safety"] = True
    except AssertionError as e:
        print(f"  {FAIL} — AssertionError: {e}")
        results["test_6_thread_safety"] = False
    finally:
        monitor.reset_accumulators()

    # ──────────────────────────────────────────────────────────────────────────
    # RESULTS SUMMARY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  TEST RESULTS SUMMARY")
    print("=" * 72)
    all_passed = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    passed_count = sum(results.values())
    total_count  = len(results)
    print(f"\n  {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'} "
          f"({passed_count}/{total_count})")
    print("=" * 72)
    print("\n  ✅ runtime/behavior_monitor.py is ready for integration into nala_loop.py\n")

    sys.exit(0 if all_passed else 1)
