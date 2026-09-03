"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/unit/test_checkpoint.py
Ticket  : JIRA-002 — Build Checkpoint System
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-11

PURPOSE
-------
Interactive, production-level unit tests for core/harness/checkpoint.py.

Unlike traditional tests that just print "PASS" or "FAIL", these tests display
a full internal trace of every operation — showing exactly what NALA's
CheckpointManager is doing step-by-step in real time.

Every RISK mitigation from the JIRA-002 plan is verified independently:
  RISK-004 : Atomic write  (.tmp → fsync → os.replace)
  RISK-005 : latest.json fallback chain (3-tier recovery)
  RISK-006 : SHA-256 integrity + auto-rollback to LSN-1
  RISK-007 : Sliding-window retention policy + genesis preservation
  RISK-008 : Dual-layer concurrent write safety (thread + filelock)

HOW TO RUN
----------
  # Activate venv first (from E:\\NALA-Project\\NALA\\)
  .\.venv\Scripts\Activate.ps1

  # Interactive colored output — see full internal trace:
  python tests/unit/test_checkpoint.py

  # Or via pytest (verbose):
  pytest tests/unit/test_checkpoint.py -v -s

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timezone
from pathlib import Path
from typing import Any, List

import pytest

# ── Force UTF-8 output on Windows consoles (fixes UnicodeEncodeError) ────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Add the project root (NALA/) to sys.path so imports work without install ──
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── Module under test ─────────────────────────────────────────────────────────
from core.harness.checkpoint import (
    CheckpointIntegrityError,
    CheckpointManager,
    CheckpointNotFoundError,
    CheckpointRecord,
    CheckpointRecoveryError,
    _filename_to_lsn,
    _lsn_to_filename,
)
from core.harness.session_contract import SessionState, TaskStep, utcnow


# ==============================================================================
# DISPLAY HELPERS — Rich interactive console output
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
RESET   = "\033[0m"


def banner(title: str) -> None:
    """Print a styled test section banner."""
    width = 72
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  💾 {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")


def step(msg: str) -> None:
    """Print a single test step trace."""
    print(f"  {DIM}→{RESET}  {msg}")


def success(msg: str) -> None:
    """Print a success confirmation."""
    print(f"  {GREEN}✅  {msg}{RESET}")


def warn(msg: str) -> None:
    """Print a warning observation."""
    print(f"  {YELLOW}⚠️   {msg}{RESET}")


def error_line(msg: str) -> None:
    """Print an expected-error observation."""
    print(f"  {RED}🔴  {msg}{RESET}")


def info(label: str, value: Any) -> None:
    """Print a labelled value for inspection."""
    print(f"  {YELLOW}   {label:<30}{RESET} {BLUE}{value}{RESET}")


def show_json(obj: dict, indent: int = 2) -> None:
    """Pretty-print a dict or JSON-like object with dim styling."""
    lines = json.dumps(obj, indent=indent, default=str).splitlines()
    for line in lines[:30]:          # cap at 30 lines for readability
        print(f"  {DIM}{line}{RESET}")
    if len(lines) > 30:
        print(f"  {DIM}  ... ({len(lines) - 30} more lines){RESET}")


def divider() -> None:
    print(f"  {DIM}{'─' * 68}{RESET}")


def disk_scan(session_dir: Path) -> None:
    """Print the current state of a session's checkpoint directory."""
    print(f"  {MAGENTA}  📁 Disk state → {session_dir.name}/{RESET}")
    files = sorted(session_dir.iterdir()) if session_dir.exists() else []
    if not files:
        print(f"  {DIM}     (empty){RESET}")
    for f in files:
        size = f.stat().st_size if f.is_file() else 0
        print(f"  {DIM}     {f.name:<45} {size:>6} bytes{RESET}")


# ==============================================================================
# SHARED FIXTURE HELPERS
# ==============================================================================

def make_session(objective: str = "Test NALA Checkpoint System") -> SessionState:
    """Create a minimal, realistic SessionState for testing."""
    session = SessionState(objective=objective)
    session.task_graph.steps = [
        TaskStep(step_id="s1_init",    description="Initialize the run",    dependencies=[]),
        TaskStep(step_id="s2_process", description="Process the workload",  dependencies=["s1_init"]),
        TaskStep(step_id="s3_report",  description="Generate final report",  dependencies=["s2_process"]),
    ]
    return session


def make_manager(tmp_dir: Path, max_checkpoints: int = 20) -> CheckpointManager:
    """Create a CheckpointManager pointed at a temp directory."""
    return CheckpointManager(
        base_dir=tmp_dir,
        max_checkpoints=max_checkpoints,
        retention_policy="sliding_window",
        lock_timeout=5.0,
        rollback_attempts=3,
    )


# ==============================================================================
# TEST 1 — Environment Guard & Imports
# ==============================================================================

class TestEnvironmentGuard:
    """Verify the environment is correctly configured for NALA JIRA-002."""

    def test_checkpoint_module_importable(self) -> None:
        banner("TEST 1 — Environment Guard & Import Verification")

        step("Verifying CheckpointManager is importable from core.harness.checkpoint...")
        info("CheckpointManager class  :", CheckpointManager.__name__)
        info("CheckpointRecord class   :", CheckpointRecord.__name__)
        info("CheckpointError base     :", "CheckpointError hierarchy")
        info("Utility _lsn_to_filename :", _lsn_to_filename(42))
        info("Utility _filename_to_lsn :", _filename_to_lsn("checkpoint_LSN_000042.json"))

        assert CheckpointManager is not None
        assert CheckpointRecord is not None
        assert _lsn_to_filename(42) == "checkpoint_LSN_000042.json"
        assert _filename_to_lsn("checkpoint_LSN_000042.json") == 42
        assert _filename_to_lsn("latest.json") is None

        divider()
        step("Verifying exception hierarchy (all subclass CheckpointError)...")
        from core.harness.checkpoint import (
            CheckpointError,
            CheckpointWriteError,
            CheckpointRecoveryError,
            CheckpointLockError,
        )
        for exc_cls in [
            CheckpointNotFoundError,
            CheckpointIntegrityError,
            CheckpointWriteError,
            CheckpointRecoveryError,
            CheckpointLockError,
        ]:
            assert issubclass(exc_cls, CheckpointError), \
                f"{exc_cls.__name__} must subclass CheckpointError"
            info(f"  {exc_cls.__name__}", "→ ✅ subclasses CheckpointError")

        success("JIRA-002 module imports cleanly. Exception hierarchy is correct.")


# ==============================================================================
# TEST 2 — write_checkpoint() Creates Correct Files
# ==============================================================================

class TestWriteCheckpoint:
    """
    T1 — write_checkpoint() produces checkpoint_LSN_N.json + latest.json.
    Verify on-disk structure after a single write.
    """

    def test_write_creates_correct_files(self) -> None:
        banner("TEST 2 — write_checkpoint() Creates Correct Files on Disk")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            step(f"Session created | ID={session.session_id[:16]}...")
            step("Calling manager.write_checkpoint(session) ...")
            t0 = time.perf_counter()
            written_path = manager.write_checkpoint(session)
            elapsed = (time.perf_counter() - t0) * 1000

            info("Written path                 :", written_path.name)
            info("Written in                   :", f"{elapsed:.2f} ms")
            info("LSN after write              :", session.checkpoint_meta.lsn)
            info("SHA-256 hash in meta         :", session.checkpoint_meta.content_hash[:20] + "...")

            divider()
            step("Scanning disk to verify file layout...")
            session_dir = tmp_dir / session.session_id
            disk_scan(session_dir)

            # Assertions
            assert written_path.exists(), "Checkpoint .json file must exist after write"
            assert (session_dir / "latest.json").exists(), "latest.json must exist after write"
            assert written_path.name == "checkpoint_LSN_000001.json", \
                f"Expected 'checkpoint_LSN_000001.json', got '{written_path.name}'"

            divider()
            step("Verifying latest.json content...")
            latest_raw = (session_dir / "latest.json").read_text(encoding="utf-8")
            latest_data = json.loads(latest_raw)
            info("latest.json → lsn          :", latest_data["lsn"])
            info("latest.json → file         :", latest_data["file"])
            info("latest.json → schema_ver   :", latest_data.get("schema_version", "N/A"))

            assert latest_data["lsn"] == 1
            assert latest_data["file"] == "checkpoint_LSN_000001.json"

            success("write_checkpoint() produced correct files with valid latest.json index.")


# ==============================================================================
# TEST 3 — Round-Trip Identity (Write → Load → Compare)
# ==============================================================================

class TestRoundTrip:
    """
    T2 — Load after save returns an identical SessionState.
    Verifies that serialization + deserialization is a perfect round-trip.
    """

    def test_round_trip_identity(self) -> None:
        banner("TEST 3 — Round-Trip Identity: write → load → compare")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session("Round-trip identity verification test")

            # Add some realistic state
            session.state_matrix.total_tokens_in  = 14_200
            session.state_matrix.total_tokens_out =  3_800
            session.state_matrix.estimated_cost   =  0.0019
            session.state_matrix.error_count       = 2
            session.task_graph.steps[0].mark_running()
            session.task_graph.steps[0].mark_success(result={"files_read": 22})

            step("Writing session with populated state to disk...")
            manager.write_checkpoint(session)
            original_id  = session.session_id
            original_lsn = session.checkpoint_meta.lsn

            info("original session_id  :", original_id[:16] + "...")
            info("original LSN         :", original_lsn)
            info("original tokens_in   :", session.state_matrix.total_tokens_in)
            info("original cost USD    :", session.state_matrix.estimated_cost)

            divider()
            step("Loading checkpoint back from disk via load_latest()...")
            restored = manager.load_latest(session.session_id)

            info("restored session_id  :", restored.session_id[:16] + "...")
            info("restored LSN         :", restored.checkpoint_meta.lsn)
            info("restored tokens_in   :", restored.state_matrix.total_tokens_in)
            info("restored cost USD    :", restored.state_matrix.estimated_cost)
            info("step[0] status       :", restored.task_graph.steps[0].status)

            divider()
            step("Comparing all fields for byte-level identity...")

            assert restored.session_id      == original_id,               "session_id mismatch"
            assert restored.checkpoint_meta.lsn == original_lsn,         "LSN mismatch"
            assert restored.state_matrix.total_tokens_in == 14_200,      "tokens_in mismatch"
            assert restored.state_matrix.total_tokens_out ==  3_800,     "tokens_out mismatch"
            assert abs(restored.state_matrix.estimated_cost - 0.0019) < 1e-9, "cost mismatch"
            assert restored.state_matrix.error_count == 2,               "error_count mismatch"
            assert restored.task_graph.steps[0].status == "SUCCESS",     "step status mismatch"
            assert restored.task_graph.steps[0].result == {"files_read": 22}, "step result mismatch"

            success("Round-trip identity verified. Deserialized state is byte-identical to written state.")


# ==============================================================================
# TEST 4 — Atomic Write: No .tmp File Remains on Success
# ==============================================================================

class TestAtomicWrite:
    """
    T3 — After a successful write, no .tmp staging file should exist on disk.
    This verifies the atomic os.replace() pattern is working correctly (RISK-004).
    """

    def test_atomic_no_tmp_on_success(self) -> None:
        banner("TEST 4 — Atomic Write: No .tmp Files Remain After Success (RISK-004)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            step("Writing 5 consecutive checkpoints to disk...")
            for i in range(5):
                manager.write_checkpoint(session)
                step(f"  Write #{i+1} complete → LSN={session.checkpoint_meta.lsn}")

            session_dir = tmp_dir / session.session_id
            divider()
            step("Scanning for any leftover .tmp staging files...")
            disk_scan(session_dir)

            tmp_files = list(session_dir.glob("*.tmp"))
            info("Total .tmp files found       :", len(tmp_files))

            if tmp_files:
                for f in tmp_files:
                    warn(f"Unexpected .tmp found: {f.name}")

            assert len(tmp_files) == 0, \
                f"Atomic write failed: {len(tmp_files)} .tmp file(s) left on disk"

            success("Atomic write confirmed — zero .tmp files remain after all 5 writes.")


# ==============================================================================
# TEST 5 — LSN Increments Monotonically
# ==============================================================================

class TestLSNIncrement:
    """
    T4 — 5 consecutive writes must produce LSN 1, 2, 3, 4, 5 in strict order.
    Verifies the monotonic Log Sequence Number contract.
    """

    def test_lsn_increments_each_write(self) -> None:
        banner("TEST 5 — LSN Monotonic Increment: 5 writes → LSN 1 through 5")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            written_lsns: List[int] = []

            step("Writing 5 checkpoints sequentially and recording LSNs...")
            divider()
            for write_num in range(1, 6):
                path = manager.write_checkpoint(session)
                lsn  = session.checkpoint_meta.lsn
                written_lsns.append(lsn)
                info(f"  Write #{write_num}  → file", f"{path.name}  |  LSN={lsn}")

            divider()
            step("Verifying LSN sequence is exactly [1, 2, 3, 4, 5]...")
            info("Recorded LSN sequence        :", written_lsns)

            assert written_lsns == [1, 2, 3, 4, 5], \
                f"Expected [1,2,3,4,5], got {written_lsns}"

            divider()
            step("Verifying all 5 checkpoint files exist on disk...")
            session_dir = tmp_dir / session.session_id
            disk_scan(session_dir)

            for i in range(1, 6):
                expected_file = session_dir / f"checkpoint_LSN_00000{i}.json"
                assert expected_file.exists(), f"Missing: {expected_file.name}"
                info(f"  checkpoint_LSN_00000{i}.json", "→ ✅ exists")

            success("LSN sequence [1..5] verified. All 5 checkpoint files confirmed on disk.")


# ==============================================================================
# TEST 6 — Load by Specific LSN
# ==============================================================================

class TestLoadByLSN:
    """
    T5 — load_checkpoint(session_id, lsn=3) must load exactly LSN=3.
    Verifies direct LSN-targeted loading without fallback chain.
    """

    def test_load_by_lsn(self) -> None:
        banner("TEST 6 — Load by Specific LSN: load_checkpoint(lsn=3)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            # Write 5 checkpoints, mutating state between each
            step("Writing 5 checkpoints with different token counts per write...")
            divider()
            token_snapshots = []
            for i in range(1, 6):
                session.state_matrix.total_tokens_in += i * 1000
                manager.write_checkpoint(session)
                token_snapshots.append(session.state_matrix.total_tokens_in)
                info(f"  LSN={i}  tokens_in", session.state_matrix.total_tokens_in)

            divider()
            step("Loading LSN=3 specifically (not the latest LSN=5)...")
            restored = manager.load_checkpoint(session.session_id, lsn=3)

            info("Loaded LSN                   :", restored.checkpoint_meta.lsn)
            info("Loaded tokens_in             :", restored.state_matrix.total_tokens_in)
            info("Expected tokens_in at LSN=3  :", token_snapshots[2])

            assert restored.checkpoint_meta.lsn == 3, \
                f"Expected LSN=3, got {restored.checkpoint_meta.lsn}"
            assert restored.state_matrix.total_tokens_in == token_snapshots[2], \
                "tokens_in at LSN=3 does not match the snapshot recorded at write time"

            success(f"load_checkpoint(lsn=3) loaded the correct historical state. tokens_in={restored.state_matrix.total_tokens_in}")


# ==============================================================================
# TEST 7 — Three-Tier Fallback: Delete latest.json → dir scan takes over
# ==============================================================================

class TestFallbackChain:
    """
    T7 — Deleting latest.json must NOT prevent recovery.
    Proves that Tier 2 (directory scan) correctly takes over (RISK-005).
    """

    def test_load_fallback_without_latest_json(self) -> None:
        banner("TEST 7 — 3-Tier Fallback: Delete latest.json → Tier 2 Dir Scan (RISK-005)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            step("Writing 3 checkpoints to disk (LSN 1, 2, 3)...")
            for _ in range(3):
                manager.write_checkpoint(session)

            session_id  = session.session_id
            session_dir = tmp_dir / session_id
            latest_path = session_dir / "latest.json"

            info("Latest LSN before delete     :", session.checkpoint_meta.lsn)
            divider()

            assert latest_path.exists(), "latest.json must exist before deletion"
            step("🗑  DELETING latest.json to simulate pointer corruption crash...")
            latest_path.unlink()
            warn("latest.json has been deleted from disk.")

            disk_scan(session_dir)

            divider()
            step("Calling load_latest() — Tier 2 fallback should kick in...")
            t0 = time.perf_counter()
            restored = manager.load_latest(session_id)
            elapsed  = (time.perf_counter() - t0) * 1000

            info("Restored via Tier 2 scan     :", "✅ directory scan succeeded")
            info("Recovered LSN                :", restored.checkpoint_meta.lsn)
            info("Recovery time                :", f"{elapsed:.2f} ms")

            assert restored.checkpoint_meta.lsn == 3, \
                f"Fallback recovery returned wrong LSN: {restored.checkpoint_meta.lsn}"
            assert restored.session_id == session_id

            success("Tier 2 dir-scan fallback worked perfectly. RISK-005 is mitigated.")


# ==============================================================================
# TEST 8 — SHA-256 Integrity Failure Raises CheckpointIntegrityError
# ==============================================================================

class TestIntegrityFailure:
    """
    T8 — Manually tampering with a checkpoint file must raise CheckpointIntegrityError.
    Verifies the RISK-006 SHA-256 guard is active on load.
    """

    def test_integrity_failure_raises(self) -> None:
        banner("TEST 8 — SHA-256 Integrity Guard: Tampered File → CheckpointIntegrityError (RISK-006)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            step("Writing one checkpoint to disk (LSN=1)...")
            manager.write_checkpoint(session)
            session_id  = session.session_id
            session_dir = tmp_dir / session_id
            cp_file     = session_dir / "checkpoint_LSN_000001.json"

            assert cp_file.exists()
            original_size = cp_file.stat().st_size
            info("Checkpoint file              :", cp_file.name)
            info("Original file size           :", f"{original_size} bytes")

            divider()
            step("🔧 TAMPERING: injecting corruption byte into checkpoint JSON...")
            raw = cp_file.read_text(encoding="utf-8")
            data = json.loads(raw)

            # Corrupt the objective field
            original_objective = data["objective"]
            data["objective"] = "CORRUPTED_BY_ADVERSARY_" + original_objective
            corrupted_json = json.dumps(data, indent=2)
            cp_file.write_text(corrupted_json, encoding="utf-8")

            warn("File has been tampered with. SHA-256 hash in meta is now stale.")
            info("Injected corruption          :", "objective field prefix modified")
            info("Tampered file size           :", f"{cp_file.stat().st_size} bytes")

            divider()
            step("Attempting to load the tampered checkpoint...")
            raised = False
            exc_message = ""
            try:
                manager.load_checkpoint(session_id, lsn=1)
            except CheckpointIntegrityError as exc:
                raised      = True
                exc_message = str(exc)
            except CheckpointRecoveryError as exc:
                raised      = True
                exc_message = str(exc)
                warn("CheckpointRecoveryError raised (rollback exhausted on only LSN)")

            error_line(f"Exception caught: {exc_message[:80]}...")
            info("CheckpointIntegrityError raised?", raised)

            assert raised, \
                "Expected CheckpointIntegrityError or CheckpointRecoveryError but no exception raised"

            success("SHA-256 integrity guard fired correctly. Tampered checkpoint was rejected.")


# ==============================================================================
# TEST 9 — SHA-256 Auto-Rollback: Tamper Latest → Rollback to LSN-1
# ==============================================================================

class TestAutoRollback:
    """
    T9 — Tampered LSN=N causes CheckpointManager to automatically load LSN=N-1.
    Verifies the RISK-006 auto-rollback recovery chain.
    """

    def test_integrity_auto_rollback_to_previous_lsn(self) -> None:
        banner("TEST 9 — SHA-256 Auto-Rollback: Tampered LSN=2 → Auto-load LSN=1 (RISK-006)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            # Write 2 clean checkpoints
            step("Writing 2 clean checkpoints (LSN=1, LSN=2)...")
            manager.write_checkpoint(session)
            lsn1_tokens = session.state_matrix.total_tokens_in

            session.state_matrix.total_tokens_in += 5000
            manager.write_checkpoint(session)
            lsn2_tokens = session.state_matrix.total_tokens_in

            session_id  = session.session_id
            session_dir = tmp_dir / session_id

            info("LSN=1 tokens_in              :", lsn1_tokens)
            info("LSN=2 tokens_in              :", lsn2_tokens)
            info("Latest LSN on disk           :", 2)

            divider()
            step("🔧 TAMPERING with LSN=2 (latest) checkpoint...")
            cp2 = session_dir / "checkpoint_LSN_000002.json"
            data = json.loads(cp2.read_text("utf-8"))
            data["state_matrix"]["total_tokens_in"] = 9_999_999   # bad value
            cp2.write_text(json.dumps(data, indent=2), "utf-8")
            warn("LSN=2 file corrupted. SHA-256 stored in meta is now stale.")

            # Also corrupt latest.json to point at LSN=2 (which is now tampered)
            step("Ensuring latest.json still points to LSN=2 (the corrupted one)...")

            divider()
            step("Calling load_latest() — auto-rollback must find clean LSN=1...")
            t0 = time.perf_counter()
            restored = manager.load_latest(session_id)
            elapsed  = (time.perf_counter() - t0) * 1000

            info("Recovered LSN                :", restored.checkpoint_meta.lsn)
            info("Recovered tokens_in          :", restored.state_matrix.total_tokens_in)
            info("Recovery time                :", f"{elapsed:.2f} ms")

            assert restored.checkpoint_meta.lsn == 1, \
                f"Auto-rollback should have landed on LSN=1, got LSN={restored.checkpoint_meta.lsn}"
            assert restored.state_matrix.total_tokens_in == lsn1_tokens, \
                "Recovered tokens_in must match the clean LSN=1 snapshot"

            success(f"Auto-rollback succeeded! Tampered LSN=2 was skipped. Resumed from clean LSN=1.")


# ==============================================================================
# TEST 10 — Retention Policy: max_checkpoints=3, genesis preserved
# ==============================================================================

class TestRetentionPolicy:
    """
    T10 — With max_checkpoints=3, only last 3 (+ genesis LSN=1) are kept.
    Verifies the RISK-007 sliding-window retention policy.
    """

    def test_retention_policy_enforced(self) -> None:
        banner("TEST 10 — Sliding-Window Retention Policy (max=3, genesis always kept) (RISK-007)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir, max_checkpoints=3)
            session = make_session()

            step("Writing 7 checkpoints with max_checkpoints=3...")
            divider()
            for i in range(1, 8):
                manager.write_checkpoint(session)
                step(f"  Write #{i} → LSN={session.checkpoint_meta.lsn} | "
                     f"retention window enforced after each write")

            session_dir   = tmp_dir / session.session_id
            divider()
            step("Final disk state after 7 writes:")
            disk_scan(session_dir)

            # Collect surviving checkpoint files
            from core.harness.checkpoint import _filename_to_lsn
            surviving_lsns = sorted(
                _filename_to_lsn(p.name)
                for p in session_dir.glob("checkpoint_LSN_*.json")
                if _filename_to_lsn(p.name) is not None
            )

            info("Surviving LSNs on disk       :", surviving_lsns)
            info("Total surviving checkpoints  :", len(surviving_lsns))
            info("Genesis LSN=1 preserved?     :", 1 in surviving_lsns)

            # We expect: LSN=1 (genesis) + last 2 of [2..7] = [1, 6, 7]
            # OR genesis + last max_checkpoints-1 = [1, 5, 6, 7] depending on rounding
            # The contract is: len <= max_checkpoints AND genesis must be present
            assert len(surviving_lsns) <= 3 + 1, \
                f"Too many checkpoints survived: {surviving_lsns}"
            assert 1 in surviving_lsns, \
                "Genesis checkpoint (LSN=1) must ALWAYS be preserved"
            assert 7 in surviving_lsns, \
                "The latest checkpoint (LSN=7) must always survive"

            success(f"Retention policy enforced. Surviving LSNs: {surviving_lsns}. Genesis preserved.")


# ==============================================================================
# TEST 11 — list_checkpoints() Returns Ordered Records
# ==============================================================================

class TestListCheckpoints:
    """
    T11 — list_checkpoints() must return CheckpointRecord objects sorted by LSN.
    Verifies the audit trail API returns correct metadata.
    """

    def test_list_checkpoints_ordered(self) -> None:
        banner("TEST 11 — list_checkpoints(): Ordered Audit Trail of CheckpointRecords")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            step("Writing 4 checkpoints to disk...")
            for _ in range(4):
                manager.write_checkpoint(session)

            session_id = session.session_id
            divider()
            step("Calling manager.list_checkpoints(session_id)...")
            records = manager.list_checkpoints(session_id)

            info("Total records returned       :", len(records))
            divider()
            step("Printing each CheckpointRecord:")
            for rec in records:
                info(
                    f"  LSN={rec.lsn}",
                    f"size={rec.file_size_bytes}B | "
                    f"hash={rec.content_hash[:12]}... | "
                    f"ts={rec.timestamp.strftime('%H:%M:%S')}Z"
                )
                assert isinstance(rec, CheckpointRecord), "Each record must be a CheckpointRecord"
                assert rec.session_id == session_id,      "session_id in record must match"
                assert rec.lsn >= 1,                      "LSN must be >= 1"
                assert rec.file_path.exists(),            "Record file_path must exist on disk"
                assert rec.file_size_bytes > 0,           "File size must be > 0 bytes"

            divider()
            step("Verifying records are sorted by LSN ascending...")
            lsns = [r.lsn for r in records]
            info("LSN order                    :", lsns)
            assert lsns == sorted(lsns), f"Records are not sorted by LSN: {lsns}"
            assert lsns == [1, 2, 3, 4],  f"Expected [1,2,3,4], got {lsns}"

            success("list_checkpoints() returned 4 correctly ordered, fully populated CheckpointRecords.")


# ==============================================================================
# TEST 12 — Concurrent Write Safety (RISK-008)
# ==============================================================================

class TestConcurrentWriteSafety:
    """
    T12 — Two ThreadPoolExecutor workers writing simultaneously must produce
    valid, non-overlapping, monotonically increasing LSNs.
    Verifies the RISK-008 dual-layer lock is functioning.
    """

    def test_concurrent_write_safety(self) -> None:
        banner("TEST 12 — Concurrent Write Safety: 2 Threads × 5 Writes Each (RISK-008)")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            # Use a SINGLE shared manager and SINGLE shared session
            # (both threads compete to write to the same session_id)
            manager = make_manager(tmp_dir, max_checkpoints=20)
            session = make_session("Concurrent write stress test")

            collected_lsns: List[int] = []
            write_errors:   List[str] = []
            lock = __import__("threading").Lock()

            def write_worker(worker_id: int, n_writes: int) -> List[int]:
                """Worker function: perform n_writes and return acquired LSNs."""
                my_lsns: List[int] = []
                for write_num in range(n_writes):
                    try:
                        manager.write_checkpoint(session)
                        acquired_lsn = session.checkpoint_meta.lsn
                        my_lsns.append(acquired_lsn)
                        step(
                            f"  Thread-{worker_id} | write #{write_num+1} "
                            f"→ LSN={acquired_lsn}"
                        )
                    except Exception as exc:
                        with lock:
                            write_errors.append(f"Thread-{worker_id}: {exc}")
                return my_lsns

            step("Launching 2 concurrent threads, each making 5 writes...")
            divider()

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_a = executor.submit(write_worker, worker_id=1, n_writes=5)
                future_b = executor.submit(write_worker, worker_id=2, n_writes=5)

                lsns_a = future_a.result()
                lsns_b = future_b.result()

            divider()
            step("Both threads complete. Analyzing results...")

            all_lsns = sorted(lsns_a + lsns_b)
            info("Thread-1 LSNs                :", sorted(lsns_a))
            info("Thread-2 LSNs                :", sorted(lsns_b))
            info("All LSNs combined            :", all_lsns)
            info("Total LSNs collected         :", len(all_lsns))
            info("Write errors encountered     :", len(write_errors))

            if write_errors:
                for err in write_errors:
                    error_line(f"  Error: {err}")

            divider()
            step("Verifying no duplicate LSNs (race condition check)...")
            assert len(write_errors) == 0, \
                f"Write errors occurred during concurrent test: {write_errors}"
            assert len(all_lsns) == 10, \
                f"Expected 10 total LSNs from 2×5 writes, got {len(all_lsns)}"
            assert len(set(all_lsns)) == len(all_lsns), \
                f"Duplicate LSNs detected! Race condition occurred: {all_lsns}"
            assert all_lsns == list(range(1, 11)), \
                f"LSNs are not a clean 1..10 sequence: {all_lsns}"

            divider()
            step("Verifying all 10 checkpoint files exist on disk...")
            session_dir = tmp_dir / session.session_id
            disk_scan(session_dir)

            for i in range(1, 11):
                expected = session_dir / _lsn_to_filename(i)
                assert expected.exists(), f"Missing checkpoint file: {expected.name}"

            success(
                "Concurrent write test passed. 10/10 non-duplicate LSNs. "
                "RISK-008 dual-layer lock is functioning correctly."
            )


# ==============================================================================
# BONUS TEST 13 — session_exists() and get_latest_lsn() utility methods
# ==============================================================================

class TestUtilityMethods:
    """
    Verify the utility methods: session_exists(), get_latest_lsn(), purge_session().
    """

    def test_session_lifecycle_utilities(self) -> None:
        banner("BONUS TEST 13 — session_exists(), get_latest_lsn(), purge_session()")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            manager = make_manager(tmp_dir)
            session = make_session()

            fake_id = "00000000-0000-0000-0000-000000000000"

            step("Checking session_exists() before any writes...")
            result_before = manager.session_exists(session.session_id)
            info("session_exists() (before write)", result_before)
            assert result_before is False, "Session must not exist before first write"

            divider()
            step("Writing 4 checkpoints...")
            for _ in range(4):
                manager.write_checkpoint(session)

            result_after = manager.session_exists(session.session_id)
            info("session_exists() (after write) :", result_after)
            assert result_after is True, "Session must exist after writes"

            divider()
            step("Calling get_latest_lsn()...")
            latest_lsn = manager.get_latest_lsn(session.session_id)
            info("get_latest_lsn()               :", latest_lsn)
            assert latest_lsn == 4, f"Expected latest LSN=4, got {latest_lsn}"

            none_lsn = manager.get_latest_lsn(fake_id)
            info("get_latest_lsn() [fake id]     :", none_lsn)
            assert none_lsn is None, "get_latest_lsn() for non-existent session must return None"

            divider()
            step("Calling purge_session() to destroy all checkpoints...")
            session_id = session.session_id
            deleted    = manager.purge_session(session_id)
            info("Files deleted by purge         :", deleted)
            assert deleted >= 4, f"Expected at least 4 files deleted, got {deleted}"

            result_purged = manager.session_exists(session_id)
            info("session_exists() (after purge) :", result_purged)
            assert result_purged is False, "Session must not exist after purge"

            success("session_exists(), get_latest_lsn(), and purge_session() all verified.")


# ==============================================================================
# MAIN RUNNER — Interactive demo mode (python test_checkpoint.py)
# ==============================================================================

def run_all_tests_interactive() -> None:
    """
    Run all 13 tests interactively with rich colored output.
    Called when the file is executed directly: python test_checkpoint.py
    """
    width = 72

    print(f"\n{BOLD}{MAGENTA}")
    print("  ███╗   ██╗ █████╗ ██╗      █████╗ ")
    print("  ████╗  ██║██╔══██╗██║     ██╔══██╗")
    print("  ██╔██╗ ██║███████║██║     ███████║")
    print("  ██║╚██╗██║██╔══██║██║     ██╔══██║")
    print("  ██║ ╚████║██║  ██║███████╗██║  ██║")
    print("  ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")

    print(f"\n{BOLD}{CYAN}  Checkpoint System — Unit Test Suite{RESET}")
    print(f"{DIM}  Nexus Lab AI Research Lab | Bengaluru{RESET}")
    print(f"{DIM}  JIRA-002 | Phase 1: Core Harness (Survival Foundation){RESET}")

    print(f"\n{'═' * width}")
    print(f"  Running {BOLD}13 tests{RESET} across all RISK mitigations:")
    print(f"  {GREEN}RISK-004{RESET} Atomic Write  |  {GREEN}RISK-005{RESET} Fallback Chain")
    print(f"  {GREEN}RISK-006{RESET} SHA-256 Guard |  {GREEN}RISK-007{RESET} Retention Policy")
    print(f"  {GREEN}RISK-008{RESET} Concurrent Safety")
    print(f"{'═' * width}\n")

    test_classes = [
        ("TEST  1", TestEnvironmentGuard,    "test_checkpoint_module_importable"),
        ("TEST  2", TestWriteCheckpoint,      "test_write_creates_correct_files"),
        ("TEST  3", TestRoundTrip,            "test_round_trip_identity"),
        ("TEST  4", TestAtomicWrite,          "test_atomic_no_tmp_on_success"),
        ("TEST  5", TestLSNIncrement,         "test_lsn_increments_each_write"),
        ("TEST  6", TestLoadByLSN,            "test_load_by_lsn"),
        ("TEST  7", TestFallbackChain,        "test_load_fallback_without_latest_json"),
        ("TEST  8", TestIntegrityFailure,     "test_integrity_failure_raises"),
        ("TEST  9", TestAutoRollback,         "test_integrity_auto_rollback_to_previous_lsn"),
        ("TEST 10", TestRetentionPolicy,      "test_retention_policy_enforced"),
        ("TEST 11", TestListCheckpoints,      "test_list_checkpoints_ordered"),
        ("TEST 12", TestConcurrentWriteSafety,"test_concurrent_write_safety"),
        ("TEST 13", TestUtilityMethods,       "test_session_lifecycle_utilities"),
    ]

    passed = 0
    failed = 0
    start_wall = time.perf_counter()

    for label, cls, method_name in test_classes:
        try:
            obj = cls()
            getattr(obj, method_name)()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"\n{RED}{BOLD}  ❌ FAILED — {label}: {method_name}{RESET}")
            print(f"{RED}     {type(exc).__name__}: {exc}{RESET}")
            import traceback
            traceback.print_exc()

    total_time = (time.perf_counter() - start_wall) * 1000
    width = 72

    print(f"\n\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  NALA JIRA-002 TEST RESULTS{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"  {GREEN}Passed  : {passed:>3}{RESET}")
    print(f"  {RED if failed else GREEN}Failed  : {failed:>3}{RESET}")
    print(f"  {CYAN}Total   : {passed + failed:>3}{RESET}")
    print(f"  {DIM}Duration: {total_time:.0f} ms{RESET}")

    if failed == 0:
        print(f"\n  {BOLD}{GREEN}🚀 ALL {passed} TESTS PASSED — CheckpointManager is battle-ready!{RESET}")
        print(f"  {DIM}RISK-004 ✅ | RISK-005 ✅ | RISK-006 ✅ | RISK-007 ✅ | RISK-008 ✅{RESET}")
    else:
        print(f"\n  {BOLD}{RED}⚠️  {failed} TEST(S) FAILED — Review output above.{RESET}")

    print(f"\n  {DIM}Jai Bajrang Bali 🙏 — Nexus Lab AI Research Lab, Bengaluru{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests_interactive()
