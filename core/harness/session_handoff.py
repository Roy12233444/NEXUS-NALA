"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/session_handoff.py
Ticket  : JIRA-006 — Add Session Handoff File (Refactored)
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
Provides NALA's complete session handoff (spore) serialization infrastructure,
extracted from context_tracker.py for strict separation of concerns and
to eliminate the circular import risk introduced by inline imports in recovery.py.

This module is the SINGLE SOURCE OF TRUTH for all spore-related classes and
logic. context_tracker.py, nala_loop.py, and recovery.py all import from here.

DEPENDENCY CONTRACT (MUST NOT BE VIOLATED)
------------------------------------------
This module MUST remain completely free of any dependency on:
  - core.harness.context_tracker  → would cause a circular import
  - core.harness.nala_loop        → would cause a circular import
  - core.harness.recovery         → would cause a circular import

It imports ONLY from:
  - core.harness.session_contract   (pure Pydantic data models — safe)
  - stdlib: json, logging, uuid, datetime, pathlib, typing
  - third-party: pydantic (v2)

CONTENTS
--------
  SECTION 0 — Custom Exceptions
    1. ContextExhaustedSignal   — RuntimeError raised after spore is written
                                  to signal NalaLoop._execute_loop() to return
                                  LoopStatus.PAUSED.
    2. SporeValidationError     — ValueError raised on JSON schema failure,
                                  missing file, or Pydantic v2 rejection.

  SECTION 1 — Pydantic v2 Spore Sub-Models
    3. SporeTaskGraphSummary    — Compact TaskGraph state snapshot at handoff.
    4. SporeTelemetry           — Point-in-time telemetry counters at handoff.

  SECTION 2 — Root Spore Model
    5. HandoffSporeModel        — Root Pydantic v2 model for spore JSON.
                                  extra="forbid" prevents schema drift (RISK-020).

  SECTION 3 — HandoffSpore Static Utility
    6. HandoffSpore             — write_spore() + load_spore() static methods.

RISK MITIGATIONS EMBEDDED
--------------------------
  RISK-020 — Partial or corrupt handoff state:
              Pydantic v2 model_validate_json() called TWICE per write:
              once during model assembly, once post-serialization before
              the file is written to disk.
  RISK-035 — Spore written to wrong directory:
              write_spore() returns the HandoffSporeModel whose
              .new_session_id MUST be read by the caller (NalaLoop) to
              compute the canonical spore path under the new session directory.
  RISK-036 — Circular import between context_tracker and nala_loop:
              This module imports ONLY from session_contract (safe).

EXTRACTED FROM
--------------
  context_tracker.py — SECTION 0 (lines 117–174)  — exceptions
  context_tracker.py — SECTION 5 (lines 678–827)  — Pydantic models
  context_tracker.py — SECTION 6 (lines 834–1202) — HandoffSpore static class

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── third-party ───────────────────────────────────────────────────────────────
import pydantic
from pydantic import BaseModel, ConfigDict, Field

# ── local (ONLY session_contract — no other harness imports!) ─────────────────
from core.harness.session_contract import (
    SessionState,
    TaskStatus,
    utcnow,
)

# ── module-level logger ───────────────────────────────────────────────────────
_logger_handoff = logging.getLogger("nala.handoff_spore")


# ==============================================================================
# SECTION 0 — Custom Exceptions
# ==============================================================================

class ContextExhaustedSignal(RuntimeError):
    """
    Raised AFTER HandoffSpore.write_spore() has successfully written the
    spore JSON to disk. Signals that session S1's context window is fully
    exhausted and that NalaLoop._execute_loop() must catch this exception,
    emit the on_loop_end hook, and return LoopStatus.PAUSED.

    This is a RuntimeError (not an Exception subclass) to prevent it from
    being accidentally swallowed by generic ``except Exception`` guards.
    NalaLoop.run() must add an explicit ``except ContextExhaustedSignal``
    clause BEFORE its generic ``except Exception`` fallback (RISK-038).

    Extracted from: context_tracker.py SECTION 0, lines 117–147.

    Attributes
    ----------
    session_id       : str
        UUID of the session that is being handed off (S1).
    projected_tokens : int
        The projected token count that triggered ContextStatus.EXHAUSTED.
    spore_path       : Path
        Absolute path to the HandoffSpore JSON file written to disk.
        The parent directory name is the new_session_id (S2's directory).
    """

    def __init__(
        self,
        session_id:       str,
        projected_tokens: int,
        spore_path:       Path,
    ) -> None:
        self.session_id       = session_id
        self.projected_tokens = projected_tokens
        self.spore_path       = spore_path
        super().__init__(
            f"[NALA] Context EXHAUSTED for session '{session_id}': "
            f"projected {projected_tokens:,} tokens exceed safety ceiling. "
            f"HandoffSpore written to: {spore_path}"
        )


class SporeValidationError(ValueError):
    """
    Raised when HandoffSpore.write_spore() or HandoffSpore.load_spore()
    encounters any of the following failure conditions:

      - Pydantic v2 ValidationError during HandoffSporeModel assembly.
      - Pydantic v2 ValidationError during post-serialization re-validation
        before the file is written to disk.
      - FileNotFoundError or OSError when reading the spore file from disk.
      - The spore file is empty or is not a regular file.
      - The spore JSON fails json.JSONDecodeError parsing.

    A SporeValidationError during write_spore() indicates the session state
    cannot be safely serialized — the caller should attempt a fallback to the
    last good checkpoint before raising a fatal error.

    A SporeValidationError during load_spore() indicates the spore is corrupt
    or incompatible — the caller should fall back to the most recent valid
    checkpoint in the session directory.

    Extracted from: context_tracker.py SECTION 0, lines 150–174.

    Attributes
    ----------
    reason : str
        Human-readable description of the validation failure.
    path   : Optional[Path]
        Filesystem path of the offending spore file, if applicable.
    """

    def __init__(
        self,
        reason: str,
        path:   Optional[Path] = None,
    ) -> None:
        self.reason = reason
        self.path   = path
        location    = f" at '{path}'" if path else ""
        super().__init__(f"[NALA] SporeValidationError{location}: {reason}")


# ==============================================================================
# SECTION 1 — Pydantic v2 Spore Sub-Models
# ==============================================================================

class SporeTaskGraphSummary(BaseModel):
    """
    Compact, schema-validated snapshot of the TaskGraph state at the moment
    of session handoff.

    This sub-model is embedded inside HandoffSporeModel and provides the
    new session (S2) with everything it needs to reconstruct the remaining
    work queue: a crystallized prose summary of all completed steps, and the
    full serialized dicts of all steps that still need to be executed.

    Extracted from: context_tracker.py SECTION 5, lines 678–710.

    Fields
    ------
    total_steps            : int
        Total number of steps in the plan across all statuses.
    completed_steps        : int
        Count of steps that reached TaskStatus.SUCCESS.
    failed_steps           : int
        Count of steps that reached TaskStatus.FAILED.
    pending_steps          : int
        Count of steps in PENDING or RUNNING state. RUNNING steps are
        included in remaining because they were interrupted mid-execution
        and must be retried by the bootstrapped session.
    crystallized_history   : str
        Human-readable prose summary of ALL completed work, including
        per-step outputs and error messages. Formatted as a pipe-delimited
        chain: "[step_id] STATUS — description | outputs={...}"
        Built by HandoffSpore.write_spore().
    remaining_steps        : List[Dict[str, Any]]
        Full model_dump(mode="json") dicts for all steps not yet in SUCCESS,
        in their original execution order. Used by recover_session() to
        reconstruct the TaskGraph.
    last_completed_step_id : Optional[str]
        step_id of the most recently successfully completed step, or None
        if no steps have reached TaskStatus.SUCCESS in this session.
    """

    total_steps:             int
    completed_steps:         int
    failed_steps:            int
    pending_steps:           int
    crystallized_history:    str
    remaining_steps:         List[Dict[str, Any]]
    last_completed_step_id:  Optional[str] = None


class SporeTelemetry(BaseModel):
    """
    Point-in-time telemetry snapshot captured at the exact moment the
    HandoffSpore file is written to disk.

    All values are sourced directly from ``SessionState.state_matrix`` and
    ``SessionState.checkpoint_meta`` at write time. They are NOT derived
    from ContextTracker projections, which are forward-looking token
    estimates (not historical cumulative counts).

    These values are restored into the new session's StateMatrix by
    ``recover_session()`` using a monotonic max() correction to prevent
    double-counting cumulative token totals across sessions (RISK-033).

    Extracted from: context_tracker.py SECTION 5, lines 713–740.

    Fields
    ------
    total_tokens_in    : int
        Cumulative input tokens across all LLM API calls in this session.
    total_tokens_out   : int
        Cumulative output tokens across all LLM API calls in this session.
    estimated_cost_usd : float
        Accumulated USD cost of all LLM API calls (from
        StateMatrix.estimated_cost), rounded to 6 decimal places.
    error_count        : int
        Total number of errors across all steps and tool calls in session.
    elapsed_seconds    : float
        Wall-clock seconds elapsed since session creation, sourced from
        StateMatrix.elapsed_seconds. Rounded to 3 decimal places.
    session_lsn        : int
        The CheckpointMeta.lsn (Log Sequence Number) value at the exact
        moment this spore is written. Used for recovery ordering.
    """

    total_tokens_in:    int
    total_tokens_out:   int
    estimated_cost_usd: float
    error_count:        int
    elapsed_seconds:    float
    session_lsn:        int


# ==============================================================================
# SECTION 2 — Root Spore Model
# ==============================================================================

class HandoffSporeModel(BaseModel):
    """
    Root Pydantic v2 schema for NALA's HandoffSpore JSON file.

    A HandoffSpore is the complete, self-contained document that a new NALA
    session (S2) needs to resume work from a previous session (S1) that
    terminated due to context window exhaustion.

    Design decisions:
    - ``extra="forbid"`` prevents silent schema drift across NALA versions.
      Any field present in the JSON that is not declared here will raise a
      Pydantic ValidationError during both write and load. This enforces
      strict forward-compatibility discipline. (RISK-020)
    - ``spore_version`` is a string default so that schema evolution can be
      detected and handled by the bootstrap loader in future NALA versions.
    - ``handoff_timestamp`` is a UTC-aware datetime. Pydantic v2 serializes
      it as a full ISO 8601 string with timezone offset (+00:00) in
      model_dump_json(), ensuring unambiguous cross-session reconstruction.
    - ``new_session_id`` is pre-generated as a UUID4 inside write_spore()
      BEFORE the spore is assembled. The caller (NalaLoop) MUST read this
      field from the returned model to compute the canonical spore path
      under S2's directory: base_dir / new_session_id / handoff.spore.json.
      (RISK-035)

    Risk mitigated: RISK-020 — Partial or corrupt handoff state.

    Extracted from: context_tracker.py SECTION 5, lines 743–827.

    Fields
    ------
    spore_version          : str
        Schema version tag (e.g. "2.0.0"). Default is the current version.
    original_session_id    : str
        UUID of session S1 — the session being handed off.
    new_session_id         : str
        Pre-generated UUID4 for session S2 — the bootstrapped replacement.
    objective              : str
        The original user task goal. MUST NOT be summarized or truncated.
    handoff_timestamp      : datetime
        UTC-aware datetime when this spore file was written to disk.
    handoff_reason         : str
        Human-readable explanation of why the handoff was triggered
        (e.g. "CONTEXT_EXHAUSTED: safety ceiling reached").
    checkpoint_path        : str
        Absolute filesystem path to the last valid checkpoint file on disk.
        Empty string if no checkpoint has been written in this session.
    task_graph_state       : SporeTaskGraphSummary
        Compact snapshot of the TaskGraph step states at handoff time.
    telemetry_state        : SporeTelemetry
        Telemetry counter snapshot at the exact moment of handoff.
    active_variables       : Dict[str, Any]
        Key output variables extracted from the last SUCCESS step result.
        Empty dict if no steps have succeeded in this session.
    done_condition         : Optional[str]
        JSON-serialized string representation of TaskGraph.done_condition,
        or None if the task graph has no done_condition set.
    bootstrap_instructions : str
        Human-readable system-prompt fragment for the new session (S2)
        that tells it exactly where to resume in the task graph.
    """

    model_config = ConfigDict(extra="forbid")

    spore_version:          str                   = Field(
        default="2.0.0",
        description="Schema version tag for forward-compatibility detection",
    )
    original_session_id:    str                   = Field(
        ...,
        description="UUID of the session being handed off (S1)",
    )
    new_session_id:         str                   = Field(
        ...,
        description="Pre-generated UUID4 for the bootstrapped replacement session (S2)",
    )
    objective:              str                   = Field(
        ...,
        description="Original user task goal — must never be summarized or truncated",
    )
    handoff_timestamp:      datetime              = Field(
        ...,
        description="UTC-aware datetime when this spore was written to disk",
    )
    handoff_reason:         str                   = Field(
        ...,
        description="Human-readable reason for the handoff",
    )
    checkpoint_path:        str                   = Field(
        ...,
        description="Absolute path to the last valid checkpoint file on disk",
    )
    task_graph_state:       SporeTaskGraphSummary = Field(
        ...,
        description="Compact snapshot of TaskGraph step states at handoff",
    )
    telemetry_state:        SporeTelemetry        = Field(
        ...,
        description="Telemetry counter snapshot at the exact moment of handoff",
    )
    active_variables:       Dict[str, Any]        = Field(
        default_factory=dict,
        description="Key output variables extracted from the last SUCCESS step result",
    )
    done_condition:         Optional[str]         = Field(
        default=None,
        description="JSON-serialized done condition string from TaskGraph.done_condition",
    )
    bootstrap_instructions: str                   = Field(
        ...,
        description="System-prompt fragment for the bootstrapped session to resume correctly",
    )


# ==============================================================================
# SECTION 3 — HandoffSpore Static Utility
# ==============================================================================

class HandoffSpore:
    """
    Static utility class for writing and loading NALA HandoffSpore files.

    This is the ONLY correct way to produce or consume a NALA session handoff
    spore. All spore I/O must go through these two static methods.

    HandoffSpore files are produced by the JIRA-004 injection block inside
    NalaLoop._execute_loop() when ContextStatus.EXHAUSTED is confirmed and
    DronagiriCompactor.compact() has either not been attempted (safety ceiling
    reached directly) or has failed after both its compaction stages.

    IMPORTANT: The caller of write_spore() MUST read the returned
    HandoffSporeModel's ``.new_session_id`` field to construct the correct
    canonical final spore path under the new session's directory:
        base_dir / new_session_id / "handoff.spore.json"
    See RISK-035 in the JIRA-006 plan for full context.

    Extracted from: context_tracker.py SECTION 6, lines 834–1202.

    Methods
    -------
    write_spore(session, spore_path, *, handoff_reason, checkpoint_path)
        Constructs and validates a HandoffSporeModel from the live session
        state, then writes it to disk as indented JSON.
        Returns the HandoffSporeModel so the caller can read new_session_id.
        Raises SporeValidationError if Pydantic v2 validation fails.

    load_spore(spore_path)
        Reads and validates a HandoffSpore from disk.
        Returns the fully-validated HandoffSporeModel.
        Raises SporeValidationError if the file is missing, empty, invalid
        JSON, or fails Pydantic v2 schema validation.
    """

    @staticmethod
    def write_spore(
        session:         SessionState,
        spore_path:      Path,
        *,
        handoff_reason:  str = "",
        checkpoint_path: str = "",
    ) -> HandoffSporeModel:
        """
        Serialize the current session state into a Pydantic v2-validated
        HandoffSpore JSON file and write it atomically to ``spore_path``.

        This method performs the following 12 steps in strict order:

         1. Classify all task graph steps by status:
            SUCCESS steps → completed work.
            FAILED steps  → steps that errored out before completion.
            remaining     → PENDING + RUNNING steps (RUNNING must be retried).
         2. Build ``crystallized_history`` — a pipe-delimited prose chain
            of all completed and failed work with their key outputs and errors.
         3. Extract ``active_variables`` from the most recent SUCCESS step
            result. Handles both raw result dicts and pre-crystallized results.
         4. Serialize all remaining steps to JSON-safe dicts using
            model_dump(mode="json"). These are written verbatim into the spore
            so that recover_session() can reconstruct the TaskGraph exactly.
         5. Build SporeTaskGraphSummary from the classified step counts and
            the crystallized history and remaining step dicts.
         6. Build SporeTelemetry from SessionState.state_matrix and
            SessionState.checkpoint_meta at the exact current moment.
         7. Compute the effective checkpoint path: uses the ``checkpoint_path``
            argument if provided, otherwise falls back to session.metadata.
         8. Derive ``handoff_reason`` from session telemetry if the caller
            did not supply one.
         9. Serialize done_condition to a JSON string if the TaskGraph has one.
        10. Generate a fresh new_session_id UUID4 for the bootstrapped session.
        11. Build ``bootstrap_instructions`` prose string for S2's prompt.
        12. Assemble HandoffSporeModel via Pydantic v2 (first validation pass).
        13. Serialize to JSON and re-validate via model_validate_json()
            (second validation pass — RISK-020 double-check).
        14. Create parent directories and write the JSON file to disk.

        Risk mitigated: RISK-020 — Partial or corrupt handoff state.
        Risk mitigated: RISK-035 — Spore written to wrong directory:
            The returned model's ``.new_session_id`` is the UUID of the new
            session directory. The caller MUST use it to rename/move the spore
            to the canonical path: base_dir / new_session_id / handoff.spore.json.

        Parameters
        ----------
        session : SessionState
            The live session being handed off. This method reads from it but
            does NOT mutate any fields. The caller is responsible for calling
            _save_checkpoint("pre-handoff") BEFORE calling write_spore().
        spore_path : Path
            The path where the spore JSON file will be written. May be a
            temporary path (e.g. from tempfile.NamedTemporaryFile); NalaLoop
            will rename it to the canonical path after reading new_session_id.
            Parent directories are created automatically if they do not exist.
        handoff_reason : str, keyword-only
            Human-readable explanation of why the handoff was triggered.
            If empty, a default reason is auto-generated from session telemetry.
        checkpoint_path : str, keyword-only
            Absolute string path to the last valid checkpoint file on disk.
            Falls back to ``session.metadata.get("last_checkpoint_path", "")``
            if not provided.

        Returns
        -------
        HandoffSporeModel
            The fully-validated and on-disk-written spore model. The caller
            MUST read ``.new_session_id`` from this to build the final path.

        Raises
        ------
        SporeValidationError
            If Pydantic v2 validation fails during model assembly (step 12) or
            during post-serialization re-validation before the write (step 13).
        """
        spore_path = Path(spore_path)

        _logger_handoff.info(
            "[HandoffSpore] Initiating spore write. "
            "session_id=%s | LSN=%d | target=%s",
            session.session_id,
            session.checkpoint_meta.lsn,
            spore_path,
        )

        steps = session.task_graph.steps

        # ── Step 1: Classify all steps by status ────────────────────────────
        success_steps: list = [s for s in steps if s.status == TaskStatus.SUCCESS]
        failed_steps:  list = [s for s in steps if s.status == TaskStatus.FAILED]
        # RUNNING steps are interrupted mid-execution — they go into remaining
        # so the bootstrapped session will retry them from scratch.
        remaining_steps: list = [
            s for s in steps
            if s.status not in (TaskStatus.SUCCESS, TaskStatus.FAILED)
        ]

        # ── Step 2: Build crystallized_history ──────────────────────────────
        # Produces a pipe-delimited prose chain of all completed work.
        # Each entry format: "[step_id] STATUS — description | key=value"
        history_parts: List[str] = []

        for s in success_steps:
            output_annotation = ""
            if s.result:
                if s.result.get("crystallized"):
                    # Already crystallized by DronagiriCompactor Stage 2 — use summary.
                    summary_text = str(s.result.get("summary", ""))[:100]
                    output_annotation = f" | {summary_text}" if summary_text else ""
                else:
                    # Raw result — build a compact key=value annotation from
                    # the first 3 result entries that are JSON-serializable.
                    kv_items = list(s.result.items())[:3]
                    if kv_items:
                        pairs = [
                            f"{k}={json.dumps(v, default=str)}"
                            for k, v in kv_items
                        ]
                        output_annotation = f" | outputs={{{', '.join(pairs)}}}"
            history_parts.append(
                f"[{s.step_id}] SUCCESS — {s.description[:80]}{output_annotation}"
            )

        for s in failed_steps:
            error_text = (s.error_message or "unknown error")[:150]
            history_parts.append(
                f"[{s.step_id}] FAILED — {s.description[:80]} | error={error_text}"
            )

        crystallized_history = (
            " || ".join(history_parts)
            if history_parts
            else "No steps have been completed in this session."
        )

        # ── Step 3: Extract active_variables from last SUCCESS result ────────
        active_variables: Dict[str, Any] = {}
        if success_steps:
            last_success_result = success_steps[-1].result or {}
            if last_success_result.get("crystallized"):
                # Pre-crystallized result from DronagiriCompactor Stage 2.
                # key_outputs is guaranteed to contain JSON-safe values.
                active_variables = dict(last_success_result.get("key_outputs", {}))
            else:
                # Raw result dict — extract all JSON-serializable key-value pairs.
                # Non-serializable values are coerced to str to prevent loss.
                for k, v in last_success_result.items():
                    try:
                        json.dumps(v, default=str)
                        active_variables[k] = v
                    except (TypeError, ValueError):
                        active_variables[k] = str(v)

        # ── Step 4: Record last completed step id ────────────────────────────
        last_completed_step_id: Optional[str] = (
            success_steps[-1].step_id if success_steps else None
        )

        # ── Step 5: Serialize remaining steps ────────────────────────────────
        # model_dump(mode="json") ensures all Pydantic sub-models, enums, and
        # datetimes are serialized to JSON-native types (str, int, float, etc.).
        remaining_steps_dicts: List[Dict[str, Any]] = [
            s.model_dump(mode="json") for s in remaining_steps
        ]

        # ── Step 5b: Assemble SporeTaskGraphSummary ──────────────────────────
        task_graph_state = SporeTaskGraphSummary(
            total_steps=len(steps),
            completed_steps=len(success_steps),
            failed_steps=len(failed_steps),
            pending_steps=len(remaining_steps),
            crystallized_history=crystallized_history,
            remaining_steps=remaining_steps_dicts,
            last_completed_step_id=last_completed_step_id,
        )

        # ── Step 6: Assemble SporeTelemetry ─────────────────────────────────
        # Read directly from state_matrix and checkpoint_meta — NOT from
        # ContextTracker projections, which are forward-looking estimates.
        sm = session.state_matrix
        telemetry_state = SporeTelemetry(
            total_tokens_in=sm.total_tokens_in,
            total_tokens_out=sm.total_tokens_out,
            estimated_cost_usd=round(sm.estimated_cost, 6),
            error_count=sm.error_count,
            elapsed_seconds=round(sm.elapsed_seconds, 3),
            session_lsn=session.checkpoint_meta.lsn,
        )

        # ── Step 7: Effective checkpoint path ────────────────────────────────
        effective_checkpoint_path = checkpoint_path or str(
            session.metadata.get("last_checkpoint_path", "")
        )

        # ── Step 8: Derive handoff_reason if not provided ────────────────────
        if not handoff_reason:
            handoff_reason = (
                f"CONTEXT_EXHAUSTED: session '{session.session_id}' reached the "
                f"context safety ceiling. "
                f"Cumulative tokens in={sm.total_tokens_in}, "
                f"out={sm.total_tokens_out}. "
                f"Estimated cost=${sm.estimated_cost:.4f} USD. "
                f"Checkpoint LSN={session.checkpoint_meta.lsn}."
            )

        # ── Step 9: Serialize done_condition ─────────────────────────────────
        done_condition_str: Optional[str] = None
        raw_done_condition = session.task_graph.done_condition
        if raw_done_condition:
            try:
                done_condition_str = json.dumps(
                    raw_done_condition, ensure_ascii=False, default=str
                )
            except (TypeError, ValueError) as exc:
                _logger_handoff.warning(
                    "[HandoffSpore] Could not serialize done_condition: %s. "
                    "Writing None to spore.",
                    exc,
                )

        # ── Step 10: Generate new session UUID4 ──────────────────────────────
        # The caller MUST read this from the returned model to build the
        # canonical path: base_dir / new_session_id / "handoff.spore.json"
        new_session_id = str(uuid.uuid4())

        # ── Step 11: Build bootstrap_instructions ────────────────────────────
        next_step_id = remaining_steps[0].step_id if remaining_steps else "N/A"
        bootstrap_instructions = (
            f"You are resuming NALA session '{session.session_id}'. "
            f"Completed steps: {len(success_steps)}/{len(steps)}. "
            f"See task_graph_state.crystallized_history for a full factual "
            f"summary of all completed work, including outputs and errors. "
            f"Begin execution at step: '{next_step_id}'. "
            f"The active_variables dict contains key outputs from the most "
            f"recent successful step ('{last_completed_step_id or 'none'}'). "
            f"Treat the checkpoint at checkpoint_path as the ground truth for "
            f"all persisted state. Do not re-introduce bugs or re-implement "
            f"changes that are already recorded as completed in the "
            f"crystallized history."
        )

        # ── Step 12: Assemble HandoffSporeModel (first Pydantic v2 validation)
        try:
            spore_model = HandoffSporeModel(
                original_session_id=session.session_id,
                new_session_id=new_session_id,
                objective=session.objective,
                handoff_timestamp=utcnow(),
                handoff_reason=handoff_reason,
                checkpoint_path=effective_checkpoint_path,
                task_graph_state=task_graph_state,
                telemetry_state=telemetry_state,
                active_variables=active_variables,
                done_condition=done_condition_str,
                bootstrap_instructions=bootstrap_instructions,
            )
        except pydantic.ValidationError as exc:
            raise SporeValidationError(
                reason=(
                    f"HandoffSporeModel assembly failed Pydantic v2 validation: {exc}"
                ),
                path=spore_path,
            ) from exc

        # ── Step 13: Serialize + re-validate (RISK-020 double-check) ─────────
        # model_dump_json() uses Pydantic v2's fast Rust serializer.
        # Re-validating the JSON string catches any round-trip serialization
        # anomalies that could corrupt the spore in transit.
        spore_json = spore_model.model_dump_json(indent=2)
        try:
            HandoffSporeModel.model_validate_json(spore_json)
        except pydantic.ValidationError as exc:
            raise SporeValidationError(
                reason=(
                    f"Spore JSON re-validation failed before disk write — "
                    f"this is a serialization invariant violation: {exc}"
                ),
                path=spore_path,
            ) from exc

        # ── Step 14: Write to disk ────────────────────────────────────────────
        # Ensure parent directory exists — NalaLoop may pass a temp path
        # whose parent does not yet exist on disk.
        spore_path.parent.mkdir(parents=True, exist_ok=True)
        spore_path.write_text(spore_json, encoding="utf-8")

        _logger_handoff.info(
            "[HandoffSpore] Spore written successfully. "
            "session_id=%s | new_session_id=%s | path=%s | "
            "remaining_steps=%d | total_bytes=%d",
            session.session_id,
            new_session_id,
            spore_path,
            len(remaining_steps),
            len(spore_json.encode("utf-8")),
        )

        return spore_model

    @staticmethod
    def load_spore(spore_path: Path) -> HandoffSporeModel:
        """
        Read a HandoffSpore JSON file from disk and validate it via Pydantic v2.

        This method is called by recover_session() during the bootstrap of a
        new NALA session (S2) when a handoff.spore.json is detected in the
        new session's directory.

        Risk mitigated: RISK-020 — Corrupt or partial handoff state on load.

        Extracted from: context_tracker.py SECTION 6, lines 1118–1202.

        Parameters
        ----------
        spore_path : Path
            Absolute path to the HandoffSpore JSON file to load.
            Typically: base_dir / new_session_id / "handoff.spore.json"

        Returns
        -------
        HandoffSporeModel
            The fully-validated and populated spore model. All fields are
            guaranteed to be schema-compliant after this call.

        Raises
        ------
        SporeValidationError
            In any of the following conditions:
            - The file at ``spore_path`` does not exist on disk.
            - The path exists but is not a regular file (e.g. directory).
            - The file cannot be read due to an OS-level permission error.
            - The file is empty (zero bytes after stripping whitespace).
            - The file contains syntactically invalid JSON.
            - The JSON fails Pydantic v2 schema validation (missing fields,
              wrong types, or extra fields forbidden by ``extra="forbid"``).
        """
        spore_path = Path(spore_path)

        # ── Guard: file existence ─────────────────────────────────────────────
        if not spore_path.exists():
            raise SporeValidationError(
                reason="Spore file does not exist on disk.",
                path=spore_path,
            )

        if not spore_path.is_file():
            raise SporeValidationError(
                reason=(
                    "Spore path exists but is not a regular file "
                    "(may be a directory or special file — check filesystem)."
                ),
                path=spore_path,
            )

        # ── Read raw bytes from disk ──────────────────────────────────────────
        try:
            raw_json = spore_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SporeValidationError(
                reason=f"Failed to read spore file from disk (OS error): {exc}",
                path=spore_path,
            ) from exc

        # ── Guard: non-empty content ──────────────────────────────────────────
        if not raw_json.strip():
            raise SporeValidationError(
                reason="Spore file is empty (zero bytes after stripping whitespace).",
                path=spore_path,
            )

        # ── Pydantic v2 model_validate_json ──────────────────────────────────
        # model_validate_json() parses JSON and validates schema in one pass.
        # It raises ValidationError for schema violations and wraps
        # json.JSONDecodeError as ValueError for malformed JSON.
        try:
            model = HandoffSporeModel.model_validate_json(raw_json)
        except pydantic.ValidationError as exc:
            raise SporeValidationError(
                reason=f"Spore file failed Pydantic v2 schema validation: {exc}",
                path=spore_path,
            ) from exc
        except ValueError as exc:
            # Pydantic v2 wraps json.JSONDecodeError in ValueError during
            # model_validate_json() when the input string is not valid JSON.
            raise SporeValidationError(
                reason=f"Spore file contains invalid JSON (parse error): {exc}",
                path=spore_path,
            ) from exc

        _logger_handoff.info(
            "[HandoffSpore] Spore loaded and validated. "
            "path=%s | original_session_id=%s | new_session_id=%s | "
            "remaining_steps=%d | spore_version=%s",
            spore_path,
            model.original_session_id,
            model.new_session_id,
            len(model.task_graph_state.remaining_steps),
            model.spore_version,
        )

        return model
