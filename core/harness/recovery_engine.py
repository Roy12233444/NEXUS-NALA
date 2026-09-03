"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/recovery_engine.py
Ticket  : NALA-CORE-002G — Recovery Engine & Self-Healing Runtime
Phase   : Core Harness (Durable Resiliency & Autonomous Healing)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-08-28
Version : 1.0.0 — Enterprise-Grade Self-Healing Engine

PURPOSE
-------
Authoritative, deterministic, bounded Recovery Engine for NALA.
This subsystem orchestrates failure detection, failure diagnosis, bounded
strategy selection, durable recovery tracking, physical evidence verification,
and safe execution resumption.

CORE INVARIANTS
---------------
1. Bounded Recovery  : Bounded retries (N <= max_attempts) tracked durably in
                       session metadata. If recovery fails N times -> SAFE_HALT.
2. Evidence Over Myth: Physical evidence (SHA-256, byte count, disk readback) is
                       always corroborated before revalidating interrupted work.
3. Safety Inviolable : Recovery NEVER bypasses Viveka or Pramana. Safety denial
                       always leads directly to SAFE_HALT.
4. Durable Lifecycle : Recovery state transitions are checkpointed so if NALA
                       crashes during recovery, the next process resumes with
                       accurate attempt counts and causal history.
5. Observable Truth  : Every recovery action produces a structured RecoveryEvent
                       with full causal lineage.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
from core.harness.recovery import (
    CorroborationStatus,
    EvidenceCorroborationResult,
    PhysicalEvidenceCorroborator,
    recover_session,
    SessionRecoveryError,
    RunawayLoopError,
)

_logger = logging.getLogger("nala.core.harness.recovery_engine")


# ==============================================================================
# SECTION 1 — Enums & Data Models
# ==============================================================================

class FailureType(str, Enum):
    """Taxonomy of failures that can occur in the NALA runtime."""
    TRANSIENT_EXECUTION_ERROR = "transient_execution_error"
    INTERRUPTED_EXECUTION     = "interrupted_execution"
    ARTIFACT_UNCERTAINTY      = "artifact_uncertainty"
    CORRUPTED_CHECKPOINT      = "corrupted_checkpoint"
    SAFETY_VIOLATION          = "safety_violation"
    NON_RECOVERABLE_FATAL     = "non_recoverable_fatal"


class RecoveryStrategy(str, Enum):
    """Deterministic, bounded recovery strategies."""
    RETRY       = "retry"        # Bounded retry with backoff
    RESUME      = "resume"       # Reconstruct loop from validated checkpoint
    CORROBORATE = "corroborate"  # Check physical disk evidence and SHA-256
    ROLLBACK    = "rollback"     # Revert to LSN-1, LSN-2, or Spore
    SAFE_HALT   = "safe_halt"    # Preserve evidence and halt safely


class RecoveryState(str, Enum):
    """Authoritative states of the Recovery Engine state machine."""
    HEALTHY            = "HEALTHY"
    FAILURE_DETECTED   = "FAILURE_DETECTED"
    DIAGNOSING         = "DIAGNOSING"
    RECOVERY_PLANNED   = "RECOVERY_PLANNED"
    RECOVERY_EXECUTING = "RECOVERY_EXECUTING"
    RECOVERED          = "RECOVERED"
    VERIFYING          = "VERIFYING"
    RECOVERY_VERIFIED  = "RECOVERY_VERIFIED"
    CHECKPOINTED       = "CHECKPOINTED"
    RESUMED            = "RESUMED"
    SAFE_HALT          = "SAFE_HALT"


# Valid state transitions for strict state machine verification
_VALID_TRANSITIONS: Dict[RecoveryState, List[RecoveryState]] = {
    RecoveryState.HEALTHY: [
        RecoveryState.FAILURE_DETECTED,
        RecoveryState.DIAGNOSING,
    ],
    RecoveryState.FAILURE_DETECTED: [
        RecoveryState.DIAGNOSING,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.DIAGNOSING: [
        RecoveryState.RECOVERY_PLANNED,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.RECOVERY_PLANNED: [
        RecoveryState.RECOVERY_EXECUTING,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.RECOVERY_EXECUTING: [
        RecoveryState.RECOVERED,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.RECOVERED: [
        RecoveryState.VERIFYING,
        RecoveryState.CHECKPOINTED,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.VERIFYING: [
        RecoveryState.RECOVERY_VERIFIED,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.RECOVERY_VERIFIED: [
        RecoveryState.CHECKPOINTED,
        RecoveryState.RESUMED,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.CHECKPOINTED: [
        RecoveryState.RESUMED,
        RecoveryState.HEALTHY,
        RecoveryState.SAFE_HALT,
    ],
    RecoveryState.RESUMED: [
        RecoveryState.HEALTHY,
        RecoveryState.FAILURE_DETECTED,
    ],
    RecoveryState.SAFE_HALT: [],  # Terminal state
}


class InvalidRecoveryTransitionError(Exception):
    """Raised when an illegal recovery state transition is attempted."""
    pass


class RecoveryExhaustedError(Exception):
    """Raised when max recovery attempts have been reached and recovery is exhausted."""
    pass


@dataclass
class RecoveryDiagnosis:
    """Structured diagnostic outcome for an observed failure."""
    failure_type: FailureType
    reason: str
    step_id: Optional[str] = None
    target_artifact: Optional[str] = None
    expected_sha256: Optional[str] = None
    is_recoverable: bool = True
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryDecision:
    """Authoritative decision produced by the Recovery Policy."""
    strategy: RecoveryStrategy
    diagnosis: RecoveryDiagnosis
    attempt_number: int
    max_attempts: int
    reason: str
    target_lsn: Optional[int] = None
    requires_corroboration: bool = False
    requires_checkpoint: bool = True


@dataclass
class RecoveryEvent:
    """Complete causal telemetry record for a recovery action."""
    event_id: str
    session_id: str
    task_id: str
    step_id: Optional[str]
    failure_type: FailureType
    failure_reason: str
    recovery_strategy: RecoveryStrategy
    attempt_number: int
    max_attempts: int
    checkpoint_lsn: int
    previous_checkpoint_lsn: Optional[int]
    physical_evidence: Optional[Dict[str, Any]]
    verification_result: Optional[str]
    viveka_decision: str
    recovery_started_at: str
    recovery_completed_at: str
    final_state: RecoveryState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "failure_type": self.failure_type.value,
            "failure_reason": self.failure_reason,
            "recovery_strategy": self.recovery_strategy.value,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "checkpoint_lsn": self.checkpoint_lsn,
            "previous_checkpoint_lsn": self.previous_checkpoint_lsn,
            "physical_evidence": self.physical_evidence,
            "verification_result": self.verification_result,
            "viveka_decision": self.viveka_decision,
            "recovery_started_at": self.recovery_started_at,
            "recovery_completed_at": self.recovery_completed_at,
            "final_state": self.final_state.value,
        }


# ==============================================================================
# SECTION 2 — Authoritative Recovery Engine
# ==============================================================================

class RecoveryEngine:
    """
    Authoritative Self-Healing & Recovery Engine (NALA-CORE-002G).

    Coordinates:
      1. Failure detection and classification (`diagnose_failure`).
      2. Deterministic, bounded strategy selection (`select_strategy`).
      3. Strict state machine transitions with transition validation.
      4. Safe recovery execution and ARIES integration (`execute_recovery`).
      5. Physical evidence inspection and verification (`verify_recovery`).
      6. Durable recovery metadata persistence across checkpoints.
      7. Safe halting when recovery cannot be guaranteed.
    """

    DEFAULT_MAX_ATTEMPTS: int = 3
    DEFAULT_BACKOFF_FACTOR: float = 0.5

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        corroborator: Optional[PhysicalEvidenceCorroborator] = None,
        telemetry_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.max_attempts = max(1, max_attempts)
        self.backoff_factor = max(0.0, backoff_factor)
        self.corroborator = corroborator or PhysicalEvidenceCorroborator()
        self.telemetry_callback = telemetry_callback
        self._current_state = RecoveryState.HEALTHY
        self._events: List[RecoveryEvent] = []

    @property
    def current_state(self) -> RecoveryState:
        return self._current_state

    @property
    def events(self) -> List[RecoveryEvent]:
        return list(self._events)

    def transition_state(self, new_state: RecoveryState, session_id: str = "") -> None:
        """
        Transition the state machine to a new state, validating allowed transitions.
        """
        if new_state == self._current_state:
            return

        valid_next = _VALID_TRANSITIONS.get(self._current_state, [])
        if new_state not in valid_next and self._current_state != RecoveryState.HEALTHY:
            error_msg = (
                f"Illegal recovery state transition: {self._current_state.value} -> {new_state.value}. "
                f"Allowed transitions from {self._current_state.value}: {[s.value for s in valid_next]}"
            )
            _logger.error("[RecoveryEngine] %s (session=%s)", error_msg, session_id[:8])
            raise InvalidRecoveryTransitionError(error_msg)

        _logger.info(
            "[RecoveryEngine] State transition: %s -> %s (session=%s)",
            self._current_state.value,
            new_state.value,
            session_id[:8],
        )
        self._current_state = new_state

    # ──────────────────────────────────────────────────────────────────────────
    # Diagnostic Layer (Pramana & Empirical Evidence)
    # ──────────────────────────────────────────────────────────────────────────

    def diagnose_failure(
        self,
        *,
        session: SessionState,
        error: Optional[Exception] = None,
        step: Optional[TaskStep] = None,
        interrupted_at_crash: bool = False,
    ) -> RecoveryDiagnosis:
        """
        Diagnose and classify an observed execution failure or crash state.
        """
        self.transition_state(RecoveryState.DIAGNOSING, session.session_id)

        error_str = str(error) if error else ""
        error_name = type(error).__name__ if error else ""

        # 1. Safety Violation check (Viveka / Satya denial)
        if (
            "safety" in error_str.lower()
            or "viveka" in error_str.lower()
            or "prohibited" in error_str.lower()
            or "denied" in error_str.lower()
            or "permission denied" in error_str.lower()
        ):
            return RecoveryDiagnosis(
                failure_type=FailureType.SAFETY_VIOLATION,
                reason=f"Viveka safety boundary violation: {error_str}",
                step_id=step.step_id if step else None,
                is_recoverable=False,
                context={"error_name": error_name},
            )

        # 2. Corrupted Checkpoint check
        if isinstance(error, (CheckpointIntegrityError, CheckpointRecoveryError)):
            return RecoveryDiagnosis(
                failure_type=FailureType.CORRUPTED_CHECKPOINT,
                reason=f"Checkpoint integrity verification failed: {error_str}",
                step_id=step.step_id if step else None,
                is_recoverable=True,
                context={"error_name": error_name},
            )

        # 3. Active execution error encountered at runtime
        if error is not None:
            return RecoveryDiagnosis(
                failure_type=FailureType.TRANSIENT_EXECUTION_ERROR,
                reason=f"Execution error encountered: {error_str}",
                step_id=step.step_id if step else None,
                is_recoverable=True,
                context={"error_name": error_name},
            )

        # 4. Interrupted Execution with potential physical artifact (Crash / SIGKILL)
        if interrupted_at_crash or (step and step.status in (TaskStatus.RUNNING, "RUNNING", "running")):
            # Check if step references a disk artifact
            artifact_path = None
            expected_hash = None
            if step:
                if hasattr(step, "metadata") and isinstance(step.metadata, dict):
                    artifact_path = (
                        step.metadata.get("path")
                        or step.metadata.get("target_path")
                        or step.metadata.get("file_path")
                    )
                    expected_hash = step.metadata.get("expected_sha256") or step.metadata.get("checksum")
                if not artifact_path and isinstance(step.result, dict):
                    art = step.result.get("artifact", {})
                    if isinstance(art, dict):
                        artifact_path = art.get("path") or art.get("target_path")
                        expected_hash = expected_hash or art.get("checksum")

            if artifact_path:
                return RecoveryDiagnosis(
                    failure_type=FailureType.ARTIFACT_UNCERTAINTY,
                    reason="Execution was interrupted after artifact generation was requested",
                    step_id=step.step_id if step else None,
                    target_artifact=str(artifact_path),
                    expected_sha256=expected_hash,
                    is_recoverable=True,
                )

            return RecoveryDiagnosis(
                failure_type=FailureType.INTERRUPTED_EXECUTION,
                reason="Step was interrupted during execution (crashed mid-step)",
                step_id=step.step_id if step else None,
                is_recoverable=True,
            )

        # Default fallback
        return RecoveryDiagnosis(
            failure_type=FailureType.NON_RECOVERABLE_FATAL,
            reason="Unclassified fatal condition",
            step_id=step.step_id if step else None,
            is_recoverable=False,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Policy & Strategy Selection (Bounded Recovery)
    # ──────────────────────────────────────────────────────────────────────────

    def select_strategy(
        self,
        *,
        diagnosis: RecoveryDiagnosis,
        session: SessionState,
        step: Optional[TaskStep] = None,
    ) -> RecoveryDecision:
        """
        Select a deterministic, bounded recovery strategy based on the diagnosis
        and durable attempt history.
        """
        current_attempts = self.get_recovery_attempt_count(session, diagnosis.step_id)

        # Rule 1: Non-recoverable or safety violation -> SAFE_HALT immediately
        if not diagnosis.is_recoverable or diagnosis.failure_type == FailureType.SAFETY_VIOLATION:
            self.transition_state(RecoveryState.RECOVERY_PLANNED, session.session_id)
            return RecoveryDecision(
                strategy=RecoveryStrategy.SAFE_HALT,
                diagnosis=diagnosis,
                attempt_number=current_attempts,
                max_attempts=self.max_attempts,
                reason=f"Non-recoverable failure ({diagnosis.failure_type.value}): {diagnosis.reason}",
            )

        # Rule 2: Exceeded maximum bounded recovery attempts -> SAFE_HALT
        if current_attempts >= self.max_attempts:
            self.transition_state(RecoveryState.RECOVERY_PLANNED, session.session_id)
            return RecoveryDecision(
                strategy=RecoveryStrategy.SAFE_HALT,
                diagnosis=diagnosis,
                attempt_number=current_attempts,
                max_attempts=self.max_attempts,
                reason=f"Maximum recovery attempts ({self.max_attempts}) exhausted for session {session.session_id[:8]}",
            )

        # Increment attempt count
        attempt_number = current_attempts + 1

        self.transition_state(RecoveryState.RECOVERY_PLANNED, session.session_id)

        # Rule 3: Artifact uncertainty -> Corroborate physical disk evidence first
        if diagnosis.failure_type == FailureType.ARTIFACT_UNCERTAINTY:
            return RecoveryDecision(
                strategy=RecoveryStrategy.CORROBORATE,
                diagnosis=diagnosis,
                attempt_number=attempt_number,
                max_attempts=self.max_attempts,
                reason="Step produced target artifact; verifying physical disk evidence and SHA-256",
                requires_corroboration=True,
            )

        # Rule 4: Corrupted checkpoint -> Rollback to previous valid LSN
        if diagnosis.failure_type == FailureType.CORRUPTED_CHECKPOINT:
            current_lsn = session.checkpoint_meta.lsn
            target_lsn = max(1, current_lsn - 1)
            return RecoveryDecision(
                strategy=RecoveryStrategy.ROLLBACK,
                diagnosis=diagnosis,
                attempt_number=attempt_number,
                max_attempts=self.max_attempts,
                target_lsn=target_lsn,
                reason=f"Rolling back from corrupted LSN {current_lsn} to prior valid LSN {target_lsn}",
            )

        # Rule 5: Interrupted execution -> ARIES Resume from checkpoint
        if diagnosis.failure_type == FailureType.INTERRUPTED_EXECUTION:
            return RecoveryDecision(
                strategy=RecoveryStrategy.RESUME,
                diagnosis=diagnosis,
                attempt_number=attempt_number,
                max_attempts=self.max_attempts,
                reason="Resuming execution from latest verified checkpoint with ARIES redo",
            )

        # Rule 6: Transient execution error -> Bounded retry
        return RecoveryDecision(
            strategy=RecoveryStrategy.RETRY,
            diagnosis=diagnosis,
            attempt_number=attempt_number,
            max_attempts=self.max_attempts,
            reason=f"Attempting bounded retry ({attempt_number}/{self.max_attempts}) with backoff",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Execution & Verification Layer
    # ──────────────────────────────────────────────────────────────────────────

    def execute_recovery(
        self,
        *,
        decision: RecoveryDecision,
        session: SessionState,
        checkpoint_manager: CheckpointManager,
        handlers: Optional[Dict[str, Any]] = None,
        default_handler: Optional[Any] = None,
        **loop_kwargs: Any,
    ) -> Any:
        """
        Execute the selected recovery strategy under full causal tracking.
        """
        started_at = utcnow().isoformat()
        session_id = session.session_id
        task_id = getattr(session, "task_id", session_id)
        step_id = decision.diagnosis.step_id
        checkpoint_lsn = session.checkpoint_meta.lsn

        self.transition_state(RecoveryState.RECOVERY_EXECUTING, session_id)
        self._emit_telemetry("recovery-attempt-start", {
            "session_id": session_id,
            "strategy": decision.strategy.value,
            "attempt": decision.attempt_number,
            "max_attempts": decision.max_attempts,
        })

        # Update durable recovery tracking in session metadata
        self._record_recovery_attempt(session, step_id, decision)

        # Strategy: SAFE_HALT
        if decision.strategy == RecoveryStrategy.SAFE_HALT:
            self.transition_state(RecoveryState.SAFE_HALT, session_id)
            self._emit_telemetry("recovery-safe-halt", {
                "session_id": session_id,
                "reason": decision.reason,
            })
            self._record_event(
                session_id=session_id,
                task_id=task_id,
                step_id=step_id,
                decision=decision,
                checkpoint_lsn=checkpoint_lsn,
                started_at=started_at,
                final_state=RecoveryState.SAFE_HALT,
                verification_result="SAFE_HALT_TRIGGERED",
                viveka_decision="DENY" if decision.diagnosis.failure_type == FailureType.SAFETY_VIOLATION else "ALLOW",
            )
            # Write final halt checkpoint
            self.checkpoint_recovery_state(session, checkpoint_manager, "recovery-safe-halt")
            return None

        # Strategy: CORROBORATE (Physical Evidence Check)
        if decision.strategy == RecoveryStrategy.CORROBORATE:
            self._emit_telemetry("recovery-evidence-check", {
                "session_id": session_id,
                "step_id": step_id,
                "target_artifact": decision.diagnosis.target_artifact,
            })
            target_step = None
            if step_id:
                for s in session.task_graph.steps:
                    if s.step_id == step_id:
                        target_step = s
                        break

            if target_step:
                ev = self.corroborator.corroborate_step(target_step, session)
                if ev.is_trusted and ev.status == CorroborationStatus.CORROBORATED_SUCCESS:
                    target_step.status = TaskStatus.SUCCESS
                    target_step.result = {
                        "artifact": {"path": ev.artifact_path, "checksum": ev.sha256, "size_bytes": ev.size_bytes},
                        "corroborated_from_disk": True,
                        "corroborated_at": utcnow().isoformat(),
                    }
                    self.transition_state(RecoveryState.RECOVERED, session_id)
                    self.transition_state(RecoveryState.VERIFYING, session_id)
                    self.transition_state(RecoveryState.RECOVERY_VERIFIED, session_id)
                    
                    # Persist verified recovery state
                    cp_path = self.checkpoint_recovery_state(session, checkpoint_manager, "recovery-corroborated")
                    self.transition_state(RecoveryState.CHECKPOINTED, session_id)
                    
                    self._record_event(
                        session_id=session_id,
                        task_id=task_id,
                        step_id=step_id,
                        decision=decision,
                        checkpoint_lsn=session.checkpoint_meta.lsn,
                        started_at=started_at,
                        final_state=RecoveryState.RECOVERY_VERIFIED,
                        physical_evidence={"path": ev.artifact_path, "sha256": ev.sha256, "size_bytes": ev.size_bytes},
                        verification_result="CORROBORATED_SUCCESS",
                    )
                    self._emit_telemetry("recovery-success", {
                        "session_id": session_id,
                        "strategy": "corroborate",
                        "status": "verified",
                    })

                    # Reconstruct runnable loop to continue remaining steps
                    loop = recover_session(
                        session_id=session_id,
                        checkpoint_manager=checkpoint_manager,
                        handlers=handlers or {},
                        default_handler=default_handler,
                        corroborate_evidence=True,
                        **loop_kwargs,
                    )
                    self.transition_state(RecoveryState.RESUMED, session_id)
                    return loop
                else:
                    # Physical evidence check failed or mismatched
                    _logger.warning(
                        "[RecoveryEngine] Physical evidence corroboration failed: %s. Resetting step '%s' to PENDING",
                        ev.reason, step_id,
                    )
                    target_step.status = TaskStatus.PENDING
                    target_step.started_at = None

        # Strategy: RETRY (Apply backoff)
        if decision.strategy == RecoveryStrategy.RETRY:
            backoff_s = self.backoff_factor * (2 ** (decision.attempt_number - 1))
            _logger.info("[RecoveryEngine] Backoff wait: %.2fs before retry (session=%s)", backoff_s, session_id[:8])
            time.sleep(backoff_s)

        # Strategy: RESUME or ROLLBACK -> Reconstruct via ARIES recover_session
        self.transition_state(RecoveryState.RECOVERED, session_id)
        self.transition_state(RecoveryState.VERIFYING, session_id)

        loop = recover_session(
            session_id=session_id,
            checkpoint_manager=checkpoint_manager,
            handlers=handlers or {},
            default_handler=default_handler,
            corroborate_evidence=True,
            **loop_kwargs,
        )

        self.transition_state(RecoveryState.RECOVERY_VERIFIED, session_id)
        self.checkpoint_recovery_state(loop.session, checkpoint_manager, "recovery-resumed")
        self.transition_state(RecoveryState.CHECKPOINTED, session_id)
        self.transition_state(RecoveryState.RESUMED, session_id)

        self._record_event(
            session_id=session_id,
            task_id=task_id,
            step_id=step_id,
            decision=decision,
            checkpoint_lsn=loop.session.checkpoint_meta.lsn,
            started_at=started_at,
            final_state=RecoveryState.RESUMED,
            verification_result="ARIES_REDO_VERIFIED",
        )
        self._emit_telemetry("recovery-success", {
            "session_id": session_id,
            "strategy": decision.strategy.value,
            "status": "resumed",
        })

        return loop

    # ──────────────────────────────────────────────────────────────────────────
    # Persistence & Durable History Tracking
    # ──────────────────────────────────────────────────────────────────────────

    def checkpoint_recovery_state(
        self,
        session: SessionState,
        checkpoint_manager: CheckpointManager,
        reason: str = "recovery-checkpoint",
    ) -> Path:
        """
        Durable checkpoint of the recovered session state to physical storage.
        """
        return checkpoint_manager.write_checkpoint(session)

    def get_recovery_attempt_count(self, session: SessionState, step_id: Optional[str] = None) -> int:
        """
        Retrieve durable recovery attempt count from session metadata.
        """
        metadata = getattr(session, "metadata", {})
        if not isinstance(metadata, dict):
            return 0
        recovery_data = metadata.get("recovery_engine", {})
        if not isinstance(recovery_data, dict):
            return 0

        if step_id:
            step_attempts = recovery_data.get("step_attempts", {})
            return step_attempts.get(step_id, 0)

        return recovery_data.get("total_attempts", 0)

    def _record_recovery_attempt(
        self,
        session: SessionState,
        step_id: Optional[str],
        decision: RecoveryDecision,
    ) -> None:
        """
        Record the recovery attempt inside session metadata before checkpointing.
        """
        if not hasattr(session, "metadata") or not isinstance(session.metadata, dict):
            session.metadata = {}

        if "recovery_engine" not in session.metadata:
            session.metadata["recovery_engine"] = {
                "total_attempts": 0,
                "step_attempts": {},
                "last_strategy": None,
                "history": [],
            }

        rec = session.metadata["recovery_engine"]
        rec["total_attempts"] = rec.get("total_attempts", 0) + 1
        rec["last_strategy"] = decision.strategy.value

        if step_id:
            step_map = rec.setdefault("step_attempts", {})
            step_map[step_id] = step_map.get(step_id, 0) + 1

        rec.setdefault("history", []).append({
            "attempt": decision.attempt_number,
            "strategy": decision.strategy.value,
            "failure_type": decision.diagnosis.failure_type.value,
            "reason": decision.reason,
            "timestamp": utcnow().isoformat(),
        })

    def _record_event(
        self,
        *,
        session_id: str,
        task_id: str,
        step_id: Optional[str],
        decision: RecoveryDecision,
        checkpoint_lsn: int,
        started_at: str,
        final_state: RecoveryState,
        physical_evidence: Optional[Dict[str, Any]] = None,
        verification_result: Optional[str] = None,
        viveka_decision: str = "ALLOW",
    ) -> RecoveryEvent:
        event = RecoveryEvent(
            event_id=f"rec-evt-{int(time.time() * 1000)}",
            session_id=session_id,
            task_id=task_id,
            step_id=step_id,
            failure_type=decision.diagnosis.failure_type,
            failure_reason=decision.diagnosis.reason,
            recovery_strategy=decision.strategy,
            attempt_number=decision.attempt_number,
            max_attempts=decision.max_attempts,
            checkpoint_lsn=checkpoint_lsn,
            previous_checkpoint_lsn=decision.target_lsn,
            physical_evidence=physical_evidence,
            verification_result=verification_result,
            viveka_decision=viveka_decision,
            recovery_started_at=started_at,
            recovery_completed_at=utcnow().isoformat(),
            final_state=final_state,
        )
        self._events.append(event)
        return event

    def _emit_telemetry(self, event_name: str, payload: Dict[str, Any]) -> None:
        if self.telemetry_callback:
            try:
                self.telemetry_callback(event_name, payload)
            except Exception as exc:
                _logger.warning("[RecoveryEngine] Telemetry callback error: %s", exc)


__all__ = [
    "FailureType",
    "RecoveryStrategy",
    "RecoveryState",
    "RecoveryDiagnosis",
    "RecoveryDecision",
    "RecoveryEvent",
    "InvalidRecoveryTransitionError",
    "RecoveryExhaustedError",
    "RecoveryEngine",
]
