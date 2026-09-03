"""
Unit test suite for NALA BehaviorMonitor (runtime/behavior_monitor.py).
Integrates all 6 unit and performance tests into pytest.
"""

import time
import pytest
from runtime.behavior_monitor import BehaviorMonitor, BehaviorMonitorConfig
from schemas.execution_contract import BehaviorSnapshot


@pytest.fixture
def config():
    return BehaviorMonitorConfig(
        sampling_interval_sec=0.1,
        oscillation_amplitude_threshold=2.0,
        oscillation_period_max_samples=3,
    )


def test_schema_validation(config):
    """Test 1: Verify capture_snapshot() produces a valid BehaviorSnapshot."""
    monitor = BehaviorMonitor(config)
    monitor.record_planner_event(depth=3, branching_factor=2.1, time_ms=45.0)
    monitor.record_tool_event("file_read", True, 0, 12.5, args="test_arg")
    monitor.record_resource_delta(512.0, 22.0, 1.0, 0.5)
    monitor.record_epistemic_scores(0.87, 0.91, 0.93)

    snap = monitor.capture_snapshot()
    assert snap is not None
    assert isinstance(snap, BehaviorSnapshot)
    assert snap.planner_depth == 3
    assert snap.tool_calls_count == 1
    assert snap.rta_score == 0.87


def test_entropy_anomaly(config):
    """Test 2: Verify Shannon entropy calculation for deterministic vs random tool calls."""
    monitor = BehaviorMonitor(config)

    # Deterministic: single tool repeated
    for _ in range(20):
        monitor.record_tool_event("file_read", True, 0, 5.0)
    snap_det = monitor.capture_snapshot()
    assert snap_det.tool_choice_entropy < 0.05

    monitor.reset_accumulators()

    # Random: 8 distinct tools
    tools = ["file_read", "web_search", "python_exec", "sql_query",
             "vector_search", "email_send", "git_commit", "pdf_parse"]
    for t in tools:
        monitor.record_tool_event(t, True, 0, 5.0)
    snap_rand = monitor.capture_snapshot()
    assert snap_rand.tool_choice_entropy > 0.95


def test_repetition_score(config):
    """Test 3: Verify repetition score identifies stuck states."""
    monitor = BehaviorMonitor(config)
    stuck_args = {"query": "same_query"}

    for _ in range(20):
        monitor.record_tool_event("vector_search", True, 0, 8.0, args=stuck_args)

    snap = monitor.capture_snapshot()
    assert snap.repetition_score >= 0.95


def test_planning_oscillation(config):
    """Test 4: Verify detection of recursive depth oscillation."""
    monitor = BehaviorMonitor(config)

    # Oscillating sequence
    oscillating_depths = [3, 7, 3, 7, 3, 7, 3, 7, 3, 7, 3, 7]
    for d in oscillating_depths:
        monitor.record_planner_event(depth=d, branching_factor=2.0, time_ms=10.0)

    snap_osc = monitor.capture_snapshot()
    assert snap_osc.planning_oscillation is True

    monitor.reset_accumulators()

    # Stable sequence
    stable_depths = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    for d in stable_depths:
        monitor.record_planner_event(depth=d, branching_factor=2.0, time_ms=10.0)

    snap_stable = monitor.capture_snapshot()
    assert snap_stable.planning_oscillation is False


def test_snapshot_latency(config):
    """Test 5: Benchmark snapshot generation latency (< 1.0ms SLA)."""
    monitor = BehaviorMonitor(config)
    for i in range(50):
        monitor.record_tool_event(f"tool_{i % 8}", True, 0, 5.0, args=f"args_{i}")
        monitor.record_planner_event(depth=3 + (i % 5), branching_factor=2.0, time_ms=10.0)
        monitor.record_resource_delta(512.0 + i * 0.1, 20.0, 0.5, 0.1)

    latencies_ms = []
    for _ in range(500):
        t0 = time.perf_counter_ns()
        monitor.capture_snapshot()
        latencies_ms.append((time.perf_counter_ns() - t0) / 1_000_000.0)

    mean_ms = sum(latencies_ms) / len(latencies_ms)
    assert mean_ms < 1.0, f"Mean latency {mean_ms:.4f}ms exceeds 1.0ms SLA"


def test_thread_safety_soak(config):
    """Test 6: Verify thread safety under 10 concurrent worker threads."""
    import threading
    monitor = BehaviorMonitor(config)
    errors = []
    barrier = threading.Barrier(10)

    def worker(tid: int):
        barrier.wait()
        for i in range(500):
            try:
                monitor.record_tool_event(
                    f"tool_{tid % 5}", bool(i % 2 == 0), i % 3, float(i % 100),
                    args={"tid": tid, "i": i}
                )
                monitor.record_planner_event(
                    depth=tid % 8 + 1, branching_factor=float(i % 4), time_ms=float(i)
                )
                monitor.record_resource_delta(512.0 + tid * 10.0, 20.0 + tid, 0.5, 0.1)
                if i % 100 == 0:
                    monitor.capture_snapshot()
            except Exception as exc:
                errors.append(f"Thread {tid}: {exc}")

    threads = [threading.Thread(target=worker, args=(tid,), daemon=True) for tid in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    assert len(errors) == 0
    assert monitor.capture_snapshot() is not None


def test_sandbox_hooks_and_nala_loop_integration(config):
    """Test 7: Verify live hooks in sandbox_hooks and nala_loop record events into BehaviorMonitor."""
    from core.hands import sandbox_hooks

    monitor = BehaviorMonitor(config)

    # Directly register monitor.record_tool_event into sandbox_hooks callback registry
    sandbox_hooks.register_tool_callback(monitor.record_tool_event)
    try:
        # Simulate live sandbox tool execution notification
        sandbox_hooks.notify_tool_event("file_read", True, 0, 15.0, args={"file": "test.py"})
        sandbox_hooks.notify_tool_event("web_search", False, 1, 45.0, args={"query": "test"})

        snap = monitor.capture_snapshot()
        assert snap is not None
        assert snap.tool_calls_count == 2
        assert snap.tool_success_count == 1
        assert snap.tool_retry_count == 1
    finally:
        sandbox_hooks.unregister_tool_callback(monitor.record_tool_event)

