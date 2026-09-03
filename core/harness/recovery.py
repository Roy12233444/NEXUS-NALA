"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/recovery.py
Ticket  : JIRA-005 — Crash Recovery System
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-19
Version : 2.0.0 — Enterprise-Grade Recovery

PURPOSE
-------
This module is NALA's crash resiliency foundation. It implements the complete
ARIES (Algorithm for Recovery and Isolation Exploiting Semantics) protocol
adapted for NALA's Python + Pydantic stack, enabling seamless resumption after
SIGKILL, power loss, OOM kill, or any other hard process termination.

Core Guarantee
--------------
  If a NALA process is terminated at ANY point mid-execution, calling
  recover_session() will:
    1. Resolve any stale filesystem lock left by the crashed process.
    2. Load the latest SHA-256-verified checkpoint (with rollback chain).
    3. Fall back to the HandoffSpore if ALL checkpoint LSNs are corrupt.
    4. Reset any RUNNING step to PENDING (ARIES Redo Phase).
    5. Apply monotonic corrections to StateMatrix accumulators (no double-counting).
    6. Validate the TaskGraph topology.
    7. Guard against runaway crash loops (error ceiling check).
    8. Validate all handler signatures before binding to the new loop.
    9. Return a fully configured, immediately runnable NalaLoop instance.

ARIES Protocol Mapping
----------------------
  Phase A (Analysis) : Lock resolution → checkpoint load → SHA-256 verify →
                       rollback chain → spore fallback
  Phase R (Redo)     : RUNNING → PENDING reset → TaskGraph validation →
                       StateMatrix monotonic correction
  Phase U (Undo)     : RunawayLoopGuard halt on excessive error count

RISK MITIGATIONS
----------------
  RISK-015 : Corrupted LSN → SHA-256 hash chain + auto-rollback to LSN-1, -2
  RISK-023 : Missing handlers after restore → HandlerSignatureValidator
  RISK-024 : StateMatrix double-counting → monotonic max() correction
  RISK-025 : Infinite reboot loops → RunawayLoopGuard (error ceiling check)
  RISK-026 : Stale .checkpoint.lock blocks recovery → LockResolver + PID check
  RISK-027 : Handler signature mismatch → inspect.signature() pre-flight check
  RISK-028 : RUNNING step survives crash → ARIES Redo resets to PENDING
  RISK-029 : All checkpoints corrupt + no spore → SessionRecoveryError
  RISK-030 : OOM during recovery → fallback to smaller LSN-1

JIRA ACCEPTANCE CRITERIA
------------------------
  T01  Full SIGKILL simulation — loop resumes from last checkpoint, no double-exec
  T02  StateMatrix accumulators monotonically corrected after corruption
  T03  SHA-256 mismatch at LSN-N triggers rollback to LSN-N-1
  T04  All LSNs corrupt AND no spore → SessionRecoveryError
  T05  Handlers can be replaced/updated during recovery
  T06  Stale .checkpoint.lock cleared before checkpoint load
  T07  RunawayLoopError raised when error_count >= MAX_ERRORS
  T08  Session rebuilt from HandoffSpore when all checkpoints corrupt
  T09  Invalid handler signature rejected before any execution

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import inspect
import json
import logging
import os
import socket
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ── NALA first-party ──────────────────────────────────────────────────────────
from core.harness.session_contract import (
    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)
from core.harness.checkpoint import (
    CheckpointIntegrityError,
    CheckpointManager,
    CheckpointNotFoundError,
    CheckpointRecoveryError,
)
from core.harness.nala_loop import (
    NalaLoop,
    NalaLoopError,
)
from core.harness.context_tracker import (
    ContextTracker,
    DronagiriCompactor,
)
from core.harness.session_handoff import (
    HandoffSpore,
    SporeValidationError,
)

# ── Module logger ──────────────────────────────────────────────────────────────
_logger = logging.getLogger("nala.core.harness.recovery")


# ==============================================================================
# SECTION 1 — Exception Hierarchy
# ==============================================================================

class SessionRecoveryError(NalaLoopError):
    """
    Root exception for all NALA crash recovery failures.

    Raised when ``recover_session()`` cannot restore a valid, runnable
    ``NalaLoop`` from any available checkpoint or HandoffSpore. The caller
    must inspect the session and decide whether to start fresh or escalate.

    Inherits from ``NalaLoopError`` so callers can catch all loop-level
    failures with a single ``except NalaLoopError`` clause.

    Attributes
    ----------
    session_id     : UUID of the session recovery was attempted for.
    last_lsn_tried : Highest LSN that was attempted and failed (-1 if unknown).
    reason         : Human-readable description of the failure.
    """

    def __init__(
        self,
        session_id:     str,
        last_lsn_tried: int,
        reason:         str,
    ) -> None:
        self.session_id      = session_id
        self.last_lsn_tried  = last_lsn_tried
        self.reason          = reason
        super().__init__(
            f"[NALA Recovery] FAILED for session '{session_id}' "
            f"(last LSN tried: {last_lsn_tried}): {reason}"
        )


class SessionRecoveryLockError(SessionRecoveryError):
    """
    Raised when a ``.checkpoint.lock`` file cannot be resolved within the
    configured backoff window, indicating another process may still hold
    an active session lock.

    This exception is raised only after exhausting all exponential backoff
    retry attempts (2s → 4s → 8s). Manual inspection of the lock file
    is required to resolve this condition.

    Risk mitigated: RISK-026 — Stale lock file blocks recovery forever.

    Attributes
    ----------
    lock_path  : Absolute path to the unresolvable lock file.
    lock_age_s : Age of the lock file in seconds at the time of failure.
    """

    def __init__(
        self,
        session_id: str,
        lock_path:  Path,
        lock_age_s: float,
    ) -> None:
        self.lock_path  = lock_path
        self.lock_age_s = lock_age_s
        super().__init__(
            session_id=session_id,
            last_lsn_tried=-1,
            reason=(
                f"Lock file unresolved after all backoff attempts: {lock_path} "
                f"(age={lock_age_s:.1f}s). "
                f"Another process may still hold the session. "
                f"If the holding process is confirmed dead, manually delete the lock file."
            ),
        )


class RunawayLoopError(SessionRecoveryError):
    """
    Raised when ``StateMatrix.error_count`` meets or exceeds ``MAX_ERRORS``
    at recovery time, indicating the session is trapped in a persistent crash loop.

    Halting instead of resuming prevents unbounded API spend and runaway
    token/cost accumulation on a permanently broken task graph.

    This exception is raised BEFORE any handler is bound and BEFORE ``NalaLoop``
    is instantiated, guaranteeing zero additional API calls are made.

    Risk mitigated: RISK-025 — Infinite reboot loops on persistent failures.

    Attributes
    ----------
    error_count : Error count found in the restored StateMatrix.
    max_errors  : The configured maximum error ceiling.
    """

    def __init__(
        self,
        session_id:  str,
        error_count: int,
        max_errors:  int,
        last_lsn:    int,
    ) -> None:
        self.error_count = error_count
        self.max_errors  = max_errors
        super().__init__(
            session_id=session_id,
            last_lsn_tried=last_lsn,
            reason=(
                f"Runaway crash loop detected: error_count={error_count} >= "
                f"MAX_ERRORS={max_errors}. "
                f"Hard halt triggered to prevent unbounded API spend. "
                f"Manual inspection of session '{session_id}' required."
            ),
        )


# ==============================================================================
# SECTION 2 — LockResolver
# ==============================================================================

class LockResolver:
    """
    Implements the ``.checkpoint.lock`` acquisition, resolution, and release
    protocol for NALA's crash recovery subsystem.

    A lock file is created atomically using ``O_CREAT | O_EXCL`` to prevent
    two recovery processes from loading the same session checkpoint simultaneously.
    Stale locks (from crashed processes) are detected by:

      1. PID liveness check via ``os.kill(pid, 0)``
      2. Lock file age via ``time.time() - lock_path.stat().st_mtime``

    If either check indicates the lock is stale, it is unlinked and re-acquired.
    If the lock appears to be held by an active PID, exponential backoff is
    applied (2s → 4s → 8s) before raising ``SessionRecoveryLockError``.

    Risk mitigated: RISK-026 — Stale .checkpoint.lock file blocks recovery.

    Constants
    ---------
    LOCK_TIMEOUT_S   : Seconds after which any lock is considered stale (default 60).
    BACKOFF_DELAYS_S : Exponential backoff delays before raising (2, 4, 8 seconds).
    """

    LOCK_TIMEOUT_S:   int            = 60
    BACKOFF_DELAYS_S: tuple[int, ...] = (2, 4, 8)

    @classmethod
    def resolve(cls, session_id: str, base_dir: Path) -> Path:
        """
        Acquire the checkpoint lock for the given session.

        Clears any stale lock file if found, then writes a new lock file
        atomically using ``O_CREAT | O_EXCL`` with ``os.fsync()`` to ensure
        durability. Returns the path to the acquired lock file.

        Parameters
        ----------
        session_id : str
            UUID of the session to lock.
        base_dir : Path
            Base directory for checkpoint storage.

        Returns
        -------
        Path
            Absolute path to the acquired ``.checkpoint.lock`` file.

        Raises
        ------
        SessionRecoveryLockError
            If the lock cannot be acquired after all backoff retry attempts.
        """
        lock_path: Path = base_dir / session_id / ".checkpoint.lock"

        # Ensure session directory exists before we attempt to create a lock
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Initial attempt (attempt index -1) followed by backoff retries
        for attempt_index, delay in enumerate([-1] + list(cls.BACKOFF_DELAYS_S)):
            if attempt_index > 0:
                _logger.warning(
                    "[LockResolver] Lock still held on attempt %d. "
                    "Sleeping %ds before retry. session=%s",
                    attempt_index, delay, session_id[:8],
                )
                time.sleep(delay)

            # ── Case A: No lock file present → acquire immediately ─────────
            if not lock_path.exists():
                cls._write_lock(lock_path)
                _logger.info(
                    "[LockResolver] Lock acquired (no prior lock). "
                    "session=%s lock=%s",
                    session_id[:8], lock_path.name,
                )
                return lock_path

            # ── Case B: Lock file present → inspect it ────────────────────
            lock_age_s: float = time.time() - lock_path.stat().st_mtime

            try:
                raw_content: str  = lock_path.read_text(encoding="utf-8")
                lock_data:   dict = json.loads(raw_content)
                held_pid:    int  = int(lock_data.get("pid", -1))
                is_alive:    bool = cls._pid_is_alive(held_pid)
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                # Corrupt or unreadable lock file → unlink and re-acquire
                _logger.warning(
                    "[LockResolver] Corrupt lock file at %s (error: %s). "
                    "Unlinking and re-acquiring. session=%s",
                    lock_path, exc, session_id[:8],
                )
                lock_path.unlink(missing_ok=True)
                cls._write_lock(lock_path)
                return lock_path

            # ── Stale detection: dead PID or exceeded timeout ─────────────
            if lock_age_s > cls.LOCK_TIMEOUT_S or not is_alive:
                _logger.warning(
                    "[LockResolver] Stale lock detected. "
                    "held_pid=%d alive=%s age=%.1fs timeout=%ds. "
                    "Unlinking stale lock. session=%s",
                    held_pid, is_alive, lock_age_s,
                    cls.LOCK_TIMEOUT_S, session_id[:8],
                )
                lock_path.unlink(missing_ok=True)
                cls._write_lock(lock_path)
                _logger.info(
                    "[LockResolver] Stale lock cleared and new lock acquired. "
                    "session=%s",
                    session_id[:8],
                )
                return lock_path

            # Lock appears to be held by an active PID → loop for backoff
            _logger.warning(
                "[LockResolver] Active lock held by PID=%d (age=%.1fs). "
                "Will retry with backoff. session=%s",
                held_pid, lock_age_s, session_id[:8],
            )

        # ── All backoff attempts exhausted ────────────────────────────────────
        try:
            final_age: float = time.time() - lock_path.stat().st_mtime
        except OSError:
            final_age = 0.0

        _logger.error(
            "[LockResolver] FAILED to acquire lock after %d backoff attempts. "
            "session=%s lock=%s age=%.1fs",
            len(cls.BACKOFF_DELAYS_S), session_id[:8], lock_path, final_age,
        )
        raise SessionRecoveryLockError(
            session_id=session_id,
            lock_path=lock_path,
            lock_age_s=final_age,
        )

    @classmethod
    def release(cls, lock_path: Path) -> None:
        """
        Safely release the checkpoint lock file.

        Uses ``unlink(missing_ok=True)`` so this method is idempotent and
        safe to call multiple times (e.g. from both success and except paths).
        Never raises — all errors are logged as warnings.

        Parameters
        ----------
        lock_path : Path
            The path returned by ``resolve()``.
        """
        try:
            lock_path.unlink(missing_ok=True)
            _logger.debug("[LockResolver] Lock released: %s", lock_path)
        except OSError as exc:
            _logger.warning(
                "[LockResolver] Failed to release lock at %s: %s",
                lock_path, exc,
            )

    @staticmethod
    def _write_lock(lock_path: Path) -> None:
        """
        Atomically create and write a new lock file using ``O_CREAT | O_EXCL``.

        The lock file contains JSON metadata including the current PID,
        hostname, UTC timestamp, and an initial LSN of -1 (updated after
        checkpoint load). The file is ``fsync``-ed before the file descriptor
        is closed to guarantee durability against power loss.

        If another process wins the race (``FileExistsError``), this method
        silently exits — the caller's poll loop will handle re-inspection.

        Parameters
        ----------
        lock_path : Path
            Absolute path where the lock file should be created.
        """
        content: str = json.dumps(
            {
                "pid":         os.getpid(),
                "hostname":    socket.gethostname(),
                "acquired_at": utcnow().isoformat(),
                "lsn_at_lock": -1,  # Updated after successful checkpoint load
            },
            indent=None,
            separators=(",", ":"),
        )
        fd: int = -1
        try:
            # O_EXCL guarantees atomic creation — raises FileExistsError on race
            fd = os.open(
                str(lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            os.write(fd, content.encode("utf-8"))
            os.fsync(fd)   # Force kernel buffer → physical storage
        except FileExistsError:
            # Another recovery process won the creation race — benign, caller retries
            _logger.debug("[LockResolver] Race: lock file appeared mid-write at %s", lock_path)
        except OSError as exc:
            _logger.error("[LockResolver] Failed to write lock file at %s: %s", lock_path, exc)
            raise
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass  # fd already closed or invalid — safe to ignore

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        """
        Check if a process with the given PID is still running.

        Uses ``os.kill(pid, 0)`` which sends signal 0 (a no-op probe).
        On POSIX systems, this returns without error if the process exists
        and we have permission to signal it.

        Parameters
        ----------
        pid : int
            The process ID to probe. Values <= 0 always return False.

        Returns
        -------
        bool
            True if the process exists and is reachable. False if dead.
        """
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # ESRCH — process does not exist
            return False
        except PermissionError:
            # EPERM — process exists but we lack permission to signal it
            # Treat as alive (conservative — better to backoff than unlink)
            return True
        except OSError:
            # Other OS errors — treat as unknown/alive for safety
            return True


# ==============================================================================
# SECTION 3 — StateMatrixValidator
# ==============================================================================

class StateMatrixValidator:
    """
    Validates and monotonically corrects ``StateMatrix`` telemetry accumulators
    after checkpoint recovery, implementing the ARIES lower-bound correction.

    After a crash, ``StateMatrix.total_tokens_in`` and ``total_tokens_out``
    are loaded verbatim from the checkpoint. Without validation, it is
    impossible to know whether these accumulators are accurate or whether a
    partial write caused them to be lower than the actual consumed values.

    ARIES Solution (StateMatrix Reconstruction Invariant)
    -----------------------------------------------------
    For each SUCCESS step ``s`` in the TaskGraph:
      - ``floor_tokens_in  = sum(s.result["_meta_tokens_in"]  for SUCCESS steps)``
      - ``floor_tokens_out = sum(s.result["_meta_tokens_out"] for SUCCESS steps)``
      - ``floor_cost       = sum(s.result["_meta_cost_usd"]   for SUCCESS steps)``

    Correction (monotonic — only ever increases):
      ``SM.total_tokens_in  = max(SM.total_tokens_in,  floor_tokens_in)``
      ``SM.total_tokens_out = max(SM.total_tokens_out, floor_tokens_out)``

    This guarantees accumulators are never LOWER than what the SUCCESS step
    results imply, preventing under-counting without risking double-counting.

    Risk mitigated: RISK-024 — Telemetry reset or double-counting on crash.
    """

    # Keys injected into TaskStep.result by executors at step SUCCESS time
    _TOKENS_IN_KEY:  str = "_meta_tokens_in"
    _TOKENS_OUT_KEY: str = "_meta_tokens_out"
    _COST_KEY:       str = "_meta_cost_usd"

    @classmethod
    def validate_reconstructed(cls, session: SessionState) -> Dict[str, Any]:
        """
        Validate and monotonically correct the StateMatrix accumulators against
        per-step result metadata from the TaskGraph.

        Mutates ``session.state_matrix`` in-place if any accumulator is found
        to be below its lower bound derived from SUCCESS step results.

        Parameters
        ----------
        session : SessionState
            The recovered session. Modified in-place if corrections are needed.

        Returns
        -------
        Dict[str, Any]
            Diagnostic report of all corrections applied. Empty dict means the
            StateMatrix invariant already held — no correction was needed.
        """
        sm:     StateMatrix = session.state_matrix
        graph:  TaskGraph   = session.task_graph
        report: Dict[str, Any] = {}

        # ── Compute lower bounds from SUCCESS step result metadata ────────────
        floor_tokens_in: int = 0
        floor_tokens_out: int = 0
        floor_cost: float = 0.0

        for step in graph.steps:
            if step.status == TaskStatus.SUCCESS and step.result:
                try:
                    floor_tokens_in  += int(step.result.get(cls._TOKENS_IN_KEY,  0) or 0)
                    floor_tokens_out += int(step.result.get(cls._TOKENS_OUT_KEY, 0) or 0)
                    floor_cost       += float(step.result.get(cls._COST_KEY,     0.0) or 0.0)
                except (TypeError, ValueError) as exc:
                    _logger.warning(
                        "[StateMatrixValidator] Could not parse token/cost metadata "
                        "for step '%s': %s. Skipping this step in floor computation.",
                        step.step_id, exc,
                    )

        floor_errors: int = graph.failed_count()

        # ── Apply monotonic corrections (only upward — never reduce a value) ──

        if sm.total_tokens_in < floor_tokens_in:
            report["tokens_in_corrected"] = {
                "before": sm.total_tokens_in,
                "after":  floor_tokens_in,
            }
            sm.total_tokens_in = floor_tokens_in

        if sm.total_tokens_out < floor_tokens_out:
            report["tokens_out_corrected"] = {
                "before": sm.total_tokens_out,
                "after":  floor_tokens_out,
            }
            sm.total_tokens_out = floor_tokens_out

        if sm.estimated_cost < floor_cost:
            report["cost_corrected"] = {
                "before": round(sm.estimated_cost, 6),
                "after":  round(floor_cost, 6),
            }
            sm.estimated_cost = floor_cost

        if sm.error_count < floor_errors:
            report["error_count_corrected"] = {
                "before": sm.error_count,
                "after":  floor_errors,
            }
            sm.error_count = floor_errors

        # ── Log result ────────────────────────────────────────────────────────
        if report:
            _logger.warning(
                "[StateMatrixValidator] Monotonic corrections applied for "
                "session '%s' at LSN=%d: %s",
                session.session_id,
                session.checkpoint_meta.lsn,
                report,
            )
        else:
            _logger.info(
                "[StateMatrixValidator] StateMatrix invariant holds for "
                "session '%s' at LSN=%d. No corrections needed.",
                session.session_id,
                session.checkpoint_meta.lsn,
            )

        return report


# ==============================================================================
# SECTION 4 — HandlerSignatureValidator
# ==============================================================================

class HandlerSignatureValidator:
    """
    Validates that all registered step handler callables have a signature
    compatible with NalaLoop's dispatch protocol BEFORE the recovered loop starts.

    The expected executor signature is:
        ``def my_handler(step: TaskStep, session: SessionState) -> StepResult``

    Validation rejects handlers at recovery time rather than at runtime,
    preventing silent ``TypeError`` exceptions during active task execution
    that would waste API tokens and produce corrupted state.

    Risk mitigated: RISK-023 — Handler missing after restore → TypeError at dispatch.
    Risk mitigated: RISK-027 — Handler signature mismatch causes silent wrong output.
    """

    # Minimum required positional (non-default, non-variadic) parameter count
    _MIN_PARAMS: int = 2

    # Expected parameter names for informational warnings (not enforced as errors)
    _EXPECTED_PARAM_NAMES: tuple[str, ...] = ("step", "session")

    @classmethod
    def validate_all(
        cls,
        handlers:        Dict[str, Callable],
        default_handler: Optional[Callable],
        graph:           TaskGraph,
    ) -> None:
        """
        Validate all handlers in the registry and the default handler.

        Iterates over every ``{step_id: callable}`` entry and the optional
        ``default_handler``, calling ``_validate_single()`` on each. Also emits
        warnings for PENDING steps that have no registered handler and no
        default handler (they will raise ``MissingHandlerError`` at dispatch).

        Parameters
        ----------
        handlers        : Dict mapping step_id strings to executor callables.
        default_handler : Optional fallback callable for unregistered steps.
        graph           : The recovered TaskGraph — used for coverage warnings.

        Raises
        ------
        TypeError
            If any handler has fewer than 2 required positional parameters or
            its signature cannot be introspected.
        """
        # Validate all explicitly registered step handlers
        for step_id, handler in handlers.items():
            cls._validate_single(handler, context=f"handler[{step_id!r}]")

        # Validate the default handler if provided
        if default_handler is not None:
            cls._validate_single(default_handler, context="default_handler")

        # Warn on PENDING steps with no coverage (MissingHandlerError at dispatch)
        if default_handler is None:
            registered_ids: set = set(handlers.keys())
            for step in graph.steps:
                if step.status == TaskStatus.PENDING and step.step_id not in registered_ids:
                    _logger.warning(
                        "[HandlerSignatureValidator] Step '%s' has no registered "
                        "handler and no default_handler is set. It will raise "
                        "MissingHandlerError when dispatched.",
                        step.step_id,
                    )

        _logger.info(
            "[HandlerSignatureValidator] All %d handler(s) validated. "
            "default_handler=%s",
            len(handlers),
            "set" if default_handler is not None else "None",
        )

    @classmethod
    def _validate_single(cls, handler: Callable, context: str) -> None:
        """
        Validate a single callable against the NalaLoop dispatch signature.

        Counts only required positional parameters (those without defaults
        and not ``*args`` / ``**kwargs``). Requires at least 2 (``step``
        and ``session``). Also emits a DEBUG-level warning if the parameter
        names differ from the canonical names (not an error — just advisory).

        Parameters
        ----------
        handler : Callable
            The executor callable to validate.
        context : str
            Human-readable label for error messages (e.g. ``"handler['step_001']"``).

        Raises
        ------
        TypeError
            If the handler has fewer than 2 required positional parameters,
            or if ``inspect.signature()`` cannot be called on the object.
        """
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"[HandlerValidator] Cannot inspect signature of {context}: {exc}"
            ) from exc

        # Count required positional parameters (no default, not *args/**kwargs)
        required_params = [
            p for p in sig.parameters.values()
            if (
                p.default is inspect.Parameter.empty
                and p.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            )
        ]

        if len(required_params) < cls._MIN_PARAMS:
            raise TypeError(
                f"[HandlerValidator] {context} has {len(required_params)} required "
                f"positional parameter(s) but NalaLoop dispatch requires at least "
                f"{cls._MIN_PARAMS} (step: TaskStep, session: SessionState). "
                f"Actual signature: {sig}"
            )

        # Advisory check on parameter names (DEBUG only — not a hard error)
        actual_names = [p.name for p in required_params[:2]]
        for expected, actual in zip(cls._EXPECTED_PARAM_NAMES, actual_names):
            if actual not in (expected, "_", "__"):
                _logger.debug(
                    "[HandlerValidator] %s param[%d] name is %r (expected %r). "
                    "Name mismatch is advisory — handler is still accepted.",
                    context,
                    cls._EXPECTED_PARAM_NAMES.index(expected),
                    actual,
                    expected,
                )


# ==============================================================================
# SECTION 5 — RunawayLoopGuard
# ==============================================================================

class RunawayLoopGuard:
    """
    Detects persistent crash loop patterns in a recovered ``SessionState``
    and halts recovery before any API calls are made.

    If ``state_matrix.error_count`` meets or exceeds the configured ceiling,
    ``RunawayLoopError`` is raised. This prevents unbounded API spend and
    runaway token costs on sessions that consistently crash.

    The guard runs BEFORE handler re-binding and BEFORE ``NalaLoop`` is
    instantiated, guaranteeing no API calls occur on a fatally broken session.

    Risk mitigated: RISK-025 — Infinite reboot loops on persistent failures.

    Constants
    ---------
    DEFAULT_MAX_ERRORS  : Default error count ceiling (10).
    DEFAULT_MAX_RETRIES : Informational — max per-step retries before step is FAILED.
    WARNING_THRESHOLD   : Fraction of ceiling at which a WARNING is emitted (0.7).
    """

    DEFAULT_MAX_ERRORS:  int   = 10
    DEFAULT_MAX_RETRIES: int   = 5
    WARNING_THRESHOLD:   float = 0.7

    @classmethod
    def check(
        cls,
        session:    SessionState,
        max_errors: int = DEFAULT_MAX_ERRORS,
    ) -> None:
        """
        Evaluate the session's error state and raise ``RunawayLoopError`` if
        the error count ceiling has been reached.

        Also emits a WARNING-level log if error_count exceeds 70% of the
        ceiling, giving the operator early notice before a hard halt.

        Parameters
        ----------
        session    : SessionState  The recovered session to evaluate.
        max_errors : int           The error count ceiling (default 10).

        Raises
        ------
        RunawayLoopError
            If ``state_matrix.error_count >= max_errors``.
        """
        sm:  StateMatrix = session.state_matrix
        lsn: int         = session.checkpoint_meta.lsn

        # ── Hard halt check ───────────────────────────────────────────────────
        if sm.error_count >= max_errors:
            _logger.critical(
                "[RunawayLoopGuard] HARD HALT triggered for session '%s' at LSN=%d. "
                "error_count=%d >= MAX_ERRORS=%d. "
                "Manual inspection required before retrying.",
                session.session_id, lsn, sm.error_count, max_errors,
            )
            raise RunawayLoopError(
                session_id=session.session_id,
                error_count=sm.error_count,
                max_errors=max_errors,
                last_lsn=lsn,
            )

        # ── Warning threshold check (early notice to operator) ────────────────
        warning_threshold = max_errors * cls.WARNING_THRESHOLD
        if sm.error_count >= warning_threshold:
            _logger.warning(
                "[RunawayLoopGuard] High error count for session '%s' at LSN=%d: "
                "%d/%d errors (%.0f%% of halt threshold). "
                "Approaching hard halt ceiling.",
                session.session_id, lsn, sm.error_count, max_errors,
                (sm.error_count / max_errors) * 100,
            )

        # ── Zero-token + positive error count: possible config issue ──────────
        if sm.error_count > 0 and sm.total_tokens_in == 0:
            _logger.warning(
                "[RunawayLoopGuard] Session '%s' at LSN=%d has error_count=%d "
                "but total_tokens_in=0. "
                "Session may have crashed before making any LLM calls. "
                "Possible environment or configuration issue — allowing one recovery attempt.",
                session.session_id, lsn, sm.error_count,
            )

        _logger.info(
            "[RunawayLoopGuard] Session '%s' at LSN=%d cleared. "
            "error_count=%d (ceiling=%d).",
            session.session_id, lsn, sm.error_count, max_errors,
        )


# ==============================================================================
# SECTION 6 — ARIES Redo Phase Helper
# ==============================================================================

def _apply_redo_phase(session: SessionState) -> List[str]:
    """
    ARIES Redo Phase: Reset all steps in ``RUNNING`` status back to ``PENDING``.

    A step found in ``RUNNING`` state at recovery time was interrupted mid-execution
    (the process was killed before the step could be marked ``SUCCESS`` or ``FAILED``).
    The step's result was never written. Resetting it to ``PENDING`` allows the
    scheduler to re-dispatch it safely without skipping it.

    This operation is **idempotent** — calling it multiple times produces the
    same result. Steps already in ``PENDING`` are untouched.

    Additional cleanup performed for each RUNNING → PENDING transition:
      - ``step.started_at`` is cleared to ``None`` (interrupted start is invalid)
      - ``step.tool_used`` is cleared to ``None`` (partial assignment is invalid)

    Risk mitigated: RISK-028 — OOM kill leaves RUNNING step in permanent RUNNING state.

    Parameters
    ----------
    session : SessionState
        The recovered session. Mutates ``session.task_graph.steps`` in-place.

    Returns
    -------
    List[str]
        List of ``step_id`` values that were reset from RUNNING → PENDING.
        Empty list if no steps were in RUNNING state.
    """
    reset_ids: List[str] = []

    for step in session.task_graph.steps:
        if step.status == TaskStatus.RUNNING:
            step.status     = TaskStatus.PENDING
            step.started_at = None    # Clear the interrupted start timestamp
            step.tool_used  = None    # Clear partial tool assignment
            reset_ids.append(step.step_id)
            _logger.info(
                "[Recovery Redo] Step '%s' reset: RUNNING → PENDING "
                "(was interrupted at crash time).",
                step.step_id,
            )

    if not reset_ids:
        _logger.info(
            "[Recovery Redo] No RUNNING steps found. "
            "Session '%s' was in a clean inter-step state at crash time.",
            session.session_id,
        )

    return reset_ids


# ==============================================================================
# SECTION 7 — HandoffSpore Fallback Helper
# ==============================================================================

def _rebuild_from_spore(
    spore_path:          Path,
    original_session_id: str,
) -> SessionState:
    """
    Rebuild a runnable ``SessionState`` from a ``HandoffSpore`` JSON file.

    Called as the **last resort** when all checkpoint LSNs are unavailable
    or corrupted. The spore file provides enough information to reconstruct:
      - A new session identity (new UUID from the spore)
      - The original user objective (never summarized)
      - The remaining (not-yet-SUCCESS) steps to execute
      - Accumulated telemetry (tokens, cost, elapsed, LSN) from the spore

    The ``crystallized_history``, ``active_variables``, and
    ``bootstrap_instructions`` fields from the spore are injected into
    ``session.metadata`` so executor agents have full prior context.

    Risk mitigated: RISK-029 — All checkpoints corrupt AND no spore → fatal.

    Parameters
    ----------
    spore_path : Path
        Absolute path to the ``handoff.spore.json`` file on disk.
    original_session_id : str
        The session UUID of the crashed session (for metadata and logging).

    Returns
    -------
    SessionState
        A fully reconstructed, Pydantic-validated, runnable SessionState.

    Raises
    ------
    SessionRecoveryError
        If the spore file does not exist, is corrupt, or fails Pydantic validation.
    """


    _logger.info(
        "[Recovery Spore] Attempting HandoffSpore fallback. "
        "session=%s spore=%s",
        original_session_id[:8], spore_path,
    )

    # ── Load and Pydantic-validate the spore from disk ────────────────────────
    try:
        spore = HandoffSpore.load_spore(spore_path)
    except SporeValidationError as exc:
        raise SessionRecoveryError(
            session_id=original_session_id,
            last_lsn_tried=-1,
            reason=(
                f"HandoffSpore at '{spore_path}' failed validation: {exc}. "
                f"No recovery path remains. Manual intervention required."
            ),
        ) from exc
    except FileNotFoundError as exc:
        raise SessionRecoveryError(
            session_id=original_session_id,
            last_lsn_tried=-1,
            reason=(
                f"HandoffSpore file not found at '{spore_path}'. "
                f"All checkpoint LSNs were also corrupt. "
                f"Session '{original_session_id}' cannot be recovered."
            ),
        ) from exc
    except Exception as exc:
        raise SessionRecoveryError(
            session_id=original_session_id,
            last_lsn_tried=-1,
            reason=f"Unexpected error loading HandoffSpore at '{spore_path}': {exc}",
        ) from exc

    # ── Reconstruct TaskGraph from remaining (non-SUCCESS) steps ─────────────
    remaining_steps: List[TaskStep] = []
    for step_dict in spore.task_graph_state.remaining_steps:
        try:
            remaining_steps.append(TaskStep.model_validate(step_dict))
        except Exception as exc:
            _logger.warning(
                "[Recovery Spore] Could not reconstruct TaskStep from spore dict: %s. "
                "Skipping this step. Error: %s",
                step_dict.get("step_id", "<unknown>"), exc,
            )

    # Parse done_condition from JSON string if present
    done_condition: Dict[str, Any] = {}
    if spore.done_condition:
        try:
            done_condition = json.loads(spore.done_condition)
        except json.JSONDecodeError as exc:
            _logger.warning(
                "[Recovery Spore] Could not parse done_condition JSON: %s. "
                "Using empty done_condition.",
                exc,
            )

    task_graph = TaskGraph(
        steps=remaining_steps,
        done_condition=done_condition,
    )

    # ── Rebuild StateMatrix from spore telemetry snapshot ────────────────────
    state_matrix = StateMatrix(
        total_tokens_in  = spore.telemetry_state.total_tokens_in,
        total_tokens_out = spore.telemetry_state.total_tokens_out,
        estimated_cost   = spore.telemetry_state.estimated_cost_usd,
        error_count      = spore.telemetry_state.error_count,
        elapsed_seconds  = spore.telemetry_state.elapsed_seconds,
    )

    # ── Rebuild CheckpointMeta with LSN continuity from spore ────────────────
    checkpoint_meta = CheckpointMeta(
        lsn=spore.telemetry_state.session_lsn,
    )

    # ── Assemble the recovered SessionState ──────────────────────────────────
    session = SessionState(
        session_id      = spore.new_session_id,
        objective       = spore.objective,
        state_matrix    = state_matrix,
        checkpoint_meta = checkpoint_meta,
        task_graph      = task_graph,
        metadata        = {
            "recovered_from_spore":   True,
            "original_session_id":    original_session_id,
            "spore_path":             str(spore_path),
            "crystallized_history":   spore.task_graph_state.crystallized_history,
            "active_variables":       spore.active_variables,
            "bootstrap_instructions": spore.bootstrap_instructions,
        },
    )

    _logger.info(
        "[Recovery Spore] SessionState rebuilt from HandoffSpore. "
        "new_session_id=%s | original_session_id=%s | "
        "remaining_steps=%d | LSN=%d",
        spore.new_session_id,
        original_session_id,
        len(remaining_steps),
        spore.telemetry_state.session_lsn,
    )

    return session


# ==============================================================================
# SECTION 8 — recover_session() — Public API
# ==============================================================================

def recover_session(
    session_id:          str,
    checkpoint_manager:  CheckpointManager,
    handlers:            Dict[str, Callable],
    default_handler:     Optional[Callable]        = None,
    context_tracker:     Optional[ContextTracker]  = None,
    compactor:           Optional[DronagiriCompactor] = None,
    max_errors:          int                       = RunawayLoopGuard.DEFAULT_MAX_ERRORS,
    lock_timeout_s:      int                       = LockResolver.LOCK_TIMEOUT_S,
    **loop_kwargs:       Any,
) -> NalaLoop:
    """
    Recover a crashed or paused NALA session from its latest valid checkpoint.

    This function is the **single public entry point** for all crash recovery
    operations in NALA. It implements the full ARIES Analysis → Redo → Undo
    protocol, adapted for NALA's Python + Pydantic + CheckpointManager stack.

    Recovery Pipeline
    -----------------
    Phase A.1 (Analysis — Lock)          : Resolve stale .checkpoint.lock file.
    Phase A.2 (Analysis — Checkpoint)   : Load latest SHA-256-verified checkpoint
                                          with automatic LSN-N-1 rollback chain.
    Phase A.3 (Analysis — Spore)        : If all LSNs corrupt → HandoffSpore fallback.
    Phase R.1 (Redo — Step Reset)       : Reset RUNNING → PENDING (idempotent).
    Phase R.2 (Redo — Telemetry)        : Monotonic StateMatrix correction.
    Phase R.3 (Redo — Graph Validation) : Check for cycles and dangling refs.
    Phase U.1 (Undo — Runaway Guard)    : Halt if error_count >= max_errors.
    Phase U.2 (Undo — Handler Validate) : Signature pre-flight for all callables.
    Build NalaLoop                       : Instantiate, register handlers, bind
                                          context_tracker and compactor.

    Lock Release Guarantee
    ----------------------
    The recovery lock is ALWAYS released in a ``finally`` block, regardless of
    whether any phase raises an exception. No lock leak is possible.

    Parameters
    ----------
    session_id : str
        UUID of the crashed or paused NALA session to recover.
    checkpoint_manager : CheckpointManager
        The initialized CheckpointManager for this session's checkpoint directory.
    handlers : Dict[str, Callable]
        ``{step_id: executor_callable}`` map to re-register on the recovered loop.
        Handlers from the crashed process are lost at termination; they must be
        re-provided here by the boot script.
    default_handler : Optional[Callable]
        Fallback executor for steps not covered by the ``handlers`` map. May be
        None if every step has an explicit handler entry.
    context_tracker : Optional[ContextTracker]
        JIRA-004 ContextTracker to bind to the recovered NalaLoop. If None, the
        loop runs without context window tracking.
    compactor : Optional[DronagiriCompactor]
        JIRA-004 DronagiriCompactor to bind to the recovered NalaLoop. If None,
        Dronagiri compaction is disabled for this recovery run.
    max_errors : int
        Error count ceiling for ``RunawayLoopGuard``. If the checkpoint's
        ``state_matrix.error_count`` equals or exceeds this value, recovery is
        aborted with ``RunawayLoopError``. Default: 10.
    lock_timeout_s : int
        Seconds after which a ``.checkpoint.lock`` file is considered stale and
        safe to unlink. Default: 60. Adjust for slow-startup environments.
    **loop_kwargs : Any
        Additional keyword arguments forwarded directly to ``NalaLoop.__init__()``.
        Supported: ``max_retries_per_step``, ``checkpoint_on_success_only``,
        ``hooks``.

    Returns
    -------
    NalaLoop
        A fully configured, validated NalaLoop instance ready to call ``.run()`` on.
        All handlers are registered, context_tracker and compactor are bound.

    Raises
    ------
    SessionRecoveryLockError
        If the ``.checkpoint.lock`` file cannot be resolved within the backoff window.
    SessionRecoveryError
        If all checkpoint LSNs AND the HandoffSpore are unreadable or corrupt.
    RunawayLoopError
        If ``state_matrix.error_count >= max_errors`` (hard halt guard triggered).
    CheckpointNotFoundError
        If no checkpoint directory or files exist for the given session_id.
    TypeError
        If any registered handler has a signature incompatible with NalaLoop dispatch.
    ValueError
        If the recovered TaskGraph fails structural validation (cycles or dangling refs).

    Example
    -------
    >>> from pathlib import Path
    >>> from core.harness import CheckpointManager
    >>> from core.harness.recovery import recover_session
    >>>
    >>> cm = CheckpointManager(base_dir=Path("data/checkpoints"))
    >>>
    >>> def my_handler(step, session):
    ...     return StepResult(success=True, output={"done": True})
    >>>
    >>> loop = recover_session(
    ...     session_id="dead-beef-...",
    ...     checkpoint_manager=cm,
    ...     handlers={"step_001": my_handler},
    ...     default_handler=my_handler,
    ...     max_errors=10,
    ... )
    >>> status = loop.run()
    """
    _logger.info(
        "[Recovery] ═══ Starting crash recovery for session_id=%s ═══",
        session_id,
    )

    # ── Apply custom lock timeout to the class-level constant ─────────────────
    # This is set before resolution so LockResolver.resolve() uses the caller's
    # configured timeout for the stale detection age check.
    original_lock_timeout       = LockResolver.LOCK_TIMEOUT_S
    LockResolver.LOCK_TIMEOUT_S = lock_timeout_s

    lock_path: Optional[Path] = None

    try:
        # ══════════════════════════════════════════════════════════════════════
        # Phase A.1 — Lock Resolution
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase A.1: Lock resolution. session=%s", session_id[:8]
        )
        lock_path = LockResolver.resolve(
            session_id=session_id,
            base_dir=checkpoint_manager.base_dir,
        )

        # ══════════════════════════════════════════════════════════════════════
        # Phase A.2 — Checkpoint Load with SHA-256 Rollback Chain
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase A.2: Checkpoint load. session=%s", session_id[:8]
        )

        session: Optional[SessionState] = None
        last_lsn_tried: int = -1

        try:
            session        = checkpoint_manager.load_latest(session_id)
            last_lsn_tried = session.checkpoint_meta.lsn
            _logger.info(
                "[Recovery] Checkpoint loaded at LSN=%d. session=%s",
                last_lsn_tried, session_id[:8],
            )

        except CheckpointNotFoundError as exc:
            # No checkpoint directory or files exist at all
            _logger.error(
                "[Recovery] No checkpoints found for session '%s'. "
                "Attempting HandoffSpore fallback. Error: %s",
                session_id, exc,
            )
            spore_path = checkpoint_manager.base_dir / session_id / "handoff.spore.json"
            session        = _rebuild_from_spore(spore_path, session_id)
            last_lsn_tried = session.checkpoint_meta.lsn

        except CheckpointRecoveryError as exc:
            # All checkpoint LSNs were attempted and all failed integrity checks
            _logger.error(
                "[Recovery] All checkpoint LSNs corrupt for session '%s'. "
                "Attempting HandoffSpore fallback. Error: %s",
                session_id, exc,
            )

            # ── Phase A.3: HandoffSpore Fallback ─────────────────────────────
            _logger.info(
                "[Recovery] Phase A.3: HandoffSpore fallback. session=%s",
                session_id[:8],
            )
            spore_path = checkpoint_manager.base_dir / session_id / "handoff.spore.json"
            session        = _rebuild_from_spore(spore_path, session_id)
            last_lsn_tried = session.checkpoint_meta.lsn

        # At this point, `session` is guaranteed to be a valid SessionState instance.
        # Both the checkpoint path and the spore path either return a session or raise.
        assert session is not None, "[NALA BUG] session is None after load phase — unreachable"

        # ══════════════════════════════════════════════════════════════════════
        # Phase R.1 — ARIES Redo: Reset RUNNING → PENDING
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase R.1: ARIES Redo phase (RUNNING → PENDING). "
            "session=%s LSN=%d",
            session_id[:8], session.checkpoint_meta.lsn,
        )
        reset_ids: List[str] = _apply_redo_phase(session)
        if reset_ids:
            _logger.info(
                "[Recovery] Redo phase reset %d RUNNING step(s) to PENDING: %s",
                len(reset_ids), reset_ids,
            )

        # ══════════════════════════════════════════════════════════════════════
        # Phase R.2 — StateMatrix Monotonic Correction
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase R.2: StateMatrix monotonic correction. session=%s",
            session_id[:8],
        )
        correction_report: Dict[str, Any] = StateMatrixValidator.validate_reconstructed(session)

        # ══════════════════════════════════════════════════════════════════════
        # Phase R.3 — TaskGraph Structural Validation
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase R.3: TaskGraph validation. session=%s", session_id[:8]
        )
        session.validate_task_graph()

        # ══════════════════════════════════════════════════════════════════════
        # Phase U.1 — Runaway Loop Guard (Hard Halt Check)
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase U.1: Runaway loop guard check. "
            "error_count=%d ceiling=%d session=%s",
            session.state_matrix.error_count, max_errors, session_id[:8],
        )
        RunawayLoopGuard.check(session, max_errors=max_errors)

        # ══════════════════════════════════════════════════════════════════════
        # Phase U.2 — Handler Signature Pre-Flight Validation
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Phase U.2: Handler signature validation. "
            "handlers=%d default=%s session=%s",
            len(handlers),
            "set" if default_handler is not None else "None",
            session_id[:8],
        )
        HandlerSignatureValidator.validate_all(
            handlers=handlers,
            default_handler=default_handler,
            graph=session.task_graph,
        )

        # ══════════════════════════════════════════════════════════════════════
        # Build NalaLoop — Instantiate, Register Handlers, Bind Components
        # ══════════════════════════════════════════════════════════════════════
        _logger.info(
            "[Recovery] Building NalaLoop. session=%s pending_steps=%d",
            session_id[:8], session.task_graph.pending_count(),
        )

        loop = NalaLoop(
            session=session,
            checkpoint_manager=checkpoint_manager,
            context_tracker=context_tracker,
            compactor=compactor,
            **loop_kwargs,
        )

        # Register all step-level handlers
        for step_id, handler in handlers.items():
            loop.register_handler(step_id, handler)
            _logger.debug(
                "[Recovery] Handler registered for step_id='%s'. session=%s",
                step_id, session_id[:8],
            )

        # Set fallback default handler if provided
        if default_handler is not None:
            loop.set_default_handler(default_handler)
            _logger.debug("[Recovery] Default handler set. session=%s", session_id[:8])

        # ── Final success log ─────────────────────────────────────────────────
        _logger.info(
            "[Recovery] ═══ SUCCESS ═══ "
            "session_id=%s | LSN=%d | pending_steps=%d | "
            "redo_resets=%d | corrections=%s | "
            "handlers=%d | default_handler=%s",
            session.session_id,
            session.checkpoint_meta.lsn,
            session.task_graph.pending_count(),
            len(reset_ids),
            correction_report if correction_report else "none",
            len(handlers),
            "set" if default_handler is not None else "None",
        )

        return loop

    except (SessionRecoveryLockError, SessionRecoveryError, RunawayLoopError):
        # Re-raise NALA-domain exceptions unchanged — already fully logged above
        raise

    except Exception as exc:
        # Wrap any unexpected exception in a SessionRecoveryError for uniform
        # handling at the caller level
        _logger.critical(
            "[Recovery] Unexpected error during recovery for session '%s'. "
            "last_lsn_tried=%d. Error: %s: %s",
            session_id, last_lsn_tried, type(exc).__name__, exc,
            exc_info=True,
        )
        raise SessionRecoveryError(
            session_id=session_id,
            last_lsn_tried=last_lsn_tried,
            reason=f"Unexpected {type(exc).__name__}: {exc}",
        ) from exc

    finally:
        # ── ALWAYS release the lock — no lock leak on ANY code path ──────────
        if lock_path is not None:
            LockResolver.release(lock_path)
            _logger.debug(
                "[Recovery] Lock released in finally block. session=%s lock=%s",
                session_id[:8], lock_path,
            )

        # Restore original class-level lock timeout to avoid cross-call side effects
        LockResolver.LOCK_TIMEOUT_S = original_lock_timeout


# ==============================================================================
# SECTION 9 — Module-level __all__ export
# ==============================================================================

__all__ = [
    # Exception hierarchy
    "SessionRecoveryError",
    "SessionRecoveryLockError",
    "RunawayLoopError",
    # Core classes
    "LockResolver",
    "StateMatrixValidator",
    "HandlerSignatureValidator",
    "RunawayLoopGuard",
    # Module-level helpers
    "_apply_redo_phase",
    "_rebuild_from_spore",
    # Public API
    "recover_session",
]
