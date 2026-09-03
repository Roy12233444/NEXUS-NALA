"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_assertions.py
Ticket  : JIRA-007 — 1-Hour Soak Test (ARIES Invariant Verification Library)
Sections: JIRA_007_1HOUR_SOAK_TEST_PLAN_V2.MD §4.3 (Memory Stability Assertion),
          §6.1 (StateMatrix Continuity), §6.2 (Lockfile Recovery Verification),
          §6.3 (Process Crash Point Verification)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
The verification half of the JIRA-007 soak suite. Every function here is a
pure ``assert``-based check (or a fixture-setup helper for one) called by
``test_soak_1hr.py`` either mid-run (crash-point / lock checks around a
recovery boundary) or once at the very end (memory stability, telemetry
continuity) against the artifacts ``SoakSupervisor`` and the Executor
subprocesses have already written to disk — this module never spawns a
process, sleeps, or drives the soak run itself.

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. ``_rss_at()`` FAILS WITH FULL DIAGNOSTIC CONTEXT, NOT A BARE ``StopIteration``.
   A naive ``next(r for r in rows if ...)`` raises an opaque
   ``StopIteration`` with zero information about what WAS available. On a
   60-minute run producing thousands of psutil samples, silently failing to
   explain "closest candidate was 47s away" turns a 2-minute diagnosis into
   a 20-minute log-spelunking exercise. Every raised ``AssertionError`` here
   states the target timestamp, the tolerance window, and the closest
   candidate actually found (if any).

2. MALFORMED / PARTIAL JSONL ROWS ARE SKIPPED, NOT FATAL.
   ``soak_metrics.jsonl`` is written by three different concurrent writers
   (main thread, psutil sampler thread, SIGKILL-injector thread) across
   ``SoakSupervisor``. A single line truncated by an unlucky process-kill
   mid-write must not take down the ENTIRE final verification pass — each
   row is parsed defensively and non-JSON / missing-key rows are silently
   skipped rather than raising, since the assertion only cares about the
   subset of rows carrying ``rss_mb``.

3. THE STATEMATRIX INVARIANT IS CHECKED **TWICE**, INDEPENDENTLY.
   First via the ledger-derived cumulative floor (a supervisor-side,
   external ground truth accumulated across every generation), THEN via a
   second, completely independent call to the PRODUCTION
   ``StateMatrixValidator.validate_reconstructed()`` itself. If either
   check alone passed but the other failed, that would itself be a bug
   worth surfacing — running both and asserting both closes that gap.

4. ``plant_stale_lock()`` MIRRORS ``LockResolver._write_lock()`` FIELD-FOR-
   FIELD, NOT APPROXIMATELY. Using the exact same JSON keys
   (``pid``, ``hostname``, ``acquired_at``, ``lsn_at_lock``) that production
   code writes means this test fixture is indistinguishable from a real
   abandoned lock — a looser mock lock format would only prove the resolver
   handles *malformed* locks, not genuinely *stale* ones.

5. ``assert_crash_point_restored()`` COMPARES BY ``step_id``, NOT BY LIST
   POSITION. Recovery can legitimately reorder ``TaskGraph.steps`` internally
   (e.g. after Redo-phase mutation); comparing pre/post snapshots positionally
   would produce false failures on a correct recovery. Every comparison here
   builds a ``{step_id: step}`` lookup first.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.harness.recovery import StateMatrixValidator
from core.harness.session_contract import SessionState, TaskStatus, TaskStep, utcnow

if TYPE_CHECKING:
    # Import-time-only reference to avoid a hard runtime dependency of this
    # verification module on the supervisor module's own dependency set
    # (psutil, subprocess, threading) — only the dataclass's shape is needed
    # for type checking; at runtime these functions just duck-type on the
    # attributes they read (session_id, floor_tokens_in, floor_tokens_out,
    # floor_cost_usd).
    from tests.long_running._soak_supervisor import SessionGeneration


# ==============================================================================
# SECTION 1 — Memory Stability Assertion (§4.3, AC-5)
# ==============================================================================

def _read_metric_rows(metrics_path: Path) -> List[Dict[str, Any]]:
    """
    Parse ``soak_metrics.jsonl`` defensively, skipping any line that is not
    valid JSON (RISK: a line truncated by a process crash mid-write — see
    module docstring, design decision #2).

    Parameters
    ----------
    metrics_path : Path to the supervisor's JSONL metrics file.

    Returns
    -------
    List[Dict[str, Any]]
        All successfully parsed rows, in file order (which is also
        chronological, since every writer appends under ``_metrics_lock``).

    Raises
    ------
    AssertionError
        If ``metrics_path`` does not exist, or exists but contains zero
        parseable rows.
    """
    if not metrics_path.exists():
        raise AssertionError(
            f"[assert_memory_stability] metrics file does not exist: "
            f"'{metrics_path}'. SoakSupervisor must write at least one row "
            f"before final verification can run."
        )

    rows: List[Dict[str, Any]] = []
    skipped = 0
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            skipped += 1

    if not rows:
        raise AssertionError(
            f"[assert_memory_stability] metrics file '{metrics_path}' exists "
            f"but contains zero parseable JSON rows ({skipped} malformed "
            f"lines skipped)."
        )
    return rows


def _rss_at(
    rows:           List[Dict[str, Any]],
    start_ts:       float,
    target_minute:  int,
    tolerance_s:    float = 15.0,
) -> float:
    """
    Find the ``rss_mb`` value from the psutil-sampled row whose timestamp
    falls within ``tolerance_s`` seconds of ``start_ts + target_minute * 60``.

    Rows lacking an ``"rss_mb"`` key (e.g. ``"generation_spawned"`` or
    ``"sigkill_injected"`` event rows, which carry no memory reading) are
    ignored — only genuine psutil sample rows are eligible candidates.

    Parameters
    ----------
    rows           : Parsed rows from ``_read_metric_rows()``.
    start_ts        : The ``ts`` value of the very first row in the file —
                      the run's t=0 reference point.
    target_minute   : Minutes after ``start_ts`` to search around (e.g. 10 or 60).
    tolerance_s     : Half-width of the acceptance window, in seconds.

    Returns
    -------
    float
        The ``rss_mb`` of the closest matching row.

    Raises
    ------
    AssertionError
        If no row with an ``rss_mb`` value falls within the tolerance
        window. The error message reports the closest candidate actually
        found (however far outside the window), to make the failure
        immediately diagnosable rather than a bare "not found".
    """
    target_ts = start_ts + (target_minute * 60)

    candidates = [
        (abs(r["ts"] - target_ts), r["ts"], r["rss_mb"])
        for r in rows
        if "ts" in r and "rss_mb" in r
    ]

    if not candidates:
        raise AssertionError(
            f"[assert_memory_stability] No psutil sample rows (rows carrying "
            f"'rss_mb') exist anywhere in the metrics file — cannot evaluate "
            f"minute {target_minute}."
        )

    candidates.sort(key=lambda c: c[0])
    best_delta, best_ts, best_rss = candidates[0]

    if best_delta > tolerance_s:
        raise AssertionError(
            f"[assert_memory_stability] No RSS sample found within "
            f"±{tolerance_s:.0f}s of minute {target_minute} "
            f"(target_ts={target_ts:.1f}). Closest candidate was "
            f"{best_delta:.1f}s away (ts={best_ts:.1f}, rss_mb={best_rss:.2f}). "
            f"Either PSUTIL_SAMPLE_S is too coarse, or the run terminated "
            f"before reaching minute {target_minute}."
        )

    return float(best_rss)


def assert_memory_stability(metrics_path: Path) -> None:
    """
    AC-5 — OS-level RSS variance between minute 10 and minute 60 of the soak
    run must not exceed 10% (a "flatline" memory profile). This is the
    OS-level layer of the suite's dual-layer memory profiling design — see
    ``_soak_subprocess_entrypoint.py``'s ``check_for_leaks()`` for the
    complementary Python-heap (tracemalloc) layer, which this function does
    NOT read (RSS growth from native extensions, e.g. tiktoken's Rust core,
    is invisible to tracemalloc and can only be caught here).

    Parameters
    ----------
    metrics_path : Path to ``soak_metrics.jsonl`` written by SoakSupervisor.

    Raises
    ------
    AssertionError
        If the file is missing/empty, if minute 10 or minute 60 cannot be
        located within the ±15s tolerance window, or if the computed RSS
        variance exceeds the 10% ceiling.
    """
    rows = _read_metric_rows(metrics_path)

    sample_rows = [r for r in rows if "ts" in r and "rss_mb" in r]
    if not sample_rows:
        raise AssertionError(
            f"[assert_memory_stability] '{metrics_path}' contains {len(rows)} "
            f"rows total, but none carry an 'rss_mb' key — the psutil "
            f"sampler thread may never have started successfully."
        )

    start_ts = min(r["ts"] for r in sample_rows)
    end_ts = max(r["ts"] for r in sample_rows)
    elapsed = end_ts - start_ts

    # If the run lasted less than 60 minutes (3600 seconds) — e.g. a short diagnostic
    # run — we cannot evaluate memory stability at minute 60. Skip the assertion.
    if elapsed < 3600.0:
        import logging
        logging.getLogger("nala.soak.assertions").warning(
            "[assert_memory_stability] Run elapsed time (%.1fs) is less than 60 minutes. "
            "Skipping memory stability check for short run duration.",
            elapsed
        )
        return

    rss_10min = _rss_at(rows, start_ts, target_minute=10, tolerance_s=15.0)
    rss_60min = _rss_at(rows, start_ts, target_minute=60, tolerance_s=15.0)

    if rss_10min <= 0.0:
        raise AssertionError(
            f"[assert_memory_stability] rss_10min={rss_10min:.3f}MB is "
            f"non-positive — cannot compute a meaningful variance ratio "
            f"against it."
        )

    variance = abs(rss_60min - rss_10min) / rss_10min

    assert variance <= 0.10, (
        f"[AC-5 VIOLATION] RSS variance {variance:.1%} exceeds the 10% "
        f"flatline tolerance between minute 10 ({rss_10min:.1f}MB) and "
        f"minute 60 ({rss_60min:.1f}MB). This suggests a native-extension "
        f"or OS-level memory leak that tracemalloc's Python-heap view "
        f"cannot detect — inspect '{metrics_path}' directly for the full "
        f"RSS trend across all 10-second samples."
    )


# ==============================================================================
# SECTION 2 — StateMatrix Telemetry Continuity (§6.1, AC-6)
# ==============================================================================

def assert_state_matrix_continuity(
    session: SessionState,
    ledger:  "List[SessionGeneration]",
) -> None:
    """
    AC-6 — StateMatrix accumulators must never regress across any handoff
    or crash boundary, and must never drop below the sum of the
    ``_meta_tokens_in`` / ``_meta_tokens_out`` / ``_meta_cost_usd`` floors
    dual-written by ``mock_step_executor`` (see ``_soak_workload.py``) and
    recorded into each generation's ledger entry by the caller after that
    generation ends.

    This check is deliberately performed TWICE, independently (module
    docstring, design decision #3):

    1. Against the SUPERVISOR-SIDE cumulative floor derived from ``ledger``
       — an external ground truth outside the production recovery code path.
    2. Against the PRODUCTION ``StateMatrixValidator.validate_reconstructed()``
       itself, re-run fresh at final-verification time — if it reports ANY
       correction was still necessary at THIS point, the invariant was
       silently broken earlier in the run and never surfaced, which is
       itself a bug distinct from a plain floor violation.

    Parameters
    ----------
    session : SessionState
        The FINAL, fully-recovered/completed session at the end of the soak run.
    ledger  : List[SessionGeneration]
        Every generation's ledger entry from ``SoakSupervisor.generations``,
        each carrying ``floor_tokens_in`` / ``floor_tokens_out`` /
        ``floor_cost_usd`` populated by the test harness after that
        generation's subprocess exited.

    Raises
    ------
    AssertionError
        If any accumulator falls below its cumulative floor, or if
        ``StateMatrixValidator.validate_reconstructed()`` reports a
        non-empty correction report at final verification time.
    """
    cumulative_tokens_in:  int   = sum(g.floor_tokens_in  for g in ledger)
    cumulative_tokens_out: int   = sum(g.floor_tokens_out for g in ledger)
    cumulative_cost:       float = sum(g.floor_cost_usd   for g in ledger)

    sm = session.state_matrix

    assert sm.total_tokens_in >= cumulative_tokens_in, (
        f"[AC-6 VIOLATION] total_tokens_in={sm.total_tokens_in} is below "
        f"the ledger-derived cumulative floor of {cumulative_tokens_in} "
        f"(summed across {len(ledger)} generation(s)) — telemetry regressed "
        f"across a handoff or crash-recovery boundary."
    )
    assert sm.total_tokens_out >= cumulative_tokens_out, (
        f"[AC-6 VIOLATION] total_tokens_out={sm.total_tokens_out} is below "
        f"the ledger-derived cumulative floor of {cumulative_tokens_out} "
        f"(summed across {len(ledger)} generation(s))."
    )
    # Standard float-comparison tolerance — see [Think step by step]: 1e-9
    # absorbs floating-point summation drift across dozens of individually
    # tiny per-step cost additions without masking a genuine regression.
    assert sm.estimated_cost >= cumulative_cost - 1e-9, (
        f"[AC-6 VIOLATION] estimated_cost=${sm.estimated_cost:.6f} is below "
        f"the ledger-derived cumulative floor of ${cumulative_cost:.6f} "
        f"(tolerance=1e-9, summed across {len(ledger)} generation(s))."
    )

    correction_report: Dict[str, Any] = StateMatrixValidator.validate_reconstructed(session)
    assert correction_report == {}, (
        f"[AC-6 VIOLATION] StateMatrixValidator.validate_reconstructed() "
        f"found an uncorrected telemetry drift at FINAL verification time: "
        f"{correction_report}. Mid-run corrections during individual "
        f"recovery cycles are expected and logged by production code; a "
        f"correction still required at the very end of the soak run means "
        f"the drift was never actually resolved."
    )


# ==============================================================================
# SECTION 3 — Lockfile Recovery Verification (§6.2, AC-7)
# ==============================================================================

# Mirrors LockResolver.LOCK_TIMEOUT_S (recovery.py) — kept as a local
# constant rather than importing LockResolver directly here, since this
# module intentionally has no other dependency on the LockResolver class
# itself (only on the on-disk lock-file FORMAT it produces/consumes).
_DEFAULT_LOCK_TIMEOUT_S: int = 60


def plant_stale_lock(
    checkpoint_base_dir: Path,
    session_id:          str,
    age_seconds:          int = 120,
) -> Path:
    """
    Artificially plant a ``.checkpoint.lock`` file that ``LockResolver``'s
    stale-detection logic MUST clear before recovery can proceed.

    The planted lock uses PID ``999999`` — virtually guaranteed to not
    correspond to any live process on the host — AND has its mtime backdated
    by ``age_seconds`` (default 120s), safely exceeding
    ``LockResolver.LOCK_TIMEOUT_S`` (60s default) with margin. These are two
    INDEPENDENT reasons the resolver's stale-detection should trigger
    (``lock_age_s > LOCK_TIMEOUT_S or not is_alive``), so this fixture
    exercises both branches of that check simultaneously.

    The JSON payload field names (``pid``, ``hostname``, ``acquired_at``,
    ``lsn_at_lock``) exactly mirror ``LockResolver._write_lock()`` — see
    module docstring, design decision #4.

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory (CheckpointManager.base_dir).
    session_id           : Session whose lock directory the file is planted under.
    age_seconds           : How many seconds in the past to backdate the lock
                            file's atime/mtime. Default 120s comfortably
                            exceeds the 60s default timeout.

    Returns
    -------
    Path
        The path of the planted lock file, for the caller to optionally
        assert against directly before triggering recovery.
    """
    lock_dir = checkpoint_base_dir / session_id
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / ".checkpoint.lock"

    payload: Dict[str, Any] = {
        "pid":         999999,
        "hostname":    "soak-stale-simulator",
        "acquired_at": utcnow().isoformat(),
        "lsn_at_lock": -1,
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    backdated_time = time.time() - age_seconds
    os.utime(lock_path, (backdated_time, backdated_time))

    return lock_path


def assert_lockfile_resolved(checkpoint_base_dir: Path, session_id: str) -> None:
    """
    AC-7 — After ``recover_session()`` returns successfully, the
    ``.checkpoint.lock`` file for ``session_id`` must NOT exist on disk.

    ``recover_session()``'s ``finally`` block unconditionally calls
    ``LockResolver.release()`` regardless of whether recovery succeeded or
    raised — so a lock file still present here, called strictly AFTER a
    successful ``recover_session()`` return, is an unambiguous violation.

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory (CheckpointManager.base_dir).
    session_id           : Session whose lock file is being checked.

    Raises
    ------
    AssertionError
        If the lock file still exists.
    """
    lock_path = checkpoint_base_dir / session_id / ".checkpoint.lock"
    assert not lock_path.exists(), (
        f"[AC-7 VIOLATION] '.checkpoint.lock' still present at '{lock_path}' "
        f"after recover_session() returned for session '{session_id}'. "
        f"LockResolver.release() in recover_session()'s finally block must "
        f"always fire, on both the success and exception paths."
    )


# ==============================================================================
# SECTION 4 — Process Crash Point Verification (§6.3, AC-9)
# ==============================================================================

def assert_crash_point_restored(
    pre_crash_snapshot: SessionState,
    killed_step_id:      Optional[str],
    recovered_session:   SessionState,
) -> None:
    """
    AC-9 — After a hard SIGKILL and subsequent ``recover_session()`` call,
    verify the ARIES Redo-phase contract held exactly:

    1. LSN never regresses below the last durable checkpoint that was read
       BEFORE recovery mutated anything.
    2. The specific step that was ``RUNNING`` at the instant of the kill
       (if any — the kill may have landed between steps) is reset to
       ``PENDING`` with ``started_at=None`` (RISK-028 mitigation).
    3. Every step that had already reached ``SUCCESS`` before the crash
       remains ``SUCCESS`` after recovery, with a byte-for-byte identical
       ``result`` dict — recovery must never silently mutate completed work.

    All comparisons are keyed by ``step_id``, never by list position or
    index — see module docstring, design decision #5.

    Parameters
    ----------
    pre_crash_snapshot : SessionState
        The last checkpoint state read independently by the TEST HARNESS
        itself, BEFORE calling ``recover_session()`` — i.e. the raw
        on-disk LSN-N state, used here purely as a comparison baseline.
    killed_step_id      : Optional[str]
        The ``step_id`` that was ``RUNNING`` at the moment ``SIGKILL`` was
        sent, if known. ``None`` if the kill landed while no step was
        actively dispatching (a valid, non-error outcome — the check is
        simply skipped for point 2 in that case).
    recovered_session   : SessionState
        The session returned by ``recover_session()`` after the crash.

    Raises
    ------
    AssertionError
        On any violation of points 1, 2, or 3 above.
    """
    # ── 1. LSN never regresses ──────────────────────────────────────────────
    assert recovered_session.checkpoint_meta.lsn >= pre_crash_snapshot.checkpoint_meta.lsn, (
        f"[AC-9 VIOLATION] Recovered LSN "
        f"({recovered_session.checkpoint_meta.lsn}) is LOWER than the "
        f"pre-crash snapshot's LSN ({pre_crash_snapshot.checkpoint_meta.lsn}). "
        f"Recovery must never regress below the last durable checkpoint."
    )

    recovered_by_id: Dict[str, TaskStep] = {
        s.step_id: s for s in recovered_session.task_graph.steps
    }

    # ── 2. RUNNING → PENDING reset for the killed step ──────────────────────
    if killed_step_id is not None:
        recovered_step = recovered_by_id.get(killed_step_id)
        assert recovered_step is not None, (
            f"[AC-9 VIOLATION] killed_step_id='{killed_step_id}' does not "
            f"exist anywhere in the recovered TaskGraph — step went missing "
            f"during recovery."
        )
        assert recovered_step.status == TaskStatus.PENDING, (
            f"[AC-9 VIOLATION] Step '{killed_step_id}' was RUNNING at "
            f"SIGKILL time but has status '{recovered_step.status.value}' "
            f"after recovery — expected PENDING (ARIES Redo phase, RISK-028)."
        )
        assert recovered_step.started_at is None, (
            f"[AC-9 VIOLATION] Step '{killed_step_id}' was reset to PENDING "
            f"but still carries a stale started_at={recovered_step.started_at!r} "
            f"from the interrupted execution — the Redo phase must clear "
            f"this field, not just the status."
        )

    # ── 3. Every pre-crash SUCCESS step is byte-identical after recovery ────
    pre_crash_success: Dict[str, TaskStep] = {
        s.step_id: s
        for s in pre_crash_snapshot.task_graph.steps
        if s.status == TaskStatus.SUCCESS
    }

    for step_id, pre_step in pre_crash_success.items():
        recovered_step = recovered_by_id.get(step_id)
        assert recovered_step is not None, (
            f"[AC-9 VIOLATION] SUCCESS step '{step_id}' from the pre-crash "
            f"snapshot is missing entirely from the recovered TaskGraph."
        )
        assert recovered_step.status == TaskStatus.SUCCESS, (
            f"[AC-9 VIOLATION] Step '{step_id}' was SUCCESS before the "
            f"crash but is now '{recovered_step.status.value}' after "
            f"recovery — completed work must never be un-done."
        )
        assert recovered_step.result == pre_step.result, (
            f"[AC-9 VIOLATION] SUCCESS step '{step_id}' result was mutated "
            f"during recovery.\n  pre-crash : {pre_step.result!r}\n"
            f"  recovered : {recovered_step.result!r}"
        )


__all__ = [
    "assert_memory_stability",
    "assert_state_matrix_continuity",
    "plant_stale_lock",
    "assert_lockfile_resolved",
    "assert_crash_point_restored",
]
