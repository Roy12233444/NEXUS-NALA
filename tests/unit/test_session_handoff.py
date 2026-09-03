"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/unit/test_session_handoff.py
Ticket  : JIRA-006 — Add Session Handoff File (Test Suite)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
Interactive unit and integration tests for core/harness/session_handoff.py.

These tests display a detailed internal trace of each handoff, checkpoint validation,
and session recovery lifecycle in real time with styled ANSI terminal outputs.

HOW TO RUN
----------
    # Run via pytest:
    pytest tests/unit/test_session_handoff.py -v -s --tb=short

    # Or run directly as a standalone demo:
    python tests/unit/test_session_handoff.py

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import io
import json
import logging
import pathlib
import sys
import uuid
import tempfile
import shutil
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pydantic
import pytest
import tiktoken

# ── Force UTF-8 output on Windows consoles ───────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Add NALA project root to sys.path ────────────────────────────────────────
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── NALA harness imports ──────────────────────────────────────────────────────
from core.harness.session_contract import (
    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)
from core.harness.checkpoint import CheckpointManager
from core.harness.context_tracker import ContextStatus, ContextTracker, TrackerConfig
from core.harness.session_handoff import (
    ContextExhaustedSignal,
    HandoffSpore,
    HandoffSporeModel,
    SporeTaskGraphSummary,
    SporeTelemetry,
    SporeValidationError,
)
from core.harness.nala_loop import NalaLoop, LoopStatus, StepResult
from core.harness.recovery import recover_session


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
    width = 75
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
    print(f"  {DIM}{'─' * 71}{RESET}")


# ==============================================================================
# SUT HELPERS & FACTORIES
# ==============================================================================

def _enc() -> tiktoken.Encoding:
    """Return the cl100k_base tokenizer encoding used for token-count helpers."""
    return tiktoken.get_encoding("cl100k_base")


def _exact_token_text(n: int) -> str:
    """Generate a string that tiktoken decodes/re-encodes to EXACTLY ``n`` tokens."""
    enc = _enc()
    source_ids = enc.encode("nexus " * (n + 50), disallowed_special=())
    return enc.decode(source_ids[:n])


def _make_step(step_id: str, description: str = "", status: TaskStatus = TaskStatus.PENDING,
               result: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None,
               ) -> TaskStep:
    """Build a fully-configured TaskStep for test setup."""
    step_obj = TaskStep(step_id=step_id, description=description or f"Description for {step_id}")
    if status == TaskStatus.SUCCESS:
        step_obj.mark_running()
        step_obj.mark_success(result or {"ok": True})
    elif status == TaskStatus.FAILED:
        step_obj.mark_running()
        step_obj.mark_failed(error_message or "test error")
    elif status == TaskStatus.RUNNING:
        step_obj.mark_running()
    return step_obj


def _build_session_with_n_steps(n: int, objective: str = "Verify handoff continuity") -> SessionState:
    """Build a SessionState with n steps all in PENDING status."""
    steps = [
        TaskStep(step_id=f"step_{i:03d}", description=f"Task step number {i}")
        for i in range(1, n + 1)
    ]
    return SessionState(objective=objective, task_graph=TaskGraph(steps=steps))


def _build_mixed_session(
    success_results: List[Dict[str, Any]],
    failed_errors: List[str],
    n_pending: int = 2,
) -> SessionState:
    """
    Build a SessionState whose task graph has:
      - len(success_results) SUCCESS steps with given result payloads.
      - len(failed_errors) FAILED steps with given error messages.
      - n_pending PENDING steps after those.
    """
    steps: List[TaskStep] = []
    idx = 1

    for res in success_results:
        steps.append(_make_step(f"step_{idx:03d}", status=TaskStatus.SUCCESS, result=res))
        idx += 1

    for err in failed_errors:
        steps.append(_make_step(f"step_{idx:03d}", status=TaskStatus.FAILED, error_message=err))
        idx += 1

    for _ in range(n_pending):
        steps.append(_make_step(f"step_{idx:03d}", status=TaskStatus.PENDING))
        idx += 1

    return SessionState(
        objective="Mixed session for handoff testing",
        task_graph=TaskGraph(steps=steps),
    )


def _write_valid_spore_file(path: Path, session: SessionState) -> HandoffSporeModel:
    """Helper: call HandoffSpore.write_spore() writing to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return HandoffSpore.write_spore(
        session,
        path,
        handoff_reason="unit-test handoff",
        checkpoint_path="/tmp/test_checkpoint.json",
    )


def _build_minimal_spore_model_dict() -> Dict[str, Any]:
    """Build a minimal valid dict that can instantiate HandoffSporeModel."""
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    return {
        "spore_version": "2.0.0",
        "original_session_id": str(uuid.uuid4()),
        "new_session_id": str(uuid.uuid4()),
        "objective": "Test objective",
        "handoff_timestamp": now_iso,
        "handoff_reason": "unit-test",
        "checkpoint_path": "/tmp/cp.json",
        "task_graph_state": {
            "total_steps": 3,
            "completed_steps": 1,
            "failed_steps": 0,
            "pending_steps": 2,
            "crystallized_history": "[step_001] SUCCESS — did something",
            "remaining_steps": [],
            "last_completed_step_id": "step_001",
        },
        "telemetry_state": {
            "total_tokens_in": 1000,
            "total_tokens_out": 500,
            "estimated_cost_usd": 0.000123,
            "error_count": 0,
            "elapsed_seconds": 42.5,
            "session_lsn": 7,
        },
        "active_variables": {"key_a": "val_a"},
        "done_condition": None,
        "bootstrap_instructions": "Resume at step_002.",
    }


# ==============================================================================
# T01–T02 — ContextExhaustedSignal Tests
# ==============================================================================

class TestContextExhaustedSignal:

    def test_T01_attributes_stored_correctly(self, tmp_path):
        """T01: ContextExhaustedSignal stores session_id, projected_tokens, spore_path."""
        banner("TEST T01 — ContextExhaustedSignal Attributes Storage")
        fake_path = tmp_path / "handoff.spore.json"
        sid = "abc-123"
        projected = 98_765

        step("Instantiating ContextExhaustedSignal...")
        sig = ContextExhaustedSignal(
            session_id=sid,
            projected_tokens=projected,
            spore_path=fake_path,
        )

        info("session_id", sig.session_id)
        info("projected_tokens", sig.projected_tokens)
        info("spore_path", sig.spore_path)

        assert sig.session_id == sid
        assert sig.projected_tokens == projected
        assert sig.spore_path == fake_path
        success("Attributes verified successfully.")

    def test_T02_message_contains_token_count_formatted(self, tmp_path):
        """T02: __str__ contains the projected token count with thousands separator."""
        banner("TEST T02 — ContextExhaustedSignal Message Formatting")
        sig = ContextExhaustedSignal(
            session_id="s1",
            projected_tokens=120_000,
            spore_path=tmp_path / "x.json",
        )
        msg = str(sig)
        info("Exception string representation", msg)

        assert "120,000" in msg
        assert "Context EXHAUSTED" in msg
        success("Pretty-printed token count found in error message.")

    def test_is_runtime_error_not_just_exception(self, tmp_path):
        """T02-extra: Signal must be RuntimeError to avoid generic swallowing."""
        banner("TEST T02-Extra — ContextExhaustedSignal Exception Hierarchy")
        sig = ContextExhaustedSignal("s", 1, tmp_path / "f.json")
        info("Is instance of RuntimeError", isinstance(sig, RuntimeError))
        assert isinstance(sig, RuntimeError)
        success("Signal successfully inherits from RuntimeError.")


# ==============================================================================
# T03–T04 — SporeValidationError Tests
# ==============================================================================

class TestSporeValidationError:

    def test_T03_attributes_with_path(self, tmp_path):
        """T03: SporeValidationError stores reason and path; formats message with path."""
        banner("TEST T03 — SporeValidationError with Path")
        p = tmp_path / "broken.spore.json"
        err = SporeValidationError(reason="Schema drift detected", path=p)

        info("reason", err.reason)
        info("path", err.path)
        info("formatted message", str(err))

        assert err.reason == "Schema drift detected"
        assert err.path == p
        assert str(p) in str(err)
        assert "Schema drift detected" in str(err)
        success("Validation error formatted with path correctly.")

    def test_T04_attributes_without_path(self):
        """T04: SporeValidationError omits path segment in message when path=None."""
        banner("TEST T04 — SporeValidationError without Path")
        err = SporeValidationError(reason="Empty file")

        info("reason", err.reason)
        info("path", err.path)
        info("formatted message", str(err))

        assert err.path is None
        msg = str(err)
        assert "Empty file" in msg
        assert "at '" not in msg
        success("Validation error formatted without path correctly.")

    def test_is_value_error_subclass(self):
        """SporeValidationError must be a ValueError subclass."""
        banner("TEST T04-Extra — SporeValidationError Hierarchy")
        err = SporeValidationError("test")
        assert isinstance(err, ValueError)
        success("Subclass of ValueError confirmed.")


# ==============================================================================
# T05–T09 — Pydantic v2 Model Tests
# ==============================================================================

class TestSporeTaskGraphSummary:

    def test_T05_construction_and_last_step_default(self):
        """T05: SporeTaskGraphSummary constructs correctly; last_completed_step_id defaults None."""
        banner("TEST T05 — SporeTaskGraphSummary Creation & Defaults")
        summary = SporeTaskGraphSummary(
            total_steps=5,
            completed_steps=3,
            failed_steps=1,
            pending_steps=1,
            crystallized_history="[s1] SUCCESS — did X || [s2] FAILED — err",
            remaining_steps=[{"step_id": "step_005"}],
        )
        info("total_steps", summary.total_steps)
        info("completed_steps", summary.completed_steps)
        info("failed_steps", summary.failed_steps)
        info("last_completed_step_id (default)", summary.last_completed_step_id)

        assert summary.total_steps == 5
        assert summary.completed_steps == 3
        assert summary.failed_steps == 1
        assert summary.pending_steps == 1
        assert "SUCCESS" in summary.crystallized_history
        assert len(summary.remaining_steps) == 1
        assert summary.last_completed_step_id is None
        success("Defaults verified successfully.")

    def test_last_completed_step_id_when_set(self):
        """last_completed_step_id is stored when explicitly provided."""
        banner("TEST T05-Extra — SporeTaskGraphSummary Set Completed ID")
        summary = SporeTaskGraphSummary(
            total_steps=2, completed_steps=1, failed_steps=0,
            pending_steps=1, crystallized_history="x", remaining_steps=[],
            last_completed_step_id="step_001",
        )
        info("last_completed_step_id (set)", summary.last_completed_step_id)
        assert summary.last_completed_step_id == "step_001"
        success("Completed ID successfully loaded.")


class TestSporeTelemetry:

    def test_T06_construction_preserves_precision(self):
        """T06: SporeTelemetry stores all 6 fields with float precision intact."""
        banner("TEST T06 — SporeTelemetry Field Precision")
        telem = SporeTelemetry(
            total_tokens_in=48_720,
            total_tokens_out=12_345,
            estimated_cost_usd=0.001234567,
            error_count=2,
            elapsed_seconds=3601.789,
            session_lsn=42,
        )
        info("estimated_cost_usd", telem.estimated_cost_usd)
        info("elapsed_seconds", telem.elapsed_seconds)

        assert telem.total_tokens_in == 48_720
        assert telem.total_tokens_out == 12_345
        assert abs(telem.estimated_cost_usd - 0.001234567) < 1e-9
        assert telem.error_count == 2
        assert abs(telem.elapsed_seconds - 3601.789) < 1e-6
        assert telem.session_lsn == 42
        success("Float precision parameters matches inputs.")


class TestHandoffSporeModel:

    def test_T07_default_version_is_2_0_0(self):
        """T07: HandoffSporeModel defaults spore_version to '2.0.0'."""
        banner("TEST T07 — HandoffSporeModel Version Check")
        data = _build_minimal_spore_model_dict()
        model = HandoffSporeModel(**data)
        info("spore_version", model.spore_version)
        assert model.spore_version == "2.0.0"
        success("Default spore version is 2.0.0.")

    def test_T08_extra_fields_forbidden(self):
        """T08: extra='forbid' raises ValidationError for unknown JSON field (RISK-020)."""
        banner("TEST T08 — Extra Fields Forbidden in Spore Model")
        data = _build_minimal_spore_model_dict()
        data["unexpected_field"] = "hacker injection"
        step("Attempting model instantiation with unexpected field...")
        with pytest.raises(pydantic.ValidationError, match="unexpected_field") as exc_info:
            HandoffSporeModel(**data)
        info("Pydantic Validation Error caught", str(exc_info.value)[:80] + "...")
        success("Validation correctly blocked extra field injections.")

    def test_T09_full_json_round_trip(self):
        """T09: model_dump_json() ↔ model_validate_json() preserves all 12 fields exactly."""
        banner("TEST T09 — Spore Model JSON Round-Trip")
        data = _build_minimal_spore_model_dict()
        model = HandoffSporeModel(**data)
        step("Serializing to JSON...")
        json_str = model.model_dump_json(indent=2)
        print("  " + DIM + "--- Serialized Spore Output snippet ---" + RESET)
        for line in json_str.splitlines()[:6]:
            print(f"  {DIM}{line}{RESET}")
        print("  " + DIM + "... (remainder truncated) ..." + RESET)

        step("Deserializing from JSON...")
        reloaded = HandoffSporeModel.model_validate_json(json_str)

        assert reloaded.spore_version == model.spore_version
        assert reloaded.original_session_id == model.original_session_id
        assert reloaded.new_session_id == model.new_session_id
        assert reloaded.objective == model.objective
        assert reloaded.handoff_reason == model.handoff_reason
        assert reloaded.checkpoint_path == model.checkpoint_path
        assert reloaded.bootstrap_instructions == model.bootstrap_instructions
        assert reloaded.done_condition == model.done_condition
        assert reloaded.active_variables == model.active_variables
        assert reloaded.telemetry_state.session_lsn == model.telemetry_state.session_lsn
        assert reloaded.task_graph_state.total_steps == model.task_graph_state.total_steps
        assert reloaded.task_graph_state.crystallized_history == model.task_graph_state.crystallized_history
        success("Roundtrip serialization preserved all data formats.")

    def test_handoff_timestamp_is_utc_aware(self):
        """handoff_timestamp round-trips with timezone info preserved."""
        banner("TEST T09-Extra 1 — Timestamp Timezone Safety")
        data = _build_minimal_spore_model_dict()
        model = HandoffSporeModel(**data)
        info("Parsed timezone information", model.handoff_timestamp.tzinfo)
        assert model.handoff_timestamp.tzinfo is not None
        success("Handoff timestamp carries explicit timezone configuration.")

    def test_active_variables_defaults_to_empty_dict(self):
        """active_variables defaults to {} when not supplied."""
        banner("TEST T09-Extra 2 — Active Variables Defaults")
        data = _build_minimal_spore_model_dict()
        data.pop("active_variables")
        model = HandoffSporeModel(**data)
        assert model.active_variables == {}
        success("Active variables defaults to empty dictionary.")

    def test_done_condition_defaults_to_none(self):
        """done_condition defaults to None when not supplied."""
        banner("TEST T09-Extra 3 — Done Condition Defaults")
        data = _build_minimal_spore_model_dict()
        data.pop("done_condition")
        model = HandoffSporeModel(**data)
        assert model.done_condition is None
        success("Done condition defaults to None.")


# ==============================================================================
# T10–T18 — HandoffSpore.write_spore() Tests
# ==============================================================================

class TestHandoffSporeWrite:

    def test_T10_produces_valid_json_file(self, tmp_path):
        """T10: write_spore() produces a non-empty, valid JSON file on disk."""
        banner("TEST T10 — write_spore() Output JSON Validity")
        session = _build_mixed_session(
            success_results=[{"result_key": "result_val"}],
            failed_errors=[],
            n_pending=1,
        )
        spore_path = tmp_path / "out" / "handoff.spore.json"
        step(f"Writing spore to {spore_path}...")
        _write_valid_spore_file(spore_path, session)

        assert spore_path.exists()
        raw = spore_path.read_text(encoding="utf-8")
        assert len(raw.strip()) > 0
        parsed = json.loads(raw)
        assert "spore_version" in parsed
        assert "task_graph_state" in parsed
        success("Spore file written successfully and contains valid JSON.")

    def test_T11_double_validation_raises_before_file_written(self, tmp_path):
        """T11: If post-serialization re-validation fails, SporeValidationError before write."""
        banner("TEST T11 — Double-Validation Guard Enforced")
        session = _build_session_with_n_steps(2)
        spore_path = tmp_path / "blocked.spore.json"

        def mock_validate(cls, raw, *args, **kwargs):
            raise pydantic.ValidationError.from_exception_data(
                "HandoffSporeModel",
                [{"type": "value_error", "loc": (), "msg": "injected", "input": {}, "ctx": {"error": ValueError("injected")}}],
            )

        step("Triggering write_spore with simulated serialization error...")
        with patch.object(HandoffSporeModel, "model_validate_json", classmethod(mock_validate)):
            with pytest.raises(SporeValidationError, match="re-validation") as exc_info:
                HandoffSpore.write_spore(session, spore_path)

        info("SporeValidationError caught", str(exc_info.value)[:80] + "...")
        assert not spore_path.exists()
        success("Write aborted cleanly. Disk is clean.")

    def test_T12_crystallized_history_prose_chain(self, tmp_path):
        """T12: crystallized_history is a pipe-delimited chain of SUCCESS and FAILED steps."""
        banner("TEST T12 — Crystallized History Prose Chain generation")
        session = _build_mixed_session(
            success_results=[{"x": 1}, {"y": 2}],
            failed_errors=["network timeout"],
            n_pending=1,
        )
        spore_path = tmp_path / "history.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        history = model.task_graph_state.crystallized_history
        info("Generated crystallized_history", history)
        parts = history.split(" || ")

        assert len(parts) == 3
        assert "SUCCESS" in parts[0]
        assert "step_001" in parts[0]
        assert "SUCCESS" in parts[1]
        assert "step_002" in parts[1]
        assert "FAILED" in parts[2]
        assert "step_003" in parts[2]
        assert "network timeout" in parts[2]
        success("Crystallized history successfully assembled.")

    def test_T12b_crystallized_history_empty_session(self, tmp_path):
        """T12b: When no steps have completed, crystallized_history is the sentinel message."""
        banner("TEST T12-Extra — Empty Session Crystallized History")
        session = _build_session_with_n_steps(2)
        spore_path = tmp_path / "empty_hist.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        info("Generated crystallized_history", model.task_graph_state.crystallized_history)
        assert model.task_graph_state.crystallized_history == (
            "No steps have been completed in this session."
        )
        success("Sentinel output message matches expectations.")

    def test_T13_active_variables_from_last_success_result(self, tmp_path):
        """T13: active_variables contains key-value pairs from the last SUCCESS step result."""
        banner("TEST T13 — Active Variables Extraction")
        session = _build_mixed_session(
            success_results=[
                {"early_key": "early_val"},
                {"latest_key": "latest_val", "score": 99},
            ],
            failed_errors=[],
            n_pending=1,
        )
        spore_path = tmp_path / "active_vars.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        info("Extracted active_variables", model.active_variables)
        assert "latest_key" in model.active_variables
        assert model.active_variables["latest_key"] == "latest_val"
        assert "early_key" not in model.active_variables
        success("Active variables match last success result.")

    def test_T14_active_variables_from_crystallized_result(self, tmp_path):
        """T14: When last SUCCESS result is crystallized, active_variables = result['key_outputs']."""
        banner("TEST T14 — Active Variables from Crystallized Result")
        crystallized_result = {
            "crystallized": True,
            "summary": "Did the important thing",
            "key_outputs": {"extracted_var": "extracted_value", "count": 42},
        }
        session = _build_mixed_session(
            success_results=[crystallized_result],
            failed_errors=[],
            n_pending=1,
        )
        spore_path = tmp_path / "crystallized.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        info("Extracted active_variables", model.active_variables)
        assert model.active_variables == {"extracted_var": "extracted_value", "count": 42}
        assert "crystallized" not in model.active_variables
        success("Active variables resolved from key_outputs.")

    def test_T15_done_condition_serialized_to_json_string(self, tmp_path):
        """T15: TaskGraph.done_condition is serialized to a JSON string in the spore."""
        banner("TEST T15 — Done Condition JSON Serialization")
        session = _build_session_with_n_steps(2)
        condition_obj = {"type": "all_success", "threshold": 0.99}
        session.task_graph.done_condition = condition_obj

        spore_path = tmp_path / "done_cond.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        info("Serialized done_condition type", type(model.done_condition).__name__)
        info("Serialized done_condition value", model.done_condition)

        assert model.done_condition is not None
        assert isinstance(model.done_condition, str)
        reparsed = json.loads(model.done_condition)
        assert reparsed == condition_obj
        success("Done condition serialized as string.")

    def test_T16_done_condition_is_none_when_not_set(self, tmp_path):
        """T16: When TaskGraph.done_condition is {} (empty), the spore field is also None."""
        banner("TEST T16 — Done Condition Null Value Handling")
        session = _build_session_with_n_steps(2)
        session.task_graph.done_condition = {}

        spore_path = tmp_path / "no_done_cond.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        assert model.done_condition is None
        success("Done condition set to None.")

    def test_T17_new_session_id_is_unique_per_write(self, tmp_path):
        """T17: Two separate write_spore() calls produce distinct new_session_id UUIDs."""
        banner("TEST T17 — UUID Uniqueness for New Sessions")
        session_a = _build_session_with_n_steps(2)
        session_b = _build_session_with_n_steps(2)

        model_a = _write_valid_spore_file(tmp_path / "a" / "s.json", session_a)
        model_b = _write_valid_spore_file(tmp_path / "b" / "s.json", session_b)

        info("new_session_id A", model_a.new_session_id)
        info("new_session_id B", model_b.new_session_id)

        assert model_a.new_session_id != model_b.new_session_id
        uuid.UUID(model_a.new_session_id, version=4)
        uuid.UUID(model_b.new_session_id, version=4)
        success("UUID uniqueness verified.")

    def test_T18_creates_parent_directories_automatically(self, tmp_path):
        """T18: write_spore() creates deep nested parent dirs if they don't exist."""
        banner("TEST T18 — Auto-Creation of Missing Parent Folders")
        deep_path = tmp_path / "level1" / "level2" / "level3" / "handoff.spore.json"
        assert not deep_path.parent.exists()

        session = _build_session_with_n_steps(1)
        step(f"Triggering write_spore on missing path: {deep_path}...")
        HandoffSpore.write_spore(session, deep_path)

        assert deep_path.exists()
        success("Directory stack resolved successfully.")

    def test_write_spore_returns_handoff_spore_model(self, tmp_path):
        """write_spore() return type must be HandoffSporeModel."""
        banner("TEST T18-Extra 1 — write_spore Return Object Verification")
        session = _build_session_with_n_steps(1)
        result = HandoffSpore.write_spore(session, tmp_path / "ret.spore.json")
        assert isinstance(result, HandoffSporeModel)
        success("Return value verified as HandoffSporeModel.")

    def test_write_spore_handoff_reason_auto_generated_when_empty(self, tmp_path):
        """If handoff_reason is empty, write_spore() generates one from telemetry."""
        banner("TEST T18-Extra 2 — Handoff Reason Auto Generation")
        session = _build_session_with_n_steps(1)
        model = HandoffSpore.write_spore(
            session,
            tmp_path / "auto_reason.spore.json",
            handoff_reason="",
        )
        info("Auto-generated reason", model.handoff_reason)
        assert model.handoff_reason.startswith("CONTEXT_EXHAUSTED")
        success("Telemetry-based reason generated successfully.")

    def test_write_spore_custom_handoff_reason_preserved(self, tmp_path):
        """A custom handoff_reason provided by the caller is preserved verbatim."""
        banner("TEST T18-Extra 3 — Custom Handoff Reason Preservation")
        session = _build_session_with_n_steps(1)
        custom_reason = "custom: manual operator override"
        model = HandoffSpore.write_spore(
            session,
            tmp_path / "custom_reason.spore.json",
            handoff_reason=custom_reason,
        )
        assert model.handoff_reason == custom_reason
        success("Verbatim custom reason matched.")

    def test_write_spore_checkpoint_path_fallback(self, tmp_path):
        """checkpoint_path falls back to session.metadata['last_checkpoint_path'] if empty."""
        banner("TEST T18-Extra 4 — Checkpoint Path Fallback")
        session = _build_session_with_n_steps(1)
        session.metadata["last_checkpoint_path"] = "/fallback/checkpoint.json"

        model = HandoffSpore.write_spore(
            session,
            tmp_path / "fallback.spore.json",
            checkpoint_path="",
        )
        assert model.checkpoint_path == "/fallback/checkpoint.json"
        success("Fallback configuration applied successfully.")

    def test_write_spore_explicit_checkpoint_path_overrides_fallback(self, tmp_path):
        """Explicit checkpoint_path argument takes precedence over session.metadata."""
        banner("TEST T18-Extra 5 — Explicit Checkpoint Path Precedence")
        session = _build_session_with_n_steps(1)
        session.metadata["last_checkpoint_path"] = "/fallback/checkpoint.json"

        model = HandoffSpore.write_spore(
            session,
            tmp_path / "explicit.spore.json",
            checkpoint_path="/explicit/path/cp.json",
        )
        assert model.checkpoint_path == "/explicit/path/cp.json"
        success("Explicit path override verified.")

    def test_write_spore_running_steps_included_in_remaining(self, tmp_path):
        """RUNNING steps must be included in remaining_steps (for retry by S2)."""
        banner("TEST T18-Extra 6 — Include Running Steps in Handoff List")
        session = _build_session_with_n_steps(3)
        session.task_graph.steps[0].mark_running()
        session.task_graph.steps[1].mark_running()
        session.task_graph.steps[1].mark_success({"done": True})

        spore_path = tmp_path / "running.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        remaining_ids = [s["step_id"] for s in model.task_graph_state.remaining_steps]
        info("Remaining steps", remaining_ids)
        assert "step_001" in remaining_ids
        assert "step_003" in remaining_ids
        assert "step_002" not in remaining_ids
        success("RUNNING step correctly moved to remaining array.")

    def test_write_spore_bootstrap_instructions_contains_next_step(self, tmp_path):
        """bootstrap_instructions references the first remaining step_id."""
        banner("TEST T18-Extra 7 — Bootstrap Instructions Target Next Step")
        session = _build_session_with_n_steps(3)
        session.task_graph.steps[0].mark_running()
        session.task_graph.steps[0].mark_success({"x": 1})

        spore_path = tmp_path / "bootstrap.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        info("bootstrap_instructions", model.bootstrap_instructions)
        assert "step_002" in model.bootstrap_instructions
        success("Target step identifier found in prompt fragment.")

    def test_write_spore_original_session_id_matches_session(self, tmp_path):
        """original_session_id in spore must match the session that wrote it."""
        banner("TEST T18-Extra 8 — Original Session Identifier Check")
        session = _build_session_with_n_steps(1)
        model = HandoffSpore.write_spore(session, tmp_path / "sid.spore.json")
        assert model.original_session_id == session.session_id
        success("Session identifiers match.")

    def test_write_spore_objective_preserved_verbatim(self, tmp_path):
        """Objective must survive write→load without truncation or summarization."""
        banner("TEST T18-Extra 9 — Objective Preservation Verbatim")
        long_objective = "Implement the full NALA harness including " + "x" * 300
        session = _build_session_with_n_steps(1)
        session.objective = long_objective

        model = HandoffSpore.write_spore(session, tmp_path / "obj.spore.json")
        assert model.objective == long_objective
        success("Verified objective integrity.")

    def test_write_spore_telemetry_matches_state_matrix(self, tmp_path):
        """SporeTelemetry fields match SessionState.state_matrix at write time."""
        banner("TEST T18-Extra 10 — Telemetry Accumulator Matching")
        session = _build_session_with_n_steps(1)
        session.state_matrix.total_tokens_in = 5000
        session.state_matrix.total_tokens_out = 2500
        session.state_matrix.estimated_cost = 0.0099
        session.state_matrix.error_count = 3
        session.state_matrix.elapsed_seconds = 120.5
        session.checkpoint_meta.lsn = 17

        model = HandoffSpore.write_spore(session, tmp_path / "telemetry.spore.json")

        assert model.telemetry_state.total_tokens_in == 5000
        assert model.telemetry_state.total_tokens_out == 2500
        assert abs(model.telemetry_state.estimated_cost_usd - round(0.0099, 6)) < 1e-9
        assert model.telemetry_state.error_count == 3
        assert abs(model.telemetry_state.elapsed_seconds - round(120.5, 3)) < 1e-6
        assert model.telemetry_state.session_lsn == 17
        success("Telemetry snapshot loaded correctly.")

    def test_write_spore_step_counts_accuracy(self, tmp_path):
        """total_steps, completed_steps, failed_steps, pending_steps are exact."""
        banner("TEST T18-Extra 11 — Step Counter Accuracy")
        session = _build_mixed_session(
            success_results=[{"a": 1}, {"b": 2}],
            failed_errors=["err1"],
            n_pending=3,
        )
        spore_path = tmp_path / "counts.spore.json"
        model = _write_valid_spore_file(spore_path, session)

        gs = model.task_graph_state
        assert gs.total_steps == 6
        assert gs.completed_steps == 2
        assert gs.failed_steps == 1
        assert gs.pending_steps == 3
        success("Counters values are matching setup.")


# ==============================================================================
# T19–T25 — HandoffSpore.load_spore() Tests
# ==============================================================================

class TestHandoffSporeLoad:

    def test_T19_raises_on_missing_file(self, tmp_path):
        """T19: load_spore() raises SporeValidationError when file does not exist."""
        banner("TEST T19 — load_spore Missing File Validation")
        ghost_path = tmp_path / "does_not_exist.spore.json"
        with pytest.raises(SporeValidationError, match="does not exist") as exc_info:
            HandoffSpore.load_spore(ghost_path)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Missing file validation caught successfully.")

    def test_T20_raises_on_directory_path(self, tmp_path):
        """T20: load_spore() raises SporeValidationError when path is a directory."""
        banner("TEST T20 — load_spore Directory Type Validation")
        dir_path = tmp_path / "i_am_a_dir"
        dir_path.mkdir()
        with pytest.raises(SporeValidationError, match="not a regular file") as exc_info:
            HandoffSpore.load_spore(dir_path)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Directory type check caught successfully.")

    def test_T21_raises_on_os_read_error(self, tmp_path):
        """T21: OSError during file read is wrapped in SporeValidationError."""
        banner("TEST T21 — load_spore OS Error Handling")
        spore_path = tmp_path / "perm_denied.spore.json"
        spore_path.write_text("{}", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(SporeValidationError, match="OS error") as exc_info:
                HandoffSpore.load_spore(spore_path)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("OS read error successfully wrapped.")

    def test_T22_raises_on_empty_file(self, tmp_path):
        """T22: A zero-byte file raises SporeValidationError with 'empty' reason."""
        banner("TEST T22 — load_spore Empty File Validation")
        empty = tmp_path / "empty.spore.json"
        empty.write_text("   \n   ", encoding="utf-8")

        with pytest.raises(SporeValidationError, match="empty") as exc_info:
            HandoffSpore.load_spore(empty)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Empty file checked and rejected.")

    def test_T23_raises_on_corrupt_json(self, tmp_path):
        """T23: Truncated JSON raises SporeValidationError with 'validation' reason."""
        banner("TEST T23 — load_spore Corrupted JSON Validation")
        corrupt = tmp_path / "corrupt.spore.json"
        corrupt.write_text('{"spore_version": "2.0.0", "obj', encoding="utf-8")

        with pytest.raises(SporeValidationError, match="validation") as exc_info:
            HandoffSpore.load_spore(corrupt)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Truncated JSON correctly blocked.")

    def test_T24_raises_on_schema_violation(self, tmp_path):
        """T24: Valid JSON with wrong types raises SporeValidationError (schema validation)."""
        banner("TEST T24 — load_spore Schema Validation Rejection")
        bad_schema = {
            "spore_version": 99,
            "original_session_id": None,
        }
        bad_file = tmp_path / "bad_schema.spore.json"
        bad_file.write_text(json.dumps(bad_schema), encoding="utf-8")

        with pytest.raises(SporeValidationError, match="schema validation") as exc_info:
            HandoffSpore.load_spore(bad_file)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Schema violation correctly rejected.")

    def test_T25_success_full_field_reconstruction(self, tmp_path):
        """T25: load_spore() correctly reconstructs all 12 HandoffSporeModel fields."""
        banner("TEST T25 — load_spore Reconstruction Completeness")
        session = _build_mixed_session(
            success_results=[{"output_1": "v1"}],
            failed_errors=[],
            n_pending=2,
        )
        spore_path = tmp_path / "round_trip" / "handoff.spore.json"
        original_model = _write_valid_spore_file(spore_path, session)

        loaded = HandoffSpore.load_spore(spore_path)

        assert loaded.spore_version == original_model.spore_version
        assert loaded.original_session_id == original_model.original_session_id
        assert loaded.new_session_id == original_model.new_session_id
        assert loaded.objective == original_model.objective
        assert loaded.handoff_reason == original_model.handoff_reason
        assert loaded.checkpoint_path == original_model.checkpoint_path
        assert loaded.bootstrap_instructions == original_model.bootstrap_instructions
        assert loaded.done_condition == original_model.done_condition
        assert loaded.active_variables == original_model.active_variables
        assert loaded.task_graph_state.total_steps == original_model.task_graph_state.total_steps
        assert loaded.task_graph_state.completed_steps == original_model.task_graph_state.completed_steps
        assert loaded.task_graph_state.crystallized_history == original_model.task_graph_state.crystallized_history
        assert loaded.telemetry_state.session_lsn == original_model.telemetry_state.session_lsn
        success("All fields round-tripped with 100% equivalence.")

    def test_load_spore_rejects_extra_fields_in_file(self, tmp_path):
        """A spore file with injected extra fields fails on load (extra='forbid')."""
        banner("TEST T25-Extra — Extra Field Rejection during Load")
        session = _build_session_with_n_steps(1)
        spore_path = tmp_path / "extra_field.spore.json"
        _write_valid_spore_file(spore_path, session)

        raw = json.loads(spore_path.read_text(encoding="utf-8"))
        raw["injected_by_attacker"] = "evil"
        spore_path.write_text(json.dumps(raw), encoding="utf-8")

        with pytest.raises(SporeValidationError, match="schema validation") as exc_info:
            HandoffSpore.load_spore(spore_path)
        info("ValidationError caught", str(exc_info.value)[:80] + "...")
        success("Extra fields correctly caught on load.")


# ==============================================================================
# T26–T29 — E2E Integration Tests (NalaLoop + recover_session)
# ==============================================================================

class TestE2EHandoffIntegration:

    def _make_exhaust_config(self, max_tokens: int = 400) -> TrackerConfig:
        """Build a TrackerConfig that is very easy to exhaust."""
        return TrackerConfig(
            max_context_tokens=max_tokens,
            warning_percent=0.50,
            compaction_percent=0.60,
            safety_buffer_fraction=0.05,
        )

    def test_T26_end_to_end_context_handoff_trigger(self, tmp_path):
        """T26: Loop exits PAUSED; spore lands in S2 directory with correct content."""
        banner("TEST T26 — E2E Context Handoff Trigger & Spore Placement")
        cm = CheckpointManager(base_dir=tmp_path)
        session = _build_session_with_n_steps(3)
        tracker = ContextTracker(self._make_exhaust_config())
        loop = NalaLoop(session, cm, context_tracker=tracker)

        # Large output to immediately cross the safety ceiling
        loop.set_default_handler(
            lambda step_obj, sess: StepResult(success=True, output={"data": "X" * 2000})
        )

        step("Running S1 task loop to trigger exhaustion...")
        status = loop.run()

        info("Loop termination status", status)
        assert status == LoopStatus.PAUSED

        spore_files = list(tmp_path.rglob("handoff.spore.json"))
        info("Discovered spore files count", len(spore_files))
        assert len(spore_files) == 1
        spore_path = spore_files[0]
        info("Spore path", spore_path)

        assert session.session_id not in str(spore_path.parent)

        spore = HandoffSpore.load_spore(spore_path)
        assert isinstance(spore, HandoffSporeModel)
        assert spore.original_session_id == session.session_id
        assert spore.handoff_reason.startswith("CONTEXT_EXHAUSTED")
        success("Loop correctly paused and placed spore in S2 folder.")

    def test_T27_pre_handoff_checkpoint_written_before_spore(self, tmp_path):
        """T27: pre-handoff checkpoint in S1 directory with label 'pre-handoff' and valid LSN."""
        banner("TEST T27 — E2E Pre-Handoff Checkpoint Sequence")
        cm = CheckpointManager(base_dir=tmp_path)
        session = _build_session_with_n_steps(2)
        tracker = ContextTracker(self._make_exhaust_config(max_tokens=300))
        loop = NalaLoop(session, cm, context_tracker=tracker)

        loop.set_default_handler(
            lambda step_obj, sess: StepResult(success=True, output={"data": "B" * 1500})
        )

        step("Running loop to exhaust context...")
        status = loop.run()
        assert status == LoopStatus.PAUSED

        s1_dir = tmp_path / session.session_id
        checkpoints = sorted(s1_dir.glob("checkpoint_LSN_*.json"))
        info("S1 checkpoint count", len(checkpoints))
        assert len(checkpoints) >= 1

        # Find the written spore and load it
        spore_path = next(tmp_path.rglob("handoff.spore.json"))
        spore = HandoffSpore.load_spore(spore_path)
        info("Spore checkpoint_path", spore.checkpoint_path)

        # Verify that the checkpoint path exists
        assert spore.checkpoint_path is not None
        saved_checkpoint = Path(spore.checkpoint_path)
        assert saved_checkpoint.exists()

        # Latest checkpoint must carry a valid LSN
        latest_cp = cm.load_latest(session.session_id)
        info("Checkpoint LSN", latest_cp.checkpoint_meta.lsn)

        assert latest_cp is not None
        assert latest_cp.checkpoint_meta.lsn >= 1
        success("Pre-handoff checkpoint safely logged in S1 before handoff.")

    def test_T28_bootstrapped_resumption_via_recover_session(self, tmp_path):
        """T28: recover_session(new_session_id) rebuilds S2 from spore with full state."""
        banner("TEST T28 — E2E Recovery & Spore Resumption")
        cm = CheckpointManager(base_dir=tmp_path)
        session_s1 = _build_session_with_n_steps(4)
        tracker = ContextTracker(self._make_exhaust_config())
        loop_s1 = NalaLoop(session_s1, cm, context_tracker=tracker)

        def handler_s1(step_obj, sess):
            if step_obj.step_id == "step_001":
                return StepResult(success=True, output={"critical_var": "gold_value", "run_id": 42})
            return StepResult(success=True, output={"critical_var": "gold_value", "payload": "X" * 2000})

        loop_s1.set_default_handler(handler_s1)
        step("Running S1 to exhaustion...")
        status_s1 = loop_s1.run()
        assert status_s1 == LoopStatus.PAUSED

        spore_path = next(tmp_path.rglob("handoff.spore.json"))
        spore = HandoffSpore.load_spore(spore_path)
        new_session_id = spore.new_session_id

        step(f"Recovering session for S2 ID: {new_session_id}...")
        def handler_s2(step_obj, sess):
            return StepResult(success=True, output={"done": True})

        loop_s2 = recover_session(
            session_id=new_session_id,
            checkpoint_manager=cm,
            handlers={},
            default_handler=handler_s2,
        )

        assert loop_s2 is not None
        assert isinstance(loop_s2, NalaLoop)
        assert loop_s2.session.session_id == new_session_id
        assert loop_s2.session.objective == session_s1.objective

        s2_step_ids = [s.step_id for s in loop_s2.session.task_graph.steps]
        info("S2 task list", s2_step_ids)
        assert "step_001" not in s2_step_ids
        assert "step_002" not in s2_step_ids
        assert "step_003" in s2_step_ids
        assert "step_004" in s2_step_ids

        active_vars = loop_s2.session.metadata.get("active_variables")
        info("Restored active variables", active_vars)
        assert active_vars is not None
        assert active_vars.get("critical_var") == "gold_value"
        success("Session recovered successfully with all active variables intact.")

    def test_T29_continuity_of_task_execution(self, tmp_path):
        """T29: S2 runs to COMPLETED; only remaining steps execute; no re-execution of S1 steps."""
        banner("TEST T29 — E2E Task Execution Continuity & No-Duplicate-runs")
        cm = CheckpointManager(base_dir=tmp_path)
        session_s1 = _build_session_with_n_steps(5)
        tracker = ContextTracker(self._make_exhaust_config(max_tokens=500))
        loop_s1 = NalaLoop(session_s1, cm, context_tracker=tracker)

        executed_in_s1 = []

        def handler_s1(step_obj, sess):
            executed_in_s1.append(step_obj.step_id)
            if step_obj.step_id in ("step_001", "step_002"):
                return StepResult(success=True, output={"key": step_obj.step_id})
            return StepResult(success=True, output={"data": "Z" * 2000})

        loop_s1.set_default_handler(handler_s1)
        step("Executing S1 until context exhaustion triggers...")
        status_s1 = loop_s1.run()
        assert status_s1 == LoopStatus.PAUSED
        info("Steps executed in S1", executed_in_s1)

        spore_path = next(tmp_path.rglob("handoff.spore.json"))
        spore = HandoffSpore.load_spore(spore_path)
        new_session_id = spore.new_session_id

        executed_in_s2 = []

        def handler_s2(step_obj, sess):
            executed_in_s2.append(step_obj.step_id)
            return StepResult(success=True, output={"s2_done": True})

        step(f"Recovering S2 and executing to completion...")
        loop_s2 = recover_session(
            session_id=new_session_id,
            checkpoint_manager=cm,
            handlers={},
            default_handler=handler_s2,
        )
        status_s2 = loop_s2.run()
        assert status_s2 == LoopStatus.COMPLETED
        info("Steps executed in S2", executed_in_s2)

        crystallized_ids = {
            line.split("]")[0].lstrip("[")
            for line in spore.task_graph_state.crystallized_history.split(" || ")
            if "SUCCESS" in line
        }
        info("Completed steps in S1 (crystallized)", list(crystallized_ids))

        for step_id in executed_in_s2:
            assert step_id not in crystallized_ids

        all_executed = set(executed_in_s1) | set(executed_in_s2)
        assert len(all_executed) == 5
        success("NALA completed the rest of tasks without executing previously succeeded ones.")

    def test_no_circular_import_from_session_handoff(self):
        """Importing session_handoff must not pull in context_tracker, nala_loop, or recovery."""
        banner("TEST E2E-Extra 1 — Circular Dependency Contract")
        import sys

        for mod_name in list(sys.modules.keys()):
            if "session_handoff" in mod_name:
                del sys.modules[mod_name]

        step("Importing core.harness.session_handoff...")
        import core.harness.session_handoff as sh

        src_file = inspect.getfile(sh)
        src_text = Path(src_file).read_text(encoding="utf-8")

        assert "from core.harness.context_tracker" not in src_text
        assert "from core.harness.nala_loop" not in src_text
        assert "from core.harness.recovery" not in src_text
        success("Strict imports isolation validated.")

    def test_spore_version_is_2_0_0_on_disk(self, tmp_path):
        """The spore JSON written to disk must have spore_version == '2.0.0'."""
        banner("TEST E2E-Extra 2 — On-Disk Spore Version")
        session = _build_session_with_n_steps(1)
        spore_path = tmp_path / "version_check.spore.json"
        HandoffSpore.write_spore(session, spore_path)

        raw = json.loads(spore_path.read_text(encoding="utf-8"))
        info("On-disk version tag", raw["spore_version"])
        assert raw["spore_version"] == "2.0.0"
        success("Spore version is 2.0.0.")


# ==============================================================================
# STANDALONE DEMO RUNNER — Run directly without pytest
# ==============================================================================

if __name__ == "__main__":
    print(f"\n{BOLD}{RED}")
    print("  ███╗   ██╗ █████╗ ██╗      █████╗ ")
    print("  ████╗  ██║██╔══██╗██║     ██╔══██╗")
    print("  ██╔██╗ ██║███████║██║     ███████║")
    print("  ██║╚██╗██║██╔══██║██║     ██╔══██║")
    print("  ██║ ╚████║██║  ██║███████╗██║  ██║")
    print("  ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")
    print(f"  {BOLD}Session Handoff — Unit Test Suite{RESET}")
    print(f"  {DIM}Nexus Lab AI Research Lab | Bengaluru{RESET}\n")

    test_classes = [
        TestContextExhaustedSignal(),
        TestSporeValidationError(),
        TestSporeTaskGraphSummary(),
        TestSporeTelemetry(),
        TestHandoffSporeModel(),
        TestHandoffSporeWrite(),
        TestHandoffSporeLoad(),
        TestE2EHandoffIntegration(),
    ]

    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        for method_name in methods:
            # Create a temporary directory for each test run if needed
            test_dir = tempfile.mkdtemp(prefix="nala_test_handoff_")
            tmp_path_val = Path(test_dir)
            try:
                method = getattr(cls, method_name)
                sig = inspect.signature(method)
                if "tmp_path" in sig.parameters:
                    method(tmp_path_val)
                else:
                    method()
                passed += 1
            except Exception as e:
                failed += 1
                errors.append((f"{cls.__class__.__name__}.{method_name}", str(e)))
                print(f"\n  {RED}❌ FAILED: {cls.__class__.__name__}.{method_name}{RESET}")
                print(f"     {RED}{e}{RESET}")
            finally:
                # Cleanup temp directory
                shutil.rmtree(test_dir, ignore_errors=True)

    # Final summary
    width = 75
    print(f"\n{BOLD}{'═' * width}{RESET}")
    print(f"{BOLD}  📊 TEST RESULTS SUMMARY{RESET}")
    print(f"{'═' * width}")
    print(f"  {GREEN}✅ Passed : {passed}{RESET}")
    print(f"  {RED}❌ Failed : {failed}{RESET}")
    print(f"  {'─' * 71}")
    if failed == 0:
        print(f"  {BOLD}{GREEN}ALL TESTS PASSED — JIRA-006 Session Handoff: COMPLETE ✅{RESET}")
    else:
        print(f"  {BOLD}{RED}SOME TESTS FAILED — Review errors above before proceeding.{RESET}")
        for test_name, err in errors:
            print(f"  {RED}  • {test_name}: {err}{RESET}")
    print(f"{BOLD}{'═' * width}{RESET}\n")
    print(f"  {DIM}Jai Bajrang Bali 🙏{RESET}\n")

    sys.exit(0 if failed == 0 else 1)
