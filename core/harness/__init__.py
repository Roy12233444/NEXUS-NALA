"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/__init__.py
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru

PURPOSE
-------
Public API surface for the core.harness package.

Consumers of this package import from here:

    from core.harness import SessionState, CheckpointManager
    from core.harness import NalaLoop, LoopStatus, StepResult, LoopHooks

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

# ── JIRA-001: Session Contract ─────────────────────────────────────────────────
from core.harness.session_contract import (
    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)

# ── JIRA-002: Checkpoint System ────────────────────────────────────────────────
from core.harness.checkpoint import (
    CheckpointError,
    CheckpointIntegrityError,
    CheckpointLockError,
    CheckpointManager,
    CheckpointNotFoundError,
    CheckpointRecord,
    CheckpointRecoveryError,
    CheckpointWriteError,
)

# ── JIRA-003: Task Loop Orchestrator ───────────────────────────────────────────
from core.harness.nala_loop import (
    CheckpointWriteFailure,
    LoopHooks,
    LoopStatus,
    MissingHandlerError,
    NalaLoop,
    NalaLoopError,
    StepResult,
)

# ── JIRA-004: Context Window Tracker & Dronagiri Compactor ────────────────────
from core.harness.context_tracker import (
    ContextStatus,
    ContextTracker,
    DronagiriCompactor,
    TrackerConfig,
)

# ── JIRA-006: Session Handoff ─────────────────────────────────────────────────
from core.harness.session_handoff import (
    ContextExhaustedSignal,
    HandoffSpore,
    HandoffSporeModel,
    SporeTaskGraphSummary,
    SporeTelemetry,
    SporeValidationError,
)

# ── JIRA-005: Crash Recovery ──────────────────────────────────────────────────
from core.harness.recovery import (
    HandlerSignatureValidator,
    LockResolver,
    RunawayLoopError,
    RunawayLoopGuard,
    SessionRecoveryError,
    SessionRecoveryLockError,
    StateMatrixValidator,
    recover_session,
)

__all__ = [
    # JIRA-001
    "utcnow",
    "TaskStatus",
    "TaskStep",
    "TaskGraph",
    "CheckpointMeta",
    "StateMatrix",
    "SessionState",
    # JIRA-002
    "CheckpointManager",
    "CheckpointRecord",
    "CheckpointError",
    "CheckpointNotFoundError",
    "CheckpointIntegrityError",
    "CheckpointWriteError",
    "CheckpointRecoveryError",
    "CheckpointLockError",
    # JIRA-003
    "NalaLoop",
    "LoopStatus",
    "StepResult",
    "LoopHooks",
    "NalaLoopError",
    "MissingHandlerError",
    "CheckpointWriteFailure",
    # JIRA-004
    "ContextStatus",
    "ContextTracker",
    "DronagiriCompactor",
    "TrackerConfig",
    # JIRA-005
    "SessionRecoveryError",
    "SessionRecoveryLockError",
    "RunawayLoopError",
    "LockResolver",
    "StateMatrixValidator",
    "HandlerSignatureValidator",
    "RunawayLoopGuard",
    "recover_session",
    # JIRA-006
    "ContextExhaustedSignal",
    "HandoffSpore",
    "HandoffSporeModel",
    "SporeTaskGraphSummary",
    "SporeTelemetry",
    "SporeValidationError",
]


