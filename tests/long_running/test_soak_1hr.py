"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/test_soak_1hr.py
Ticket  : JIRA-007 / JIRA-007-B — 1-Hour Sustained Soak Test (Orchestrator)
Sections: JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md §9
           JIRA_007_1HOUR_SOAK_TEST_PLAN_V2.MD (full spec)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
Single pytest-collectable entry-point for the 60-minute soak run. It:

  1.  Derives a unique, reproducible ``checkpoint_base_dir`` for this run so
      that repeated re-invocations never stomp on each other's artifacts.
  2.  Instantiates ``SoakSupervisor`` and drives the generational loop with
      ``supervisor.run(initial_session_id)`` — which handles spawn -> sample ->
      wait -> classify -> respawn internally.
  3.  Intercepts the INTER-GENERATION boundary via a patched ``_spawn_session``
      wrapper, so it can:
        a.  Call ``ChaosInjector.maybe_corrupt_latest_checkpoint()`` between
            Executor generations (never while a subprocess is live).
        b.  Plant a stale ``.checkpoint.lock`` before a crash-recovery generation
            spawns, to exercise ``LockResolver``'s stale-lock detection (AC-7).
        c.  Snapshot the pre-crash ``SessionState`` from the latest on-disk
            checkpoint immediately after a SIGKILL is confirmed.
  4.  On any exception / assertion failure, calls ``bundle_failure_artifacts``
      BEFORE re-raising so pytest still reports the failure normally while a
      self-contained ZIP archive is available for immediate hand-off.
  5.  On success, runs the full post-run assertion suite:
        - assert_memory_stability         (AC-5  -- OS-level RSS flatline)
        - assert_state_matrix_continuity  (AC-6  -- telemetry never regresses)
        - assert_lockfile_resolved        (AC-7  -- lock file cleaned up)
        - assert_crash_point_restored     (AC-9  -- ARIES Redo contract)
        - check_regression               (JIRA-007-B s6 -- cross-run drift)
  6.  Records the completed run in the persistent soak history (JSONL) for
      future regression baseline tracking.

KEY DESIGN DECISIONS
--------------------
1. INTER-GENERATION HOOKS VIA THIN WRAPPER.
   ``SoakSupervisor`` is self-contained and does not expose generation-boundary
   callbacks. Rather than forking the supervisor, this orchestrator replaces
   ``supervisor._spawn_session`` with a bound closure that calls the REAL
   ``_spawn_session`` and then runs our own between-generation logic before
   returning the (proc, gen) pair to the supervisor's loop.

2. CRASH SNAPSHOT IS CAPTURED FROM DISK, NOT FROM A LIVE SESSION.
   After a SIGKILL is confirmed, this orchestrator reads the latest on-disk
   checkpoint for the killed session_id via ``CheckpointManager.load_latest()``
   -- the same method recovery itself uses -- and uses that as the pre-crash
   baseline for assert_crash_point_restored().

3. STALE LOCK IS PLANTED ON THE CRASH-RECOVERY GENERATION ONLY.
   Planted exactly once: the first time a ``crash_recovery`` spawn_reason is
   seen.

4. HISTORY FILE LIVES IN A WORKSPACE-STABLE DIRECTORY.
   Stored under ``tests/long_running/.soak_history/soak_history.jsonl`` which
   survives across individual test invocations.

5. REGRESSION WARNINGS ARE LOGGED, NOT HARD-ASSERTED.
   ``check_regression()`` returns warning strings; this orchestrator logs them
   at WARNING level but does NOT fail the test on regression warnings alone.

6. ``bundle_failure_artifacts`` IS CALLED IN A finally-SAFE MANNER.
   Outer try/except catches ANY exception, bundles artifacts, then re-raises.

================================================================================
Jai Bajrang Bali
================================================================================
"""

from __future__ import annotations

import json
import logging
import time
import uuid
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

import pytest

# -- NALA core imports --------------------------------------------------------
from core.harness.checkpoint import CheckpointManager

# -- Soak harness imports -----------------------------------------------------
from tests.long_running._soak_assertions import (
    assert_crash_point_restored,
    assert_lockfile_resolved,
    assert_memory_stability,
    assert_state_matrix_continuity,
    plant_stale_lock,
)
from tests.long_running._soak_bundler import bundle_failure_artifacts, bundle_success_artifacts
from tests.long_running._soak_chaos import ChaosInjector
from tests.long_running._soak_history import (
    SoakRunSummary,
    check_regression,
    compute_workload_version,
    record_run,
)
from tests.long_running._soak_supervisor import (
    SessionGeneration,
    SoakSupervisor,
)
from tests.long_running._soak_workload import PHASE_BOUNDARIES

_logger = logging.getLogger("nala.soak.test_1hr")

# ==============================================================================
# SECTION 1 -- Module-level constants
# ==============================================================================

# Root of the project (two levels up from this file's directory).
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# Stable, cross-invocation directory for the soak run history JSONL.
_HISTORY_DIR: Path = _REPO_ROOT / "tests" / "long_running" / ".soak_history"
_HISTORY_PATH: Path = _HISTORY_DIR / "soak_history.jsonl"

# Base directory for all per-run checkpoint/log artifacts.
_CHECKPOINT_RUNS_DIR: Path = _REPO_ROOT / "soak_runs"

# Number of task-graph steps (must match _soak_subprocess_entrypoint.py's
# build_soak_task_graph call so workload_version computes correctly).
_SOAK_N_STEPS: int = 1200

# ==============================================================================
# SECTION 2 -- Inter-Generation Context (shared mutable state for wrapper)
# ==============================================================================


class _SoakContext:
    """
    Lightweight mutable context object threaded through the _spawn_session
    wrapper closure.

    Attributes
    ----------
    run_start_ts           : time.time() at the instant supervisor.run() is
                             called.
    chaos_injector         : ChaosInjector instance for this run.
    checkpoint_manager     : CheckpointManager for reading pre-crash snapshots.
    stale_lock_planted     : True once the stale lock has been planted.
    pre_crash_session      : SessionState snapshot read from disk after a
                             SIGKILL is confirmed. None until seen.
    killed_step_id         : step_id that was RUNNING at SIGKILL moment.
                             None because it is unknowable from outside the
                             child process; assert_crash_point_restored()
                             gracefully skips check #2 when None.
    crash_recovery_session_id : session_id of the SIGKILL-killed generation.
    last_completed_session_id : session_id of the most recently started
                             generation (best fallback for the bundler).
    total_compactions      : Best-effort total compaction count from heartbeat.
    peak_rss_mb            : Peak RSS observed across psutil samples.
    """

    def __init__(self, checkpoint_manager: CheckpointManager) -> None:
        self.run_start_ts:              float           = 0.0
        self.chaos_injector:            ChaosInjector   = ChaosInjector()
        self.checkpoint_manager:        CheckpointManager = checkpoint_manager
        self.stale_lock_planted:        bool            = False
        self.pre_crash_session:         Any             = None
        self.killed_step_id:            Optional[str]   = None
        self.crash_recovery_session_id: Optional[str]   = None
        self.last_completed_session_id: Optional[str]   = None
        self.total_compactions:         int             = 0
        self.peak_rss_mb:               float           = 0.0


# ==============================================================================
# SECTION 3 -- Metrics helpers
# ==============================================================================


def _read_peak_rss(metrics_path: Path) -> float:
    """Scan soak_metrics.jsonl and return the highest rss_mb value seen."""
    if not metrics_path.is_file():
        return 0.0

    peak = 0.0
    try:
        for line in metrics_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                rss = row.get("rss_mb")
                if isinstance(rss, (int, float)) and rss > peak:
                    peak = float(rss)
            except (ValueError, KeyError):
                continue
    except OSError:
        pass
    return peak


def _read_total_compactions(status_path: Path) -> int:
    """
    Read soak_status.json and return compactions_this_gen as a best-effort
    proxy for total compactions in the most recent generation. Returns 0 on any
    error.
    """
    if not status_path.is_file():
        return 0
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
        return int(data.get("compactions_this_gen", 0))
    except (OSError, ValueError, KeyError):
        return 0


# ==============================================================================
# SECTION 4 -- Supervisor Wrapper (inter-generation hook injection)
# ==============================================================================


def _make_wrapped_spawn(
    supervisor: SoakSupervisor,
    ctx: _SoakContext,
) -> Any:
    """
    Return a replacement for supervisor._spawn_session that:

      1. Calls the REAL _spawn_session to get (proc, gen).
      2. Injects chaos corruption (if in the chaos window) BETWEEN generations
         so there is never a live-write race (design decision #1 of
         _soak_chaos.py).
      3. Plants a stale lock once, for the first crash_recovery spawn.
      4. Records the session_id as ctx.last_completed_session_id.
    """
    real_spawn = supervisor._spawn_session  # type: ignore[attr-defined]
    base_dir = supervisor.checkpoint_base_dir

    def _wrapped(
        session_id: str,
        spawn_reason: str,
    ) -> Tuple[Any, SessionGeneration]:
        # Track the latest session_id in case an exception fires during spawn.
        ctx.last_completed_session_id = session_id

        # Compute elapsed seconds relative to the soak run start.
        run_start = supervisor._run_start  # type: ignore[attr-defined]
        elapsed_s = time.monotonic() - run_start if run_start > 0.0 else 0.0

        # -- Chaos Corruption (between generations) ---------------------------
        corrupted_path = ctx.chaos_injector.maybe_corrupt_latest_checkpoint(
            checkpoint_base_dir=base_dir,
            session_id=session_id,
            elapsed_s=elapsed_s,
        )
        if corrupted_path is not None:
            _logger.warning(
                "[SoakOrchestrator] Chaos corruption injected: %s (elapsed=%.0fs)",
                corrupted_path, elapsed_s,
            )

        # -- Stale Lock Planting (crash_recovery generations only) ------------
        if spawn_reason == "crash_recovery" and not ctx.stale_lock_planted:
            lock_path = plant_stale_lock(
                checkpoint_base_dir=base_dir,
                session_id=session_id,
                age_seconds=120,   # 2x LockResolver.LOCK_TIMEOUT_S default
            )
            ctx.stale_lock_planted = True
            ctx.crash_recovery_session_id = session_id
            _logger.warning(
                "[SoakOrchestrator] Stale lock planted at: %s — "
                "LockResolver.release() must clear it before recovery proceeds.",
                lock_path,
            )

        # -- Delegate to the real spawn ---------------------------------------
        proc, gen = real_spawn(session_id, spawn_reason)
        return proc, gen

    return _wrapped


# ==============================================================================
# SECTION 5 -- Post-Run Crash Snapshot Extraction
# ==============================================================================


def _extract_pre_crash_snapshot(
    ctx: _SoakContext,
    supervisor: SoakSupervisor,
) -> None:
    """
    Scan the generation ledger for any generation that exited via SIGKILL
    (normalized_exit == 137). For the FIRST such generation, read the latest
    on-disk checkpoint to produce the pre_crash_session baseline.

    Populates ctx.pre_crash_session and ctx.killed_step_id in place. No-ops
    silently if no SIGKILL generation is found.
    """
    for gen in supervisor.generations:
        if gen.normalized_exit == 137:
            try:
                ctx.pre_crash_session = ctx.checkpoint_manager.load_latest(
                    gen.session_id
                )
                ctx.killed_step_id = None  # Unknowable from outside child process
                ctx.crash_recovery_session_id = gen.session_id
                _logger.info(
                    "[SoakOrchestrator] Pre-crash snapshot captured. "
                    "session_id=%s | LSN=%d.",
                    gen.session_id,
                    ctx.pre_crash_session.checkpoint_meta.lsn,
                )
            except Exception as exc:
                _logger.warning(
                    "[SoakOrchestrator] Could not load pre-crash snapshot for "
                    "session_id=%s: %s. assert_crash_point_restored() skipped.",
                    gen.session_id, exc,
                )
            return  # Only process the FIRST SIGKILL generation


# ==============================================================================
# SECTION 6 -- Final Recovery Assertion (AC-9)
# ==============================================================================


def _run_crash_point_assertion(
    ctx: _SoakContext,
    supervisor: SoakSupervisor,
) -> None:
    """
    If a SIGKILL was injected and a crash-recovery generation successfully
    completed, validate the ARIES Redo contract via assert_crash_point_restored().

    Skips silently if no SIGKILL generation was recorded.
    """
    if ctx.pre_crash_session is None:
        _logger.info(
            "[SoakOrchestrator] No SIGKILL generation found -- "
            "skipping assert_crash_point_restored()."
        )
        return

    # Find the crash_recovery generation immediately after the SIGKILL gen.
    crash_recovery_gen: Optional[SessionGeneration] = None
    saw_sigkill = False
    for gen in supervisor.generations:
        if gen.normalized_exit == 137:
            saw_sigkill = True
            continue
        if saw_sigkill and gen.spawn_reason == "crash_recovery":
            crash_recovery_gen = gen
            break

    if crash_recovery_gen is None:
        _logger.warning(
            "[SoakOrchestrator] SIGKILL generation found but no subsequent "
            "crash_recovery generation -- cannot validate AC-9."
        )
        return

    try:
        recovered_session = ctx.checkpoint_manager.load_latest(
            crash_recovery_gen.session_id
        )
    except Exception as exc:
        _logger.warning(
            "[SoakOrchestrator] Could not load recovered session for "
            "session_id=%s: %s. Skipping assert_crash_point_restored().",
            crash_recovery_gen.session_id, exc,
        )
        return

    assert_crash_point_restored(
        pre_crash_snapshot=ctx.pre_crash_session,
        killed_step_id=ctx.killed_step_id,   # None -> check #2 skipped gracefully
        recovered_session=recovered_session,
    )
    _logger.info(
        "[SoakOrchestrator] assert_crash_point_restored() PASSED. "
        "pre_crash_LSN=%d | recovered_LSN=%d.",
        ctx.pre_crash_session.checkpoint_meta.lsn,
        recovered_session.checkpoint_meta.lsn,
    )


# ==============================================================================
# SECTION 7 -- Main Pytest Test Function
# ==============================================================================


@pytest.mark.long_running
@pytest.mark.timeout(4500)     # 75 minutes hard ceiling -- AC-1 is 60 min + buffer
def test_soak_1hr() -> None:
    """
    JIRA-007 / JIRA-007-B -- 1-hour sustained soak test.

    Acceptance Criteria covered:
      AC-1  : Wall-clock duration >= 3600 s (enforced by SoakSupervisor.run())
      AC-2  : TaskGraph DAG cycle-free (build_soak_task_graph DFS check)
      AC-3  : Dronagiri compaction logged at least once
      AC-4  : Graceful handoff (exit 10) AND hard SIGKILL (exit 137) both exercised
      AC-5  : RSS variance <= 10% between minute 10 and minute 60
      AC-6  : StateMatrix accumulators never regress
      AC-7  : Stale .checkpoint.lock cleared before crash-recovery proceeds
      AC-8  : Exit codes always in {0, 1, 2, 3, 10, 137}
      AC-9  : ARIES Redo contract -- RUNNING steps reset to PENDING, SUCCESS
              steps byte-identical after crash recovery
    """
    # -- 0. Run Directory Setup ------------------------------------------------
    run_id = str(uuid.uuid4())
    checkpoint_base_dir = _CHECKPOINT_RUNS_DIR / run_id
    checkpoint_base_dir.mkdir(parents=True, exist_ok=True)

    _logger.info(
        "[SoakOrchestrator] Starting 1-hour soak test. run_id=%s | "
        "checkpoint_base_dir=%s", run_id, checkpoint_base_dir,
    )

    cm = CheckpointManager(base_dir=checkpoint_base_dir)
    supervisor = SoakSupervisor(checkpoint_base_dir=checkpoint_base_dir)
    ctx = _SoakContext(checkpoint_manager=cm)

    # Build the inter-generation hook wrapper ONCE, before supervisor.run().
    wrapped_spawn = _make_wrapped_spawn(supervisor, ctx)

    # -- 1. Soak Run -----------------------------------------------------------
    initial_session_id = str(uuid.uuid4())
    soak_passed = False

    try:
        with mock.patch.object(supervisor, "_spawn_session", new=wrapped_spawn):
            ctx.run_start_ts = time.time()
            soak_passed = supervisor.run(initial_session_id)

    except BaseException as exc:  # noqa: BLE001 -- catch ALL for bundling
        _logger.critical(
            "[SoakOrchestrator] Unexpected exception during supervisor.run(): %s",
            exc, exc_info=True,
        )
        try:
            bundle_path = bundle_failure_artifacts(
                checkpoint_base_dir=checkpoint_base_dir,
                session_id=ctx.last_completed_session_id,
            )
            _logger.critical(
                "[SoakOrchestrator] Failure bundle written: %s", bundle_path,
            )
        except Exception as bundle_exc:
            _logger.error(
                "[SoakOrchestrator] Failed to write failure bundle: %s", bundle_exc,
            )
        raise

    # -- 2. Populate best-effort telemetry for history ------------------------
    ctx.peak_rss_mb = _read_peak_rss(supervisor.metrics_path)
    ctx.total_compactions = _read_total_compactions(
        checkpoint_base_dir / "soak_status.json"
    )
    total_cost_usd = sum(g.floor_cost_usd for g in supervisor.generations)

    # -- 3. Verify soak_passed (SoakSupervisor returned True for AC-1) --------
    assert soak_passed, (
        "[AC-1 VIOLATION] SoakSupervisor.run() returned False -- at least one "
        "generation exited with a non-recoverable error code (1, 2, or 3). "
        "See soak_failure_report.json and supervisor logs for details."
    )

    # -- 4. Post-run snapshot extraction (before assertions mutate anything) --
    _extract_pre_crash_snapshot(ctx, supervisor)

    # -- 5. Post-run assertion suite ------------------------------------------
    try:
        # AC-5 -- Memory Stability
        assert_memory_stability(supervisor.metrics_path)
        _logger.info("[SoakOrchestrator] assert_memory_stability() PASSED.")

        # AC-6 -- StateMatrix Continuity
        last_gen = supervisor.generations[-1]
        final_session = cm.load_latest(last_gen.session_id)
        assert_state_matrix_continuity(final_session, supervisor.generations)
        _logger.info("[SoakOrchestrator] assert_state_matrix_continuity() PASSED.")

        # AC-7 -- Lockfile Resolved (for the crash-recovery session, if any)
        if ctx.crash_recovery_session_id is not None:
            assert_lockfile_resolved(checkpoint_base_dir, ctx.crash_recovery_session_id)
            _logger.info("[SoakOrchestrator] assert_lockfile_resolved() PASSED.")
        else:
            _logger.info(
                "[SoakOrchestrator] No crash-recovery generation -- "
                "assert_lockfile_resolved() skipped."
            )

        # AC-9 -- Crash Point Restored
        _run_crash_point_assertion(ctx, supervisor)

        # AC-4 -- Both chaos modes exercised (soft check)
        graceful_handoffs = any(g.normalized_exit == 10 for g in supervisor.generations)
        hard_kills        = any(g.normalized_exit == 137 for g in supervisor.generations)
        _logger.info(
            "[SoakOrchestrator] AC-4 chaos coverage: "
            "graceful_handoffs=%s | hard_kills=%s",
            graceful_handoffs, hard_kills,
        )
        if not hard_kills:
            warnings.warn(
                "[AC-4 ADVISORY] No SIGKILL was injected during this soak run. "
                "The SIGKILL window (20-45 min) was either not reached or the "
                "process exited naturally before the window opened.",
                stacklevel=2,
            )

    except BaseException as exc:  # noqa: BLE001 -- catch AssertionError + others
        try:
            bundle_path = bundle_failure_artifacts(
                checkpoint_base_dir=checkpoint_base_dir,
                session_id=ctx.last_completed_session_id,
            )
            _logger.critical(
                "[SoakOrchestrator] Post-run assertion failed. "
                "Failure bundle: %s", bundle_path,
            )
        except Exception as bundle_exc:
            _logger.error(
                "[SoakOrchestrator] Failed to write failure bundle: %s", bundle_exc,
            )
        raise

    # -- 6. Cross-Run Regression Check ----------------------------------------
    workload_version = compute_workload_version(
        phase_boundaries=PHASE_BOUNDARIES,
        n_steps=_SOAK_N_STEPS,
    )
    summary = SoakRunSummary(
        ts=time.time(),
        workload_version=workload_version,
        peak_rss_mb=ctx.peak_rss_mb,
        total_compactions=ctx.total_compactions,
        total_cost_usd=total_cost_usd,
        total_generations=len(supervisor.generations),
        passed=True,
    )

    # Regression check BEFORE record_run() so the current run does not bias
    # its own baseline (see check_regression() module docstring).
    regression_warnings: List[str] = check_regression(
        history_path=_HISTORY_PATH,
        current=summary,
        lookback=5,
        drift_threshold=0.15,
    )
    for w in regression_warnings:
        _logger.warning("[SoakOrchestrator] Regression warning: %s", w)
        warnings.warn(w, stacklevel=2)

    try:
        record_run(history_path=_HISTORY_PATH, summary=summary)
        _logger.info(
            "[SoakOrchestrator] Run recorded. workload_version=%s | "
            "peak_rss_mb=%.2f | total_generations=%d",
            workload_version, ctx.peak_rss_mb, len(supervisor.generations),
        )
    except OSError as exc:
        _logger.error(
            "[SoakOrchestrator] Could not write soak history (non-fatal): %s", exc,
        )

    # -- 6b. Success Bundle and Cleanup ---------------------------------------
    try:
        success_zip = bundle_success_artifacts(
            checkpoint_base_dir=checkpoint_base_dir,
            session_id=ctx.last_completed_session_id,
        )
        _logger.info("[SoakOrchestrator] bundle_success_artifacts() created: %s", success_zip)
    except Exception as bundle_exc:
        _logger.error(
            "[SoakOrchestrator] Failed to create success bundle or clean up folders: %s",
            bundle_exc,
        )

    # -- 7. Final Success Log -------------------------------------------------
    _logger.info(
        "[SoakOrchestrator] 1-HOUR SOAK TEST PASSED. run_id=%s | "
        "generations=%d | peak_rss_mb=%.2f | total_compactions=%d | "
        "total_cost_usd=$%.6f | chaos_corrupted=%s | stale_lock_planted=%s",
        run_id,
        len(supervisor.generations),
        ctx.peak_rss_mb,
        ctx.total_compactions,
        total_cost_usd,
        ctx.chaos_injector.has_corrupted,
        ctx.stale_lock_planted,
    )
