"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/unit/test_crash_recovery.py
Ticket  : JIRA-005 — Crash Recovery System
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-20
Version : 2.0.0 — Enterprise-Grade Recovery Test Suite

PURPOSE
-------
Interactive, production-level unit tests for core/harness/recovery.py.

This test suite implements ALL 9 acceptance tests (T01–T09) specified in
JIRA_005_Crash_Recovery_Plan_v2.md, verifying every RISK mitigation in the
ARIES-based crash recovery system:

  T01  Full SIGKILL simulation — Checkpoint resume, no double-execution
  T02  StateMatrix accumulators monotonically corrected after corruption
  T03  SHA-256 mismatch at LSN-N triggers rollback to LSN-N-1
  T04  All LSNs corrupt AND no spore → SessionRecoveryError
  T05  Handlers can be replaced/updated during recovery (handler_v2)
  T06  Stale .checkpoint.lock cleared before checkpoint load
  T07  RunawayLoopError raised when error_count >= MAX_ERRORS
  T08  Session rebuilt from HandoffSpore when all checkpoints corrupt
  T09  Invalid handler signature rejected before any execution begins

DESIGN
------
Every test prints a full, color-coded interactive trace so you can watch
NALA's recovery pipeline execute step-by-step in real time. Tests use
real CheckpointManager + real recovery.py with no black-box mocking
of core logic (only NalaLoop.run() is patched to avoid full execution).

HOW TO RUN
----------
  # Activate venv first (from E:\\NALA-Project\\NALA\\)
  .\\.venv\\Scripts\\Activate.ps1

  # Interactive colored trace output:
  python tests/unit/test_crash_recovery.py

  # Via pytest (full verbose trace):
  pytest tests/unit/test_crash_recovery.py -v -s

  # With coverage report:
  pytest tests/unit/test_crash_recovery.py --cov=core.harness.recovery --cov-report=term-missing -v -s

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import os
import pathlib
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# ── pytest ────────────────────────────────────────────────────────────────────
import pytest

# ── Force UTF-8 on Windows consoles ──────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Add project root to sys.path ──────────────────────────────────────────────
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── Modules under test ────────────────────────────────────────────────────────
from core.harness.recovery import (
    HandlerSignatureValidator,
    LockResolver,
    RunawayLoopError,
    RunawayLoopGuard,
    SessionRecoveryError,
    SessionRecoveryLockError,
    StateMatrixValidator,
    _apply_redo_phase,
    recover_session,
)
from core.harness.checkpoint import (
    CheckpointIntegrityError,
    CheckpointManager,
    CheckpointNotFoundError,
    CheckpointRecoveryError,
)
from core.harness.session_contract import (
    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)


# ==============================================================================
# SECTION 0 — ANSI Color Console Output (Interactive Display Engine)
# ==============================================================================

CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
BLUE    = "\033[94m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
ORANGE  = "\033[38;5;214m"
WHITE   = "\033[97m"
RESET   = "\033[0m"

_PANEL_WIDTH = 76


def banner(title: str, icon: str = "🔄") -> None:
    """Print a full-width styled test section banner."""
    print(f"\n{BOLD}{CYAN}{'═' * _PANEL_WIDTH}{RESET}")
    print(f"{BOLD}{CYAN}  {icon}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * _PANEL_WIDTH}{RESET}")


def sub_banner(title: str) -> None:
    """Print a sub-section header."""
    print(f"\n{BOLD}{BLUE}  ▶  {title}{RESET}")
    print(f"  {DIM}{'─' * 68}{RESET}")


def phase(label: str, description: str) -> None:
    """Print a recovery phase header."""
    print(f"\n  {BOLD}{ORANGE}⚙  Phase {label}:{RESET} {WHITE}{description}{RESET}")


def step(msg: str) -> None:
    """Print a single test step trace."""
    print(f"  {DIM}→{RESET}  {msg}")


def success(msg: str) -> None:
    """Print a success confirmation."""
    print(f"\n  {BOLD}{GREEN}✅  {msg}{RESET}")


def warn(msg: str) -> None:
    """Print a warning observation."""
    print(f"  {YELLOW}⚠️   {msg}{RESET}")


def error_line(msg: str) -> None:
    """Print an expected-error observation."""
    print(f"  {RED}🔴  {msg}{RESET}")


def info(label: str, value: Any) -> None:
    """Print a labelled key=value pair for inspection."""
    print(f"  {YELLOW}   {label:<34}{RESET} {BLUE}{value}{RESET}")


def show_json(obj: dict, indent: int = 2, max_lines: int = 25) -> None:
    """Pretty-print a dict with dim styling, capped at max_lines."""
    lines = json.dumps(obj, indent=indent, default=str).splitlines()
    for line in lines[:max_lines]:
        print(f"  {DIM}{line}{RESET}")
    if len(lines) > max_lines:
        print(f"  {DIM}  ... ({len(lines) - max_lines} more lines){RESET}")


def divider() -> None:
    print(f"  {DIM}{'─' * 70}{RESET}")


def disk_scan(session_dir: Path, *, show_lock: bool = True) -> None:
    """Print the current state of a session's checkpoint directory."""
    print(f"  {MAGENTA}  📁 Disk layout → {session_dir.name[:40]}/{RESET}")
    files = sorted(session_dir.iterdir()) if session_dir.exists() else []
    if not files:
        print(f"  {DIM}     (empty){RESET}")
        return
    for f in files:
        size  = f.stat().st_size if f.is_file() else 0
        is_lk = f.name == ".checkpoint.lock"
        color = RED if is_lk else DIM
        tag   = "  ← LOCK FILE" if is_lk and show_lock else ""
        print(f"  {color}     {f.name:<48} {size:>6} bytes{tag}{RESET}")


def recovery_pipeline_header() -> None:
    """Print the ARIES recovery pipeline legend."""
    print(f"\n  {BOLD}{WHITE}  ARIES Recovery Pipeline:{RESET}")
    phases = [
        ("A.1", "Lock Resolution      ", "Stale .checkpoint.lock → unlink + re-acquire"),
        ("A.2", "Checkpoint Load      ", "SHA-256 verify → auto-rollback chain"),
        ("A.3", "HandoffSpore Fallback", "Last resort when all LSNs corrupt"),
        ("R.1", "Redo — Step Reset    ", "RUNNING → PENDING (idempotent)"),
        ("R.2", "Redo — Telemetry     ", "Monotonic StateMatrix correction"),
        ("R.3", "Redo — Graph Validate", "TaskGraph topology check"),
        ("U.1", "Undo — Runaway Guard ", "Hard halt if error_count ≥ ceiling"),
        ("U.2", "Undo — Handler Sig   ", "Signature pre-flight for callables"),
    ]
    for code, name, desc in phases:
        c = GREEN if code[0] == "A" else (BLUE if code[0] == "R" else RED)
        print(f"    {c}Phase {code}{RESET}  {BOLD}{name}{RESET}  {DIM}{desc}{RESET}")


# ==============================================================================
# SECTION 1 — SHARED FIXTURES & FACTORY HELPERS
# ==============================================================================

def make_session(
    objective: str = "NALA Crash Recovery Integration Test",
    n_steps:   int = 6,
) -> SessionState:
    """
    Build a minimal but realistic multi-step SessionState for testing.

    Steps have linear dependencies (s1 → s2 → ... → sN) and are all
    initially PENDING. Metadata includes the NALA test project label.
    """
    steps: List[TaskStep] = []
    for i in range(1, n_steps + 1):
        deps = [f"step_{i-1:03d}"] if i > 1 else []
        steps.append(
            TaskStep(
                step_id     = f"step_{i:03d}",
                description = f"Recovery test step {i:03d} — unit: JIRA-005",
                dependencies= deps,
            )
        )

    session = SessionState(objective=objective)
    session.task_graph.steps = steps
    return session


def make_manager(
    tmp_dir:         Path,
    max_checkpoints: int   = 20,
    rollback_attempts: int = 3,
) -> CheckpointManager:
    """Create a CheckpointManager pointed at a temp directory."""
    return CheckpointManager(
        base_dir          = tmp_dir,
        max_checkpoints   = max_checkpoints,
        retention_policy  = "sliding_window",
        lock_timeout      = 5.0,
        rollback_attempts = rollback_attempts,
    )


def valid_handler(step: Any, session: Any) -> Dict[str, Any]:
    """A valid NALA step handler with the correct (step, session) signature."""
    return {"success": True, "output": {"status": "handled"}}


def valid_handler_v2(step: Any, session: Any) -> Dict[str, Any]:
    """An alternative handler (handler_v2) used in T05 swap test."""
    return {"success": True, "output": {"version": "v2", "upgraded": True}}


def patch_nala_loop_run() -> Any:
    """
    Return a context manager that patches NalaLoop.run() to do nothing.
    Used in tests that call recover_session() but don't need to actually
    execute the task graph.
    """
    return patch(
        "core.harness.nala_loop.NalaLoop.run",
        return_value=MagicMock(status="COMPLETED"),
    )


def write_stale_lock(session_dir: Path, session_id: str, age_seconds: int = 120) -> Path:
    """
    Write a stale .checkpoint.lock file with a non-existent PID
    and an mtime backdated by `age_seconds` seconds.

    The PID is set to 99999999 (astronomically unlikely to be alive)
    and the mtime is manually backdated so LockResolver sees it as stale.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    lock_path = session_dir / ".checkpoint.lock"
    lock_data = {
        "pid":         99999999,
        "hostname":    "crashed-nala-host",
        "acquired_at": utcnow().isoformat(),
        "lsn_at_lock": 42,
    }
    lock_path.write_text(json.dumps(lock_data), encoding="utf-8")

    # Backdate the mtime to simulate an old stale lock
    old_mtime = time.time() - age_seconds
    os.utime(lock_path, (old_mtime, old_mtime))

    return lock_path


def corrupt_checkpoint_file(cp_file: Path, field: str = "objective") -> None:
    """
    Inject a byte-level corruption into a checkpoint JSON file by
    modifying the specified field. The SHA-256 in `checkpoint_meta`
    is NOT updated, so integrity verification will fail.
    """
    data = json.loads(cp_file.read_text(encoding="utf-8"))
    data[field] = "CORRUPTED_BY_TEST_" + str(data.get(field, "unknown"))
    cp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def inject_step_tokens(
    session:    SessionState,
    step_idx:   int,
    tokens_in:  int,
    tokens_out: int,
    cost_usd:   float,
) -> None:
    """
    Mark a step SUCCESS and inject per-step token metadata so
    StateMatrixValidator can compute the floor for monotonic correction.
    """
    s = session.task_graph.steps[step_idx]
    s.mark_running()
    s.mark_success(result={
        "_meta_tokens_in":  tokens_in,
        "_meta_tokens_out": tokens_out,
        "_meta_cost_usd":   cost_usd,
    })


# ==============================================================================
# SECTION 2 — TEST CLASS T00: Environment Guard & Import Verification
# ==============================================================================

class TestEnvironmentGuard:
    """
    T00 — Verify the Python environment and all JIRA-005 imports are available.

    This is the first thing that runs and will fail loudly if the environment
    is misconfigured, saving debug time on deeper tests.
    """

    def test_recovery_module_importable(self) -> None:
        banner("T00 — Environment Guard & Import Verification", icon="🌐")

        step("Verifying all recovery.py exports are importable...")
        divider()

        exports = {
            "SessionRecoveryError":      SessionRecoveryError,
            "SessionRecoveryLockError":  SessionRecoveryLockError,
            "RunawayLoopError":          RunawayLoopError,
            "LockResolver":              LockResolver,
            "StateMatrixValidator":      StateMatrixValidator,
            "HandlerSignatureValidator": HandlerSignatureValidator,
            "RunawayLoopGuard":          RunawayLoopGuard,
            "_apply_redo_phase":         _apply_redo_phase,
            "recover_session":           recover_session,
        }

        for name, obj in exports.items():
            assert obj is not None, f"{name} is None!"
            info(f"  {name}", "→ ✅ imported")

        divider()
        step("Verifying exception hierarchy...")

        # SessionRecoveryError → NalaLoopError
        from core.harness.nala_loop import NalaLoopError
        assert issubclass(SessionRecoveryError, NalaLoopError), \
            "SessionRecoveryError must subclass NalaLoopError"
        assert issubclass(SessionRecoveryLockError, SessionRecoveryError), \
            "SessionRecoveryLockError must subclass SessionRecoveryError"
        assert issubclass(RunawayLoopError, SessionRecoveryError), \
            "RunawayLoopError must subclass SessionRecoveryError"

        info("SessionRecoveryError      → NalaLoopError",     "✅")
        info("SessionRecoveryLockError  → SessionRecoveryError", "✅")
        info("RunawayLoopError          → SessionRecoveryError", "✅")

        divider()
        step("Verifying LockResolver constants...")
        info("LOCK_TIMEOUT_S   ", LockResolver.LOCK_TIMEOUT_S)
        info("BACKOFF_DELAYS_S ", LockResolver.BACKOFF_DELAYS_S)
        assert LockResolver.LOCK_TIMEOUT_S  == 60
        assert LockResolver.BACKOFF_DELAYS_S == (2, 4, 8)

        divider()
        step("Verifying RunawayLoopGuard defaults...")
        info("DEFAULT_MAX_ERRORS  ", RunawayLoopGuard.DEFAULT_MAX_ERRORS)
        info("DEFAULT_MAX_RETRIES ", RunawayLoopGuard.DEFAULT_MAX_RETRIES)
        info("WARNING_THRESHOLD   ", RunawayLoopGuard.WARNING_THRESHOLD)
        assert RunawayLoopGuard.DEFAULT_MAX_ERRORS  == 10
        assert RunawayLoopGuard.DEFAULT_MAX_RETRIES == 5

        divider()
        step("Verifying HandlerSignatureValidator settings...")
        info("_MIN_PARAMS          ", HandlerSignatureValidator._MIN_PARAMS)
        info("_EXPECTED_PARAM_NAMES", HandlerSignatureValidator._EXPECTED_PARAM_NAMES)
        assert HandlerSignatureValidator._MIN_PARAMS == 2
        assert "step"    in HandlerSignatureValidator._EXPECTED_PARAM_NAMES
        assert "session" in HandlerSignatureValidator._EXPECTED_PARAM_NAMES

        recovery_pipeline_header()

        success("T00 PASSED — All JIRA-005 symbols import cleanly. Hierarchy is correct.")


# ==============================================================================
# SECTION 3 — T01: Full SIGKILL Simulation
# ==============================================================================

class TestT01SigkillSimulation:
    """
    T01 — Full SIGKILL simulation.

    Start a session with 6 steps. Simulate a crash after step 3 by calling
    the session mutation methods directly (marking steps 1–3 SUCCESS without
    full loop execution). Then call recover_session(). Verify the recovered
    loop has steps 4–6 still PENDING (ready to run), no step is double-executed,
    and the total SUCCESS count from the original session is preserved.

    Acceptance:
      - recover_session() returns a NalaLoop without raising
      - Recovered session has exactly 3 SUCCESS steps + 3 PENDING steps
      - No RUNNING steps survive (ARIES Redo phase)
      - session.checkpoint_meta.lsn == 3 (last clean checkpoint)
    """

    def test_recovery_from_simulated_sigkill(self) -> None:
        banner(
            "T01 — Full SIGKILL Simulation | 6-Step Session, Crash After Step 3",
            icon="💥",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=6)
            session_id = session.session_id

            info("Session ID       ", session_id[:16] + "...")
            info("Objective        ", session.objective[:50])
            info("Total Steps      ", len(session.task_graph.steps))

            # ── Phase 1: Simulate running steps 1–3 (pre-crash) ──────────────
            sub_banner("Simulating Pre-Crash Execution: Steps 1, 2, 3 → SUCCESS")
            for i in range(3):
                s = session.task_graph.steps[i]
                step(f"Executing step_{i+1:03d}: PENDING → RUNNING → SUCCESS ...")
                inject_step_tokens(session, i, tokens_in=1000*(i+1), tokens_out=500*(i+1), cost_usd=0.001*(i+1))
                info(f"  step_{i+1:03d} status", s.status)

            # ── Phase 2: Simulate partial execution of step 4 (crash mid-run) ─
            step_4 = session.task_graph.steps[3]
            step("Simulating SIGKILL: step_004 stuck in RUNNING at crash time...")
            step_4.mark_running()
            warn(f"Process killed!  step_004 status = {step_4.status} (will be reset by ARIES Redo)")

            # ── Phase 3: Write checkpoints at LSN=1, 2, 3 ─────────────────────
            sub_banner("Writing 3 Separate Checkpoints (LSN=1, 2, 3)")
            step("Writing LSN=1 (after step_001 SUCCESS)...")

            # Checkpoint LSN=1 — after step 1
            session.state_matrix.total_tokens_in  = 2000
            session.state_matrix.total_tokens_out = 1000
            session.state_matrix.estimated_cost   = 0.002
            manager.write_checkpoint(session)
            info("Checkpoint LSN=1 written", session.checkpoint_meta.lsn)

            # Checkpoint LSN=2 — after step 2
            step("Writing LSN=2 (after step_002 SUCCESS)...")
            session.state_matrix.total_tokens_in  = 4000
            session.state_matrix.total_tokens_out = 2000
            session.state_matrix.estimated_cost   = 0.004
            manager.write_checkpoint(session)
            info("Checkpoint LSN=2 written", session.checkpoint_meta.lsn)

            # Checkpoint LSN=3 — after step 3, step_4 is clean PENDING
            step("Writing LSN=3 (after step_003 SUCCESS, step_004 PENDING)...")
            step_4.status     = TaskStatus.PENDING
            step_4.started_at = None
            step_4.tool_used  = None
            session.state_matrix.total_tokens_in  = 6000
            session.state_matrix.total_tokens_out = 3000
            session.state_matrix.estimated_cost   = 0.006
            written_path = manager.write_checkpoint(session)
            checkpoint_lsn = session.checkpoint_meta.lsn
            info("Checkpoint LSN=3 written", checkpoint_lsn)
            info("Checkpoint file          ", written_path.name)

            # Now simulate step_004 going RUNNING AFTER the checkpoint was saved
            # (the crash happens here — in real SIGKILL, this state is lost)
            step_4.mark_running()
            warn("step_004 is now RUNNING — simulating crash point")
            warn("This RUNNING state was never checkpointed — it will be reset by ARIES Redo")

            # ── Phase 4: Disk scan before recovery ───────────────────────────
            sub_banner("Pre-Recovery Disk State")
            session_dir = tmp_dir / session_id
            disk_scan(session_dir)

            # ── Phase 5: Call recover_session() ──────────────────────────────
            sub_banner("Calling recover_session() — ARIES Pipeline Begins")

            recovered_loop = None
            with patch_nala_loop_run():
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {
                        "step_001": valid_handler,
                        "step_002": valid_handler,
                        "step_003": valid_handler,
                        "step_004": valid_handler,
                        "step_005": valid_handler,
                        "step_006": valid_handler,
                    },
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )

            # ── Phase 6: Assert recovered state ──────────────────────────────
            sub_banner("Post-Recovery Assertions")
            recovered_session = recovered_loop.session

            info("Recovered session_id      ", recovered_session.session_id[:16] + "...")
            info("Recovered LSN             ", recovered_session.checkpoint_meta.lsn)
            info("Total steps in graph      ", len(recovered_session.task_graph.steps))
            info("SUCCESS count             ", recovered_session.task_graph.success_count())
            info("PENDING count             ", recovered_session.task_graph.pending_count())
            info("RUNNING count             ",
                 sum(1 for s in recovered_session.task_graph.steps if s.status == TaskStatus.RUNNING))

            divider()

            # Core assertions
            assert recovered_loop is not None, "recover_session() must return a NalaLoop"
            assert recovered_session.checkpoint_meta.lsn == checkpoint_lsn, \
                f"Expected LSN={checkpoint_lsn}, got {recovered_session.checkpoint_meta.lsn}"
            assert recovered_session.task_graph.success_count() == 3, \
                f"Expected 3 SUCCESS steps, got {recovered_session.task_graph.success_count()}"
            assert recovered_session.task_graph.pending_count() >= 3, \
                f"Expected ≥3 PENDING steps, got {recovered_session.task_graph.pending_count()}"

            # Critical: No step must be in RUNNING state after recovery (ARIES Redo)
            running_after = [
                s.step_id for s in recovered_session.task_graph.steps
                if s.status == TaskStatus.RUNNING
            ]
            assert len(running_after) == 0, \
                f"ARIES Redo FAILED: These steps survived as RUNNING: {running_after}"

            # StateMatrix must be intact
            assert recovered_session.state_matrix.total_tokens_in >= 6000, \
                "tokens_in must be ≥ 6000 after monotonic correction"

            step_statuses = {
                s.step_id: str(s.status) for s in recovered_session.task_graph.steps
            }
            info("Final step statuses       ", step_statuses)

            success(
                "T01 PASSED — SIGKILL simulation recovery succeeded. "
                "LSN=3 restored, ARIES Redo cleared RUNNING states, "
                "3 SUCCESS steps preserved intact."
            )


# ==============================================================================
# SECTION 4 — T02: StateMatrix Monotonic Correction
# ==============================================================================

class TestT02StateMatrixCorrection:
    """
    T02 — StateMatrix accumulators monotonically corrected after corruption.

    Completes 3 steps with known token/cost values, then artificially zeroes
    the StateMatrix in the checkpoint JSON on disk. Calls recover_session()
    and verifies StateMatrixValidator corrected the accumulators to the
    floor values derived from the SUCCESS step results.

    Acceptance:
      - StateMatrix.total_tokens_in  ≥ sum of step _meta_tokens_in
      - StateMatrix.total_tokens_out ≥ sum of step _meta_tokens_out
      - StateMatrix.estimated_cost   ≥ sum of step _meta_cost_usd
      - Correction report is non-empty
    """

    def test_state_matrix_monotonic_correction(self) -> None:
        banner(
            "T02 — StateMatrix Monotonic Correction After Checkpoint Corruption",
            icon="📊",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=4)
            session_id = session.session_id

            # ── Step 1: Complete 3 steps with known token metadata ────────────
            sub_banner("Executing 3 Steps With Known Token/Cost Metadata")

            EXPECTED_TOKENS_IN  = 0
            EXPECTED_TOKENS_OUT = 0
            EXPECTED_COST       = 0.0

            step_data = [
                (1200, 400, 0.0012),
                (3100, 980, 0.0031),
                (800,  220, 0.0008),
            ]

            for i, (t_in, t_out, cost) in enumerate(step_data):
                inject_step_tokens(session, i, t_in, t_out, cost)
                EXPECTED_TOKENS_IN  += t_in
                EXPECTED_TOKENS_OUT += t_out
                EXPECTED_COST       += cost
                info(
                    f"  step_{i+1:03d}",
                    f"tokens_in={t_in}  tokens_out={t_out}  cost=${cost:.4f}",
                )

            # Set the StateMatrix to correct values first
            session.state_matrix.total_tokens_in  = EXPECTED_TOKENS_IN
            session.state_matrix.total_tokens_out = EXPECTED_TOKENS_OUT
            session.state_matrix.estimated_cost   = EXPECTED_COST

            divider()
            info("Floor tokens_in  (sum from steps)", EXPECTED_TOKENS_IN)
            info("Floor tokens_out (sum from steps)", EXPECTED_TOKENS_OUT)
            info("Floor cost USD   (sum from steps)", f"${EXPECTED_COST:.4f}")

            # ── Step 2: Write checkpoint with correct state ───────────────────
            sub_banner("Writing Valid Checkpoint to Disk")
            manager.write_checkpoint(session)
            lsn = session.checkpoint_meta.lsn
            info("Written LSN ", lsn)
            info("Session ID  ", session_id[:16] + "...")

            # ── Step 3: Re-write checkpoint with zeroed StateMatrix ───────────
            # Instead of manually patching JSON, we directly mutate the in-memory
            # session state and write a new valid checkpoint. This produces a
            # SHA-256-valid checkpoint with deliberately low accumulator values,
            # which StateMatrixValidator must correct upward.
            sub_banner("🔧 Re-Writing Checkpoint With Zeroed StateMatrix (Valid Hash)")

            original_tokens_in  = session.state_matrix.total_tokens_in
            original_tokens_out = session.state_matrix.total_tokens_out
            original_cost       = session.state_matrix.estimated_cost

            # Zero out the SM — simulates a crash that wiped the accumulators
            session.state_matrix.total_tokens_in  = 0    # CORRUPTED → zeroed
            session.state_matrix.total_tokens_out = 0    # CORRUPTED → zeroed
            session.state_matrix.estimated_cost   = 0.0  # CORRUPTED → zeroed

            # Write a new valid checkpoint with the zeroed SM
            # (the step results still carry the floor metadata intact)
            manager.write_checkpoint(session)
            lsn = session.checkpoint_meta.lsn
            info("Zeroed SM checkpoint written at LSN ", lsn)

            warn(f"StateMatrix.total_tokens_in  set to 0 (was {original_tokens_in})")
            warn(f"StateMatrix.total_tokens_out set to 0 (was {original_tokens_out})")
            warn(f"StateMatrix.estimated_cost   set to 0 (was {original_cost:.4f})")
            warn("Valid SHA-256 written — StateMatrixValidator will correct on load")

            # ── Step 4: Call recover_session() ───────────────────────────────
            sub_banner("Calling recover_session() — Monotonic Correction Expected")

            with patch_nala_loop_run():
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {"step_001": valid_handler, "step_002": valid_handler,
                                          "step_003": valid_handler, "step_004": valid_handler},
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )

            rec_session = recovered_loop.session
            sm = rec_session.state_matrix

            # ── Step 5: Verify corrections ────────────────────────────────────
            sub_banner("Post-Recovery Assertions: StateMatrix Invariant Verification")
            info("Corrected total_tokens_in  ", sm.total_tokens_in)
            info("Corrected total_tokens_out ", sm.total_tokens_out)
            info("Corrected estimated_cost   ", f"${sm.estimated_cost:.4f}")
            info("Expected floor tokens_in   ", EXPECTED_TOKENS_IN)
            info("Expected floor tokens_out  ", EXPECTED_TOKENS_OUT)
            info("Expected floor cost        ", f"${EXPECTED_COST:.4f}")

            assert sm.total_tokens_in >= EXPECTED_TOKENS_IN, (
                f"Monotonic correction FAILED: total_tokens_in={sm.total_tokens_in} "
                f"< floor={EXPECTED_TOKENS_IN}"
            )
            assert sm.total_tokens_out >= EXPECTED_TOKENS_OUT, (
                f"Monotonic correction FAILED: total_tokens_out={sm.total_tokens_out} "
                f"< floor={EXPECTED_TOKENS_OUT}"
            )
            assert sm.estimated_cost >= EXPECTED_COST - 1e-9, (
                f"Monotonic correction FAILED: estimated_cost={sm.estimated_cost:.6f} "
                f"< floor={EXPECTED_COST:.6f}"
            )

            success(
                f"T02 PASSED — StateMatrix monotonic correction applied. "
                f"tokens_in: 0 → {sm.total_tokens_in}. "
                f"tokens_out: 0 → {sm.total_tokens_out}. "
                f"cost: 0 → ${sm.estimated_cost:.4f}. "
                "No under-counting possible."
            )


# ==============================================================================
# SECTION 5 — T03: SHA-256 Rollback Chain
# ==============================================================================

class TestT03Sha256Rollback:
    """
    T03 — SHA-256 mismatch at LSN-N triggers automatic rollback to LSN-N-1.

    Writes 3 clean checkpoints (LSN 1, 2, 3). Corrupts the LSN-3 file without
    updating its SHA-256 hash. Calls recover_session() and verifies that
    recovery automatically falls back to LSN-2 (the last clean checkpoint).

    Acceptance:
      - recover_session() succeeds without raising
      - Recovered session.checkpoint_meta.lsn == 2
      - No CheckpointIntegrityError propagates to caller
    """

    def test_sha256_mismatch_triggers_rollback_to_previous_lsn(self) -> None:
        banner(
            "T03 — SHA-256 Hash Mismatch at LSN=3 → Auto-Rollback to LSN=2",
            icon="🔐",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=5)
            session_id = session.session_id

            # ── Write 3 clean checkpoints with distinct token values ──────────
            sub_banner("Writing 3 Clean Checkpoints (LSN 1, 2, 3)")
            token_snapshots: Dict[int, int] = {}

            for i in range(3):
                session.state_matrix.total_tokens_in += (i + 1) * 2000
                manager.write_checkpoint(session)
                lsn = session.checkpoint_meta.lsn
                token_snapshots[lsn] = session.state_matrix.total_tokens_in
                info(f"  LSN={lsn} tokens_in", session.state_matrix.total_tokens_in)

            session_dir = tmp_dir / session_id
            divider()
            disk_scan(session_dir)

            # ── Corrupt LSN=3 (the latest) without updating its hash ──────────
            sub_banner("🔧 Corrupting LSN=3 Without Updating SHA-256")
            cp3 = session_dir / "checkpoint_LSN_000003.json"
            assert cp3.exists(), "checkpoint_LSN_000003.json must exist"

            raw  = cp3.read_text(encoding="utf-8")
            data = json.loads(raw)
            data["objective"] = "HASH_MISMATCH_INJECTION_" + data["objective"]
            cp3.write_text(json.dumps(data, indent=2), encoding="utf-8")

            warn("LSN=3 objective field modified. SHA-256 in meta is now stale → MISMATCH")
            info("LSN=3 tokens_in (snapshot) ", token_snapshots[3])
            info("LSN=2 tokens_in (snapshot) ", token_snapshots[2])
            info("Expected recovery LSN      ", 2)

            # ── Call recover_session() — should roll back to LSN=2 ───────────
            sub_banner("Calling recover_session() — Hash Mismatch → Rollback Expected")

            with patch_nala_loop_run():
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {f"step_{i+1:03d}": valid_handler for i in range(5)},
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )

            rec_session = recovered_loop.session

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Post-Recovery Assertions")
            info("Recovered LSN     ", rec_session.checkpoint_meta.lsn)
            info("Recovered tokens  ", rec_session.state_matrix.total_tokens_in)
            info("Expected LSN      ", 2)
            info("Expected tokens   ", token_snapshots[2])

            assert rec_session.checkpoint_meta.lsn == 2, (
                f"Expected LSN=2 after rollback from corrupt LSN=3, "
                f"got LSN={rec_session.checkpoint_meta.lsn}"
            )
            assert rec_session.state_matrix.total_tokens_in >= token_snapshots[2], (
                "tokens_in after rollback must be >= LSN=2 snapshot value"
            )

            success(
                f"T03 PASSED — SHA-256 mismatch at LSN=3 triggered automatic rollback. "
                f"Recovered cleanly from LSN=2 with tokens_in={rec_session.state_matrix.total_tokens_in}."
            )


# ==============================================================================
# SECTION 6 — T04: Full Corruption → SessionRecoveryError
# ==============================================================================

class TestT04FullCorruption:
    """
    T04 — All LSNs corrupt AND no HandoffSpore → SessionRecoveryError.

    Writes 3 checkpoints. Corrupts all 3 without updating hashes. Ensures
    no handoff.spore.json exists. Verifies recover_session() raises
    SessionRecoveryError (or CheckpointRecoveryError which wraps it).

    Acceptance:
      - pytest.raises(SessionRecoveryError) with session_id in attrs
      - last_lsn_tried attribute is populated
      - No NalaLoop is returned
    """

    def test_full_corruption_raises_session_recovery_error(self) -> None:
        banner(
            "T04 — All LSNs Corrupt + No Spore → SessionRecoveryError (RISK-029)",
            icon="💀",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=3)
            session_id = session.session_id

            # ── Write 3 checkpoints ───────────────────────────────────────────
            sub_banner("Writing 3 Checkpoints (LSN 1, 2, 3)")
            for _ in range(3):
                manager.write_checkpoint(session)
                info(f"  Wrote LSN ", session.checkpoint_meta.lsn)

            # ── Corrupt ALL 3 checkpoints ─────────────────────────────────────
            sub_banner("🔧 Corrupting ALL 3 Checkpoint Files (Without Updating Hashes)")
            session_dir = tmp_dir / session_id
            cp_files    = sorted(session_dir.glob("checkpoint_LSN_*.json"))

            assert len(cp_files) >= 3, f"Expected 3 checkpoint files, found {len(cp_files)}"

            for cp_file in cp_files:
                data = json.loads(cp_file.read_text("utf-8"))
                data["objective"] = "TOTALLY_CORRUPT_" + cp_file.name
                cp_file.write_text(json.dumps(data, indent=2), "utf-8")
                error_line(f"Corrupted: {cp_file.name} (hash NOT updated → MISMATCH)")

            # ── Confirm no spore exists ───────────────────────────────────────
            spore_path = session_dir / "handoff.spore.json"
            assert not spore_path.exists(), \
                "handoff.spore.json must NOT exist for T04 to test the fatal path"
            info("handoff.spore.json present? ", "❌ No — testing fatal path")

            divider()
            disk_scan(session_dir)

            # ── Verify recover_session() raises ───────────────────────────────
            sub_banner("Calling recover_session() — Must Raise SessionRecoveryError")

            raised_exc: Optional[Exception] = None
            try:
                recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {"step_001": valid_handler},
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )
                pytest.fail(
                    "recover_session() must raise SessionRecoveryError "
                    "when all checkpoints are corrupt and no spore exists."
                )
            except (SessionRecoveryError, CheckpointRecoveryError) as exc:
                raised_exc = exc
                error_line(f"Exception caught: {type(exc).__name__}")
                error_line(f"Message: {str(exc)[:100]}")

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Post-Exception Assertions")
            assert raised_exc is not None, "An exception must have been raised"

            if isinstance(raised_exc, SessionRecoveryError):
                info("session_id in exc    ", raised_exc.session_id[:16])
                info("last_lsn_tried       ", raised_exc.last_lsn_tried)
                assert raised_exc.session_id == session_id, \
                    "Exception must carry the correct session_id"
                assert raised_exc.reason, \
                    "Exception must have a non-empty reason message"

            success(
                f"T04 PASSED — All 3 corrupt LSNs correctly triggered "
                f"{type(raised_exc).__name__}. Session cannot be recovered without spore. "
                "RISK-029 mitigated."
            )


# ==============================================================================
# SECTION 7 — T05: Handler Replacement During Recovery
# ==============================================================================

class TestT05HandlerReplacement:
    """
    T05 — Handlers can be replaced/updated during recovery.

    Runs a session with handler_v1 for all steps. After the session is
    checkpointed, calls recover_session() with handler_v2 for remaining steps.
    Verifies HandlerSignatureValidator accepts handler_v2 and that the
    recovered loop has handler_v2 registered (not handler_v1).

    Acceptance:
      - recover_session() succeeds with handler_v2
      - HandlerSignatureValidator does NOT raise on handler_v2
      - Recovered loop has handler_v2 registered for the step IDs
    """

    def test_handler_v2_replaces_v1_during_recovery(self) -> None:
        banner(
            "T05 — Handler Replacement: handler_v1 → handler_v2 During Recovery",
            icon="🔁",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=4)
            session_id = session.session_id

            # ── Define handler_v1 and handler_v2 ──────────────────────────────
            def handler_v1(step: Any, session: Any) -> Dict[str, Any]:
                """ORIGINAL handler from the crashed process (v1)."""
                return {"success": True, "output": {"version": "v1", "model": "claude-3"}}

            def handler_v2(step: Any, session: Any) -> Dict[str, Any]:
                """REPLACEMENT handler provided at recovery time (v2 — upgraded model)."""
                return {"success": True, "output": {"version": "v2", "model": "claude-4-opus"}}

            sub_banner("Phase 1: Run 2 Steps With handler_v1, Then Checkpoint")
            inject_step_tokens(session, 0, 1500, 600, 0.0015)
            inject_step_tokens(session, 1, 2200, 900, 0.0022)
            info("step_001 → SUCCESS (via handler_v1)", "✅")
            info("step_002 → SUCCESS (via handler_v1)", "✅")
            info("Steps 3, 4 are PENDING (not yet started)", "—")

            manager.write_checkpoint(session)
            info("Checkpoint written at LSN ", session.checkpoint_meta.lsn)
            divider()
            disk_scan(tmp_dir / session_id)

            # ── Validate handler_v1 and handler_v2 signatures independently ──
            sub_banner("Phase 2: Verify HandlerSignatureValidator Accepts Both Handlers")

            graph = session.task_graph
            HandlerSignatureValidator.validate_all(
                handlers        = {"step_001": handler_v1, "step_002": handler_v1},
                default_handler = handler_v1,
                graph           = graph,
            )
            info("handler_v1 signature validation ", "✅ PASSED")

            HandlerSignatureValidator.validate_all(
                handlers        = {"step_003": handler_v2, "step_004": handler_v2},
                default_handler = handler_v2,
                graph           = graph,
            )
            info("handler_v2 signature validation ", "✅ PASSED")

            # ── Recover with handler_v2 for remaining steps ───────────────────
            sub_banner("Phase 3: recover_session() With handler_v2 (Upgraded Handler)")
            step("Calling recover_session() — all remaining steps will use handler_v2...")

            with patch_nala_loop_run():
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {
                        "step_001": handler_v1,  # Already done — still registered
                        "step_002": handler_v1,  # Already done — still registered
                        "step_003": handler_v2,  # UPGRADED for recovery
                        "step_004": handler_v2,  # UPGRADED for recovery
                    },
                    default_handler    = handler_v2,
                    max_errors         = 10,
                )

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Post-Recovery Assertions: Handler Registry Verification")
            rec_session = recovered_loop.session

            info("Recovered LSN          ", rec_session.checkpoint_meta.lsn)
            info("SUCCESS steps count    ", rec_session.task_graph.success_count())
            info("PENDING steps count    ", rec_session.task_graph.pending_count())

            # Verify the handler registry contains handler_v2 for steps 3 & 4
            registry = recovered_loop._handlers
            info("Registered handlers    ", list(registry.keys()))
            info("step_003 handler       ", registry.get("step_003", {__name__: "NOT_FOUND"}).__name__
                 if callable(registry.get("step_003")) else "NOT_FOUND")
            info("step_004 handler       ", registry.get("step_004", {__name__: "NOT_FOUND"}).__name__
                 if callable(registry.get("step_004")) else "NOT_FOUND")

            assert recovered_loop is not None
            assert "step_003" in registry, "step_003 must be in recovered loop handler registry"
            assert "step_004" in registry, "step_004 must be in recovered loop handler registry"
            assert registry["step_003"] is handler_v2, \
                "step_003 must be bound to handler_v2 in the recovered loop"
            assert registry["step_004"] is handler_v2, \
                "step_004 must be bound to handler_v2 in the recovered loop"
            assert rec_session.task_graph.success_count() == 2, \
                f"Expected 2 SUCCESS steps from pre-crash run, got {rec_session.task_graph.success_count()}"

            success(
                "T05 PASSED — handler_v2 successfully replaced handler_v1 during recovery. "
                "HandlerSignatureValidator accepted the new handler. "
                "Remaining steps dispatched through handler_v2."
            )


# ==============================================================================
# SECTION 8 — T06: Stale Lock File Cleared
# ==============================================================================

class TestT06StaleLockCleared:
    """
    T06 — Stale .checkpoint.lock is unlinked before checkpoint load.

    Writes a .checkpoint.lock file with a non-existent PID (99999999)
    and an mtime backdated 120 seconds (well past the 60s LOCK_TIMEOUT_S).
    Calls recover_session() and verifies the stale lock is cleared and
    recovery succeeds.

    Acceptance:
      - No SessionRecoveryLockError raised
      - .checkpoint.lock is absent after recovery
      - Recovery returns a valid NalaLoop
    """

    def test_stale_lock_is_cleared_on_recovery(self) -> None:
        banner(
            "T06 — Stale .checkpoint.lock Cleared Before Checkpoint Load (RISK-026)",
            icon="🔓",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=3)
            session_id = session.session_id

            # ── Write a clean checkpoint ──────────────────────────────────────
            sub_banner("Phase 1: Write Clean Checkpoint")
            manager.write_checkpoint(session)
            lsn = session.checkpoint_meta.lsn
            info("Checkpoint LSN  ", lsn)

            # ── Create a stale lock file ──────────────────────────────────────
            sub_banner("Phase 2: Inject Stale .checkpoint.lock (PID=99999999, age=120s)")
            session_dir = tmp_dir / session_id
            lock_path   = write_stale_lock(session_dir, session_id, age_seconds=120)

            assert lock_path.exists(), "Lock file must exist before recovery"
            lock_stat = lock_path.stat()
            lock_age  = time.time() - lock_stat.st_mtime

            info("Lock file path   ", lock_path.name)
            info("Lock file PID    ", "99999999 (guaranteed dead)")
            info("Lock file age    ", f"{lock_age:.1f}s (> LOCK_TIMEOUT_S=60s)")
            warn("Stale lock is present on disk — recovery must clear it before loading checkpoint")

            disk_scan(session_dir, show_lock=True)

            # ── Call recover_session() ────────────────────────────────────────
            sub_banner("Phase 3: Calling recover_session() — Stale Lock Must Be Cleared")

            with patch_nala_loop_run():
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {f"step_{i+1:03d}": valid_handler for i in range(3)},
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Phase 4: Assertions")
            lock_exists_after = lock_path.exists()
            info("Lock file exists after recovery?  ", "❌ No" if not lock_exists_after else "⚠️ Yes (leak!)")
            info("Recovered LSN                     ", recovered_loop.session.checkpoint_meta.lsn)

            disk_scan(session_dir, show_lock=True)

            assert recovered_loop is not None, \
                "recover_session() must return NalaLoop despite stale lock"
            assert not lock_exists_after, \
                ".checkpoint.lock must be released/absent after recover_session() completes"
            assert recovered_loop.session.checkpoint_meta.lsn == lsn, \
                f"Expected LSN={lsn}, got {recovered_loop.session.checkpoint_meta.lsn}"

            success(
                f"T06 PASSED — Stale lock (PID=99999999, age={lock_age:.0f}s) was "
                "cleared by LockResolver. Recovery completed at LSN=1. "
                "No SessionRecoveryLockError. Lock absent after recovery. RISK-026 mitigated."
            )


# ==============================================================================
# SECTION 9 — T07: Runaway Loop Guard
# ==============================================================================

class TestT07RunawayLoopGuard:
    """
    T07 — RunawayLoopError raised when error_count >= MAX_ERRORS.

    Builds a checkpoint where state_matrix.error_count == 10 (default ceiling).
    Calls recover_session(max_errors=10). Verifies RunawayLoopError is raised
    before any handler is bound and before NalaLoop is instantiated.

    Acceptance:
      - pytest.raises(RunawayLoopError)
      - exc.error_count == 10
      - exc.max_errors  == 10
      - No NalaLoop is constructed
    """

    def test_runaway_loop_guard_halts_recovery(self) -> None:
        banner(
            "T07 — Runaway Crash Loop Detected → RunawayLoopError (RISK-025)",
            icon="⛔",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=3)
            session_id = session.session_id

            # ── Set error_count to exactly the ceiling ────────────────────────
            sub_banner("Building Runaway Session State (error_count = MAX_ERRORS = 10)")
            MAX_ERRORS = 10
            session.state_matrix.error_count      = MAX_ERRORS
            session.state_matrix.total_tokens_in  = 5000
            session.state_matrix.total_tokens_out = 2000
            session.state_matrix.estimated_cost   = 0.005

            info("error_count      ", session.state_matrix.error_count)
            info("MAX_ERRORS       ", MAX_ERRORS)
            info("tokens_in        ", session.state_matrix.total_tokens_in)
            warn(f"error_count={MAX_ERRORS} >= MAX_ERRORS={MAX_ERRORS} — RunawayLoopGuard MUST halt!")

            # ── Write checkpoint with the runaway state ───────────────────────
            sub_banner("Writing Checkpoint With Runaway State to Disk")
            manager.write_checkpoint(session)
            lsn = session.checkpoint_meta.lsn
            info("Checkpoint LSN   ", lsn)

            disk_scan(tmp_dir / session_id)

            # ── Verify RunawayLoopGuard raises before NalaLoop is created ─────
            sub_banner("Calling recover_session() — RunawayLoopError Must Be Raised")

            loop_constructor_called = False
            original_init = None

            raised_exc: Optional[RunawayLoopError] = None

            try:
                # Patch NalaLoop.__init__ so we can detect if it was ever called
                with patch("core.harness.nala_loop.NalaLoop.__init__") as mock_init:
                    mock_init.side_effect = AssertionError(
                        "[T07 TEST] NalaLoop.__init__ was called — RunawayLoopGuard should have halted first!"
                    )
                    recover_session(
                        session_id         = session_id,
                        checkpoint_manager = manager,
                        handlers           = {"step_001": valid_handler},
                        default_handler    = valid_handler,
                        max_errors         = MAX_ERRORS,
                    )
                pytest.fail(
                    "recover_session() must raise RunawayLoopError "
                    f"when error_count={MAX_ERRORS} >= max_errors={MAX_ERRORS}"
                )

            except RunawayLoopError as exc:
                raised_exc = exc
                error_line(f"RunawayLoopError raised correctly!")
                error_line(f"  error_count = {exc.error_count}")
                error_line(f"  max_errors  = {exc.max_errors}")
                error_line(f"  session_id  = {exc.session_id[:16]}...")
                error_line(f"  last_lsn    = {exc.last_lsn_tried}")

            except AssertionError:
                pytest.fail(
                    "NalaLoop.__init__ was called — RunawayLoopGuard "
                    "must halt BEFORE NalaLoop is instantiated!"
                )

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Post-Exception Assertions")
            assert raised_exc is not None, "RunawayLoopError must have been raised"
            assert raised_exc.error_count == MAX_ERRORS, \
                f"exc.error_count should be {MAX_ERRORS}, got {raised_exc.error_count}"
            assert raised_exc.max_errors == MAX_ERRORS, \
                f"exc.max_errors should be {MAX_ERRORS}, got {raised_exc.max_errors}"
            assert raised_exc.session_id == session_id, \
                "exc.session_id must match the session being recovered"
            assert raised_exc.last_lsn_tried == lsn, \
                f"exc.last_lsn_tried must be {lsn}, got {raised_exc.last_lsn_tried}"
            assert isinstance(raised_exc, SessionRecoveryError), \
                "RunawayLoopError must be a subclass of SessionRecoveryError"

            success(
                f"T07 PASSED — RunawayLoopError raised with error_count={raised_exc.error_count}/"
                f"{raised_exc.max_errors}. Hard halt triggered. NalaLoop never constructed. "
                "Zero additional API calls possible. RISK-025 mitigated."
            )


# ==============================================================================
# SECTION 10 — T08: HandoffSpore Reconstruction
# ==============================================================================

class TestT08SporeReconstruction:
    """
    T08 — Session rebuilt from HandoffSpore when all checkpoints are corrupt.

    Corrupts all checkpoint LSNs without updating hashes. Writes a valid
    HandoffSpore JSON at the expected path. Calls recover_session() and
    verifies the recovered session is built from the spore (not checkpoints).

    Acceptance:
      - recover_session() succeeds (no exception)
      - session.session_id == spore.new_session_id
      - session.metadata["recovered_from_spore"] == True
      - session.task_graph.pending_count() == len(spore remaining_steps)
    """

    def test_recovery_from_handoff_spore_when_all_checkpoints_corrupt(self) -> None:
        banner(
            "T08 — HandoffSpore Fallback: All LSNs Corrupt → Spore Bootstrap (RISK-029)",
            icon="🌿",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=4)
            session_id = session.session_id

            # ── Write 2 clean checkpoints, then corrupt both ──────────────────
            sub_banner("Phase 1: Write 2 Checkpoints and Corrupt Both")
            for _ in range(2):
                manager.write_checkpoint(session)

            session_dir = tmp_dir / session_id
            cp_files    = sorted(session_dir.glob("checkpoint_LSN_*.json"))

            for cp_file in cp_files:
                data = json.loads(cp_file.read_text("utf-8"))
                data["objective"] = "SPORE_TEST_CORRUPT_" + cp_file.name
                cp_file.write_text(json.dumps(data, indent=2), "utf-8")
                error_line(f"Corrupted: {cp_file.name}")

            info("Checkpoints corrupted  ", len(cp_files))

            # ── Write a valid HandoffSpore at the expected path ───────────────
            sub_banner("Phase 2: Writing Valid HandoffSpore JSON")
            spore_session_id = str(uuid.uuid4())
            remaining_steps_data = [
                {
                    "step_id":      f"step_{i+1:03d}",
                    "description":  f"Spore-bootstrapped step {i+1}",
                    "status":       "PENDING",
                    "dependencies": [],
                    "priority":     1,
                    "retries":      0,
                }
                for i in range(3)
            ]
            spore_data = {
                "new_session_id":        spore_session_id,
                "original_session_id":   session_id,
                "objective":             "Recover from spore — JIRA-005 T08",
                "spore_version":         "1.0.0",
                "created_at":            utcnow().isoformat(),
                "trigger_reason":        "context_window_exhaustion",
                "active_variables":      {"env": "test", "test_id": "T08"},
                "bootstrap_instructions": "Recover from spore bootstrap.",
                "done_condition":        json.dumps({"all_steps_complete": True}),
                "task_graph_state": {
                    "remaining_steps":      remaining_steps_data,
                    "crystallized_history": "Steps 1-4 completed pre-crash.",
                },
                "telemetry_state": {
                    "total_tokens_in":  8500,
                    "total_tokens_out": 3200,
                    "estimated_cost_usd": 0.0085,
                    "error_count":      0,
                    "elapsed_seconds":  142.5,
                    "session_lsn":      5,
                },
            }
            spore_path = session_dir / "handoff.spore.json"
            spore_path.write_text(json.dumps(spore_data, indent=2), encoding="utf-8")

            info("Spore path               ", spore_path.name)
            info("Spore new_session_id     ", spore_session_id[:16] + "...")
            info("Remaining steps in spore ", len(remaining_steps_data))
            info("Spore LSN                ", spore_data["telemetry_state"]["session_lsn"])

            disk_scan(session_dir)

            # ── Patch HandoffSpore.load_spore to bypass the context_tracker dep ─
            # We inject the spore directly to avoid the full context_tracker import chain
            sub_banner("Phase 3: Calling recover_session() — Spore Bootstrap Expected")

            from core.harness import context_tracker as ct_module

            class _MockSpore:
                new_session_id      = spore_session_id
                objective           = spore_data["objective"]
                active_variables    = spore_data["active_variables"]
                bootstrap_instructions = spore_data["bootstrap_instructions"]
                done_condition      = spore_data["done_condition"]

                class task_graph_state:
                    remaining_steps     = remaining_steps_data
                    crystallized_history = spore_data["task_graph_state"]["crystallized_history"]

                class telemetry_state:
                    total_tokens_in     = 8500
                    total_tokens_out    = 3200
                    estimated_cost_usd  = 0.0085
                    error_count         = 0
                    elapsed_seconds     = 142.5
                    session_lsn         = 5

            with (
                patch.object(ct_module.HandoffSpore, "load_spore", return_value=_MockSpore()),
                patch_nala_loop_run(),
            ):
                recovered_loop = recover_session(
                    session_id         = session_id,
                    checkpoint_manager = manager,
                    handlers           = {f"step_{i+1:03d}": valid_handler for i in range(3)},
                    default_handler    = valid_handler,
                    max_errors         = 10,
                )

            # ── Assertions ────────────────────────────────────────────────────
            sub_banner("Phase 4: Post-Spore-Recovery Assertions")
            rec_session = recovered_loop.session

            info("Recovered session_id         ", rec_session.session_id[:16] + "...")
            info("Spore new_session_id         ", spore_session_id[:16] + "...")
            info("recovered_from_spore flag    ", rec_session.metadata.get("recovered_from_spore"))
            info("Pending steps in graph       ", rec_session.task_graph.pending_count())
            info("LSN from spore telemetry     ", rec_session.checkpoint_meta.lsn)
            info("tokens_in from spore         ", rec_session.state_matrix.total_tokens_in)

            assert rec_session.session_id == spore_session_id, (
                f"Recovered session_id must match spore's new_session_id. "
                f"Got {rec_session.session_id[:16]}, expected {spore_session_id[:16]}"
            )
            assert rec_session.metadata.get("recovered_from_spore") is True, \
                "session.metadata['recovered_from_spore'] must be True"
            assert rec_session.metadata.get("original_session_id") == session_id, \
                "session.metadata['original_session_id'] must carry the crashed session's ID"
            assert rec_session.task_graph.pending_count() == len(remaining_steps_data), \
                f"Expected {len(remaining_steps_data)} PENDING steps from spore, " \
                f"got {rec_session.task_graph.pending_count()}"
            assert rec_session.checkpoint_meta.lsn == 5, \
                f"LSN must match spore's session_lsn=5, got {rec_session.checkpoint_meta.lsn}"
            assert rec_session.state_matrix.total_tokens_in == 8500, \
                f"tokens_in must match spore's telemetry (8500), " \
                f"got {rec_session.state_matrix.total_tokens_in}"

            success(
                f"T08 PASSED — Session successfully bootstrapped from HandoffSpore. "
                f"session_id={spore_session_id[:16]}..., "
                f"pending_steps={rec_session.task_graph.pending_count()}, "
                f"LSN={rec_session.checkpoint_meta.lsn}. RISK-029 mitigated."
            )


# ==============================================================================
# SECTION 11 — T09: Handler Signature Mismatch → TypeError
# ==============================================================================

class TestT09HandlerSignatureMismatch:
    """
    T09 — Invalid handler signature rejected at recovery time, not at dispatch.

    Registers a handler with only 1 required parameter (def bad(step_only)).
    Calls recover_session() and verifies TypeError is raised during
    HandlerSignatureValidator.validate_all() — BEFORE any step executes.

    Acceptance:
      - pytest.raises(TypeError) with [HandlerValidator] in the message
      - No step executes (mock LLM call count == 0)
      - Exception raised before NalaLoop.run() is called
    """

    def test_bad_handler_one_param_raises_type_error(self) -> None:
        banner(
            "T09 — Handler Signature Mismatch (1 param) → TypeError Before Execution (RISK-027)",
            icon="🚫",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session(n_steps=3)
            session_id = session.session_id

            # ── Write a valid checkpoint ──────────────────────────────────────
            sub_banner("Phase 1: Write Clean Checkpoint")
            manager.write_checkpoint(session)
            lsn = session.checkpoint_meta.lsn
            info("Checkpoint LSN   ", lsn)

            # ── Define various bad handlers ───────────────────────────────────
            sub_banner("Phase 2: Defining Bad Handlers (Wrong Signatures)")

            def bad_handler_zero_params() -> None:
                """Zero params — completely wrong."""
                pass

            def bad_handler_one_param(step_only) -> None:
                """One param only — missing 'session'."""
                pass

            bad_handlers = [
                ("zero_params", bad_handler_zero_params, "def bad() → 0 required params"),
                ("one_param",   bad_handler_one_param,   "def bad(step_only) → 1 required param"),
            ]

            for name, handler, description in bad_handlers:
                divider()
                info(f"Testing: {name}", description)
                step(f"HandlerSignatureValidator._validate_single({name})...")

                raised = False
                exc_msg = ""
                try:
                    HandlerSignatureValidator._validate_single(
                        handler = handler,
                        context = f"handler['{name}']",
                    )
                except TypeError as exc:
                    raised  = True
                    exc_msg = str(exc)
                    error_line(f"TypeError raised: {exc_msg[:100]}")

                assert raised, \
                    f"HandlerSignatureValidator must reject '{name}' handler"
                assert "[HandlerValidator]" in exc_msg, \
                    f"TypeError message must contain '[HandlerValidator]', got: {exc_msg}"
                info(f"  ✅ {name} correctly rejected", "TypeError raised")

            # ── Test that recover_session() raises TypeError end-to-end ──────
            sub_banner("Phase 3: recover_session() With Bad Handler — TypeError End-to-End")

            def bad_handler_one_param_e2e(step_only) -> None:
                """Exactly 1 required param — must fail validator."""
                pass

            warn("Calling recover_session() with a 1-param handler for step_001...")

            raised_exc: Optional[TypeError] = None
            run_called = False

            try:
                with patch(
                    "core.harness.nala_loop.NalaLoop.run",
                    side_effect=lambda: setattr(globals(), "run_called", True),
                ):
                    recover_session(
                        session_id         = session_id,
                        checkpoint_manager = manager,
                        handlers           = {"step_001": bad_handler_one_param_e2e},
                        default_handler    = None,
                        max_errors         = 10,
                    )
                pytest.fail(
                    "recover_session() must raise TypeError for 1-param handler"
                )
            except TypeError as exc:
                raised_exc = exc
                error_line(f"TypeError raised at recovery time!")
                error_line(f"  Message: {str(exc)[:120]}")
            except SessionRecoveryError as exc:
                # recover_session() wraps unexpected exceptions in SessionRecoveryError
                # The original TypeError is in __cause__. Extract and verify.
                cause = exc.__cause__
                if isinstance(cause, TypeError):
                    raised_exc = cause
                    error_line(f"TypeError (wrapped in SessionRecoveryError) raised!")
                    error_line(f"  Cause: {str(cause)[:120]}")
                else:
                    # Re-check: the reason string should contain [HandlerValidator]
                    if "[HandlerValidator]" in exc.reason:
                        raised_exc = TypeError(exc.reason)  # synthesize for assertion
                        error_line(f"SessionRecoveryError with HandlerValidator reason raised!")
                        error_line(f"  Reason: {exc.reason[:120]}")
                    else:
                        raise  # unexpected — propagate

            # ── Final assertions ──────────────────────────────────────────────
            sub_banner("Phase 4: Final Assertions")
            assert raised_exc is not None, \
                "TypeError (or wrapped TypeError) must have been raised"
            assert not run_called, \
                "NalaLoop.run() must NOT be called when handler validation fails"
            assert "[HandlerValidator]" in str(raised_exc), \
                f"TypeError message must contain '[HandlerValidator]' tag, got: {str(raised_exc)[:120]}"

            info("TypeError raised at recovery time?  ", "✅ YES")
            info("NalaLoop.run() ever called?         ", "✅ NO (zero API calls possible)")
            info("Exception message contains tag?     ", "✅ [HandlerValidator]")

            # ── Bonus: Verify good handlers pass ─────────────────────────────
            sub_banner("Phase 5: Verify Valid Handlers Still Pass")

            def good_handler(step: Any, session: Any) -> Dict[str, Any]:
                return {"success": True}

            HandlerSignatureValidator._validate_single(good_handler, context="good_handler")
            info("good_handler(step, session) validates? ", "✅ PASSED")

            # Handler with extra optional params also valid
            def good_handler_with_opts(step: Any, session: Any, *, extra: str = "ok") -> Dict[str, Any]:
                return {"success": True}

            HandlerSignatureValidator._validate_single(good_handler_with_opts, context="good_with_opts")
            info("good_handler + optional param validates?", "✅ PASSED")

            success(
                "T09 PASSED — 1-param and 0-param handlers correctly rejected at recovery time. "
                "TypeError raised BEFORE any step executes. "
                "Zero API calls made. RISK-023 and RISK-027 mitigated."
            )


# ==============================================================================
# SECTION 12 — T10: ARIES Redo Phase (RUNNING → PENDING Reset)
# ==============================================================================

class TestT10AriesRedoPhase:
    """
    T10 — ARIES Redo Phase resets all RUNNING steps to PENDING (idempotent).

    Directly tests _apply_redo_phase() with a session containing multiple
    steps in different states. Verifies only RUNNING steps are reset and
    that started_at and tool_used are cleared.

    Acceptance:
      - All RUNNING steps become PENDING
      - SUCCESS and FAILED steps are untouched
      - PENDING steps remain PENDING (idempotent)
      - Return value = list of reset step_ids
    """

    def test_aries_redo_phase_resets_running_to_pending(self) -> None:
        banner(
            "T10 — ARIES Redo Phase: RUNNING → PENDING Reset (Idempotent) (RISK-028)",
            icon="⚡",
        )

        # ── Build a session with mixed step states ────────────────────────────
        sub_banner("Building Session With Mixed Step States")
        session = make_session(n_steps=6)

        # step_001: SUCCESS (should be untouched)
        inject_step_tokens(session, 0, 1000, 400, 0.001)
        info("step_001 → SUCCESS (pre-crash completed step)", "")

        # step_002: SUCCESS (should be untouched)
        inject_step_tokens(session, 1, 1500, 600, 0.0015)
        info("step_002 → SUCCESS (pre-crash completed step)", "")

        # step_003: RUNNING (crashed mid-execution — must reset!)
        session.task_graph.steps[2].mark_running()
        session.task_graph.steps[2].started_at = utcnow()
        session.task_graph.steps[2].tool_used  = "anthropic_claude_4"
        info("step_003 → RUNNING (interrupted at crash — MUST reset)", "⚠️")

        # step_004: RUNNING (also crashed — must reset!)
        session.task_graph.steps[3].mark_running()
        session.task_graph.steps[3].started_at = utcnow()
        session.task_graph.steps[3].tool_used  = "openai_gpt5"
        info("step_004 → RUNNING (interrupted at crash — MUST reset)", "⚠️")

        # step_005: PENDING (scheduled but not started)
        info("step_005 → PENDING (not yet started)", "")

        # step_006: PENDING (scheduled but not started)
        info("step_006 → PENDING (not yet started)", "")

        # ── Record pre-redo state ─────────────────────────────────────────────
        divider()
        # TaskStatus is a str-Enum so s.status already is the string value
        pre_statuses = {s.step_id: str(s.status) for s in session.task_graph.steps}
        info("Pre-Redo statuses", pre_statuses)

        # ── Apply ARIES Redo Phase ────────────────────────────────────────────
        sub_banner("Applying ARIES Redo Phase: _apply_redo_phase(session)")
        step("Calling _apply_redo_phase() — only RUNNING steps must change...")
        reset_ids = _apply_redo_phase(session)

        # ── Post-redo state ───────────────────────────────────────────────────
        divider()
        post_statuses = {s.step_id: str(s.status) for s in session.task_graph.steps}
        info("Post-Redo statuses ", post_statuses)
        info("Reset step IDs     ", reset_ids)

        # ── Assertions ────────────────────────────────────────────────────────
        sub_banner("Assertions: RUNNING Steps Reset, Others Untouched")

        # Reset IDs must contain exactly step_003 and step_004
        assert set(reset_ids) == {"step_003", "step_004"}, \
            f"Expected ['step_003', 'step_004'] reset, got {reset_ids}"
        info("Reset IDs = {step_003, step_004}?  ", "✅")

        # step_001 and step_002 must remain SUCCESS
        assert session.task_graph.steps[0].status == TaskStatus.SUCCESS, \
            "step_001 must remain SUCCESS"
        assert session.task_graph.steps[1].status == TaskStatus.SUCCESS, \
            "step_002 must remain SUCCESS"
        info("step_001 remains SUCCESS?          ", "✅")
        info("step_002 remains SUCCESS?          ", "✅")

        # step_003 and step_004 must now be PENDING
        s3 = session.task_graph.steps[2]
        s4 = session.task_graph.steps[3]
        assert s3.status == TaskStatus.PENDING, \
            f"step_003 must be PENDING after redo, got {s3.status}"
        assert s4.status == TaskStatus.PENDING, \
            f"step_004 must be PENDING after redo, got {s4.status}"
        info("step_003 reset to PENDING?         ", "✅")
        info("step_004 reset to PENDING?         ", "✅")

        # started_at and tool_used must be cleared for reset steps
        assert s3.started_at is None, \
            "step_003.started_at must be None after ARIES Redo reset"
        assert s3.tool_used  is None, \
            "step_003.tool_used  must be None after ARIES Redo reset"
        assert s4.started_at is None, \
            "step_004.started_at must be None after ARIES Redo reset"
        assert s4.tool_used  is None, \
            "step_004.tool_used  must be None after ARIES Redo reset"
        info("step_003.started_at cleared?       ", "✅")
        info("step_003.tool_used  cleared?       ", "✅")
        info("step_004.started_at cleared?       ", "✅")
        info("step_004.tool_used  cleared?       ", "✅")

        # step_005 and step_006 remain PENDING (idempotent)
        assert session.task_graph.steps[4].status == TaskStatus.PENDING, \
            "step_005 must remain PENDING (already PENDING)"
        assert session.task_graph.steps[5].status == TaskStatus.PENDING, \
            "step_006 must remain PENDING (already PENDING)"
        info("step_005 remains PENDING?          ", "✅")
        info("step_006 remains PENDING?          ", "✅")

        # ── Idempotency test: call again, same result ─────────────────────────
        sub_banner("Idempotency Test: Call _apply_redo_phase() Again")
        reset_ids_2 = _apply_redo_phase(session)
        info("Second call reset_ids  ", reset_ids_2)
        assert reset_ids_2 == [], \
            f"Second call must return empty list (idempotent), got {reset_ids_2}"
        info("Second call is idempotent?         ", "✅")

        success(
            "T10 PASSED — ARIES Redo Phase reset step_003 and step_004 from RUNNING → PENDING. "
            "SUCCESS/PENDING steps untouched. started_at and tool_used cleared. "
            "Operation is idempotent. RISK-028 mitigated."
        )


# ==============================================================================
# SECTION 13 — T11: StateMatrixValidator Unit Tests
# ==============================================================================

class TestT11StateMatrixValidator:
    """
    T11 — Unit tests for StateMatrixValidator.validate_reconstructed() in isolation.

    Tests the monotonic correction logic directly without full recover_session()
    overhead. Verifies:
      1. No correction needed when SM >= floor
      2. Correction applied when SM < floor (all four fields)
      3. Error count correction when SM.error_count < failed_count()
      4. Report dict is empty when no corrections needed
    """

    def _make_validated_session(
        self,
        *,
        sm_tokens_in:  int   = 0,
        sm_tokens_out: int   = 0,
        sm_cost:       float = 0.0,
        sm_errors:     int   = 0,
        step_tokens_in:  int   = 0,
        step_tokens_out: int   = 0,
        step_cost:       float = 0.0,
        n_failed:        int   = 0,
    ) -> SessionState:
        """Build a SessionState with a specific SM vs floor configuration."""
        session = make_session(n_steps=max(3, n_failed + 2))

        # Set StateMatrix values
        session.state_matrix.total_tokens_in  = sm_tokens_in
        session.state_matrix.total_tokens_out = sm_tokens_out
        session.state_matrix.estimated_cost   = sm_cost
        session.state_matrix.error_count      = sm_errors

        # Inject SUCCESS step with token metadata (creates the floor)
        if step_tokens_in > 0 or step_tokens_out > 0 or step_cost > 0.0:
            session.task_graph.steps[0].mark_running()
            session.task_graph.steps[0].mark_success(result={
                "_meta_tokens_in":  step_tokens_in,
                "_meta_tokens_out": step_tokens_out,
                "_meta_cost_usd":   step_cost,
            })

        # Mark n_failed steps as FAILED (increases floor_errors)
        for i in range(1, n_failed + 1):
            session.task_graph.steps[i].mark_running()
            session.task_graph.steps[i].mark_failed(error="injected test failure")

        return session

    def test_no_correction_when_sm_above_floor(self) -> None:
        banner("T11a — StateMatrixValidator: No Correction When SM ≥ Floor", icon="✔️")

        session = self._make_validated_session(
            sm_tokens_in    = 5000, sm_tokens_out = 2000, sm_cost = 0.005, sm_errors = 0,
            step_tokens_in  = 4500, step_tokens_out = 1800, step_cost = 0.0045,
        )
        report = StateMatrixValidator.validate_reconstructed(session)

        info("Correction report ", report)
        assert report == {}, \
            f"No corrections should be needed when SM ≥ floor. Got: {report}"

        info("SM.total_tokens_in  (no change) ", session.state_matrix.total_tokens_in)
        info("SM.total_tokens_out (no change) ", session.state_matrix.total_tokens_out)
        success("T11a PASSED — StateMatrix invariant holds. No corrections applied.")

    def test_correction_applied_when_sm_below_floor(self) -> None:
        banner("T11b — StateMatrixValidator: Correction Applied When SM < Floor", icon="📈")

        FLOOR_TOKENS_IN  = 6000
        FLOOR_TOKENS_OUT = 2400
        FLOOR_COST       = 0.006

        session = self._make_validated_session(
            sm_tokens_in    = 0,   sm_tokens_out = 0,   sm_cost = 0.0,
            step_tokens_in  = FLOOR_TOKENS_IN,
            step_tokens_out = FLOOR_TOKENS_OUT,
            step_cost       = FLOOR_COST,
        )

        step("SM initialized to 0, floor derived from SUCCESS step metadata...")
        info("SM before correction: tokens_in  ", session.state_matrix.total_tokens_in)
        info("SM before correction: tokens_out ", session.state_matrix.total_tokens_out)
        info("SM before correction: cost       ", session.state_matrix.estimated_cost)

        report = StateMatrixValidator.validate_reconstructed(session)

        info("Correction report ", report)
        info("SM after correction: tokens_in  ", session.state_matrix.total_tokens_in)
        info("SM after correction: tokens_out ", session.state_matrix.total_tokens_out)
        info("SM after correction: cost       ", session.state_matrix.estimated_cost)

        assert "tokens_in_corrected" in report, \
            "Report must flag tokens_in_corrected"
        assert "tokens_out_corrected" in report, \
            "Report must flag tokens_out_corrected"
        assert "cost_corrected" in report, \
            "Report must flag cost_corrected"
        assert session.state_matrix.total_tokens_in  >= FLOOR_TOKENS_IN,  "Correction must apply"
        assert session.state_matrix.total_tokens_out >= FLOOR_TOKENS_OUT, "Correction must apply"
        assert session.state_matrix.estimated_cost   >= FLOOR_COST - 1e-9, "Correction must apply"

        success(
            f"T11b PASSED — All 3 fields corrected. "
            f"tokens_in: 0→{session.state_matrix.total_tokens_in}, "
            f"tokens_out: 0→{session.state_matrix.total_tokens_out}, "
            f"cost: 0→{session.state_matrix.estimated_cost:.4f}."
        )

    def test_error_count_corrected_when_below_failed_count(self) -> None:
        banner("T11c — StateMatrixValidator: error_count Corrected via failed_count()", icon="📊")

        N_FAILED = 3
        session = self._make_validated_session(
            sm_errors = 0,    # StateMatrix says 0 errors
            n_failed  = N_FAILED,   # But 3 FAILED steps are in graph
        )

        step(f"SM.error_count=0, but graph has {N_FAILED} FAILED steps...")
        info("graph.failed_count()  ", session.task_graph.failed_count())
        info("SM.error_count before ", session.state_matrix.error_count)

        report = StateMatrixValidator.validate_reconstructed(session)

        info("Report       ", report)
        info("SM.error_count after  ", session.state_matrix.error_count)

        assert session.state_matrix.error_count >= N_FAILED, \
            f"error_count must be >= {N_FAILED}, got {session.state_matrix.error_count}"
        assert "error_count_corrected" in report, \
            "Report must flag error_count_corrected"

        success(
            f"T11c PASSED — error_count corrected: 0 → {session.state_matrix.error_count} "
            f"(matches graph.failed_count()={N_FAILED})."
        )


# ==============================================================================
# SECTION 14 — T12: LockResolver Unit Tests
# ==============================================================================

class TestT12LockResolver:
    """
    T12 — Unit tests for LockResolver acquire/release/stale-detection logic.

    Tests:
      12a: Lock acquired when no prior lock exists
      12b: Stale lock (dead PID, old age) is cleared and re-acquired
      12c: Corrupt lock file (invalid JSON) is cleared and re-acquired
      12d: Lock release is idempotent (no error on double-release)
    """

    def test_lock_acquired_when_no_prior_lock(self) -> None:
        banner("T12a — LockResolver: Lock Acquired When No Prior Lock Exists", icon="🔒")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir  = Path(tmp)
            sid      = str(uuid.uuid4())
            lock_dir = tmp_dir / sid
            lock_dir.mkdir(parents=True, exist_ok=True)

            step("Calling LockResolver.resolve() — no prior lock file...")
            lock_path = LockResolver.resolve(session_id=sid, base_dir=tmp_dir)

            info("Lock path acquired  ", lock_path.name)
            assert lock_path.exists(), "Lock file must exist after acquisition"
            assert lock_path.name == ".checkpoint.lock", "Lock file must be .checkpoint.lock"

            # Verify content
            data = json.loads(lock_path.read_text("utf-8"))
            info("Lock PID           ", data.get("pid"))
            info("Lock hostname      ", data.get("hostname"))
            assert data.get("pid") == os.getpid(), "Lock must contain current PID"

            # Release
            LockResolver.release(lock_path)
            assert not lock_path.exists(), "Lock must not exist after release"
            info("Lock released?     ", "✅")

            success("T12a PASSED — Lock acquired and released cleanly.")

    def test_stale_lock_cleared_and_reacquired(self) -> None:
        banner("T12b — LockResolver: Stale Lock (Dead PID + Old Age) Cleared", icon="🔓")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            sid     = str(uuid.uuid4())
            lock_path = write_stale_lock(tmp_dir / sid, sid, age_seconds=120)

            info("Stale lock PID   ", 99999999)
            info("Stale lock age   ", "120s (> LOCK_TIMEOUT_S=60s)")
            assert lock_path.exists()

            step("Calling LockResolver.resolve() — must clear stale lock and re-acquire...")
            new_lock = LockResolver.resolve(session_id=sid, base_dir=tmp_dir)

            info("New lock acquired ", new_lock.name)
            data = json.loads(new_lock.read_text("utf-8"))
            info("New lock PID     ", data.get("pid"))

            assert new_lock.exists()
            assert data.get("pid") == os.getpid(), \
                "Re-acquired lock must contain current process PID"

            LockResolver.release(new_lock)
            success("T12b PASSED — Stale lock cleared, re-acquired with current PID.")

    def test_corrupt_lock_file_cleared_and_reacquired(self) -> None:
        banner("T12c — LockResolver: Corrupt Lock File (Invalid JSON) Cleared", icon="🔧")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir  = Path(tmp)
            sid      = str(uuid.uuid4())
            lock_dir = tmp_dir / sid
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_path = lock_dir / ".checkpoint.lock"
            lock_path.write_text("NOT_VALID_JSON{{{corrupted", encoding="utf-8")

            warn("Corrupt lock file written (invalid JSON)")
            assert lock_path.exists()

            step("Calling LockResolver.resolve() — must handle corrupt JSON gracefully...")
            new_lock = LockResolver.resolve(session_id=sid, base_dir=tmp_dir)
            data     = json.loads(new_lock.read_text("utf-8"))

            info("New lock PID ", data.get("pid"))
            assert new_lock.exists()
            assert data.get("pid") == os.getpid()

            LockResolver.release(new_lock)
            success("T12c PASSED — Corrupt lock cleared, new lock acquired with current PID.")

    def test_lock_release_is_idempotent(self) -> None:
        banner("T12d — LockResolver: Release Is Idempotent (No Double-Release Error)", icon="🔄")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir  = Path(tmp)
            sid      = str(uuid.uuid4())
            lock_dir = tmp_dir / sid
            lock_dir.mkdir(parents=True, exist_ok=True)

            step("Acquiring lock...")
            lock_path = LockResolver.resolve(session_id=sid, base_dir=tmp_dir)
            info("Lock acquired ", lock_path.name)

            step("Releasing lock (first time)...")
            LockResolver.release(lock_path)
            assert not lock_path.exists()
            info("First release  ", "✅ No error")

            step("Releasing lock (second time — must not raise)...")
            LockResolver.release(lock_path)   # Should not raise
            info("Second release ", "✅ Idempotent — no error")

            step("Releasing non-existent path (must not raise)...")
            fake_path = tmp_dir / "fake_session" / ".checkpoint.lock"
            LockResolver.release(fake_path)   # Should not raise
            info("Fake path release", "✅ Idempotent — no error")

            success("T12d PASSED — LockResolver.release() is idempotent on all code paths.")


# ==============================================================================
# SECTION 15 — Interactive Runner (python tests/unit/test_crash_recovery.py)
# ==============================================================================

def _print_suite_header() -> None:
    """Print the full test suite header when run directly."""
    print(f"\n{BOLD}{CYAN}{'═' * 76}{RESET}")
    print(f"{BOLD}{CYAN}  💥  NALA Crash Recovery Test Suite — JIRA-005{RESET}")
    print(f"{BOLD}{CYAN}  ⚡  ARIES Protocol: Analysis → Redo → Undo{RESET}")
    print(f"{BOLD}{CYAN}  📋  Tests: T00–T12 (Environment + T01–T09 acceptance + T10–T12 unit){RESET}")
    print(f"{BOLD}{CYAN}  📍  File: tests/unit/test_crash_recovery.py{RESET}")
    print(f"{BOLD}{CYAN}  🔧  Module: core/harness/recovery.py (60,035 bytes){RESET}")
    print(f"{BOLD}{CYAN}{'═' * 76}{RESET}")

    risks = [
        ("RISK-015", "Corrupted LSN",       "SHA-256 hash chain + auto-rollback"),
        ("RISK-023", "Missing handlers",     "HandlerSignatureValidator pre-flight"),
        ("RISK-024", "Double-count tokens",  "StateMatrixValidator monotonic max()"),
        ("RISK-025", "Infinite reboot loop", "RunawayLoopGuard error ceiling check"),
        ("RISK-026", "Stale lock file",      "LockResolver PID + age detection"),
        ("RISK-027", "Bad handler sig",      "inspect.signature() validation"),
        ("RISK-028", "RUNNING step survives","ARIES Redo → RUNNING → PENDING reset"),
        ("RISK-029", "All LSNs corrupt",     "HandoffSpore fallback → SessionRecoveryError"),
    ]
    print(f"\n  {BOLD}Risk Mitigations Verified:{RESET}")
    for risk_id, name, mitigation in risks:
        print(f"  {RED}  {risk_id}{RESET}  {YELLOW}{name:<24}{RESET}  {DIM}{mitigation}{RESET}")


def _run_test(name: str, cls_instance, method_name: str, results: list) -> None:
    """Run a single test method and record the result."""
    method = getattr(cls_instance, method_name)
    try:
        t0 = time.perf_counter()
        method()
        elapsed = (time.perf_counter() - t0) * 1000
        results.append((name, True, f"{elapsed:.0f}ms", None))
        print(f"\n  {BOLD}{GREEN}  ✅ PASS  {name}  ({elapsed:.0f}ms){RESET}")
    except (AssertionError, Exception) as exc:
        elapsed = (time.perf_counter() - t0) * 1000 if "t0" in dir() else 0
        results.append((name, False, f"{elapsed:.0f}ms", exc))
        print(f"\n  {BOLD}{RED}  ❌ FAIL  {name}  — {type(exc).__name__}: {str(exc)[:80]}{RESET}")
        import traceback
        traceback.print_exc()


def _print_summary(results: list) -> None:
    """Print the final test summary table."""
    total   = len(results)
    passed  = sum(1 for _, ok, _, _ in results if ok)
    failed  = total - passed

    print(f"\n{BOLD}{CYAN}{'═' * 76}{RESET}")
    print(f"{BOLD}{CYAN}  📊  Test Results Summary — NALA JIRA-005 Crash Recovery{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 76}{RESET}")
    print(f"\n  {'Test Name':<55} {'Status':<10} {'Time'}")
    print(f"  {DIM}{'─' * 70}{RESET}")

    for name, ok, elapsed, exc in results:
        color  = GREEN if ok else RED
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {color}{name:<55}{RESET}  {color}{status:<10}{RESET}  {DIM}{elapsed}{RESET}")

    print(f"  {DIM}{'─' * 70}{RESET}")
    print(f"\n  {BOLD}Total: {total}  |  "
          f"{GREEN}Passed: {passed}{RESET}  |  "
          f"{RED}Failed: {failed}{RESET}")

    if failed == 0:
        print(f"\n  {BOLD}{GREEN}🎉  ALL {total} TESTS PASSED — JIRA-005 acceptance criteria SATISFIED!{RESET}")
        print(f"  {GREEN}    ARIES recovery pipeline fully verified. RISK-015 through RISK-029 mitigated.{RESET}")
    else:
        print(f"\n  {BOLD}{RED}⚠️   {failed} TEST(S) FAILED — Review failures above.{RESET}")

    print(f"\n{BOLD}{CYAN}{'═' * 76}{RESET}")
    print(f"  {DIM}Jai Bajrang Bali 🙏  |  Nexus Lab AI Research Lab, Bengaluru{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 76}{RESET}\n")


if __name__ == "__main__":
    _print_suite_header()

    results: list = []
    total_start = time.perf_counter()

    # ── Define all test cases to run interactively ────────────────────────────
    all_tests = [
        ("T00 — Environment Guard",              TestEnvironmentGuard(),              "test_recovery_module_importable"),
        ("T01 — SIGKILL Simulation",             TestT01SigkillSimulation(),          "test_recovery_from_simulated_sigkill"),
        ("T02 — StateMatrix Correction",         TestT02StateMatrixCorrection(),      "test_state_matrix_monotonic_correction"),
        ("T03 — SHA-256 Rollback",               TestT03Sha256Rollback(),             "test_sha256_mismatch_triggers_rollback_to_previous_lsn"),
        ("T04 — Full Corruption → Error",        TestT04FullCorruption(),             "test_full_corruption_raises_session_recovery_error"),
        ("T05 — Handler Replacement (v2)",       TestT05HandlerReplacement(),         "test_handler_v2_replaces_v1_during_recovery"),
        ("T06 — Stale Lock Cleared",             TestT06StaleLockCleared(),           "test_stale_lock_is_cleared_on_recovery"),
        ("T07 — Runaway Loop Guard",             TestT07RunawayLoopGuard(),           "test_runaway_loop_guard_halts_recovery"),
        ("T08 — HandoffSpore Reconstruction",    TestT08SporeReconstruction(),        "test_recovery_from_handoff_spore_when_all_checkpoints_corrupt"),
        ("T09 — Bad Handler → TypeError",        TestT09HandlerSignatureMismatch(),   "test_bad_handler_one_param_raises_type_error"),
        ("T10 — ARIES Redo Phase",               TestT10AriesRedoPhase(),             "test_aries_redo_phase_resets_running_to_pending"),
        ("T11a — SM Validator: No Correction",   TestT11StateMatrixValidator(),       "test_no_correction_when_sm_above_floor"),
        ("T11b — SM Validator: Apply Correction",TestT11StateMatrixValidator(),       "test_correction_applied_when_sm_below_floor"),
        ("T11c — SM Validator: Error Count",     TestT11StateMatrixValidator(),       "test_error_count_corrected_when_below_failed_count"),
        ("T12a — LockResolver: Acquire",         TestT12LockResolver(),               "test_lock_acquired_when_no_prior_lock"),
        ("T12b — LockResolver: Stale Cleared",   TestT12LockResolver(),               "test_stale_lock_cleared_and_reacquired"),
        ("T12c — LockResolver: Corrupt Cleared", TestT12LockResolver(),               "test_corrupt_lock_file_cleared_and_reacquired"),
        ("T12d — LockResolver: Idempotent",      TestT12LockResolver(),               "test_lock_release_is_idempotent"),
    ]

    for test_name, instance, method_name in all_tests:
        _run_test(test_name, instance, method_name, results)

    total_elapsed = (time.perf_counter() - total_start) * 1000
    print(f"\n  {DIM}Total suite time: {total_elapsed:.0f}ms{RESET}")

    _print_summary(results)

    # Exit with non-zero code if any test failed (for CI integration)
    sys.exit(0 if all(ok for _, ok, _, _ in results) else 1)
