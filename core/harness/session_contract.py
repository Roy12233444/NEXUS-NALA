"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/session_contract.py
Ticket  : JIRA-001 — Define Session Contract
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-10

PURPOSE
-------
This is the single source of truth for all NALA session state.
It defines the complete, validated, serializable data model that NALA must
save to survive crashes, restarts, context-window overflows, and any other
form of interruption.

Without this file, checkpoints have nothing to write, recovery has nothing
to read, and the long-running loop has nothing to resume from.
This is the first brick. Everything else is built on top of it.

ARCHITECTURE
------------
  SessionState (root)
    ├── StateMatrix       → Live telemetry (tokens, cost, errors, agents)
    ├── CheckpointMeta    → Persistence audit trail (LSN, hash, timestamp)
    └── TaskGraph         → The executable plan
          └── List[TaskStep]  → Individual steps with status and dependencies

DESIGN PRINCIPLES
-----------------
1. Pydantic v2 ONLY — no v1 methods (.json(), .dict(), @validator, parse_raw)
2. All datetimes are UTC-aware — never naive Python datetimes
3. TaskGraph is safe — circular dependency detection via DFS before execution
4. Immutable after creation where possible — validate_assignment catches bugs early
5. Self-describing — every field has a description and a docstring
6. Zero external dependencies beyond pydantic and stdlib

JIRA ACCEPTANCE CRITERIA
------------------------
  [AC-1] Session schema exists and is importable
  [AC-2] session_id, objective, state_matrix, checkpoint_meta, task_graph all present
  [AC-3] TaskGraph has current_step_id and List[TaskStep]
  [AC-4] TaskStep has step_id, description, status, dependencies
  [AC-5] TaskStatus enum with PENDING, RUNNING, SUCCESS, FAILED
  [AC-6] CheckpointMeta has lsn, timestamp, content_hash
  [AC-7] serialize() produces valid JSON
  [AC-8] deserialize() reconstructs identical Python object from that JSON
  [AC-9] All 10 unit tests in test_session_contract.py pass
  [AC-10] No runtime errors on realistic multi-step task graph creation

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

# ── third-party ───────────────────────────────────────────────────────────────
import pydantic

# ── RISK-001 GUARD: Enforce Pydantic v2 at import time ────────────────────────
# If someone accidentally has Pydantic v1, this raises immediately with a clear
# error message instead of a cryptic AttributeError buried inside a method call.
_PYDANTIC_MAJOR = int(pydantic.VERSION.split(".")[0])
if _PYDANTIC_MAJOR < 2:
    raise RuntimeError(
        f"\n\n[NALA FATAL] session_contract.py requires Pydantic v2+.\n"
        f"  Detected:  pydantic=={pydantic.VERSION}\n"
        f"  Fix:       pip install 'pydantic>=2.0,<3.0'\n"
        f"  Or update: pyproject.toml → dependencies = [\"pydantic>=2.0,<3.0\"]\n"
    )

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ── logger ────────────────────────────────────────────────────────────────────
logger = logging.getLogger("nala.core.harness.session_contract")


# ==============================================================================
# SECTION 0 — UTC HELPER
# ==============================================================================

def utcnow() -> datetime:
    """
    Return the current UTC time as a **timezone-aware** datetime object.

    This is the ONLY function that should be used anywhere in NALA to generate
    timestamps.  Never call ``datetime.utcnow()`` directly — it returns a
    *naive* datetime (no tzinfo) despite the misleading name.

    Risk mitigated: RISK-002 — Datetime Timezone Confusion.
    """
    return datetime.now(timezone.utc)


# ==============================================================================
# SECTION 1 — TaskStatus Enum
# ==============================================================================

class TaskStatus(str, Enum):
    """
    Represents the lifecycle state of a single ``TaskStep`` inside the
    ``TaskGraph``.

    Inherits from ``str`` so that enum values serialize directly to JSON strings
    (e.g. ``"PENDING"``) without any extra conversion logic.  This is the
    Pydantic v2–recommended pattern for string-backed enums.

    States
    ------
    PENDING  → The step has not started yet (initial state).
    RUNNING  → The step is actively being executed right now.
    SUCCESS  → The step completed successfully. Its outputs are in TaskStep.result.
    FAILED   → The step has permanently failed after all retry attempts.
               Recovery logic in JIRA-002 will handle this.

    State Transitions
    -----------------
    PENDING → RUNNING → SUCCESS
                     ↘ FAILED  (after max retries exhausted)
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"


# ==============================================================================
# SECTION 2 — TaskStep Model
# ==============================================================================

class TaskStep(BaseModel):
    """
    A single, atomic unit of work inside NALA's ``TaskGraph``.

    Each TaskStep is one node in the execution plan.  It records not just what
    needs to happen, but what *did* happen: which tool was used, what it
    returned, any errors that occurred, and how many times it was retried.

    Fields
    ------
    step_id       : Unique human-readable identifier, e.g. ``"step_002_write_file"``.
    description   : Plain-English description of what this step does.
    status        : Current lifecycle state (TaskStatus).
    dependencies  : List of step_ids that must reach SUCCESS before this step runs.
                    An empty list means this step can run immediately.
    tool_used     : Name of the NALA tool that executed this step (set at runtime).
    result        : Dict of all outputs produced by this step (set on SUCCESS).
    error_message : The last exception message if status is FAILED.
    retries       : Count of how many retry attempts have been made so far.
    started_at    : UTC timestamp when NALA began executing this step.
    completed_at  : UTC timestamp when the step reached SUCCESS or FAILED.
    """

    model_config = ConfigDict(
        validate_assignment=True,   # Re-validate on every field mutation
        use_enum_values=True,       # Store "PENDING" not TaskStatus.PENDING
    )

    step_id:       str                        = Field(..., description="Unique step identifier")
    description:   str                        = Field(..., description="Human-readable step description")
    status:        TaskStatus                 = Field(default=TaskStatus.PENDING, description="Current lifecycle state")
    dependencies:  List[str]                  = Field(default_factory=list, description="step_ids that must be SUCCESS first")
    tool_used:     Optional[str]              = Field(default=None, description="NALA tool that executed this step")
    result:        Optional[Dict[str, Any]]   = Field(default=None, description="Dict of outputs on SUCCESS")
    error_message: Optional[str]              = Field(default=None, description="Last error string on FAILED")
    retries:       int                        = Field(default=0, ge=0, description="Number of retry attempts made")
    started_at:    Optional[datetime]         = Field(default=None, description="UTC timestamp when step began")
    completed_at:  Optional[datetime]         = Field(default=None, description="UTC timestamp when step finished")

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def ensure_timestamps_are_utc(cls, v: Any) -> Optional[datetime]:
        """
        Auto-correct any naive datetime passed into timestamp fields.
        Risk mitigated: RISK-002 — Datetime Timezone Confusion.
        """
        if isinstance(v, datetime) and v.tzinfo is None:
            logger.warning(
                "TaskStep received a naive datetime. Attaching UTC timezone automatically."
            )
            return v.replace(tzinfo=timezone.utc)
        return v

    def mark_running(self) -> None:
        """Transition this step to RUNNING and record the start timestamp."""
        self.status     = TaskStatus.RUNNING
        self.started_at = utcnow()

    def mark_success(self, result: Dict[str, Any]) -> None:
        """Transition this step to SUCCESS and store the output result dict."""
        self.status       = TaskStatus.SUCCESS
        self.result       = result
        self.completed_at = utcnow()

    def mark_failed(self, error: str) -> None:
        """Transition this step to FAILED and record the error message."""
        self.status        = TaskStatus.FAILED
        self.error_message = error
        self.completed_at  = utcnow()
        self.retries      += 1


# ==============================================================================
# SECTION 3 — TaskGraph Model
# ==============================================================================

class TaskGraph(BaseModel):
    """
    The complete execution plan for a NALA session.

    The TaskGraph is an ordered, dependency-aware list of ``TaskStep`` objects.
    It implements a safe topological scheduler: it will only release a step
    for execution when ALL of its declared dependencies have reached SUCCESS.

    Circular dependencies are detected using Depth-First Search (DFS) before
    the run loop begins.  A graph with cycles is invalid and NALA will refuse
    to execute it.

    Fields
    ------
    current_step_id : The step_id of the step NALA is currently working on.
    done_condition  : Structured completion criteria (loaded from done_condition.json).
    steps           : Ordered list of all TaskStep objects in this session's plan.

    Risk mitigated: RISK-003 — Dependency Ordering Bugs in TaskGraph.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
    )

    current_step_id: Optional[str]       = Field(default=None, description="ID of the step currently executing")
    done_condition:  Dict[str, Any]       = Field(default_factory=dict, description="Structured done condition from done_condition.json")
    steps:           List[TaskStep]       = Field(default_factory=list, description="All execution steps in plan order")

    # ── Internal helpers ────────────────────────────────────────────────────

    def _get_success_ids(self) -> Set[str]:
        """
        Return the set of step_ids that have reached SUCCESS.
        Used internally by the scheduler to evaluate dependency readiness.
        """
        return {s.step_id for s in self.steps if s.status == TaskStatus.SUCCESS}

    def _step_by_id(self, step_id: str) -> Optional[TaskStep]:
        """Return the TaskStep with the given step_id, or None if not found."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    # ── Scheduler ──────────────────────────────────────────────────────────

    def get_next_pending_step(self) -> Optional[TaskStep]:
        """
        Return the first PENDING step whose ALL dependencies have completed
        successfully, or None if no step is currently schedulable.

        Safety guarantees (RISK-003 mitigations):
        - Uses ``all()`` to check EVERY dependency, not just the first one.
        - Explicitly skips RUNNING steps (already being processed).
        - Explicitly skips FAILED steps (handled by recovery logic).
        - Returns None cleanly when the graph is blocked, done, or failed.

        Returns
        -------
        TaskStep | None
            The next schedulable step, or None if nothing is ready.
        """
        done_ids = self._get_success_ids()
        for step in self.steps:
            if step.status != TaskStatus.PENDING:
                continue
            if all(dep in done_ids for dep in step.dependencies):
                return step
        return None

    # ── Graph state queries ─────────────────────────────────────────────────

    def is_complete(self) -> bool:
        """
        Return True only when every step in the graph has reached SUCCESS.
        An empty steps list is NOT considered complete (it indicates a
        misconfigured session, not a finished one).
        """
        return bool(self.steps) and all(
            s.status == TaskStatus.SUCCESS for s in self.steps
        )

    def has_failed(self) -> bool:
        """Return True if at least one step is permanently FAILED."""
        return any(s.status == TaskStatus.FAILED for s in self.steps)

    def is_blocked(self) -> bool:
        """
        Return True if there are PENDING steps but none are schedulable.
        This indicates either a circular dependency or an unrecoverable FAILED step.
        """
        has_pending = any(s.status == TaskStatus.PENDING for s in self.steps)
        return has_pending and self.get_next_pending_step() is None

    def pending_count(self) -> int:
        """Return the number of steps still in PENDING state."""
        return sum(1 for s in self.steps if s.status == TaskStatus.PENDING)

    def success_count(self) -> int:
        """Return the number of steps that have reached SUCCESS."""
        return sum(1 for s in self.steps if s.status == TaskStatus.SUCCESS)

    def failed_count(self) -> int:
        """Return the number of steps that have permanently FAILED."""
        return sum(1 for s in self.steps if s.status == TaskStatus.FAILED)

    def progress_percent(self) -> float:
        """
        Return the graph's completion percentage as a float from 0.0 to 100.0.
        Computed as (SUCCESS steps / total steps) * 100.
        Returns 0.0 if there are no steps.
        """
        if not self.steps:
            return 0.0
        return round((self.success_count() / len(self.steps)) * 100, 2)

    # ── Circular Dependency Detection (DFS) ────────────────────────────────

    def has_circular_dependency(self) -> bool:
        """
        Detect circular dependencies using iterative Depth-First Search.

        A circular dependency (e.g. step_A depends on step_B, step_B depends
        on step_A) will cause NALA's scheduler to block permanently.  This
        method MUST be called via ``validate_task_graph()`` before the run
        loop begins.

        Risk mitigated: RISK-003 — Scenario B (Infinite Scheduling Loop).

        Returns
        -------
        bool
            True if a cycle exists in the dependency graph. False if safe.
        """
        step_map   = {s.step_id: s for s in self.steps}
        visited:   Set[str] = set()
        rec_stack: Set[str] = set()

        def _dfs(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            step = step_map.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    if dep_id not in visited:
                        if _dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        logger.error(
                            "Circular dependency detected: '%s' → '%s'",
                            step_id, dep_id,
                        )
                        return True
            rec_stack.discard(step_id)
            return False

        return any(
            _dfs(s.step_id)
            for s in self.steps
            if s.step_id not in visited
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a concise summary dict of the graph's current state.
        Useful for logging and telemetry dashboards.
        """
        return {
            "total_steps":        len(self.steps),
            "pending":            self.pending_count(),
            "success":            self.success_count(),
            "failed":             self.failed_count(),
            "progress_percent":   self.progress_percent(),
            "is_complete":        self.is_complete(),
            "has_failed":         self.has_failed(),
            "is_blocked":         self.is_blocked(),
            "current_step_id":    self.current_step_id,
        }


# ==============================================================================
# SECTION 4 — CheckpointMeta Model
# ==============================================================================

class CheckpointMeta(BaseModel):
    """
    Persistence audit trail for NALA's checkpoint system.

    Every time NALA writes its state to disk (checkpoint), this model records:
    - ``lsn``          : A monotonically increasing integer sequence number.
                         Used to determine which checkpoint is the most recent
                         without relying solely on file timestamps.
    - ``timestamp``    : UTC-aware datetime of when the checkpoint was written.
    - ``content_hash`` : SHA-256 hash of the serialized JSON at write time.
                         Verified on load to detect corruption or tampering.

    The combination of LSN + hash provides both ordering guarantees AND
    integrity guarantees for NALA's survival system.

    Risk mitigated: RISK-002 — Datetime Timezone Confusion (timestamp is UTC-aware).
    """

    model_config = ConfigDict(validate_assignment=True)

    lsn:          int              = Field(default=0, ge=0, description="Monotonically increasing Log Sequence Number")
    timestamp:    datetime         = Field(default_factory=utcnow, description="UTC datetime of the last checkpoint write")
    content_hash: Optional[str]   = Field(default=None, description="SHA-256 hash of the serialized state JSON")

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_checkpoint_timestamp_utc(cls, v: Any) -> Optional[datetime]:
        """
        Auto-correct naive datetimes in checkpoint timestamp.
        Risk mitigated: RISK-002 — Datetime Timezone Confusion.
        """
        if isinstance(v, datetime) and v.tzinfo is None:
            logger.warning(
                "CheckpointMeta.timestamp received a naive datetime. "
                "Attaching UTC timezone automatically."
            )
            return v.replace(tzinfo=timezone.utc)
        return v

    def compute_hash(self, state_json: str) -> str:
        """
        Compute a SHA-256 hex digest of the given JSON string.

        This hash is stored in ``content_hash`` at checkpoint write time and
        compared against the recomputed hash at load time to detect corruption.

        Parameters
        ----------
        state_json : str
            The fully serialized JSON string of the SessionState.

        Returns
        -------
        str
            64-character lowercase hex string (SHA-256 digest).
        """
        return hashlib.sha256(state_json.encode("utf-8")).hexdigest()

    def verify_hash(self, state_json: str) -> bool:
        """
        Verify that the stored ``content_hash`` matches the given JSON string.

        Called during checkpoint load to confirm the data was not corrupted
        or tampered with between write and read.

        Parameters
        ----------
        state_json : str
            The JSON string loaded from disk.

        Returns
        -------
        bool
            True if the hash matches (data is clean). False if corrupted.
        """
        if self.content_hash is None:
            logger.warning("CheckpointMeta has no content_hash. Skipping verification.")
            return True  # No hash to compare against — treat as unverified (not failed)
        return self.compute_hash(state_json) == self.content_hash

    def increment(self, state_json: str) -> None:
        """
        Advance the LSN by 1, update the timestamp, and recompute the hash.

        Call this method immediately before writing a checkpoint to disk.

        Parameters
        ----------
        state_json : str
            The fully serialized JSON string to hash and store.
        """
        self.lsn          += 1
        self.timestamp     = utcnow()
        self.content_hash  = self.compute_hash(state_json)
        logger.debug("CheckpointMeta incremented → LSN=%d", self.lsn)


# ==============================================================================
# SECTION 5 — StateMatrix Model
# ==============================================================================

class StateMatrix(BaseModel):
    """
    Live telemetry and resource consumption counters for the current session.

    This model provides NALA with real-time visibility into the cost, token
    usage, and error rate of the current run.  It is updated after every
    tool call, API request, and step completion.

    Fields
    ------
    total_tokens_in  : Total input (prompt) tokens consumed across all LLM calls.
    total_tokens_out : Total output (completion) tokens generated across all LLM calls.
    elapsed_seconds  : Wall-clock seconds elapsed since the session started.
    estimated_cost   : Accumulated USD cost of all LLM API calls in this session.
    error_count      : Total number of errors raised across all steps and tools.
    active_agents    : List of agent role names currently active in this session.
    peak_memory_mb   : Peak memory usage in megabytes (populated by the run harness).
    """

    model_config = ConfigDict(validate_assignment=True)

    total_tokens_in:  int        = Field(default=0, ge=0, description="Input tokens consumed")
    total_tokens_out: int        = Field(default=0, ge=0, description="Output tokens generated")
    elapsed_seconds:  float      = Field(default=0.0, ge=0.0, description="Wall-clock seconds elapsed")
    estimated_cost:   float      = Field(default=0.0, ge=0.0, description="Accumulated USD cost")
    error_count:      int        = Field(default=0, ge=0, description="Total errors across all steps")
    active_agents:    List[str]  = Field(default_factory=list, description="Currently active agent roles")
    peak_memory_mb:   float      = Field(default=0.0, ge=0.0, description="Peak memory usage in MB")

    @property
    def total_tokens(self) -> int:
        """Return the sum of input and output tokens."""
        return self.total_tokens_in + self.total_tokens_out

    def add_llm_call(
        self,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float = 0.0,
    ) -> None:
        """
        Update telemetry counters after a single LLM API call completes.

        Parameters
        ----------
        tokens_in  : Number of input (prompt) tokens used in this call.
        tokens_out : Number of output (completion) tokens received.
        cost_usd   : Estimated USD cost of this individual call.
        """
        self.total_tokens_in  += tokens_in
        self.total_tokens_out += tokens_out
        self.estimated_cost   += cost_usd

    def record_error(self) -> None:
        """Increment the error counter by 1."""
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary dict for logging and dashboard display."""
        return {
            "total_tokens":      self.total_tokens,
            "tokens_in":         self.total_tokens_in,
            "tokens_out":        self.total_tokens_out,
            "estimated_cost_usd": round(self.estimated_cost, 6),
            "elapsed_seconds":   round(self.elapsed_seconds, 2),
            "error_count":       self.error_count,
            "active_agents":     self.active_agents,
            "peak_memory_mb":    round(self.peak_memory_mb, 2),
        }


# ==============================================================================
# SECTION 6 — SessionState (Root Model)
# ==============================================================================

class SessionState(BaseModel):
    """
    The root Session Contract for a single NALA run.

    This is the complete, validated, serializable state of everything NALA
    knows about its current task.  Every checkpoint writes this object to disk
    as a JSON file.  Every recovery reads it back and rebuilds from it.

    Think of this as NALA's "save file" — it contains everything needed to
    resume exactly where the agent left off after any interruption.

    Fields
    ------
    session_id      : UUID4 string, auto-generated at session creation. Immutable.
    objective       : The original user-provided task/goal string. Immutable.
    version         : Schema version string for forward-compatibility (e.g. "1.0.0").
    created_at      : UTC datetime when this session was first created. Immutable.
    last_updated    : UTC datetime of the last state mutation. Updated on every write.
    state_matrix    : Live telemetry counters (tokens, cost, errors).
    checkpoint_meta : Persistence audit trail (LSN, hash, timestamp).
    task_graph      : The full execution plan with all TaskStep objects.
    metadata        : Arbitrary key-value pairs for caller-supplied context.

    Risk mitigations embedded
    -------------------------
    RISK-001 : All serialization uses .model_dump_json() and .model_validate_json()
    RISK-002 : created_at and last_updated have UTC validators; utcnow() is used
    RISK-003 : validate_task_graph() checks for cycles and missing dependency IDs
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,   # Auto-strip leading/trailing whitespace from str fields
        validate_assignment=True,    # Re-validate on every field assignment after creation
        use_enum_values=True,        # Serialize enums as their raw string values
    )

    # ── Identity & Immutable Fields ─────────────────────────────────────────
    session_id:   str      = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID4 unique identifier for this session run",
    )
    objective:    str      = Field(
        ...,
        min_length=1,
        description="The original user task/goal. Must not be empty.",
    )
    version:      str      = Field(
        default="1.0.0",
        description="Session contract schema version for forward-compatibility",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at:   datetime = Field(
        default_factory=utcnow,
        description="UTC datetime when this session was first created",
    )
    last_updated: datetime = Field(
        default_factory=utcnow,
        description="UTC datetime of the last state mutation",
    )

    # ── Sub-models ──────────────────────────────────────────────────────────
    state_matrix:    StateMatrix    = Field(default_factory=StateMatrix)
    checkpoint_meta: CheckpointMeta = Field(default_factory=CheckpointMeta)
    task_graph:      TaskGraph      = Field(default_factory=TaskGraph)

    # ── Arbitrary caller context ─────────────────────────────────────────
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value pairs for caller-supplied context",
    )

    # ── RISK-002: Timestamp Validators ─────────────────────────────────────

    @field_validator("created_at", "last_updated", mode="before")
    @classmethod
    def ensure_session_timestamps_utc(cls, v: Any) -> Optional[datetime]:
        """
        Automatically attach UTC timezone to any naive datetime passed
        into created_at or last_updated.
        Risk mitigated: RISK-002 — Datetime Timezone Confusion.
        """
        if isinstance(v, datetime) and v.tzinfo is None:
            logger.warning(
                "SessionState received a naive datetime. Attaching UTC timezone automatically."
            )
            return v.replace(tzinfo=timezone.utc)
        return v

    # ── RISK-003: Post-init Graph Validation ────────────────────────────────

    def validate_task_graph(self) -> None:
        """
        Validate the TaskGraph for structural correctness before execution.

        Call this method ONCE after constructing a SessionState with a populated
        TaskGraph, before starting the NALA run loop.

        Checks performed
        ----------------
        1. Circular dependency detection (DFS) — prevents infinite scheduling loops.
        2. Dangling reference check — every dependency ID must exist in the graph.

        Raises
        ------
        ValueError
            If a circular dependency exists, or if a step references a dependency
            that does not exist in the TaskGraph.

        Risk mitigated: RISK-003 — Dependency Ordering Bugs in TaskGraph.
        """
        # Check 1: Circular dependencies
        if self.task_graph.has_circular_dependency():
            raise ValueError(
                "[NALA FATAL] TaskGraph contains a circular dependency.\n"
                "NALA cannot schedule a cyclic task graph.\n"
                "Fix the task plan before starting the run loop."
            )

        # Check 2: Dangling dependency references
        all_step_ids: Set[str] = {s.step_id for s in self.task_graph.steps}
        for step in self.task_graph.steps:
            for dep_id in step.dependencies:
                if dep_id not in all_step_ids:
                    raise ValueError(
                        f"[NALA FATAL] Step '{step.step_id}' declares a dependency "
                        f"on '{dep_id}', but that step_id does not exist in the TaskGraph.\n"
                        f"Available step_ids: {sorted(all_step_ids)}"
                    )

        logger.info(
            "TaskGraph validation passed. %d steps, %d dependencies checked.",
            len(self.task_graph.steps),
            sum(len(s.dependencies) for s in self.task_graph.steps),
        )

    # ── Serialization ───────────────────────────────────────────────────────

    def serialize(self) -> str:
        """
        Serialize the complete SessionState to an indented JSON string
        suitable for writing to a checkpoint file on disk.

        Uses Pydantic v2's ``model_dump_json()`` — NOT the deprecated v1 ``.json()``.
        Risk mitigated: RISK-001 — Pydantic v1 vs v2 API Incompatibility.

        Also validates that both timestamp fields are UTC-aware before writing,
        catching any timezone bugs before they corrupt a checkpoint file.
        Risk mitigated: RISK-002 — Datetime Timezone Confusion.

        Returns
        -------
        str
            A UTF-8 JSON string with 2-space indentation.
        """
        # RISK-002 guard: catch naive datetimes before they corrupt the checkpoint
        if self.created_at.tzinfo is None:
            raise ValueError(
                "[NALA FATAL] SessionState.created_at is timezone-naive. "
                "This must not happen. Use utcnow() everywhere."
            )
        if self.last_updated.tzinfo is None:
            raise ValueError(
                "[NALA FATAL] SessionState.last_updated is timezone-naive. "
                "This must not happen. Use utcnow() everywhere."
            )

        return self.model_dump_json(indent=2)  # ✅ Pydantic v2 method

    @classmethod
    def deserialize(cls, json_str: str) -> "SessionState":
        """
        Reconstruct a complete SessionState from a JSON string.

        Uses Pydantic v2's ``model_validate_json()`` — NOT the deprecated v1
        ``.parse_raw()``.  All field validators run during reconstruction, so
        any naive datetimes in the JSON will be auto-corrected to UTC-aware.

        Risk mitigated: RISK-001 — Pydantic v1 vs v2 API Incompatibility.

        Parameters
        ----------
        json_str : str
            A JSON string previously produced by ``serialize()``.

        Returns
        -------
        SessionState
            A fully reconstructed, fully validated SessionState object.

        Raises
        ------
        pydantic.ValidationError
            If the JSON is malformed or does not match the expected schema.
        json.JSONDecodeError
            If the input is not valid JSON at all.
        """
        return cls.model_validate_json(json_str)  # ✅ Pydantic v2 method

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """
        Reconstruct a SessionState from a Python dictionary.

        Uses Pydantic v2's ``model_validate()`` — NOT the deprecated v1
        ``.parse_obj()``.

        Parameters
        ----------
        data : dict
            A Python dictionary (e.g. from ``json.loads()``).

        Returns
        -------
        SessionState
        """
        return cls.model_validate(data)  # ✅ Pydantic v2 method

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the SessionState to a plain Python dictionary.

        Uses Pydantic v2's ``model_dump()`` — NOT the deprecated v1 ``.dict()``.

        Returns
        -------
        dict
            A fully-serialized dictionary representation of this session.
        """
        return self.model_dump()  # ✅ Pydantic v2 method

    # ── Checkpoint helpers ──────────────────────────────────────────────────

    def touch(self) -> None:
        """
        Update ``last_updated`` to the current UTC time.
        Call this after any mutation to the session state.
        """
        self.last_updated = utcnow()

    def prepare_checkpoint(self) -> str:
        """
        Serialize the session, increment the checkpoint LSN, recompute the
        SHA-256 content hash, and update the checkpoint timestamp.

        This is the ONLY correct way to prepare a checkpoint.  Call it
        immediately before writing to disk.

        Returns
        -------
        str
            The finalized JSON string ready to be written to disk.
        """
        self.touch()
        json_str = self.serialize()
        self.checkpoint_meta.increment(json_str)
        # Re-serialize after incrementing checkpoint_meta so the hash
        # reflects the final state including the new LSN and timestamp.
        final_json = self.serialize()
        self.checkpoint_meta.content_hash = self.checkpoint_meta.compute_hash(final_json)
        return final_json

    def verify_integrity(self, loaded_json: str) -> bool:
        """
        Verify the SHA-256 hash of a loaded checkpoint JSON string against
        the hash stored inside this SessionState's CheckpointMeta.

        Call this immediately after loading a checkpoint from disk to confirm
        the data was not corrupted in storage.

        Parameters
        ----------
        loaded_json : str
            The raw JSON string as read from the checkpoint file.

        Returns
        -------
        bool
            True if data is clean. False if corrupted or tampered.
        """
        is_valid = self.checkpoint_meta.verify_hash(loaded_json)
        if not is_valid:
            logger.error(
                "CHECKPOINT INTEGRITY FAILURE: Hash mismatch for session '%s' at LSN=%d. "
                "The checkpoint file may be corrupted. Do NOT resume from this checkpoint.",
                self.session_id,
                self.checkpoint_meta.lsn,
            )
        return is_valid

    # ── Representation ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SessionState("
            f"session_id={self.session_id!r}, "
            f"objective={self.objective[:40]!r}{'...' if len(self.objective) > 40 else ''}, "
            f"lsn={self.checkpoint_meta.lsn}, "
            f"progress={self.task_graph.progress_percent()}%"
            f")"
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a concise, human-readable summary of the session state.
        Useful for logging, dashboards, and debugging.
        """
        return {
            "session_id":    self.session_id,
            "version":       self.version,
            "objective":     self.objective[:80] + ("..." if len(self.objective) > 80 else ""),
            "created_at":    self.created_at.isoformat(),
            "last_updated":  self.last_updated.isoformat(),
            "lsn":           self.checkpoint_meta.lsn,
            "task_graph":    self.task_graph.get_summary(),
            "telemetry":     self.state_matrix.get_summary(),
        }


# ==============================================================================
# SECTION 7 — Module-level __all__ export
# ==============================================================================

__all__ = [
    "utcnow",
    "TaskStatus",
    "TaskStep",
    "TaskGraph",
    "CheckpointMeta",
    "StateMatrix",
    "SessionState",
]
