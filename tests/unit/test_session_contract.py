"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/unit/test_session_contract.py
Ticket  : JIRA-001 — Define Session Contract
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru

PURPOSE
-------
Interactive, production-level unit tests for core/harness/session_contract.py.

Unlike traditional tests that just print "PASS" or "FAIL", these tests display
a full internal trace of each operation — showing exactly what NALA is doing
step-by-step so you can see the Session Contract working in real time.

HOW TO RUN
----------
    # From the E:\\NALA-Project\\NALA\\ directory:
    pip install pydantic>=2.0 pytest pytest-asyncio
    pytest tests/unit/test_session_contract.py -v -s

    # Or run directly (no pytest needed for the live demo):
    python tests/unit/test_session_contract.py

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

# ── Add project root to path so imports work without installation ──────────────
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── Import the module under test ───────────────────────────────────────────────
from core.harness.session_contract import (
    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)

# ── Try importing pydantic for version test ────────────────────────────────────
import pydantic
from pydantic import ValidationError


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
RESET   = "\033[0m"

def banner(title: str) -> None:
    """Print a styled test section banner."""
    width = 70
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  🔬 {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")


def step(msg: str) -> None:
    """Print a single test step trace."""
    print(f"  {DIM}→{RESET}  {msg}")


def success(msg: str) -> None:
    """Print a success confirmation."""
    print(f"  {GREEN}✅  {msg}{RESET}")


def info(label: str, value: Any) -> None:
    """Print a labelled value for inspection."""
    print(f"  {YELLOW}   {label:<28}{RESET} {BLUE}{value}{RESET}")


def show_json(obj: Dict[str, Any], indent: int = 2) -> None:
    """Pretty-print a dict or JSON-like object."""
    lines = json.dumps(obj, indent=indent, default=str).splitlines()
    for line in lines:
        print(f"  {DIM}{line}{RESET}")


def divider() -> None:
    print(f"  {DIM}{'─' * 66}{RESET}")


# ==============================================================================
# TEST 1 — Pydantic v2 Environment Guard
# ==============================================================================

class TestEnvironmentGuard:
    """Verify the environment is correctly configured for NALA."""

    def test_pydantic_version_is_v2(self) -> None:
        banner("TEST 1 — Pydantic v2 Environment Guard")

        step("Checking installed Pydantic version...")
        version = pydantic.VERSION
        major   = int(version.split(".")[0])

        info("Detected Pydantic version :", version)
        info("Required major version    :", "2+")
        info("Current major version     :", major)

        assert major >= 2, (
            f"NALA requires Pydantic v2+. "
            f"Detected: {version}. Run: pip install 'pydantic>=2.0'"
        )
        success(f"Environment OK — Pydantic v{version} is compatible with NALA.")


# ==============================================================================
# TEST 2 — Session Creation & Identity
# ==============================================================================

class TestSessionCreation:
    """Verify that a new SessionState is created with the correct identity fields."""

    def test_session_creates_with_objective(self) -> None:
        banner("TEST 2 — Session Creation & Identity")

        objective = "Analyze the NALA codebase and generate a full architecture report."
        step(f"Creating new SessionState with objective:")
        step(f'  "{objective[:60]}..."')

        session = SessionState(objective=objective)

        info("session_id (auto-generated UUID4)  :", session.session_id)
        info("objective                           :", session.objective[:50] + "...")
        info("version                             :", session.version)
        info("created_at (UTC-aware)              :", session.created_at.isoformat())
        info("last_updated (UTC-aware)            :", session.last_updated.isoformat())
        info("checkpoint LSN (starts at 0)        :", session.checkpoint_meta.lsn)
        info("task_graph steps (empty at start)   :", len(session.task_graph.steps))
        info("state_matrix total_tokens           :", session.state_matrix.total_tokens)

        assert session.session_id, "session_id must not be empty"
        assert len(session.session_id) == 36, "session_id must be a UUID4 (36 chars with hyphens)"
        assert session.objective == objective
        assert session.version == "1.0.0"
        assert session.checkpoint_meta.lsn == 0
        assert session.task_graph.steps == []

        divider()
        step("Checking __repr__ output:")
        print(f"   {MAGENTA}{repr(session)}{RESET}")

        success("SessionState created successfully with all identity fields correct.")


# ==============================================================================
# TEST 3 — TaskStatus Enum Serialization
# ==============================================================================

class TestTaskStatusEnum:
    """Verify that TaskStatus serializes correctly as plain JSON strings."""

    def test_enum_values_are_strings(self) -> None:
        banner("TEST 3 — TaskStatus Enum Serialization")

        step("Verifying all four TaskStatus enum members and their JSON representations...")
        divider()

        for status in TaskStatus:
            info(f"TaskStatus.{status.name}", f"→ JSON value = \"{status.value}\"")
            assert isinstance(status.value, str), f"{status.name} must serialize as a string"
            assert status.value == status.name, "Enum value must match its name exactly"

        divider()
        step("Creating a TaskStep and verifying status persists as string in JSON...")
        step_obj = TaskStep(step_id="test_step", description="A test step")
        serialized = step_obj.model_dump()

        info("Serialized status field type :", type(serialized["status"]).__name__)
        info("Serialized status value      :", serialized["status"])

        assert serialized["status"] == "PENDING", "Status must serialize as string 'PENDING'"
        success("All TaskStatus values serialize as plain JSON strings — no extra conversion needed.")


# ==============================================================================
# TEST 4 — TaskStep Lifecycle (mark_running, mark_success, mark_failed)
# ==============================================================================

class TestTaskStepLifecycle:
    """Verify that a TaskStep transitions correctly through all states."""

    def test_step_full_lifecycle(self) -> None:
        banner("TEST 4 — TaskStep Full Lifecycle Simulation")

        step_obj = TaskStep(
            step_id="step_001_analyze_code",
            description="Analyze the NALA codebase for architecture patterns",
        )

        divider()
        step("[Phase 1] Step just created. Checking initial state...")
        info("status      :", step_obj.status)
        info("started_at  :", step_obj.started_at)
        info("retries     :", step_obj.retries)
        assert step_obj.status == TaskStatus.PENDING

        divider()
        step("[Phase 2] Marking step as RUNNING...")
        step_obj.mark_running()
        info("status      :", step_obj.status)
        info("started_at  :", step_obj.started_at.isoformat() if step_obj.started_at else None)
        assert step_obj.status == TaskStatus.RUNNING
        assert step_obj.started_at is not None
        assert step_obj.started_at.tzinfo is not None, "started_at must be UTC-aware"

        divider()
        step("[Phase 3] Marking step as SUCCESS with result payload...")
        result_data = {
            "files_analyzed"   : 47,
            "patterns_found"   : ["Singleton", "Observer", "Factory"],
            "report_path"      : "/output/arch_report.md",
        }
        step_obj.mark_success(result=result_data)

        info("status       :", step_obj.status)
        info("completed_at :", step_obj.completed_at.isoformat() if step_obj.completed_at else None)
        step("Result payload stored:")
        show_json(step_obj.result)

        assert step_obj.status == TaskStatus.SUCCESS
        assert step_obj.result == result_data
        assert step_obj.completed_at is not None

        divider()
        step("[Phase 4] Simulating a separate FAILED step...")
        failed_step = TaskStep(step_id="step_002_bad_step", description="A step that fails")
        failed_step.mark_running()
        failed_step.mark_failed(error="ConnectionError: LLM API timed out after 30s")

        info("status        :", failed_step.status)
        info("error_message :", failed_step.error_message)
        info("retries       :", failed_step.retries)
        assert failed_step.status == TaskStatus.FAILED
        assert failed_step.retries == 1

        success("TaskStep lifecycle (PENDING → RUNNING → SUCCESS / FAILED) verified.")


# ==============================================================================
# TEST 5 — TaskGraph: Topological Scheduler
# ==============================================================================

class TestTaskGraphScheduler:
    """Verify the topological step scheduler correctly handles all dependency scenarios."""

    def _build_multi_step_graph(self) -> TaskGraph:
        """Helper: Build a realistic 5-step task graph with branching dependencies."""
        return TaskGraph(steps=[
            TaskStep(step_id="s1_read_files",    description="Read all project files",           dependencies=[]),
            TaskStep(step_id="s2_parse_code",    description="Parse code into AST",              dependencies=["s1_read_files"]),
            TaskStep(step_id="s3_analyze_arch",  description="Analyze architecture patterns",    dependencies=["s2_parse_code"]),
            TaskStep(step_id="s4_write_report",  description="Write architecture report to disk", dependencies=["s3_analyze_arch"]),
            TaskStep(step_id="s5_notify_user",   description="Notify user of completion",        dependencies=["s4_write_report"]),
        ])

    def test_scheduler_linear_pipeline(self) -> None:
        banner("TEST 5a — TaskGraph: Linear Pipeline Scheduler")

        graph = self._build_multi_step_graph()
        step("Built 5-step linear pipeline. Simulating execution...")
        divider()

        completed = []
        iteration = 0

        while not graph.is_complete() and iteration < 10:
            iteration += 1
            summary = graph.get_summary()
            print(
                f"  {MAGENTA}[Tick {iteration:02d}]{RESET} "
                f"Progress: {YELLOW}{summary['progress_percent']}%{RESET} | "
                f"Pending: {summary['pending']} | "
                f"Success: {summary['success']}"
            )

            next_step = graph.get_next_pending_step()
            if next_step is None:
                print(f"  {RED}No step schedulable — graph is blocked!{RESET}")
                break

            step(f"Scheduling step: '{next_step.step_id}'")
            next_step.mark_running()
            next_step.mark_success(result={"completed_at": utcnow().isoformat()})
            graph.current_step_id = next_step.step_id
            completed.append(next_step.step_id)

        divider()
        info("Execution order  :", " → ".join(completed))
        info("is_complete()    :", graph.is_complete())
        info("progress_percent :", graph.progress_percent())

        assert graph.is_complete()
        assert graph.progress_percent() == 100.0
        assert completed == ["s1_read_files", "s2_parse_code", "s3_analyze_arch", "s4_write_report", "s5_notify_user"]
        success("Linear pipeline executed in correct topological order.")

    def test_scheduler_blocks_on_pending_dependencies(self) -> None:
        banner("TEST 5b — TaskGraph: Dependency Blocking")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="First step", status=TaskStatus.RUNNING),
            TaskStep(step_id="step_B", description="Blocked step", dependencies=["step_A"]),
        ])

        step("step_A is RUNNING. step_B depends on it.")
        next_step = graph.get_next_pending_step()
        info("get_next_pending_step() returned :", next_step)
        assert next_step is None, "step_B must NOT be scheduled while step_A is still RUNNING"
        success("Scheduler correctly blocked step_B while step_A was RUNNING.")

    def test_scheduler_unblocks_after_dependency_success(self) -> None:
        banner("TEST 5c — TaskGraph: Dependency Unblocking")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="First step",   status=TaskStatus.SUCCESS),
            TaskStep(step_id="step_B", description="Blocked step", dependencies=["step_A"]),
        ])

        step("step_A just reached SUCCESS. Checking if step_B unblocks...")
        next_step = graph.get_next_pending_step()
        info("get_next_pending_step() returned :", next_step.step_id if next_step else None)
        assert next_step is not None
        assert next_step.step_id == "step_B"
        success("Scheduler correctly unblocked step_B after step_A reached SUCCESS.")

    def test_is_blocked_detection(self) -> None:
        banner("TEST 5d — TaskGraph: Blocked Graph Detection")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="Failed step",   status=TaskStatus.FAILED),
            TaskStep(step_id="step_B", description="Waiting step",  dependencies=["step_A"]),
        ])

        step("step_A is FAILED. step_B depends on it but can never succeed.")
        info("is_blocked()  :", graph.is_blocked())
        info("has_failed()  :", graph.has_failed())
        info("is_complete() :", graph.is_complete())
        assert graph.is_blocked(), "Graph must report as BLOCKED when a required dep has FAILED"
        success("is_blocked() correctly detected a permanently blocked graph.")


# ==============================================================================
# TEST 6 — Circular Dependency Detection (DFS)
# ==============================================================================

class TestCircularDependencyDetection:
    """Verify the DFS-based cycle detector catches all circular dependency patterns."""

    def test_direct_circular_dependency(self) -> None:
        banner("TEST 6a — Circular Dependency: Direct Cycle (A → B → A)")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="Step A", dependencies=["step_B"]),
            TaskStep(step_id="step_B", description="Step B", dependencies=["step_A"]),
        ])

        step("Checking if DFS detects the A → B → A cycle...")
        has_cycle = graph.has_circular_dependency()
        info("has_circular_dependency() :", has_cycle)
        assert has_cycle is True
        success("DFS correctly detected direct circular dependency A → B → A.")

    def test_indirect_circular_dependency(self) -> None:
        banner("TEST 6b — Circular Dependency: Indirect Cycle (A → B → C → A)")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="Step A", dependencies=["step_C"]),
            TaskStep(step_id="step_B", description="Step B", dependencies=["step_A"]),
            TaskStep(step_id="step_C", description="Step C", dependencies=["step_B"]),
        ])

        step("Checking A → B → C → A indirect cycle...")
        has_cycle = graph.has_circular_dependency()
        info("has_circular_dependency() :", has_cycle)
        assert has_cycle is True
        success("DFS correctly detected indirect circular dependency A → B → C → A.")

    def test_no_cycle_in_valid_graph(self) -> None:
        banner("TEST 6c — Circular Dependency: Clean Graph (No Cycles)")

        graph = TaskGraph(steps=[
            TaskStep(step_id="step_A", description="Step A", dependencies=[]),
            TaskStep(step_id="step_B", description="Step B", dependencies=["step_A"]),
            TaskStep(step_id="step_C", description="Step C", dependencies=["step_A", "step_B"]),
        ])

        step("Verifying a correctly structured DAG has no cycles...")
        has_cycle = graph.has_circular_dependency()
        info("has_circular_dependency() :", has_cycle)
        assert has_cycle is False
        success("DFS correctly confirmed no cycles in a valid DAG.")

    def test_validate_task_graph_raises_on_cycle(self) -> None:
        banner("TEST 6d — validate_task_graph(): Raises ValueError on Circular Dependency")

        session = SessionState(
            objective="Test circular dependency rejection",
            task_graph=TaskGraph(steps=[
                TaskStep(step_id="step_A", description="A", dependencies=["step_B"]),
                TaskStep(step_id="step_B", description="B", dependencies=["step_A"]),
            ]),
        )
        step("Calling session.validate_task_graph() — expecting ValueError...")
        with pytest.raises(ValueError, match="circular dependency"):
            session.validate_task_graph()
        success("ValueError raised correctly — NALA refused to run a cyclic task graph.")

    def test_validate_task_graph_raises_on_missing_dep(self) -> None:
        banner("TEST 6e — validate_task_graph(): Raises on Ghost Dependency")

        session = SessionState(
            objective="Test ghost dependency rejection",
            task_graph=TaskGraph(steps=[
                TaskStep(step_id="step_1", description="A", dependencies=["ghost_step_99"]),
            ]),
        )
        step("Calling session.validate_task_graph() — expecting ValueError for 'ghost_step_99'...")
        with pytest.raises(ValueError, match="does not exist in the TaskGraph"):
            session.validate_task_graph()
        success("ValueError raised correctly — NALA rejected a dependency on a non-existent step.")


# ==============================================================================
# TEST 7 — Serialization & Deserialization (Round-Trip)
# ==============================================================================

class TestSerializationRoundTrip:
    """Verify that serialize() and deserialize() produce identical objects."""

    def test_full_round_trip_serialization(self) -> None:
        banner("TEST 7 — Full Session Round-Trip Serialization")

        original = SessionState(
            objective="Build the NALA checkpoint system (JIRA-002)",
            task_graph=TaskGraph(steps=[
                TaskStep(step_id="s1", description="Design checkpoint schema",      dependencies=[]),
                TaskStep(step_id="s2", description="Implement write_checkpoint()",  dependencies=["s1"], status=TaskStatus.SUCCESS),
                TaskStep(step_id="s3", description="Implement load_checkpoint()",   dependencies=["s1"]),
            ]),
            metadata={"jira_ticket": "JIRA-002", "sprint": "Sprint-1"},
        )
        original.state_matrix.add_llm_call(tokens_in=2048, tokens_out=512, cost_usd=0.00314)

        divider()
        step("[Step 1] Serializing SessionState to JSON...")
        json_str = original.serialize()
        parsed_json = json.loads(json_str)

        info("JSON character count          :", len(json_str))
        info("session_id preserved          :", parsed_json["session_id"])
        info("objective preserved           :", parsed_json["objective"][:50])
        info("task_graph steps count        :", len(parsed_json["task_graph"]["steps"]))
        info("state_matrix.total_tokens_in  :", parsed_json["state_matrix"]["total_tokens_in"])
        info("metadata.jira_ticket          :", parsed_json["metadata"]["jira_ticket"])

        divider()
        step("[Step 2] Deserializing JSON back into a SessionState object...")
        restored = SessionState.deserialize(json_str)

        info("Restored session_id           :", restored.session_id)
        info("Restored objective            :", restored.objective[:50])
        info("Restored step count           :", len(restored.task_graph.steps))
        info("Restored total_tokens_in      :", restored.state_matrix.total_tokens_in)
        info("Restored step[1] status       :", restored.task_graph.steps[1].status)

        divider()
        step("[Step 3] Verifying field-by-field equality between original and restored...")
        assert original.session_id           == restored.session_id
        assert original.objective            == restored.objective
        assert original.version              == restored.version
        assert len(original.task_graph.steps) == len(restored.task_graph.steps)
        assert original.state_matrix.total_tokens_in == restored.state_matrix.total_tokens_in
        assert original.state_matrix.estimated_cost  == restored.state_matrix.estimated_cost
        assert original.metadata["jira_ticket"]      == restored.metadata["jira_ticket"]
        assert restored.task_graph.steps[1].status   == TaskStatus.SUCCESS

        success("Round-trip serialization verified — original and restored objects are identical.")


# ==============================================================================
# TEST 8 — CheckpointMeta: SHA-256 Hash & LSN
# ==============================================================================

class TestCheckpointMeta:
    """Verify SHA-256 hash integrity and monotonic LSN behavior."""

    def test_sha256_hash_is_reproducible(self) -> None:
        banner("TEST 8a — CheckpointMeta: SHA-256 Hash Reproducibility")

        meta     = CheckpointMeta()
        payload  = '{"session_id": "abc-123", "objective": "Run NALA"}'

        step("Computing SHA-256 hash of the payload twice...")
        hash_1 = meta.compute_hash(payload)
        hash_2 = meta.compute_hash(payload)

        info("Hash attempt #1 :", hash_1)
        info("Hash attempt #2 :", hash_2)
        info("Hash length     :", len(hash_1), )
        info("Hashes match    :", hash_1 == hash_2)

        assert hash_1 == hash_2, "SHA-256 must be deterministic for the same input"
        assert len(hash_1) == 64, "SHA-256 hex digest must be 64 characters"
        success("SHA-256 hash is reproducible and deterministic.")

    def test_hash_detects_tampering(self) -> None:
        banner("TEST 8b — CheckpointMeta: Tamper Detection")

        meta            = CheckpointMeta()
        original_payload = '{"session_id": "abc-123", "step": "s1"}'
        tampered_payload = '{"session_id": "abc-123", "step": "s2"}'  # One character changed

        meta.content_hash = meta.compute_hash(original_payload)

        step("Verifying original payload against stored hash...")
        is_valid_original = meta.verify_hash(original_payload)
        info("verify_hash (original)   :", is_valid_original)
        assert is_valid_original is True

        step("Verifying tampered payload against stored hash...")
        is_valid_tampered = meta.verify_hash(tampered_payload)
        info("verify_hash (tampered)   :", is_valid_tampered)
        assert is_valid_tampered is False

        success("SHA-256 tamper detection works — corrupted checkpoint correctly rejected.")

    def test_lsn_increments_monotonically(self) -> None:
        banner("TEST 8c — CheckpointMeta: Monotonic LSN Sequence")

        session = SessionState(objective="Test LSN sequence over multiple checkpoints")
        divider()

        for i in range(1, 6):
            step(f"Preparing checkpoint #{i}...")
            checkpoint_json = session.prepare_checkpoint()
            info(f"  LSN after checkpoint #{i}    :", session.checkpoint_meta.lsn)
            info(f"  Timestamp                    :", session.checkpoint_meta.timestamp.isoformat())
            info(f"  Hash (first 20 chars)        :", session.checkpoint_meta.content_hash[:20] + "...")
            assert session.checkpoint_meta.lsn == i, f"LSN must be {i} after {i} checkpoints"
            time.sleep(0.01)  # Small delay to show timestamp progression

        success(f"LSN incremented monotonically from 1 to 5 across 5 checkpoints.")

    def test_verify_integrity_full_session(self) -> None:
        banner("TEST 8d — SessionState: End-to-End Checkpoint Integrity Verification")

        session = SessionState(objective="Full integrity test run")

        step("Preparing checkpoint (serializing + hashing + incrementing LSN)...")
        checkpoint_json = session.prepare_checkpoint()

        info("Checkpoint LSN       :", session.checkpoint_meta.lsn)
        info("Stored hash (20ch)   :", session.checkpoint_meta.content_hash[:20] + "...")

        divider()
        step("Verifying integrity of the saved checkpoint (simulating load from disk)...")
        is_intact = session.verify_integrity(checkpoint_json)
        info("verify_integrity()   :", is_intact)
        assert is_intact is True

        step("Simulating disk corruption (modifying one character)...")
        corrupted_json = checkpoint_json.replace('"1.0.0"', '"9.9.9"')
        is_corrupted = session.verify_integrity(corrupted_json)
        info("verify_integrity() on corrupted data :", is_corrupted)
        assert is_corrupted is False

        success("End-to-end integrity check: clean checkpoint verified, corrupted checkpoint rejected.")


# ==============================================================================
# TEST 9 — StateMatrix: Telemetry Tracking
# ==============================================================================

class TestStateMatrix:
    """Verify telemetry counters update correctly across multiple LLM calls."""

    def test_llm_call_telemetry(self) -> None:
        banner("TEST 9 — StateMatrix: LLM Call Telemetry")

        matrix = StateMatrix()
        divider()

        calls = [
            {"tokens_in": 1024, "tokens_out": 256,  "cost": 0.00102},
            {"tokens_in": 2048, "tokens_out": 512,  "cost": 0.00256},
            {"tokens_in": 512,  "tokens_out": 128,  "cost": 0.00051},
        ]

        for i, call in enumerate(calls, 1):
            step(f"Simulating LLM call #{i}...")
            matrix.add_llm_call(
                tokens_in=call["tokens_in"],
                tokens_out=call["tokens_out"],
                cost_usd=call["cost"],
            )
            info(f"  Running total_tokens_in  :", matrix.total_tokens_in)
            info(f"  Running total_tokens_out :", matrix.total_tokens_out)
            info(f"  Running estimated_cost   :", f"${matrix.estimated_cost:.6f}")

        divider()
        step("Simulating 3 errors during the run...")
        for _ in range(3):
            matrix.record_error()
        matrix.active_agents = ["Planner", "Executor", "Verifier"]
        matrix.elapsed_seconds = 142.7
        matrix.peak_memory_mb = 387.4

        step("Final telemetry summary:")
        summary = matrix.get_summary()
        show_json(summary)

        assert matrix.total_tokens_in  == 3584
        assert matrix.total_tokens_out == 896
        assert matrix.total_tokens     == 4480
        assert matrix.error_count      == 3
        assert len(matrix.active_agents) == 3

        success("StateMatrix telemetry accumulated correctly across 3 LLM calls and 3 errors.")


# ==============================================================================
# TEST 10 — UTC Timezone Safety
# ==============================================================================

class TestDatetimeUTCSafety:
    """Verify that all datetimes are UTC-aware and naive inputs are auto-healed."""

    def test_session_timestamps_are_utc_aware(self) -> None:
        banner("TEST 10a — UTC Safety: SessionState Auto-generates UTC-Aware Timestamps")

        session = SessionState(objective="Timezone safety check")

        info("created_at tzinfo    :", session.created_at.tzinfo)
        info("last_updated tzinfo  :", session.last_updated.tzinfo)
        info("created_at ISO       :", session.created_at.isoformat())

        assert session.created_at.tzinfo is not None,   "created_at must be UTC-aware"
        assert session.last_updated.tzinfo is not None, "last_updated must be UTC-aware"
        success("SessionState auto-generates UTC-aware timestamps.")

    def test_checkpoint_timestamp_is_utc_aware(self) -> None:
        banner("TEST 10b — UTC Safety: CheckpointMeta Auto-generates UTC-Aware Timestamp")

        meta = CheckpointMeta()
        info("timestamp tzinfo :", meta.timestamp.tzinfo)
        info("timestamp ISO    :", meta.timestamp.isoformat())
        assert meta.timestamp.tzinfo is not None, "CheckpointMeta.timestamp must be UTC-aware"
        success("CheckpointMeta auto-generates UTC-aware timestamp.")

    def test_naive_datetime_is_auto_corrected(self) -> None:
        banner("TEST 10c — UTC Safety: Naive Datetime Auto-Healed by Pydantic Validator")

        naive_time = datetime(2026, 6, 10, 8, 0, 0)  # No timezone
        step(f"Passing naive datetime: {naive_time} (tzinfo={naive_time.tzinfo})")

        session = SessionState(objective="Auto-heal test", created_at=naive_time)

        info("created_at tzinfo after healing :", session.created_at.tzinfo)
        info("created_at ISO after healing    :", session.created_at.isoformat())

        assert session.created_at.tzinfo is not None, \
            "Pydantic validator must auto-attach UTC timezone to naive datetimes"
        success("Naive datetime auto-healed — UTC timezone attached automatically by validator.")

    def test_utcnow_returns_aware_datetime(self) -> None:
        banner("TEST 10d — UTC Safety: utcnow() Helper Returns Aware Datetime")

        now = utcnow()
        info("utcnow() result  :", now.isoformat())
        info("tzinfo           :", now.tzinfo)
        assert now.tzinfo is not None, "utcnow() must always return a UTC-aware datetime"
        success("utcnow() helper correctly returns a UTC-aware datetime.")


# ==============================================================================
# TEST 11 — Input Validation & Error Handling
# ==============================================================================

class TestValidationErrors:
    """Verify that invalid inputs are caught by Pydantic and raise clear errors."""

    def test_empty_objective_raises_error(self) -> None:
        banner("TEST 11a — Validation: Empty Objective Rejected")

        step("Attempting to create SessionState with empty objective...")
        with pytest.raises(ValidationError) as exc_info:
            SessionState(objective="")
        info("ValidationError raised :", "YES")
        info("Error location         :", str(exc_info.value.errors()[0]["loc"]))
        success("Empty objective correctly rejected with ValidationError.")

    def test_negative_retries_rejected(self) -> None:
        banner("TEST 11b — Validation: Negative retries Count Rejected")

        step("Attempting to create TaskStep with retries=-1...")
        with pytest.raises(ValidationError) as exc_info:
            TaskStep(step_id="s1", description="Bad step", retries=-1)
        info("ValidationError raised :", "YES")
        info("Error location         :", str(exc_info.value.errors()[0]["loc"]))
        success("Negative retries value correctly rejected by Pydantic ge=0 constraint.")

    def test_negative_lsn_rejected(self) -> None:
        banner("TEST 11c — Validation: Negative LSN Rejected")

        step("Attempting to create CheckpointMeta with lsn=-5...")
        with pytest.raises(ValidationError):
            CheckpointMeta(lsn=-5)
        success("Negative LSN correctly rejected by Pydantic ge=0 constraint.")


# ==============================================================================
# TEST 12 — Full Integration: A Complete NALA Session Lifecycle
# ==============================================================================

class TestFullSessionLifecycle:
    """Simulate a complete, realistic NALA session from creation to completion."""

    def test_complete_nala_session_lifecycle(self) -> None:
        banner("TEST 12 — FULL INTEGRATION: Complete NALA Session Lifecycle Simulation")

        print(f"\n  {BOLD}Simulating a real NALA session running JIRA-002...{RESET}\n")

        # ── Phase 1: Create session ────────────────────────────────────────
        step("[Phase 1] Creating session...")
        session = SessionState(
            objective="Implement the NALA Checkpoint System as defined in JIRA-002",
            task_graph=TaskGraph(steps=[
                TaskStep(step_id="s1_design",    description="Design checkpoint file schema",   dependencies=[]),
                TaskStep(step_id="s2_write",     description="Write write_checkpoint() method", dependencies=["s1_design"]),
                TaskStep(step_id="s3_load",      description="Write load_checkpoint() method",  dependencies=["s1_design"]),
                TaskStep(step_id="s4_test",      description="Write unit tests",                dependencies=["s2_write", "s3_load"]),
                TaskStep(step_id="s5_integrate", description="Integrate with run_loop()",       dependencies=["s4_test"]),
            ]),
            metadata={"jira": "JIRA-002", "phase": "Phase-1"},
        )
        session.validate_task_graph()
        info("Session created & validated  :", session.session_id[:18] + "...")
        info("Steps in plan                :", len(session.task_graph.steps))

        # ── Phase 2: Save initial checkpoint ─────────────────────────────
        step("\n[Phase 2] Saving initial checkpoint (LSN 0 → 1)...")
        checkpoint_1 = session.prepare_checkpoint()
        info("Checkpoint LSN      :", session.checkpoint_meta.lsn)
        info("JSON size (bytes)   :", len(checkpoint_1.encode()))

        # ── Phase 3: Execute all steps ────────────────────────────────────
        step("\n[Phase 3] Executing all 5 steps via topological scheduler...")
        executed_order = []
        iteration = 0

        while not session.task_graph.is_complete():
            iteration += 1
            next_step = session.task_graph.get_next_pending_step()
            assert next_step is not None, f"Graph blocked unexpectedly at iteration {iteration}"

            next_step.mark_running()
            session.state_matrix.add_llm_call(tokens_in=800, tokens_out=200, cost_usd=0.0012)
            next_step.mark_success(result={"iteration": iteration, "artifact": f"{next_step.step_id}_output"})
            session.task_graph.current_step_id = next_step.step_id
            executed_order.append(next_step.step_id)

            print(
                f"    {GREEN}✓{RESET} Step {iteration} completed: "
                f"{YELLOW}{next_step.step_id}{RESET} "
                f"({session.task_graph.progress_percent()}%)"
            )

        # ── Phase 4: Save final checkpoint ────────────────────────────────
        step("\n[Phase 4] Saving final checkpoint...")
        checkpoint_2 = session.prepare_checkpoint()
        info("Final LSN           :", session.checkpoint_meta.lsn)

        # ── Phase 5: Full integrity verification ──────────────────────────
        step("\n[Phase 5] Verifying checkpoint integrity...")
        is_clean = session.verify_integrity(checkpoint_2)
        info("Integrity check     :", "✅ CLEAN" if is_clean else "❌ CORRUPTED")
        assert is_clean

        # ── Phase 6: Deserialize to simulate recovery ─────────────────────
        step("\n[Phase 6] Simulating crash recovery — deserializing from checkpoint...")
        recovered = SessionState.deserialize(checkpoint_2)
        info("Recovered session_id :", recovered.session_id[:18] + "...")
        info("Recovered is_complete:", recovered.task_graph.is_complete())
        info("Recovered LSN        :", recovered.checkpoint_meta.lsn)

        # ── Phase 7: Final assertions ──────────────────────────────────────
        divider()
        step("[Phase 7] Running final assertions...")

        assert session.task_graph.is_complete()
        assert session.task_graph.progress_percent() == 100.0
        assert session.checkpoint_meta.lsn == 2
        assert recovered.session_id == session.session_id
        assert recovered.task_graph.is_complete()
        assert session.state_matrix.total_tokens_in == 4000  # 5 steps × 800

        divider()
        step("Final session summary:")
        show_json(session.get_summary())

        success("FULL NALA SESSION LIFECYCLE SIMULATION COMPLETED SUCCESSFULLY! 🚀")


# ==============================================================================
# STANDALONE DEMO RUNNER — Run directly without pytest
# ==============================================================================

if __name__ == "__main__":
    print(f"\n{BOLD}{MAGENTA}")
    print("  ███╗   ██╗ █████╗ ██╗      █████╗ ")
    print("  ████╗  ██║██╔══██╗██║     ██╔══██╗")
    print("  ██╔██╗ ██║███████║██║     ███████║")
    print("  ██║╚██╗██║██╔══██║██║     ██╔══██║")
    print("  ██║ ╚████║██║  ██║███████╗██║  ██║")
    print("  ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")
    print(f"  {BOLD}Session Contract — Unit Test Suite{RESET}")
    print(f"  {DIM}Nexus Lab AI Research Lab | Bengaluru{RESET}\n")

    test_classes = [
        TestEnvironmentGuard(),
        TestSessionCreation(),
        TestTaskStatusEnum(),
        TestTaskStepLifecycle(),
        TestTaskGraphScheduler(),
        TestCircularDependencyDetection(),
        TestSerializationRoundTrip(),
        TestCheckpointMeta(),
        TestStateMatrix(),
        TestDatetimeUTCSafety(),
        TestValidationErrors(),
        TestFullSessionLifecycle(),
    ]

    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        for method_name in methods:
            try:
                getattr(cls, method_name)()
                passed += 1
            except Exception as e:
                failed += 1
                errors.append((f"{cls.__class__.__name__}.{method_name}", str(e)))
                print(f"\n  {RED}❌ FAILED: {cls.__class__.__name__}.{method_name}{RESET}")
                print(f"     {RED}{e}{RESET}")

    # Final summary
    width = 70
    print(f"\n{BOLD}{'═' * width}{RESET}")
    print(f"{BOLD}  📊 TEST RESULTS SUMMARY{RESET}")
    print(f"{'═' * width}")
    print(f"  {GREEN}✅ Passed : {passed}{RESET}")
    print(f"  {RED}❌ Failed : {failed}{RESET}")
    print(f"  {'─' * 66}")
    if failed == 0:
        print(f"  {BOLD}{GREEN}ALL TESTS PASSED — JIRA-001 Definition of Done: COMPLETE ✅{RESET}")
    else:
        print(f"  {BOLD}{RED}SOME TESTS FAILED — Review errors above before proceeding.{RESET}")
        for test_name, err in errors:
            print(f"  {RED}  • {test_name}: {err}{RESET}")
    print(f"{BOLD}{'═' * width}{RESET}\n")
    print(f"  {DIM}Jai Bajrang Bali 🙏{RESET}\n")

    sys.exit(0 if failed == 0 else 1)
