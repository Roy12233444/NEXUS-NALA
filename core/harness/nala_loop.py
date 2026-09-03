"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/nala_loop.py
Ticket  : JIRA-003 — Build Task Loop Skeleton
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-12
Version : 1.0.0

PURPOSE
-------
NalaLoop is NALA's core run-loop orchestrator — the central engine that drives
the agent's task execution step-by-step, persists every state transition, emits
structured telemetry, and supports cooperative pause/resume without data loss.

Without this file, NALA has a Session Contract and Checkpoint System but nothing
to drive them.  NalaLoop is the engine that brings the agent to life.

ARCHITECTURE
------------
  NalaLoop
    ├── run()                → Blocking entry point — runs until terminal state
    ├── stop()               → Thread-safe cooperative stop signal
    ├── register_handler()   → Bind executor callbacks to step IDs or types
    ├── set_default_handler()→ Fallback executor for unregistered steps
    ├── _execute_loop()      → Main state machine while-loop
    ├── _dispatch_step()     → Calls the registered executor with try/except
    ├── _update_telemetry()  → Updates StateMatrix with token/cost/time data
    ├── _save_checkpoint()   → Wraps CheckpointManager.write_checkpoint with retry
    └── _emit()              → Safe hook invocation (never crashes the loop)

STATE MACHINE
-------------
  Idle → Validating → Running ──▶ FetchStep ──▶ PreCheckpoint ──▶ Dispatch
                                      │                                  │
                                  terminal?                       Success/Failure
                                      │                                  │
                               COMPLETED/BLOCKED/               PostCheckpoint
                               FAILED/PAUSED                          │
                                                              ◀──── loop back

RISK MITIGATIONS IMPLEMENTED
-----------------------------
  RISK-009 : Executor exception → step marked FAILED, loop continues cleanly
  RISK-010 : stop() mid-executor → cooperative stop checks between steps only
  RISK-011 : CP write failure → single retry, then loop exits FAILED cleanly
  RISK-012 : No handler registered → MissingHandlerError, step marked FAILED
  RISK-013 : Telemetry drift → _update_telemetry() mandatory on all paths
  RISK-014 : Deadlock / infinite loop → same-step-ID guard exits BLOCKED
  RISK-015 : Corrupted LSN on resume → verify_integrity() called after load

JIRA ACCEPTANCE CRITERIA
------------------------
  [AC-1]  NalaLoop is importable from core.harness.nala_loop
  [AC-2]  run() drives steps to completion and returns COMPLETED
  [AC-3]  stop() from another thread causes loop to exit PAUSED after current step
  [AC-4]  Executor exceptions are caught and steps are marked FAILED
  [AC-5]  Checkpoint is written pre and post every step
  [AC-6]  Telemetry (tokens, cost, errors) is updated on every step
  [AC-7]  MissingHandlerError is raised and step is marked FAILED when no handler found
  [AC-8]  Deadlock guard exits BLOCKED when same step returned twice
  [AC-9]  All 15 unit tests in test_nala_loop.py pass

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import logging
import time
import threading
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

# ── NALA first-party ──────────────────────────────────────────────────────────
from core.harness.session_contract import SessionState, TaskStep
from core.harness.checkpoint import CheckpointManager, CheckpointWriteError
from core.harness.context_tracker import ContextStatus, ContextTracker, DronagiriCompactor
from core.harness.session_handoff import ContextExhaustedSignal, HandoffSpore
import shutil
import tempfile

try:
    from runtime.behavior_monitor import BehaviorMonitor
except ImportError:
    BehaviorMonitor = None  # type: ignore[assignment,misc]


# ── Module logger ─────────────────────────────────────────────────────────────
logger = logging.getLogger("nala.core.harness.nala_loop")


# ==============================================================================
# SECTION 1 — LoopStatus Enum
# ==============================================================================

class LoopStatus(str, Enum):
    """
    Terminal and transitional status codes for the NalaLoop run engine.

    Inherits from ``str`` so values serialize cleanly to JSON strings without
    any additional conversion logic.

    States
    ------
    READY     → Loop is initialized but run() has not been called yet.
    RUNNING   → Loop is currently executing steps (internal transient state).
    COMPLETED → All steps in the TaskGraph reached SUCCESS. Final state.
    PAUSED    → Cooperative stop was requested via stop(). State is saved and
                resumable by constructing a new NalaLoop from the checkpoint.
    BLOCKED   → TaskGraph has PENDING steps but none are schedulable (circular
                dependency or deadlock detected). Non-resumable without plan fix.
    FAILED    → An unrecoverable error occurred (e.g. checkpoint write failure
                after retry). Session state was saved at the point of failure.
    """

    READY     = "READY"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    PAUSED    = "PAUSED"
    BLOCKED   = "BLOCKED"
    FAILED    = "FAILED"


# ==============================================================================
# SECTION 2 — StepResult Dataclass (Executor Return Contract)
# ==============================================================================

@dataclass
class StepResult:
    """
    The standardized return contract for every registered step executor.

    Every callable registered via ``NalaLoop.register_handler()`` or
    ``NalaLoop.set_default_handler()`` MUST return a ``StepResult`` instance.

    Fields
    ------
    success           : True if the step completed without error.
    output            : Arbitrary dict of outputs to be stored in TaskStep.result.
    prompt_tokens     : Number of LLM input (prompt) tokens consumed. 0 for
                        non-LLM steps.
    completion_tokens : Number of LLM output (completion) tokens generated.
    cost_usd          : Estimated USD cost of this step's API calls.
    elapsed_seconds   : Wall-clock execution time in seconds (auto-set by loop).
    model             : Optional LLM model identifier for telemetry logging.

    Note: ``elapsed_seconds`` is always overridden by the loop's own
    ``time.perf_counter()`` measurement for accuracy. Executors may leave it
    as 0.0.
    """

    success:           bool             = True
    output:            Dict[str, Any]   = field(default_factory=dict)
    prompt_tokens:     int              = 0
    completion_tokens: int              = 0
    cost_usd:          float            = 0.0
    elapsed_seconds:   float            = 0.0
    model:             str              = "unknown"

    @property
    def total_tokens(self) -> int:
        """Return total token usage (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens


# ==============================================================================
# SECTION 3 — LoopHooks Dataclass (Observability Protocol)
# ==============================================================================

@dataclass
class LoopHooks:
    """
    Lightweight lifecycle hook system for observing every NalaLoop event.

    Hooks are optional callables. Any hook left as ``None`` is silently skipped.
    All hooks are called via ``NalaLoop._emit()``, which swallows exceptions so
    that a broken hook NEVER crashes the loop engine.

    Hook Signatures
    ---------------
    on_loop_start(session)                           → called once before the first step
    on_step_start(step, session)                     → called after mark_running, before executor
    on_step_success(step, result, session)           → called after mark_success
    on_step_failure(step, error_message, session)    → called after mark_failed
    on_checkpoint(checkpoint_path, session)          → called after every successful checkpoint write
    on_loop_end(final_status, session)               → called once before run() returns

    Usage (JIRA-007 soak test example)
    -----------------------------------
    hooks = LoopHooks(
        on_step_start=lambda step, s: print(f"▶ {step.step_id}"),
        on_step_success=lambda step, r, s: print(f"✅ {step.step_id} ({r.total_tokens} tokens)"),
        on_loop_end=lambda status, s: print(f"🏁 {status} — LSN={s.checkpoint_meta.lsn}"),
    )
    loop = NalaLoop(session, cm, hooks=hooks)
    """

    on_loop_start:   Optional[Callable[[SessionState], None]]                           = None
    on_step_start:   Optional[Callable[[TaskStep, SessionState], None]]                 = None
    on_step_success: Optional[Callable[[TaskStep, StepResult, SessionState], None]]     = None
    on_step_failure: Optional[Callable[[TaskStep, str, SessionState], None]]            = None
    on_checkpoint:   Optional[Callable[[Path, SessionState], None]]                     = None
    on_loop_end:     Optional[Callable[[LoopStatus, SessionState], None]]               = None
    on_context_warning: Optional[Callable[[SessionState], None]]                       = None



# ==============================================================================
# SECTION 4 — Custom Exceptions
# ==============================================================================

class NalaLoopError(RuntimeError):
    """Base class for all NalaLoop-specific errors."""


class MissingHandlerError(NalaLoopError):
    """
    Raised when NalaLoop cannot find a registered handler for a step.

    This happens when:
    - No handler is registered for the step's step_id.
    - No handler is registered for the step's step_type (if present).
    - No default handler has been set via set_default_handler().

    Risk mitigated: RISK-012 — Handler not registered for step type → silent skip.
    The loop catches this exception inside _dispatch_step(), marks the step as
    FAILED, and continues to the next step rather than silently skipping it.
    """

    def __init__(self, step_id: str, step_type: Optional[str] = None) -> None:
        self.step_id   = step_id
        self.step_type = step_type
        msg = (
            f"[NALA LOOP] No handler registered for step_id='{step_id}'"
            + (f" (step_type='{step_type}')" if step_type else "")
            + ". Register one via loop.register_handler() or loop.set_default_handler()."
        )
        super().__init__(msg)


class CheckpointWriteFailure(NalaLoopError):
    """
    Raised when CheckpointManager.write_checkpoint() fails on both the initial
    attempt and the single automatic retry.

    When this exception propagates out of _save_checkpoint(), the loop catches it,
    logs a CRITICAL-level message, and exits with LoopStatus.FAILED.

    Risk mitigated: RISK-011 — Checkpoint write failure during step transition.
    """

    def __init__(self, label: str, cause: Exception) -> None:
        self.label = label
        self.cause = cause
        super().__init__(
            f"[NALA LOOP] Checkpoint write FAILED permanently for label='{label}'. "
            f"Underlying error: {type(cause).__name__}: {cause}"
        )


# ==============================================================================
# SECTION 5 — NalaLoop Orchestrator (Core Run Engine)
# ==============================================================================

class NalaLoop:
    """
    The core run-loop orchestrator for NALA — Nexus Autonomous Long-Running Agent.

    NalaLoop drives a ``SessionState``'s ``TaskGraph`` step-by-step, persisting
    every state transition via ``CheckpointManager``, emitting lifecycle events
    via ``LoopHooks``, and supporting thread-safe cooperative stop/resume.

    Design Principles
    -----------------
    1. **Zero silent failures** — every exception is caught, logged, and recorded
       in the session state before the loop continues or exits.
    2. **Checkpoint-first** — state is persisted to disk BEFORE and AFTER every
       step execution. If the process dies mid-step, the pre-step checkpoint
       allows safe recovery.
    3. **Cooperative stop** — stop() sets a threading.Event. The loop checks it
       ONLY between steps, so the current executing step always completes safely.
    4. **Decoupled execution** — the loop engine has zero knowledge of what steps
       DO. It only knows how to schedule, dispatch, checkpoint, and observe them.
    5. **Production telemetry** — every step's token usage, cost, and timing is
       captured into the StateMatrix in real time.

    Quick Start
    -----------
    .. code-block:: python

        from core.harness import SessionState, CheckpointManager
        from core.harness.nala_loop import NalaLoop, LoopStatus, StepResult

        session = build_session()                          # your SessionState
        cm      = CheckpointManager(base_dir=Path("./data/checkpoints"))
        loop    = NalaLoop(session, cm)

        def my_executor(step, session):
            # do real work here
            return StepResult(success=True, output={"done": True})

        loop.set_default_handler(my_executor)
        status = loop.run()
        assert status == LoopStatus.COMPLETED

    Parameters
    ----------
    session : SessionState
        The fully-constructed, validated session to execute.
    checkpoint_manager : CheckpointManager
        The persistence engine that writes/reads checkpoint files.
    max_retries_per_step : int
        Number of additional executor retry attempts before permanently marking
        a step as FAILED. Default 0 (no retries — fail immediately).
    checkpoint_on_success_only : bool
        If True, skip the pre-execution checkpoint write (faster but less safe).
        Default False (write checkpoint before AND after every step).
    hooks : LoopHooks | None
        Optional lifecycle observation callbacks. Never crashes the loop.

    Thread Safety
    -------------
    - ``stop()`` is safe to call from any thread at any time.
    - ``run()`` is NOT re-entrant. Do not call run() concurrently from multiple
      threads on the same NalaLoop instance.
    """

    # ── Class-level constants ─────────────────────────────────────────────────

    #: Seconds to wait between checkpoint write retry attempts (RISK-011)
    _CHECKPOINT_RETRY_DELAY_S: float = 0.25

    #: Seconds to sleep when get_next_pending_step() returns None transiently
    _TRANSIENT_WAIT_S: float = 0.01

    # ── Constructor ───────────────────────────────────────────────────────────

    def __init__(
        self,
        session: SessionState,
        checkpoint_manager: CheckpointManager,
        *,
        max_retries_per_step: int = 0,
        checkpoint_on_success_only: bool = False,
        hooks: Optional[LoopHooks] = None,
        context_tracker: Optional[ContextTracker] = None,
        compactor: Optional[DronagiriCompactor] = None,
        behavior_monitor: Optional[Any] = None,
    ) -> None:
        if not isinstance(session, SessionState):
            raise TypeError(
                f"NalaLoop requires a SessionState instance, got {type(session).__name__}"
            )
        if not isinstance(checkpoint_manager, CheckpointManager):
            raise TypeError(
                f"NalaLoop requires a CheckpointManager instance, "
                f"got {type(checkpoint_manager).__name__}"
            )
        if max_retries_per_step < 0:
            raise ValueError(
                f"max_retries_per_step must be >= 0, got {max_retries_per_step}"
            )

        self.session:            SessionState       = session
        self.cm:                 CheckpointManager  = checkpoint_manager
        self.max_retries:        int                = max_retries_per_step
        self.skip_pre_checkpoint: bool              = checkpoint_on_success_only
        self.hooks:              LoopHooks          = hooks or LoopHooks()
        self.context_tracker:    Optional[ContextTracker] = context_tracker
        self.compactor:          Optional[DronagiriCompactor] = compactor
        self.behavior_monitor:   Optional[Any]              = behavior_monitor


        # ── Internal state ────────────────────────────────────────────────────
        self._stop_event:      threading.Event          = threading.Event()
        self._status:          LoopStatus               = LoopStatus.READY
        self._handlers:        Dict[str, Callable]      = {}   # step_id/type → callable
        self._default_handler: Optional[Callable]       = None

        logger.info(
            "[NalaLoop] Initialized for session_id=%s | objective=%s | steps=%d",
            session.session_id,
            session.objective[:60],
            len(session.task_graph.steps),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def register_handler(
        self,
        step_id_or_type: str,
        handler: Callable[[TaskStep, SessionState], Any],
    ) -> None:
        """
        Register an executor callable for a specific step_id or step type.

        The handler is looked up in order:
        1. Exact match on ``step.step_id``
        2. Exact match on ``step.tool_used`` (treated as step type)
        3. Default handler (if set via ``set_default_handler()``)

        Parameters
        ----------
        step_id_or_type : str
            The step_id (e.g. ``"step_001_fetch_data"``) or a generic step type
            string (e.g. ``"llm_call"``, ``"web_search"``).
        handler : Callable[[TaskStep, SessionState], StepResult | dict]
            The executor function. Must return a StepResult or a dict that can
            be used as the step result output.

        Raises
        ------
        ValueError
            If step_id_or_type is empty or handler is not callable.
        """
        if not step_id_or_type or not step_id_or_type.strip():
            raise ValueError("step_id_or_type must be a non-empty string.")
        if not callable(handler):
            raise ValueError(
                f"handler for '{step_id_or_type}' must be callable, "
                f"got {type(handler).__name__}"
            )
        self._handlers[step_id_or_type] = handler
        logger.debug("[NalaLoop] Handler registered for key='%s'", step_id_or_type)

    def set_default_handler(
        self,
        handler: Callable[[TaskStep, SessionState], Any],
    ) -> None:
        """
        Set a fallback executor called when no specific handler matches a step.

        Parameters
        ----------
        handler : Callable[[TaskStep, SessionState], StepResult | dict]
            The default executor function.

        Raises
        ------
        ValueError
            If handler is not callable.
        """
        if not callable(handler):
            raise ValueError(
                f"default_handler must be callable, got {type(handler).__name__}"
            )
        self._default_handler = handler
        logger.debug("[NalaLoop] Default handler set: %s", getattr(handler, "__name__", repr(handler)))

    def stop(self) -> None:
        """
        Request a cooperative stop of the run loop.

        Thread-safe. Can be called from any thread at any time.

        The loop will NOT stop immediately. It completes the step currently
        executing, writes a checkpoint, and then exits cleanly with
        ``LoopStatus.PAUSED``.

        Risk mitigated: RISK-010 — stop() called mid-executor leaves step in
        RUNNING forever. Cooperative stop guarantees the step finishes first.
        """
        logger.info("[NalaLoop] Stop signal received. Loop will pause after current step.")
        self._stop_event.set()

    @property
    def status(self) -> LoopStatus:
        """Return the current loop status (thread-safe read)."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Return True if the loop is currently in RUNNING state."""
        return self._status == LoopStatus.RUNNING

    def run(self) -> LoopStatus:
        """
        Start the run loop and block until a terminal state is reached.

        This is the primary entry point for executing NALA's task graph.
        It validates the graph, then enters the main execution while-loop
        until one of the following terminal states is reached:
        - ``COMPLETED`` — all steps succeeded.
        - ``PAUSED``    — ``stop()`` was called.
        - ``BLOCKED``   — graph has unsatisfiable dependencies.
        - ``FAILED``    — executor or checkpoint failure.

        Returns
        -------
        LoopStatus
            The terminal status code describing why the loop exited.

        Raises
        ------
        ValueError
            If the TaskGraph fails structural validation (circular dependency
            or dangling step reference). The loop does NOT start.
        RuntimeError
            If ``run()`` is called on an already-running loop.
        """
        if self._status == LoopStatus.RUNNING:
            raise RuntimeError(
                "[NalaLoop] run() called on an already-running loop. "
                "NalaLoop is not re-entrant."
            )

        # ── Phase 1: Graph validation (fail fast before any execution) ────────
        logger.info("[NalaLoop] Validating task graph before starting...")
        try:
            self.session.validate_task_graph()
        except ValueError as exc:
            logger.error(
                "[NalaLoop] TaskGraph validation FAILED. Loop will not start.\n%s", exc
            )
            self._status = LoopStatus.FAILED
            return LoopStatus.FAILED

        # ── Phase 2: Enter main execution loop ────────────────────────────────
        self._status = LoopStatus.RUNNING
        logger.info(
            "[NalaLoop] ▶ Starting execution | session_id=%s | steps=%d | max_retries=%d",
            self.session.session_id,
            len(self.session.task_graph.steps),
            self.max_retries,
        )

        try:
            final_status = self._execute_loop()
        except ContextExhaustedSignal as sig:
            logger.info(
                "[NalaLoop] ContextExhaustedSignal caught. "
                "Session handed off to spore at: %s",
                sig.spore_path,
            )
            self._status = LoopStatus.PAUSED
            return LoopStatus.PAUSED
        except Exception as exc:  # pragma: no cover — last-resort guard
            logger.critical(
                "[NalaLoop] UNHANDLED EXCEPTION in _execute_loop(): %s\n%s",
                exc,
                traceback.format_exc(),
            )
            self._status = LoopStatus.FAILED
            return LoopStatus.FAILED

        self._status = final_status
        return final_status

    # ── Private Engine Methods ────────────────────────────────────────────────

    def _execute_loop(self) -> LoopStatus:
        """
        The main state machine while-loop.

        This method implements the full step execution lifecycle:
          Idle → Validating → Running → FetchStep → PreCheckpoint
          → Dispatch → PostState → PostCheckpoint → loop

        Returns
        -------
        LoopStatus
            One of: COMPLETED, PAUSED, BLOCKED, FAILED.
        """
        t_session_start = time.perf_counter()
        self._emit(self.hooks.on_loop_start, self.session)

        # Tracks the step_id of the last dispatched step.
        # Used by the deadlock guard (RISK-014).
        last_dispatched_id: Optional[str] = None

        graph = self.session.task_graph

        while not self._stop_event.is_set():

            # ── Terminal state checks (checked at top of every iteration) ─────

            if graph.is_complete():
                logger.info(
                    "[NalaLoop] ✅ COMPLETED | LSN=%d | elapsed=%.2fs | "
                    "tokens=%d | cost=$%.4f",
                    self.session.checkpoint_meta.lsn,
                    time.perf_counter() - t_session_start,
                    self.session.state_matrix.total_tokens,
                    self.session.state_matrix.estimated_cost,
                )
                self._save_checkpoint("completing")
                self._emit(self.hooks.on_loop_end, LoopStatus.COMPLETED, self.session)
                return LoopStatus.COMPLETED

            if graph.has_failed():
                # Exit FAILED if:
                #   (a) No PENDING steps remain at all — all done or failed, or
                #   (b) PENDING steps remain but none are schedulable — they are
                #       all blocked by failed dependencies (graph.is_blocked()).
                if graph.pending_count() == 0 or graph.get_next_pending_step() is None:
                    logger.warning(
                        "[NalaLoop] ⚠ FAILED | failed_count=%d | pending_count=%d",
                        graph.failed_count(),
                        graph.pending_count(),
                    )
                    self._save_checkpoint("failed")
                    self._emit(self.hooks.on_loop_end, LoopStatus.FAILED, self.session)
                    return LoopStatus.FAILED

            if graph.is_blocked():
                logger.error(
                    "[NalaLoop] 🚫 BLOCKED | No schedulable steps remain. "
                    "pending=%d | failed=%d",
                    graph.pending_count(),
                    graph.failed_count(),
                )
                self._save_checkpoint("blocked")
                self._emit(self.hooks.on_loop_end, LoopStatus.BLOCKED, self.session)
                return LoopStatus.BLOCKED

            # ── Fetch next schedulable step ───────────────────────────────────
            step = graph.get_next_pending_step()

            if step is None:
                # Transient state — graph is not complete/blocked but nothing
                # is immediately runnable. Yield CPU and retry next iteration.
                time.sleep(self._TRANSIENT_WAIT_S)
                continue

            # ── RISK-014: Deadlock guard ──────────────────────────────────────
            # If the same step is returned two iterations in a row without ever
            # having been dispatched, the executor succeeded but the status
            # never flipped. This is a deadlock condition.
            if step.step_id == last_dispatched_id:
                logger.error(
                    "[NalaLoop] 🚫 DEADLOCK DETECTED | step_id='%s' returned twice "
                    "consecutively without status change. Exiting BLOCKED.",
                    step.step_id,
                )
                self._save_checkpoint("blocked-deadlock")
                self._emit(self.hooks.on_loop_end, LoopStatus.BLOCKED, self.session)
                return LoopStatus.BLOCKED

            # ── JIRA-004: Context Window Guard ───────────────────────────────────────────
            # Injected after RISK-014 deadlock guard, before step.mark_running().
            if self.context_tracker is not None:
                ctx_status = self.context_tracker.monitor_context(self.session)

                if ctx_status == ContextStatus.WARNING:
                    logger.warning(
                        "[NalaLoop] ⚠ Context WARNING | Projected tokens approaching "
                        "compaction threshold. session_id=%s | LSN=%d",
                        self.session.session_id,
                        self.session.checkpoint_meta.lsn,
                    )
                    # Emit optional hook — does NOT pause loop
                    self._emit(self.hooks.on_context_warning, self.session)

                elif ctx_status == ContextStatus.COMPACTING:
                    logger.warning(
                        "[NalaLoop] 🔄 Context COMPACTING | Invoking DronagiriCompactor. "
                        "session_id=%s | LSN=%d",
                        self.session.session_id,
                        self.session.checkpoint_meta.lsn,
                    )
                    if self.compactor is not None:
                        success = self.compactor.compact(self.session)
                        if not success:
                            # Compaction failed — escalate to EXHAUSTED path
                            logger.error(
                                "[NalaLoop] Compaction FAILED after 2 stages. "
                                "Escalating to EXHAUSTED handoff."
                            )
                            ctx_status = ContextStatus.EXHAUSTED

                if ctx_status == ContextStatus.EXHAUSTED:
                    logger.critical(
                        "[NalaLoop] 🚨 Context EXHAUSTED | Writing HandoffSpore. "
                        "session_id=%s | LSN=%d",
                        self.session.session_id,
                        self.session.checkpoint_meta.lsn,
                    )
                    # 1. Write final checkpoint before spore
                    checkpoint_path = self._save_checkpoint("pre-handoff")
                    
                    # 2. Write handoff spore to a temp file first
                    with tempfile.NamedTemporaryFile(
                        dir=self.cm.base_dir,
                        suffix=".spore.tmp",
                        delete=False
                    ) as tmp:
                        tmp_path = Path(tmp.name)

                    spore_model = HandoffSpore.write_spore(
                        self.session,
                        tmp_path,
                        handoff_reason=(
                            f"CONTEXT_EXHAUSTED: safety ceiling reached or compaction failed "
                            f"for session '{self.session.session_id}'"
                        ),
                        checkpoint_path=str(checkpoint_path),
                    )

                    # 3. Compute final directory using new_session_id (bootstrapped S2)
                    new_session_id = spore_model.new_session_id
                    final_spore_path = Path(self.cm.base_dir) / new_session_id / "handoff.spore.json"
                    final_spore_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(tmp_path), str(final_spore_path))

                    logger.critical(
                        "[NalaLoop] ✅ HandoffSpore written to canonical path. "
                        "original_session=%s | new_session=%s | path=%s",
                        self.session.session_id,
                        new_session_id,
                        final_spore_path,
                    )

                    # 4. Emit hook and raise ContextExhaustedSignal
                    self._emit(self.hooks.on_loop_end, LoopStatus.PAUSED, self.session)
                    raise ContextExhaustedSignal(
                        session_id=self.session.session_id,
                        projected_tokens=self.context_tracker.project_token_count(self.session),
                        spore_path=final_spore_path,
                    )

            # ── Pre-execution: mark running + write checkpoint ────────────────
            step.mark_running()
            graph.current_step_id = step.step_id


            if not self.skip_pre_checkpoint:
                try:
                    self._save_checkpoint(f"pre-step-{step.step_id}")
                except CheckpointWriteFailure as exc:
                    logger.critical(
                        "[NalaLoop] Pre-step checkpoint write FAILED for step='%s'. "
                        "Aborting loop: %s",
                        step.step_id,
                        exc,
                    )
                    self._emit(self.hooks.on_loop_end, LoopStatus.FAILED, self.session)
                    return LoopStatus.FAILED

            self._emit(self.hooks.on_step_start, step, self.session)
            logger.info(
                "[NalaLoop] ▶ Dispatching step='%s' | desc='%s' | LSN=%d",
                step.step_id,
                step.description[:60],
                self.session.checkpoint_meta.lsn,
            )

            # ── Dispatch: run executor with retry support ─────────────────────
            if self.behavior_monitor is not None:
                try:
                    self.behavior_monitor.record_planner_event(
                        depth=getattr(step, 'depth', 1),
                        branching_factor=1.0,
                        time_ms=0.0
                    )
                except Exception as bm_err:
                    logger.warning("[NalaLoop] BehaviorMonitor planner event failed: %s", bm_err)

            t0 = time.perf_counter()
            result, error_msg = self._dispatch_step_with_retry(step)
            elapsed = time.perf_counter() - t0

            if self.behavior_monitor is not None:
                try:
                    tool_name = getattr(step, 'step_type', None) or getattr(step, 'action', None) or step.step_id
                    success_flag = (result is not None and result.success)
                    self.behavior_monitor.record_tool_event(
                        tool_name=str(tool_name),
                        success=success_flag,
                        retries=0,
                        latency_ms=elapsed * 1000.0,
                        args=getattr(step, 'parameters', None)
                    )
                except Exception as bm_err:
                    logger.warning("[NalaLoop] BehaviorMonitor tool event failed: %s", bm_err)

            # ── Post-execution: record state transition ───────────────────────
            if result is not None:
                step.mark_success(result.output)
                result.elapsed_seconds = elapsed
                self._update_telemetry(result, elapsed)
                self._emit(self.hooks.on_step_success, step, result, self.session)
                logger.info(
                    "[NalaLoop] ✅ Step='%s' SUCCESS | elapsed=%.3fs | "
                    "tokens=%d | cost=$%.6f",
                    step.step_id,
                    elapsed,
                    result.total_tokens,
                    result.cost_usd,
                )
            else:
                step.mark_failed(error_msg or "Unknown executor error")
                self.session.state_matrix.record_error()
                self._emit(self.hooks.on_step_failure, step, error_msg or "", self.session)
                logger.warning(
                    "[NalaLoop] ❌ Step='%s' FAILED | elapsed=%.3fs | error=%s",
                    step.step_id,
                    elapsed,
                    error_msg,
                )

            # ── Post-execution checkpoint ─────────────────────────────────────
            try:
                cp_path = self._save_checkpoint(f"post-step-{step.step_id}")
                self._emit(self.hooks.on_checkpoint, cp_path, self.session)
            except CheckpointWriteFailure as exc:
                logger.critical(
                    "[NalaLoop] Post-step checkpoint write FAILED for step='%s'. "
                    "Aborting loop: %s",
                    step.step_id,
                    exc,
                )
                self._emit(self.hooks.on_loop_end, LoopStatus.FAILED, self.session)
                return LoopStatus.FAILED

            # Record elapsed time into StateMatrix
            total_elapsed = time.perf_counter() - t_session_start
            self.session.state_matrix.elapsed_seconds = total_elapsed

            # Advance deadlock guard tracking
            last_dispatched_id = step.step_id

        # ── Loop exited via stop_event ────────────────────────────────────────
        logger.info(
            "[NalaLoop] ⏸ PAUSED (cooperative stop) | LSN=%d | progress=%.1f%%",
            self.session.checkpoint_meta.lsn,
            graph.progress_percent(),
        )
        self._save_checkpoint("paused")
        self._emit(self.hooks.on_loop_end, LoopStatus.PAUSED, self.session)
        return LoopStatus.PAUSED

    # ── Step Dispatch ─────────────────────────────────────────────────────────

    def _dispatch_step_with_retry(
        self,
        step: TaskStep,
    ) -> Tuple[Optional[StepResult], Optional[str]]:
        """
        Execute the registered handler for the given step with retry support.

        Attempts execution ``1 + self.max_retries`` times before permanently
        returning failure. Between retries, increments ``step.retries`` and
        waits with exponential backoff.

        Parameters
        ----------
        step : TaskStep
            The step to execute.

        Returns
        -------
        Tuple[StepResult | None, str | None]
            (result, None)       on success.
            (None, error_message) on permanent failure.
        """
        last_error: Optional[str] = None

        for attempt in range(1 + self.max_retries):
            result, error_msg = self._dispatch_step(step)

            if result is not None:
                return result, None

            last_error = error_msg

            if attempt < self.max_retries:
                # Exponential backoff between retries
                backoff = 0.1 * (2 ** attempt)
                logger.warning(
                    "[NalaLoop] Step='%s' failed (attempt %d/%d). "
                    "Retrying in %.2fs... Error: %s",
                    step.step_id,
                    attempt + 1,
                    1 + self.max_retries,
                    backoff,
                    error_msg,
                )
                step.retries = attempt + 1
                time.sleep(backoff)
            else:
                logger.error(
                    "[NalaLoop] Step='%s' permanently FAILED after %d attempt(s). "
                    "Final error: %s",
                    step.step_id,
                    attempt + 1,
                    error_msg,
                )

        return None, last_error

    def _dispatch_step(
        self,
        step: TaskStep,
    ) -> Tuple[Optional[StepResult], Optional[str]]:
        """
        Resolve and call the registered handler for a single step execution.

        Handler Resolution Order
        ------------------------
        1. Exact match on ``step.step_id`` in the handler registry.
        2. Exact match on ``step.tool_used`` (step type) in the handler registry.
        3. Default handler (set via ``set_default_handler()``).
        4. Raise ``MissingHandlerError`` → step marked FAILED (RISK-012).

        Parameters
        ----------
        step : TaskStep
            The step to dispatch.

        Returns
        -------
        Tuple[StepResult | None, str | None]
            (result, None)        on success.
            (None, error_message) on any exception, including MissingHandlerError.

        Risk mitigated: RISK-009 — Executor exception causes state corruption.
        """
        # ── Handler resolution ────────────────────────────────────────────────
        handler = (
            self._handlers.get(step.step_id)
            or self._handlers.get(step.tool_used or "")
            or self._default_handler
        )

        if handler is None:
            error = MissingHandlerError(
                step_id=step.step_id,
                step_type=step.tool_used,
            )
            logger.error("[NalaLoop] %s", error)
            return None, str(error)

        # ── Executor invocation ───────────────────────────────────────────────
        try:
            raw = handler(step, self.session)

            # Normalize return value to StepResult
            if isinstance(raw, StepResult):
                result = raw
            elif isinstance(raw, dict):
                result = StepResult(success=True, output=raw)
            else:
                # Executor returned something unexpected — wrap it gracefully
                logger.warning(
                    "[NalaLoop] Handler for step='%s' returned %s (expected StepResult or dict). "
                    "Wrapping as output dict.",
                    step.step_id,
                    type(raw).__name__,
                )
                result = StepResult(success=True, output={"raw_result": str(raw)})

            if not result.success:
                # Executor explicitly signalled failure via result.success=False
                error_msg = result.output.get("error", "Executor returned success=False")
                logger.warning(
                    "[NalaLoop] Executor for step='%s' returned success=False: %s",
                    step.step_id,
                    error_msg,
                )
                return None, error_msg

            return result, None

        except Exception as exc:  # noqa: BLE001 — broad catch is intentional
            tb = traceback.format_exc()
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error(
                "[NalaLoop] Executor exception for step='%s':\n%s",
                step.step_id,
                tb,
            )
            return None, error_msg

    # ── Telemetry ─────────────────────────────────────────────────────────────

    def _update_telemetry(
        self,
        result: StepResult,
        elapsed: float,
    ) -> None:
        """
        Update ``StateMatrix`` counters after a successful step execution.

        Always called, even if tokens/cost are 0 (non-LLM steps).

        Risk mitigated: RISK-013 — StateMatrix tokens/cost never updated → telemetry drift.

        Parameters
        ----------
        result  : StepResult   — The executor's return value.
        elapsed : float        — Wall-clock seconds for this step.
        """
        try:
            self.session.state_matrix.add_llm_call(
                tokens_in=result.prompt_tokens,
                tokens_out=result.completion_tokens,
                cost_usd=result.cost_usd,
            )
            logger.debug(
                "[NalaLoop] Telemetry updated | +%d tokens_in | +%d tokens_out "
                "| +$%.6f cost | step_elapsed=%.3fs",
                result.prompt_tokens,
                result.completion_tokens,
                result.cost_usd,
                elapsed,
            )
        except Exception as exc:  # pragma: no cover — defensive guard
            logger.warning(
                "[NalaLoop] Telemetry update failed (non-fatal): %s", exc
            )

    # ── Checkpoint Safety ─────────────────────────────────────────────────────

    def _save_checkpoint(self, label: str) -> Path:
        """
        Write the current session state to disk via CheckpointManager.

        Wraps ``CheckpointManager.write_checkpoint()`` with a single automatic
        retry on failure, separated by ``_CHECKPOINT_RETRY_DELAY_S`` seconds.

        Risk mitigated: RISK-011 — Checkpoint write fails during step transition.

        Parameters
        ----------
        label : str
            A human-readable label describing why this checkpoint is being taken.
            Used for debug logging only (e.g. "pre-step-001", "paused", "completed").

        Returns
        -------
        Path
            The absolute path to the checkpoint file that was written.

        Raises
        ------
        CheckpointWriteFailure
            If both the initial write attempt and the single retry fail.
        """
        session_id = self.session.session_id

        for attempt in (1, 2):
            try:
                cp_path = self.cm.write_checkpoint(self.session)
                logger.debug(
                    "[NalaLoop] Checkpoint saved | label='%s' | LSN=%d | path=%s",
                    label,
                    self.session.checkpoint_meta.lsn,
                    cp_path,
                )
                return cp_path
            except CheckpointWriteError as exc:
                if attempt == 1:
                    logger.warning(
                        "[NalaLoop] Checkpoint write attempt 1 FAILED (label='%s'). "
                        "Retrying in %.2fs... Error: %s",
                        label,
                        self._CHECKPOINT_RETRY_DELAY_S,
                        exc,
                    )
                    time.sleep(self._CHECKPOINT_RETRY_DELAY_S)
                else:
                    logger.critical(
                        "[NalaLoop] Checkpoint write attempt 2 FAILED permanently "
                        "(label='%s', session_id='%s'). Error: %s",
                        label,
                        session_id,
                        exc,
                    )
                    raise CheckpointWriteFailure(label=label, cause=exc) from exc
            except Exception as exc:  # noqa: BLE001 — unexpected non-CheckpointWriteError
                logger.critical(
                    "[NalaLoop] Unexpected error during checkpoint write "
                    "(label='%s', session_id='%s'): %s\n%s",
                    label,
                    session_id,
                    exc,
                    traceback.format_exc(),
                )
                raise CheckpointWriteFailure(label=label, cause=exc) from exc

        # Should never reach here — for type-checker satisfaction only
        raise CheckpointWriteFailure(label=label, cause=RuntimeError("Unreachable"))  # pragma: no cover

    # ── Hook Emission ─────────────────────────────────────────────────────────

    def _emit(
        self,
        hook_fn: Optional[Callable],
        *args: Any,
    ) -> None:
        """
        Safely invoke a lifecycle hook function.

        Never raises. If the hook raises an exception, it is logged at WARNING
        level and execution continues. This guarantees that a broken user-supplied
        hook NEVER causes the loop to crash.

        Parameters
        ----------
        hook_fn : Callable | None
            The hook function to invoke, or None to skip.
        *args
            Arguments forwarded to the hook function.
        """
        if hook_fn is None:
            return
        try:
            hook_fn(*args)
        except Exception as exc:  # noqa: BLE001 — hooks must never crash loop
            logger.warning(
                "[NalaLoop] Hook '%s' raised an exception (suppressed): %s",
                getattr(hook_fn, "__name__", repr(hook_fn)),
                exc,
            )

    # ── Representation ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"NalaLoop("
            f"session_id={self.session.session_id!r}, "
            f"status={self._status.value!r}, "
            f"steps={len(self.session.task_graph.steps)}, "
            f"handlers={len(self._handlers)}, "
            f"max_retries={self.max_retries}"
            f")"
        )


# ==============================================================================
# SECTION 6 — Module-level __all__ export
# ==============================================================================

__all__ = [
    "LoopStatus",
    "StepResult",
    "LoopHooks",
    "NalaLoopError",
    "MissingHandlerError",
    "CheckpointWriteFailure",
    "NalaLoop",
]
