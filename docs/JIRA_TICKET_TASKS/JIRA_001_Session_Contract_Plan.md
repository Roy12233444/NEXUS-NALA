# JIRA-001 — Define Session Contract
## Advanced Implementation Plan
**NALA: Nexus Autonomous Long-Running Agent**
**Nexus Lab AI Research Lab | Bengaluru, India**
**Ticket Priority: Highest | Estimate: 2 Days | Phase: 1**

---

## 📌 Ticket Summary

| Field | Value |
|---|---|
| **Ticket ID** | JIRA-001 |
| **Epic** | NALA-001 — Long-Running Survival Foundation |
| **Summary** | Define Session Contract |
| **Description** | Create the core state schema for all NALA sessions |
| **Priority** | Highest |
| **Estimate** | 2 Days |
| **Dependencies** | None (First brick) |
| **Phase** | Phase 1 — Core Harness |
| **Target File** | `core/harness/session_contract.py` |

---

## 🎯 Why This Ticket Exists

Every system that needs to survive crashes, restarts, and interruptions must answer one fundamental question:

> **"What exactly do I need to save in order to resume exactly where I left off?"**

The Session Contract is the complete answer to that question. It is the single source of truth — a validated, serializable, reconstructible data model that defines what NALA's state looks like at any given moment in time.

Without the Session Contract, checkpoints have nothing to write, recovery has nothing to read, and the long-running loop has nothing to resume from. It is the first brick. Everything else is built on top of it.

---

## 🏗️ Full Architecture of the Session Contract

The Session Contract is composed of **5 nested classes**. Each class has a precise responsibility.

![Session Contract Diagram](/C:/Users/soura/.gemini/antigravity-ide/brain/4ad1dfb4-0382-4d69-b4bd-11613ba5a0d0/session_contract_diagram_1781082101075.png)

```
SessionState (Root Object)
│
├── session_id            → Unique run identifier (UUID)
├── objective             → Original user task/goal (immutable)
├── created_at            → Timestamp of when this run started
├── last_updated          → Timestamp of last state mutation
│
├── StateMatrix           → Live telemetry and resource counters
│   ├── total_tokens_in   → Input tokens consumed so far
│   ├── total_tokens_out  → Output tokens generated so far
│   ├── elapsed_seconds   → Total wall-clock time elapsed
│   ├── estimated_cost    → Accumulated API cost (USD)
│   ├── error_count       → Number of errors across all steps
│   └── active_agents     → List of currently active agent roles
│
├── CheckpointMeta        → Persistence tracking metadata
│   ├── lsn               → Log Sequence Number (monotonically increasing)
│   ├── timestamp         → Exact datetime of last checkpoint write
│   └── content_hash      → SHA-256 hash of the saved JSON for integrity check
│
└── TaskGraph             → The plan: what must be done and in what order
    ├── current_step_id   → ID of the step NALA is currently on
    ├── done_condition    → The structured done condition (from done_condition.json)
    └── steps: List[TaskStep]
        └── TaskStep
            ├── step_id       → Unique string identifier (e.g., "task_002_edit_file")
            ├── description   → Human-readable description of what this step does
            ├── status        → TaskStatus Enum (PENDING, RUNNING, SUCCESS, FAILED)
            ├── dependencies  → List of step_ids that must be SUCCESS before this runs
            ├── tool_used     → Name of the tool that executed this step (if any)
            ├── result        → Dict of outputs produced (files changed, values returned)
            ├── error_message → Error string if status is FAILED
            └── retries       → Number of retry attempts made
```

---

## 📂 File Location & Structure

```
E:\NALA-Project\nala\
└── core\
    └── harness\
        └── session_contract.py    ← TARGET FILE for this ticket
```

---

## 🔢 Day 1 Plan — Design & Core Schema Writing

### Day 1 — Morning (2 hours): Setup & Dependencies
*   Install Pydantic v2 in the project environment.
*   Add Pydantic to `pyproject.toml` as a dependency.
*   Create the `core/__init__.py` and `core/harness/__init__.py` files as Python packages.

### Day 1 — Afternoon (4 hours): Write Classes 1, 2 & 3

#### Class 1: `TaskStatus` Enum
Define four states that any single execution step can be in:
```python
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
```
*   **Why `str, Enum`?** By inheriting from both `str` and `Enum`, the status values are directly serializable to JSON strings without extra conversion code.

#### Class 2: `TaskStep` Model
Defines a single node in the task graph:
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TaskStep(BaseModel):
    step_id:       str
    description:   str
    status:        TaskStatus = TaskStatus.PENDING
    dependencies:  List[str] = Field(default_factory=list)
    tool_used:     Optional[str] = None
    result:        Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retries:       int = 0
```

#### Class 3: `TaskGraph` Model
Wraps the full list of steps and tracks the pointer to the active step:
```python
class TaskGraph(BaseModel):
    current_step_id: Optional[str] = None
    done_condition:  Dict[str, Any] = Field(default_factory=dict)
    steps:           List[TaskStep] = Field(default_factory=list)

    def get_next_pending_step(self) -> Optional[TaskStep]:
        """Return the next PENDING step whose dependencies are all SUCCESS."""
        done_ids = {s.step_id for s in self.steps if s.status == TaskStatus.SUCCESS}
        for step in self.steps:
            if step.status == TaskStatus.PENDING:
                if all(dep in done_ids for dep in step.dependencies):
                    return step
        return None

    def is_complete(self) -> bool:
        """Return True if all steps are SUCCESS."""
        return all(s.status == TaskStatus.SUCCESS for s in self.steps)

    def has_failed(self) -> bool:
        """Return True if any step is in FAILED status."""
        return any(s.status == TaskStatus.FAILED for s in self.steps)
```

---

## 🔢 Day 2 Plan — Classes 4, 5 + Serialization + Unit Tests

### Day 2 — Morning (3 hours): Write Classes 4 & 5

#### Class 4: `CheckpointMeta` Model
Tracks the persistence audit trail:
```python
from datetime import datetime
import hashlib, json

class CheckpointMeta(BaseModel):
    lsn:          int = 0
    timestamp:    datetime = Field(default_factory=datetime.utcnow)
    content_hash: Optional[str] = None

    def compute_hash(self, state_json: str) -> str:
        """SHA-256 hash of the serialized state JSON string."""
        return hashlib.sha256(state_json.encode("utf-8")).hexdigest()
```

#### Class 5: `StateMatrix` Model
Tracks resource usage and runtime telemetry:
```python
class StateMatrix(BaseModel):
    total_tokens_in:  int   = 0
    total_tokens_out: int   = 0
    elapsed_seconds:  float = 0.0
    estimated_cost:   float = 0.0
    error_count:      int   = 0
    active_agents:    List[str] = Field(default_factory=list)
```

#### The Root `SessionState` Model
The final root class that wraps all four sub-models:
```python
import uuid

class SessionState(BaseModel):
    session_id:   str      = Field(default_factory=lambda: str(uuid.uuid4()))
    objective:    str
    created_at:   datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    state_matrix:    StateMatrix    = Field(default_factory=StateMatrix)
    checkpoint_meta: CheckpointMeta = Field(default_factory=CheckpointMeta)
    task_graph:      TaskGraph      = Field(default_factory=TaskGraph)

    def serialize(self) -> str:
        """Convert the entire session state to a JSON string for disk storage."""
        return self.model_dump_json(indent=2)

    @classmethod
    def deserialize(cls, json_str: str) -> "SessionState":
        """Reconstruct the full session state object from a JSON string."""
        return cls.model_validate_json(json_str)
```

### Day 2 — Afternoon (3 hours): Write Unit Test File

File: `tests/unit/test_session_contract.py`

**Test 1:** A new `SessionState` can be created with a valid objective.
**Test 2:** `TaskStatus` enum serializes/deserializes correctly as strings.
**Test 3:** `TaskGraph.get_next_pending_step()` returns the correct next step.
**Test 4:** `TaskGraph.get_next_pending_step()` correctly respects dependency ordering.
**Test 5:** `TaskGraph.is_complete()` returns `True` only when all steps are `SUCCESS`.
**Test 6:** `SessionState.serialize()` produces valid JSON output.
**Test 7:** `SessionState.deserialize()` can reconstruct a full object from valid JSON.
**Test 8:** `CheckpointMeta.compute_hash()` produces a reproducible SHA-256 hash.
**Test 9:** `LSN` increments correctly on repeated checkpoint updates.
**Test 10:** Creating a `TaskStep` with a string type error raises a `ValidationError`.

---

## ✅ Definition of Done

The JIRA-001 ticket is **complete** when ALL of the following pass:

| Check | Requirement |
|---|---|
| ✅ | `core/harness/session_contract.py` exists and is importable |
| ✅ | `SessionState` class has `session_id`, `objective`, `task_graph`, `state_matrix`, `checkpoint_meta` |
| ✅ | `TaskGraph` has `current_step_id` pointer and a list of `TaskStep` objects |
| ✅ | `TaskStep` has `step_id`, `description`, `status`, and `dependencies` |
| ✅ | `TaskStatus` is an enum with `PENDING`, `RUNNING`, `SUCCESS`, `FAILED` |
| ✅ | `CheckpointMeta` has `lsn`, `timestamp`, and `content_hash` |
| ✅ | `serialize()` produces valid JSON |
| ✅ | `deserialize()` reconstructs an identical Python object from that JSON |
| ✅ | All 10 unit tests in `test_session_contract.py` pass |
| ✅ | No runtime errors when creating a `SessionState` with a realistic multi-step task graph |

---

## ⚠️ Known Risks & Mitigation — Advanced Engineering Analysis

> This section documents every known risk for `session_contract.py` with full root-cause analysis,
> exact failure scenarios, code-level fixes, detection strategies, and acceptance tests.
> Every risk here was identified from real-world production failures in long-running agent systems.

![Session Runtime Diagram](/C:/Users/soura/.gemini/antigravity-ide/brain/4ad1dfb4-0382-4d69-b4bd-11613ba5a0d0/session_runtime_diagram_1781098106354.png)

---

### 🔴 RISK-001 — Pydantic v1 vs v2 API Incompatibility

**Severity:** CRITICAL — Will cause immediate import crash on startup.
**Probability:** HIGH — Pydantic v2 was released in 2023 and broke backwards compatibility entirely.

#### Exact Failure Scenario
```
# If Pydantic v1 is installed and you call v2 API:
session = SessionState(objective="Run task")
session.model_dump_json()       # ❌ AttributeError: 'SessionState' has no attribute 'model_dump_json'

# If Pydantic v2 is installed and you call v1 API:
session.json()                   # ❌ PydanticUserError: .json() removed in v2, use .model_dump_json()
SessionState.parse_raw(json_str) # ❌ AttributeError: 'parse_raw' was removed in v2
```

#### Root Cause
Pydantic v2 was rewritten from Python to Rust (via `pydantic-core`) for 5–50x speed gains.
This forced breaking API changes. The methods `.json()`, `.dict()`, `.parse_raw()`, `.parse_obj()`
were all removed or deprecated. There is **no automatic fallback** — it will raise errors immediately.

#### What This Breaks in NALA
| Broken Method | Was Used For | v2 Replacement |
|---|---|---|
| `session.json()` | `serialize()` to save checkpoint to disk | `session.model_dump_json()` |
| `session.dict()` | Converting to Python dict for logging | `session.model_dump()` |
| `SessionState.parse_raw(json_str)` | `deserialize()` to load from disk | `SessionState.model_validate_json(json_str)` |
| `SessionState.parse_obj(dict_obj)` | Loading from a Python dictionary | `SessionState.model_validate(dict_obj)` |
| `@validator` decorator | Field-level custom validation | `@field_validator` decorator |
| `class Config:` block | Model-level configuration | `model_config = ConfigDict(...)` |

#### Code-Level Fix (Enforced in `session_contract.py`)
```python
# ✅ CORRECT — Pydantic v2 only
from pydantic import BaseModel, Field, ConfigDict, field_validator

class SessionState(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,   # Auto-strip whitespace from string fields
        validate_assignment=True,    # Re-validate fields when they are mutated after creation
        use_enum_values=True,        # Store enum values as their primitive type (str), not Enum object
    )

    def serialize(self) -> str:
        return self.model_dump_json(indent=2)   # ✅ v2 method

    @classmethod
    def deserialize(cls, json_str: str) -> "SessionState":
        return cls.model_validate_json(json_str)  # ✅ v2 method
```

#### Dependency Pin — `pyproject.toml`
```toml
[project]
dependencies = [
    "pydantic>=2.0,<3.0",   # Pin to v2. Reject both v1 and future v3 until tested.
]

[tool.pytest.ini_options]
# Always run pydantic version check as first test
```

#### Detection Strategy
```python
# Add this guard at the TOP of session_contract.py
import pydantic
if int(pydantic.VERSION.split(".")[0]) < 2:
    raise RuntimeError(
        f"NALA requires Pydantic v2+. Detected: {pydantic.VERSION}. "
        "Run: pip install 'pydantic>=2.0'"
    )
```

#### Acceptance Test (Test 10 in `test_session_contract.py`)
```python
def test_pydantic_version_is_v2():
    """Guarantee the environment has Pydantic v2 installed."""
    import pydantic
    major_version = int(pydantic.VERSION.split(".")[0])
    assert major_version >= 2, f"Pydantic v2 required, found v{pydantic.VERSION}"
```

---

### 🟠 RISK-002 — Datetime Timezone Confusion (Naive vs Aware)

**Severity:** HIGH — Silent data corruption. No immediate crash; wrong checkpoint loaded.
**Probability:** MEDIUM — Python default is naive datetime. Easy to introduce accidentally.

#### Exact Failure Scenario
```python
from datetime import datetime, timezone

# Two checkpoints saved by different parts of the system:
checkpoint_1_time = datetime.utcnow()             # ❌ NAIVE — no timezone info
checkpoint_2_time = datetime.now(timezone.utc)    # ✅ AWARE — UTC timezone attached

# Comparison CRASHES at runtime:
latest = max(checkpoint_1_time, checkpoint_2_time)
# TypeError: can't compare offset-naive and offset-aware datetimes
```

#### Root Cause
Python `datetime.utcnow()` returns a naive datetime object (it has no `.tzinfo` set to UTC, despite
the name saying "utc"). `datetime.now(timezone.utc)` returns an aware datetime. Mixing both causes
Python to throw a `TypeError` during comparison, or worse — silently produce wrong sort results.

#### What This Breaks in NALA
1. **Wrong checkpoint loaded on recovery.** If `checkpoint_1` is naive and `checkpoint_2` is aware,
   NALA cannot compare their timestamps to find the most recent save. It may load an older checkpoint
   and replay work that was already done (data duplication), or skip work that was not yet done (data loss).
2. **LSN comparison fails.** `CheckpointMeta.timestamp` is used alongside `lsn` to validate checkpoint
   ordering. Mixed timezones corrupt this ordering logic.
3. **`elapsed_seconds` is wrong.** If `created_at` is naive but a later timestamp is aware,
   subtracting them crashes instead of computing correct elapsed time.

#### Code-Level Fix (Enforced in `session_contract.py`)
```python
from datetime import datetime, timezone

# ✅ CORRECT — single standard UTC helper used everywhere in NALA
def utcnow() -> datetime:
    """Return current time as a timezone-aware UTC datetime. Never use datetime.utcnow()."""
    return datetime.now(timezone.utc)

class CheckpointMeta(BaseModel):
    lsn:          int      = 0
    timestamp:    datetime = Field(default_factory=utcnow)  # ✅ Always UTC-aware
    content_hash: Optional[str] = None

class SessionState(BaseModel):
    created_at:   datetime = Field(default_factory=utcnow)  # ✅ UTC-aware
    last_updated: datetime = Field(default_factory=utcnow)  # ✅ UTC-aware
```

#### Pydantic v2 Enforcement (Automatic Validator)
```python
from pydantic import field_validator

class SessionState(BaseModel):
    created_at: datetime

    @field_validator("created_at", "last_updated", mode="before")
    @classmethod
    def ensure_utc_aware(cls, v: datetime) -> datetime:
        """Automatically attach UTC timezone if a naive datetime is passed in."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)  # Force UTC if naive
        return v
```

#### Detection Strategy
```python
# Add to serialize() to catch naive datetimes before they corrupt the checkpoint:
def serialize(self) -> str:
    if self.created_at.tzinfo is None:
        raise ValueError("NALA FATAL: created_at is timezone-naive. This is a bug.")
    if self.last_updated.tzinfo is None:
        raise ValueError("NALA FATAL: last_updated is timezone-naive. This is a bug.")
    return self.model_dump_json(indent=2)
```

#### Acceptance Tests
```python
def test_session_state_timestamps_are_utc_aware():
    """All datetime fields must have UTC timezone info."""
    session = SessionState(objective="Test run")
    assert session.created_at.tzinfo is not None, "created_at must be UTC-aware"
    assert session.last_updated.tzinfo is not None, "last_updated must be UTC-aware"

def test_checkpoint_timestamp_is_utc_aware():
    """CheckpointMeta timestamp must have UTC timezone info."""
    meta = CheckpointMeta()
    assert meta.timestamp.tzinfo is not None, "CheckpointMeta.timestamp must be UTC-aware"

def test_naive_datetime_is_auto_corrected():
    """If a naive datetime is passed, Pydantic validator should attach UTC timezone."""
    naive_time = datetime(2026, 6, 10, 8, 0, 0)  # No timezone
    session = SessionState(objective="Test", created_at=naive_time)
    assert session.created_at.tzinfo is not None, "Validator should have attached UTC"
```

---

### 🟡 RISK-003 — Dependency Ordering Bugs in `TaskGraph`

**Severity:** HIGH — NALA executes tasks in wrong order or enters an infinite scheduling loop.
**Probability:** MEDIUM — Graph traversal logic is complex; easy to write subtle bugs.

#### Exact Failure Scenarios

**Scenario A — Steps run before their dependencies are ready:**
```python
# If get_next_pending_step() has a bug that ignores dependency check:
# Step 3 requires Step 1 and Step 2 to be SUCCESS.
# Bug: returns Step 3 even though Step 2 is still RUNNING.
# Result: NALA tries to use the output of Step 2 before it exists → KeyError / None crash.
```

**Scenario B — Infinite scheduling loop:**
```python
# Step A depends on Step B.
# Step B depends on Step A.
# Circular dependency: get_next_pending_step() finds no ready step and returns None forever.
# NALA's run loop spins checking for the next step, burns CPU, and never progresses.
```

**Scenario C — Steps skipped entirely:**
```python
# Bug: only checks the FIRST unmet dependency, not ALL dependencies.
# Step 3 has dependencies ["step_1", "step_2"].
# Step 1 is SUCCESS, Step 2 is PENDING.
# Bug returns Step 3 as "ready" because Step 1 is done (missed Step 2 check).
# Result: Step 3 runs with incomplete inputs → data corruption in results dict.
```

#### Root Cause
The `get_next_pending_step()` method must correctly implement a **topological sort check**:
a step is "ready" only when ALL items in its `dependencies` list have `status == TaskStatus.SUCCESS`.
The `all()` built-in must be used — not `any()`.

#### Code-Level Fix (Enforced in `session_contract.py`)
```python
class TaskGraph(BaseModel):
    current_step_id: Optional[str] = None
    done_condition:  Dict[str, Any] = Field(default_factory=dict)
    steps:           List[TaskStep] = Field(default_factory=list)

    def _get_success_ids(self) -> set[str]:
        """Return a set of step_ids that are currently in SUCCESS status."""
        return {s.step_id for s in self.steps if s.status == TaskStatus.SUCCESS}

    def get_next_pending_step(self) -> Optional[TaskStep]:
        """
        Return the first PENDING step whose ALL dependencies have completed successfully.
        Returns None if no step is ready yet (all blocked or graph is done/failed).

        Safety guarantees:
        - Uses 'all()' to check EVERY dependency, not just one.
        - Skips RUNNING steps (already being processed).
        - Skips FAILED steps (handled separately by recovery logic).
        """
        done_ids = self._get_success_ids()
        for step in self.steps:
            if step.status != TaskStatus.PENDING:
                continue  # Skip non-pending steps
            if all(dep in done_ids for dep in step.dependencies):
                return step  # ✅ Only returned if ALL deps are satisfied
        return None  # No step is ready yet

    def has_circular_dependency(self) -> bool:
        """
        Detect circular dependencies using DFS (Depth-First Search).
        Returns True if a cycle exists. NALA must reject the task graph if True.
        """
        step_map = {s.step_id: s for s in self.steps}
        visited, rec_stack = set(), set()

        def dfs(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            step = step_map.get(step_id)
            if step:
                for dep in step.dependencies:
                    if dep not in visited:
                        if dfs(dep): return True
                    elif dep in rec_stack:
                        return True  # ✅ Cycle detected
            rec_stack.discard(step_id)
            return False

        return any(dfs(s.step_id) for s in self.steps if s.step_id not in visited)

    def is_complete(self) -> bool:
        """Return True only when every step in the graph has reached SUCCESS."""
        return bool(self.steps) and all(s.status == TaskStatus.SUCCESS for s in self.steps)

    def has_failed(self) -> bool:
        """Return True if any step is permanently FAILED (not retrying)."""
        return any(s.status == TaskStatus.FAILED for s in self.steps)
```

#### Detection Strategy (Guard in `SessionState`)
```python
class SessionState(BaseModel):
    # ... fields ...

    def validate_task_graph(self) -> None:
        """Call this after setting task_graph before starting the run loop."""
        if self.task_graph.has_circular_dependency():
            raise ValueError(
                "NALA FATAL: TaskGraph has a circular dependency. "
                "NALA cannot schedule this task. Fix the task plan first."
            )
        step_ids = {s.step_id for s in self.task_graph.steps}
        for step in self.task_graph.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise ValueError(
                        f"NALA FATAL: Step '{step.step_id}' depends on '{dep}' "
                        f"which does not exist in the TaskGraph."
                    )
```

#### Acceptance Tests (Must ALL pass before JIRA-002)
```python
def test_next_pending_step_returns_correct_first_step():
    """A step with no dependencies should be returned immediately."""
    graph = TaskGraph(steps=[
        TaskStep(step_id="step_1", description="First", dependencies=[]),
        TaskStep(step_id="step_2", description="Second", dependencies=["step_1"]),
    ])
    next_step = graph.get_next_pending_step()
    assert next_step.step_id == "step_1"

def test_next_pending_step_respects_dependencies():
    """step_2 must NOT be returned until step_1 is SUCCESS."""
    graph = TaskGraph(steps=[
        TaskStep(step_id="step_1", description="First", status=TaskStatus.RUNNING),
        TaskStep(step_id="step_2", description="Second", dependencies=["step_1"]),
    ])
    next_step = graph.get_next_pending_step()
    assert next_step is None  # step_2 blocked; step_1 is RUNNING not SUCCESS

def test_next_pending_step_unblocks_after_dependency_succeeds():
    """Once step_1 is SUCCESS, step_2 should become available."""
    graph = TaskGraph(steps=[
        TaskStep(step_id="step_1", description="First", status=TaskStatus.SUCCESS),
        TaskStep(step_id="step_2", description="Second", dependencies=["step_1"]),
    ])
    next_step = graph.get_next_pending_step()
    assert next_step is not None
    assert next_step.step_id == "step_2"

def test_is_complete_only_when_all_steps_success():
    """is_complete() must return False if even one step is not SUCCESS."""
    graph = TaskGraph(steps=[
        TaskStep(step_id="step_1", status=TaskStatus.SUCCESS),
        TaskStep(step_id="step_2", status=TaskStatus.PENDING),
    ])
    assert graph.is_complete() is False
    graph.steps[1].status = TaskStatus.SUCCESS
    assert graph.is_complete() is True

def test_circular_dependency_is_detected():
    """has_circular_dependency() must return True for cyclic graphs."""
    graph = TaskGraph(steps=[
        TaskStep(step_id="step_A", description="A", dependencies=["step_B"]),
        TaskStep(step_id="step_B", description="B", dependencies=["step_A"]),
    ])
    assert graph.has_circular_dependency() is True

def test_missing_dependency_raises_on_validation():
    """validate_task_graph() must raise if a dependency step_id doesn't exist."""
    session = SessionState(
        objective="Test",
        task_graph=TaskGraph(steps=[
            TaskStep(step_id="step_1", description="A", dependencies=["ghost_step"]),
        ])
    )
    with pytest.raises(ValueError, match="does not exist in the TaskGraph"):
        session.validate_task_graph()
```

---

## 📊 Risk Summary Matrix

| Risk ID | Risk Name | Severity | Probability | Impact on NALA | Status |
|---|---|---|---|---|---|
| RISK-001 | Pydantic v1/v2 API Mismatch | 🔴 CRITICAL | HIGH | Immediate import crash | Mitigated via version pin + guard |
| RISK-002 | Datetime Timezone Naive/Aware | 🟠 HIGH | MEDIUM | Silent wrong checkpoint load | Mitigated via UTC helper + validator |
| RISK-003 | TaskGraph Dependency Bug | 🟡 HIGH | MEDIUM | Wrong task order / infinite loop | Mitigated via circular check + unit tests |

> **Rule:** JIRA-001 is **NOT complete** until all mitigation code is in place AND all tests listed
> above pass with `pytest -v`. Only then can we safely move to JIRA-002.

---

*Built at Nexus Lab AI Research Lab, Bengaluru*
*Jai Bajrang Bali 🙏*
