"""
NALA Execution Contracts
========================

Canonical protocol shared by:

    UI
      ↓
    handlers.py
      ↓
    nala_runner.py
      ↓
    NalaLoop / existing NALA core
      ↓
    TaskEvent stream
      ↓
    UI

This module defines DATA CONTRACTS only.

It must NOT:
    - execute tasks
    - call LLMs
    - access Socket.IO
    - execute sandbox code
    - write checkpoints
    - manage threads
    - perform planning

The contracts are intentionally derived from the existing NALA server
concepts: session_id, step_id, event_queue, task/session lifecycle,
checkpointing, recovery, approval, telemetry, and execution results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Helpers
# ============================================================================

def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# ============================================================================
# Enumerations
# ============================================================================


class ExecutionMode(str, Enum):
    """
    Canonical NALA execution mode.

    CHAT:
        Lightweight conversational interaction.

    INTERACTIVE:
        User-guided execution.

    AUTONOMOUS:
        NALA is allowed to execute a task through its execution pipeline.
    """

    CHAT = "chat"
    INTERACTIVE = "interactive"
    AUTONOMOUS = "autonomous"


class TaskState(str, Enum):
    """Canonical lifecycle state of a NALA task."""

    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskEventType(str, Enum):
    """
    Canonical execution event vocabulary.

    These are the normalized events that the UI and backend should
    eventually share.

    Existing server events such as step_event, step_error,
    session_complete, session_error, context_warning and
    mode_transition can be mapped into these canonical events.
    """

    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Planning
    PLANNING_STARTED = "planning.started"
    PLANNING_COMPLETED = "planning.completed"

    # Steps
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"

    # Tools
    TOOL_STARTED = "tool.started"
    TOOL_OUTPUT = "tool.output"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Sandbox
    SANDBOX_STARTED = "sandbox.started"
    SANDBOX_OUTPUT = "sandbox.output"
    SANDBOX_COMPLETED = "sandbox.completed"
    SANDBOX_FAILED = "sandbox.failed"

    # Checkpointing
    CHECKPOINT_SAVED = "checkpoint.saved"

    # Recovery
    RECOVERY_STARTED = "recovery.started"
    RECOVERY_COMPLETED = "recovery.completed"
    RECOVERY_FAILED = "recovery.failed"

    # Human approval
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RECEIVED = "approval.received"

    # Runtime / telemetry
    TELEMETRY_UPDATED = "telemetry.updated"
    HEARTBEAT = "heartbeat"
    CONTEXT_WARNING = "context.warning"

    # Mode / safety
    MODE_TRANSITION = "mode.transition"
    SAFETY_UPDATE = "safety.updated"

    # Reasoning / cognitive telemetry
    PRAMANA_ACTIVE = "pramana.active"
    PRAMANA_REASONING_CLEAR = "pramana.reasoning_clear"

    # Session compatibility
    SESSION_CREATED = "session.created"
    SESSION_COMPLETED = "session.completed"
    SESSION_ERROR = "session.error"

    # Model response compatibility
    AI_RESPONSE_START = "ai.response_start"
    AI_RESPONSE = "ai.response"

    # Generic error
    ERROR = "error"


class EventSeverity(str, Enum):
    """Severity of an emitted runtime event."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# Checkpoint Contract
# ============================================================================


class CheckpointRef(BaseModel):
    """
    Reference to an existing NALA checkpoint.

    This does NOT implement checkpoint storage.

    Existing CheckpointManager remains responsible for persistence.
    """

    model_config = ConfigDict(extra="allow")

    checkpoint_id: Optional[str] = None

    task_id: Optional[str] = None

    session_id: str

    generation_id: Optional[str] = None

    step_id: Optional[str] = None

    sequence: Optional[int] = None

    label: Optional[str] = None

    timestamp: datetime = Field(default_factory=utc_now)

    storage_reference: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Task Request
# ============================================================================


class TaskRequest(BaseModel):
    """
    Canonical request entering the NALA execution system.

    Current UI submits:
        prompt
        mode

    The legacy backend also accepts:
        force_mode
        work_mode

    These should eventually be normalized here into `mode`.
    """

    model_config = ConfigDict(extra="allow")

    request_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    session_id: Optional[str] = None

    prompt: str = Field(min_length=1)

    mode: ExecutionMode = ExecutionMode.AUTONOMOUS

    metadata: Dict[str, Any] = Field(default_factory=dict)

    client_id: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("prompt cannot be empty")

        return value


# ============================================================================
# Task
# ============================================================================


class Task(BaseModel):
    """
    Authoritative representation of one NALA execution.

    Important distinction:

        session_id = execution/conversation context

        task_id = one specific autonomous job

    This allows one session to eventually contain multiple tasks.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    session_id: str

    request_id: Optional[str] = None

    generation_id: Optional[str] = None

    goal: str

    mode: ExecutionMode = ExecutionMode.AUTONOMOUS

    state: TaskState = TaskState.CREATED

    current_step_id: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)

    started_at: Optional[datetime] = None

    updated_at: datetime = Field(default_factory=utc_now)

    completed_at: Optional[datetime] = None

    checkpoint: Optional[CheckpointRef] = None

    error: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal")
    @classmethod
    def normalize_goal(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("task goal cannot be empty")

        return value


# ============================================================================
# Task Result
# ============================================================================


class TaskResult(BaseModel):
    """
    Canonical result returned after NALA execution.

    Existing NALA results can continue to live inside `output` and
    `metadata` while the protocol becomes stable.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str

    session_id: str

    success: bool

    output: Any = None

    ai_response: Optional[str] = None

    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    tool_results: List[Dict[str, Any]] = Field(
        default_factory=list
    )

    checkpoint: Optional[CheckpointRef] = None

    errors: List[str] = Field(
        default_factory=list
    )

    execution_time: Optional[float] = None

    started_at: Optional[datetime] = None

    completed_at: datetime = Field(default_factory=utc_now)

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================================
# Task Event
# ============================================================================


class TaskEvent(BaseModel):
    """
    Canonical event emitted by NALA.

    This is the primary runtime communication object.

    Every event is attributable to a task/session and can therefore
    be consumed by:

        - Socket.IO
        - Redux
        - task graph UI
        - telemetry
        - logging
        - replay systems
        - future distributed workers
    """

    model_config = ConfigDict(
        extra="allow",
        use_enum_values=True,
    )

    event_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    event_type: TaskEventType

    session_id: str

    task_id: Optional[str] = None

    generation_id: Optional[str] = None

    step_id: Optional[str] = None

    parent_event_id: Optional[str] = None

    timestamp: datetime = Field(
        default_factory=utc_now
    )

    severity: EventSeverity = EventSeverity.INFO

    state: Optional[TaskState] = None

    message: Optional[str] = None

    payload: Dict[str, Any] = Field(
        default_factory=dict
    )

    checkpoint: Optional[CheckpointRef] = None

    sequence: Optional[int] = None

    source: str = "nala"

    @classmethod
    def create(
        cls,
        event_type: TaskEventType,
        session_id: str,
        *,
        task_id: Optional[str] = None,
        generation_id: Optional[str] = None,
        step_id: Optional[str] = None,
        state: Optional[TaskState] = None,
        message: Optional[str] = None,
        payload: Optional[Mapping[str, Any]] = None,
        severity: EventSeverity = EventSeverity.INFO,
        checkpoint: Optional[CheckpointRef] = None,
        sequence: Optional[int] = None,
        source: str = "nala",
    ) -> "TaskEvent":
        """Construct a canonical event."""

        return cls(
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            generation_id=generation_id,
            step_id=step_id,
            state=state,
            message=message,
            payload=dict(payload or {}),
            severity=severity,
            checkpoint=checkpoint,
            sequence=sequence,
            source=source,
        )

    def to_socket_payload(self) -> Dict[str, Any]:
        """
        Convert the canonical event into a Socket.IO-safe payload.

        The canonical event remains the internal source of truth.
        """

        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "generation_id": self.generation_id,
            "step_id": self.step_id,
            "parent_event_id": self.parent_event_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "state": (
                self.state.value
                if isinstance(self.state, TaskState)
                else self.state
            ),
            "message": self.message,
            "payload": self.payload,
            "checkpoint": (
                self.checkpoint.model_dump(mode="json")
                if self.checkpoint
                else None
            ),
            "sequence": self.sequence,
            "source": self.source,
        }


# ============================================================================
# Compatibility / Mapping Helpers
# ============================================================================


class LegacyEventAdapter:
    """
    Adapter for converting the current monolithic nala_server.py event
    dictionaries into canonical TaskEvent objects.

    This allows us to migrate incrementally instead of rewriting
    NalaLoop/event producers immediately.
    """

    # Existing backend event names observed in nala_server.py.
    LEGACY_MAP: Dict[str, TaskEventType] = {
        "step_event": TaskEventType.STEP_COMPLETED,
        "step_error": TaskEventType.STEP_FAILED,
        "session_complete": TaskEventType.SESSION_COMPLETED,
        "session_error": TaskEventType.SESSION_ERROR,
        "context_warning": TaskEventType.CONTEXT_WARNING,
        "mode_transition": TaskEventType.MODE_TRANSITION,
        "pramana-active": TaskEventType.PRAMANA_ACTIVE,
        "pramana-reasoning-clear": (
            TaskEventType.PRAMANA_REASONING_CLEAR
        ),
        "heartbeat": TaskEventType.HEARTBEAT,
        "ai_response_start": TaskEventType.AI_RESPONSE_START,
        "ai_response": TaskEventType.AI_RESPONSE,
        "approval_received": TaskEventType.APPROVAL_RECEIVED,
        "error": TaskEventType.ERROR,
    }

    @classmethod
    def normalize_event_type(
        cls,
        event_type: str,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> TaskEventType:
        """
        Convert an existing server event name into the canonical event type.

        Unknown legacy events are treated as generic errors rather than
        silently inventing a semantic meaning.
        """

        normalized = str(event_type).strip()

        if normalized in cls.LEGACY_MAP:
            return cls.LEGACY_MAP[normalized]

        # Existing event payloads often carry a `type`.
        if payload:
            payload_type = payload.get("type")

            if payload_type and payload_type in cls.LEGACY_MAP:
                return cls.LEGACY_MAP[payload_type]

        return TaskEventType.ERROR

    @classmethod
    def from_legacy(
        cls,
        event_type: str,
        payload: Mapping[str, Any],
        session_id: str,
        *,
        task_id: Optional[str] = None,
        generation_id: Optional[str] = None,
        sequence: Optional[int] = None,
    ) -> TaskEvent:
        """
        Convert a legacy event_queue payload into a TaskEvent.
        """

        canonical_type = cls.normalize_event_type(
            event_type,
            payload,
        )

        step_id = payload.get("step_id")

        message = payload.get("message")

        if message is None:
            message = payload.get("description")

        severity = EventSeverity.INFO

        if canonical_type in {
            TaskEventType.STEP_FAILED,
            TaskEventType.TOOL_FAILED,
            TaskEventType.SANDBOX_FAILED,
            TaskEventType.TASK_FAILED,
            TaskEventType.SESSION_ERROR,
            TaskEventType.ERROR,
        }:
            severity = EventSeverity.ERROR

        if canonical_type == TaskEventType.CONTEXT_WARNING:
            severity = EventSeverity.WARNING

        return TaskEvent.create(
            event_type=canonical_type,
            session_id=session_id,
            task_id=task_id or payload.get("task_id"),
            generation_id=(
                generation_id
                or payload.get("generation_id")
            ),
            step_id=step_id,
            message=message,
            payload=dict(payload),
            severity=severity,
            sequence=sequence,
            source="legacy_nala_server",
        )


# ============================================================================
# Task State Transition Contract
# ============================================================================


class TaskTransition(BaseModel):
    """
    Explicit state transition record.

    This does not execute the transition.

    It provides an auditable description of:

        previous state → next state
    """

    model_config = ConfigDict(extra="allow")

    task_id: str

    session_id: str

    from_state: TaskState

    to_state: TaskState

    timestamp: datetime = Field(
        default_factory=utc_now
    )

    reason: Optional[str] = None

    event_id: Optional[str] = None

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================================
# Approval Contract
# ============================================================================


class ApprovalRequest(BaseModel):
    """
    Human approval request for a paused NALA operation.

    Compatible with the existing backend approval concept:
        req_id
        approved
        modifications
    """

    model_config = ConfigDict(extra="allow")

    req_id: str

    task_id: str

    session_id: str

    step_id: Optional[str] = None

    reason: str

    risk_level: Optional[str] = None

    proposed_action: Optional[str] = None

    created_at: datetime = Field(
        default_factory=utc_now
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


class ApprovalResponse(BaseModel):
    """Response to an ApprovalRequest."""

    req_id: str

    task_id: str

    session_id: str

    approved: bool = False

    modifications: Optional[Dict[str, Any]] = None

    responded_at: datetime = Field(
        default_factory=utc_now
    )


# ============================================================================
# Telemetry Contract
# ============================================================================


class TaskTelemetry(BaseModel):
    """
    Runtime telemetry associated with a task.

    This is deliberately generic so existing telemetry such as:

        Ṛta
        Pramāṇa
        safety
        CPU/memory
        tool usage
        context usage

    can be transported without forcing those systems into contracts.py.
    """

    model_config = ConfigDict(extra="allow")

    task_id: Optional[str] = None

    session_id: str

    timestamp: datetime = Field(
        default_factory=utc_now
    )

    elapsed_seconds: Optional[float] = None

    cpu_percent: Optional[float] = None

    memory_mb: Optional[float] = None

    tokens_in: Optional[int] = None

    tokens_out: Optional[int] = None

    model_latency_ms: Optional[float] = None

    tool_latency_ms: Optional[float] = None

    sandbox_latency_ms: Optional[float] = None

    checkpoint_latency_ms: Optional[float] = None

    retry_count: int = 0

    rita_score: Optional[float] = None

    safety_score: Optional[float] = None

    context_usage: Optional[float] = None

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================================
# Task Event Factory
# ============================================================================


def task_event(
    event_type: TaskEventType,
    task: Task,
    *,
    message: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
    severity: EventSeverity = EventSeverity.INFO,
    checkpoint: Optional[CheckpointRef] = None,
    sequence: Optional[int] = None,
) -> TaskEvent:
    """
    Convenience factory for events associated with an existing Task.
    """

    return TaskEvent.create(
        event_type=event_type,
        session_id=task.session_id,
        task_id=task.task_id,
        generation_id=task.generation_id,
        step_id=task.current_step_id,
        state=task.state,
        message=message,
        payload=payload,
        severity=severity,
        checkpoint=checkpoint,
        sequence=sequence,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Enums
    "ExecutionMode",
    "TaskState",
    "TaskEventType",
    "EventSeverity",

    # Core contracts
    "TaskRequest",
    "Task",
    "TaskEvent",
    "TaskResult",
    "CheckpointRef",

    # Runtime contracts
    "TaskTransition",
    "ApprovalRequest",
    "ApprovalResponse",
    "TaskTelemetry",

    # Compatibility
    "LegacyEventAdapter",

    # Helpers
    "task_event",
    "utc_now",
]