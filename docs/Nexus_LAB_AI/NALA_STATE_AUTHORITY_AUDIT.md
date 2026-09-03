# NALA State Authority Audit

**Date**: August 14, 2026  
**Status**: AUDIT COMPLETE — EVIDENCE-BASED FORENSIC REPORT  
**Scope**: `contracts.py`, `state.py`, `nala_runner.py`, `nala_server.py`, `core/harness/`, `tests/`

---

## 1. CURRENT STATE OWNERSHIP MAP

| Subsystem | File / Component | What It Owns | What It Does NOT Own |
| :--- | :--- | :--- | :--- |
| **Runtime State Authority** | `nala_server/state.py` (`RuntimeState`) | • Authoritative `Task` instances (`_tasks`)<br>• Authoritative `SessionRecord` registry (`_sessions`)<br>• Monotonic state versioning (`_state_versions`)<br>• Transition history (`_transitions`)<br>• Rich provenance records (`_transition_provenance`)<br>• Canonical `TaskEvent` history (`_event_history`)<br>• Canonical `TaskEvent` queue (`_event_queue`)<br>• Idempotency tracking (`_committed_proposals`)<br>• Checkpoint references (`CheckpointRef`) | • Execution engine (`NalaLoop`)<br>• Checkpoint disk persistence (`CheckpointManager`)<br>• Session recovery reconstruction (`recover_session`)<br>• Transport / Socket.IO<br>• Planning / LLM calls |
| **Canonical Contracts** | `nala_server/contracts.py` | • Pure domain schemas (`Task`, `TaskRequest`, `TaskEvent`, `TaskResult`, `TaskState`, `CheckpointRef`, `TaskEventType`) | • In-memory state mutation<br>• Network transport |
| **Execution Coordinator** | `nala_server/nala_runner.py` (`NalaRunner`) | • Worker thread lifecycle (`RunnerHandle`)<br>• Ephemeral diagnostic phase (`RunnerPhase`)<br>• Approval wait events (`_ApprovalWaiter`) | • Authoritative `TaskState`<br>• Checkpoint disk writing |
| **Execution Engine** | `core/harness/nala_loop.py` (`NalaLoop`) | • Step execution loop & harness | • Global task registry<br>• Transport events |
| **Persistence Engine** | `core/harness/checkpoint.py` (`CheckpointManager`) | • Durable `.chk` files on disk | • Canonical in-memory runtime task state |

---

## 2. TRANSITION MUTATION PATHS

All state transitions in `nala_server/state.py` adhere strictly to the **Proposal $\to$ Validation $\to$ Commit** pattern:

```text
       TransitionProposal (Immutable)
                  │
                  ▼
       _validate_transition_locked()
         ├── Identity match (proposal.task_id == task.task_id)
         ├── Optimistic concurrency (expected_state_version == current_version)
         ├── Source state match (proposal.from_state == task.state)
         ├── Structural transition legality (VALID_TRANSITIONS)
         ├── Terminal evidence check (require_evidence_for_terminal_transitions)
         └── Semantic guards (DefaultTransitionGuard + custom TransitionGuard)
                  │
                  ▼
       commit_transition() [ATOMIC UNDER self._lock]
         ├── Mutation: task.state = proposal.to_state
         ├── Version bump: _state_versions[task_id] += 1
         ├── Timestamp: task.updated_at = now (started_at/completed_at)
         ├── Counters: _completed_tasks / _failed_tasks / _cancelled_tasks
         ├── Session sync: active_task_ids / completed_task_ids
         ├── Event creation: _build_event() -> _publish_event()
         ├── Provenance logging: _transition_provenance[task_id].append()
         └── Idempotency: _committed_proposals.add(proposal_id)
```

### Classification of Transition Methods

1. `propose_transition(...)` $\to$ **PROPOSAL** (Read-only, returns `TransitionProposal`).
2. `validate_transition(...)` $\to$ **VALIDATION** (Read-only dry-run).
3. `commit_transition(proposal)` $\to$ **AUTHORITATIVE COMMIT** (Exclusive mutation point).
4. `propose_and_commit(...)` $\to$ **AUTHORITATIVE CONVENIENCE** (Composes proposal + commit for trusted callers).
5. `transition_task(...)` $\to$ **COMPATIBILITY WRAPPER** (Delegates legacy calls to `propose_and_commit(actor="legacy")`).

---

## 3. CALLERS OF `transition_task()`

| File & Location | Caller | Intent / Target State |
| :--- | :--- | :--- |
| `nala_server/state.py:1747` | Definition: `def transition_task(...)` | Compatibility API wrapper |
| `nala_server/state.py:748` | Docstring example | Reference documentation |
| `nala_server/nala_runner.py:1835` | `NalaRunner._transition(task_id, state)` | Invokes `self.state.transition(task_id, state, reason)` |

---

## 4. DIRECT `Task.state` MUTATIONS OUTSIDE `RuntimeState`

* **Forensic ripgrep Query**: `.state =` across all Python source files.
* **Finding**: **0 direct `Task.state` mutations found outside `RuntimeState`**.
* The **sole** place in the entire codebase where `task.state` is assigned is:
  `nala_server/state.py: Line 1454` inside `RuntimeState.commit_transition()`:

  ```python
  task.state = proposal.to_state
  ```

---

## 5. EVENT GENERATION PATHS

1. **Canonical `TaskEvent`s (`state.py`)**:
   * Generated exclusively in `RuntimeState._build_event()` upon committed transitions or explicit `publish()`.
   * Enqueued into `_event_queue` and appended to bounded `_event_history`.
   * Assigned a strictly monotonic `sequence` integer per task.
   * `TaskEvent`s are **observations of committed state**, never the source of canonical truth.
2. **Runner-Local Observations (`nala_runner.py`)**:
   * Generated in `NalaRunner._emit()` as ephemeral `RunnerEvent` instances.
   * Published to `EventSink` / `QueueEventSink`.

---

## 6. CHECKPOINT / STATE RELATIONSHIP

* `RuntimeState.attach_checkpoint(task_id, checkpoint)`:
  * Stores lightweight `CheckpointRef` in memory on the `Task` instance.
  * Generates `TaskEventType.CHECKPOINT_CREATED` event.
  * **Does NOT write files to disk**.
* `CheckpointManager.write_checkpoint(session_state, label)`:
  * Writes binary/JSON `.chk` snapshot files to `sessions/<session_id>/checkpoints/`.
  * Returns `CheckpointRef` which is passed across the boundary into `RuntimeState`.
* **Zero state duplication**: `RuntimeState` holds the index/reference; `CheckpointManager` holds disk blobs.

---

## 7. CONCURRENCY & OPTIMISTIC LOCKING

1. **Re-entrant Lock**: All operations in `RuntimeState` synchronize on `self._lock = threading.RLock()`.
2. **Optimistic Versioning (`state_version`)**:
   * Every task initializes with `state_version = 0`.
   * Every committed transition increments `state_version` by exactly `+1`.
   * If Worker A and Worker B both create proposals at `state_version = 7`:
     * Worker A commits $\to$ task advances to `state_version = 8`.
     * Worker B attempts to commit $\to$ rejected with `StaleTransitionProposal("Stale transition proposal: expected version 7, current version 8")`.
   * **Guaranteed Prevention of Silent State Overwrites**.

---

## 8. EXISTING TEST COVERAGE & GAPS

### Existing Tests

* `tests/unit/test_session_contract.py`: Tests core `SessionState` and data contracts.
* `tests/unit/test_checkpoint.py`: Tests `CheckpointManager` disk persistence and CRC integrity.
* `tests/unit/test_crash_recovery.py`: Tests ARIES recovery reconstruction.
* `tests/unit/test_nala_loop.py`: Tests `NalaLoop` step execution.

### Gaps Identified

* `RuntimeState` lacked a dedicated, standalone test file verifying:
  1. Proposal creation & validation.
  2. Optimistic concurrency race rejection (`StaleTransitionProposal`).
  3. Structural state machine enforcement (`InvalidStateTransition`).
  4. Terminal state invariants & evidence policy (`MissingTransitionEvidence`).
  5. Monotonic event sequence numbers.
  6. `RuntimeStatePort` compatibility (`state.transition(...)` alias).

---

## 9. COMPATIBILITY RISKS & RECOMMENDATIONS

### Compatibility Analysis

* `nala_runner.py`'s `RuntimeStatePort` specifies:

  ```python
  def transition(self, task_id: str, new_state: Any, *, reason: Optional[str] = None) -> Any: ...
  ```

* `RuntimeState` had `transition_task(...)`, `propose_transition(...)`, `commit_transition(...)`, and `propose_and_commit(...)`.
* **Recommended Action**: Add `transition(...)` alias to `RuntimeState` that normalizes string/enum states and routes through `propose_and_commit()`.

---

## 10. VERDICT & NEXT STEPS

* **Verdict**: **B. MINIMAL state.py REFINEMENT & TESTS REQUIRED**.
* `state.py` already contains the full `TransitionProposal`, `TransitionGuard`, `DefaultTransitionGuard`, `TransitionCommitResult`, and `state_version` machinery.
* We ensure `def transition(...)` alias is present in `state.py` and write a comprehensive unit test suite in `tests/unit/test_runtime_state_authority.py`.

Searched for "transition_task"
Searched for "TaskState"
Listed directory NALA
Listed directory tests
Listed directory nala_server
Listed directory unit
Searched for "RuntimeState"
Searched for "nala_server"
Ran command: `pytest tests/unit/test_session_contract.py -v`
Used tool: manage_task
Viewed task-291.log:1-9
Ran command: `.venv\Scripts\python.exe -m pytest tests/unit/test_session_contract.py`
Used tool: manage_task
Searched for "transition"
Searched for "state"
Viewed nala_runner.py:150-250
Searched for "state"
Viewed nala_runner.py:120-150
Viewed nala_runner.py:300-450
Searched for "def transition("
Searched for "self._state."
Viewed nala_runner.py:500-600
Viewed nala_runner.py:600-750
Viewed nala_runner.py:750-900
Viewed nala_runner.py:1900-2050
Viewed nala_runner.py:2050-2200
Viewed nala_runner.py:2200-2350
Viewed nala_runner.py:1700-1900
Searched for ".state ="
Created NALA_STATE_AUTHORITY_AUDIT.md
Viewed state.py:1740-1820
Edited state.py
Created test_runtime_state_authority.py
Ran command: `.venv\Scripts\pytest.exe tests/unit/test_runtime_state_authority.py -v`
Viewed contracts.py:180-240
Viewed contracts.py:240-300
Viewed state.py:1125-1160
Edited state.py
Ran command: `.venv\Scripts\pytest.exe tests/unit/test_runtime_state_authority.py -v`
Viewed contracts.py:90-175
Viewed state.py:2760-2810
Edited state.py
Viewed state.py:1980-2005
Edited state.py
Viewed test_runtime_state_authority.py:240-280
Edited test_runtime_state_authority.py
Ran command: `.venv\Scripts\pytest.exe tests/unit/test_runtime_state_authority.py -v`
Ran command: `.venv\Scripts\pytest.exe tests/unit/test_session_contract.py tests/unit/test_checkpoint.py -v`

# NALA State Authority Audit & Evolution

**Status**: AUDIT COMPLETE & VERIFIED (50/50 Tests Passing)  
**Artifact Generated**: [`NALA_STATE_AUTHORITY_AUDIT.md`](file:///E:/NALA-Project/NALA/docs/Nexus_LAB_AI/NALA_STATE_AUTHORITY_AUDIT.md)

---

## 1. CURRENT STATE OWNERSHIP

* **`RuntimeState` (`nala_server/state.py`)**: Authoritative owner of `Task` instances, `SessionRecord` registry, monotonic `state_version`, transition history, rich lightweight provenance, monotonic `TaskEvent` history/queue, and `CheckpointRef` references.
* **`Task` Registry**: Private `self._tasks: Dict[str, Task]` protected by `self._lock = threading.RLock()`.
* **`SessionRecord` Registry**: Private `self._sessions: Dict[str, SessionRecord]`.
* **Task Lifecycle**: Validated through `VALID_TRANSITIONS` and `TransitionGuard` protocols.
* **Event History & Queue**: Bounded `self._event_history` deque and `self._event_queue`.
* **Checkpoint References**: Holds in-memory `CheckpointRef`. Checkpoint disk files are strictly owned by `CheckpointManager`.

---

## 2. TRANSITION MUTATION PATHS

Every canonical state mutation adheres strictly to the **Proposal $\to$ Validation $\to$ Commit** pattern:

```text
       TransitionProposal (Immutable)
                  │
                  ▼
       _validate_transition_locked()
         ├── Identity match (proposal.task_id == task.task_id)
         ├── Optimistic concurrency check (expected_state_version == current_version)
         ├── Source state check (proposal.from_state == task.state)
         ├── State machine legality (VALID_TRANSITIONS)
         ├── Terminal evidence check (require_evidence_for_terminal_transitions)
         └── Semantic guards (DefaultTransitionGuard + custom TransitionGuards)
                  │
                  ▼
       commit_transition() [ATOMIC COMMIT UNDER self._lock]
         ├── task.state = proposal.to_state
         ├── _state_versions[task_id] += 1
         ├── Lifecycle timestamps & counters updated
         ├── Active / Completed session sets synced
         ├── Canonical TaskEvent published with monotonic sequence
         └── Lightweight provenance appended
```

**Classification of Entry Points**:

1. `propose_transition(...)` $\to$ **PROPOSAL** (Read-only, generates immutable proposal).
2. `validate_transition(...)` $\to$ **VALIDATION** (Read-only dry-run).
3. `commit_transition(proposal)` $\to$ **AUTHORITATIVE COMMIT** (The single exclusive mutation point).
4. `propose_and_commit(...)` $\to$ **AUTHORITATIVE CONVENIENCE** (For trusted orchestrators like `NalaRunner`).
5. `transition_task(...)` $\to$ **COMPATIBILITY WRAPPER** (Routes through `propose_and_commit(actor="legacy")`).
6. `transition(...)` $\to$ **PORT ADAPTER** (Standard entry point satisfying `RuntimeStatePort` in `nala_runner.py`).

---

## 3. `transition_task()` CALLERS

1. `nala_server/state.py:1747`: Definition of backward-compatible wrapper.
2. `nala_server/nala_runner.py:1835`: Invokes `self.state.transition(task_id, state, reason)`.

---

## 4. DIRECT `Task.state` MUTATIONS OUTSIDE `RuntimeState`

* **Forensic Search Result**: **0 direct `Task.state` mutations found outside `RuntimeState`**.
* The **single place** in the entire codebase where `task.state` is mutated is:
  [`nala_server/state.py: Line 1454`](file:///E:/NALA-Project/NALA/nala_server/state.py#L1454) inside `commit_transition()`.

---

## 5. EVENT GENERATION

* Canonical `TaskEvent`s are generated exclusively in `RuntimeState._build_event()` upon committed transitions.
* Monotonic `sequence` integer is assigned per task.
* Events are observations of committed state, **never** the source of canonical truth.

---

## 6. CHECKPOINT / STATE RELATIONSHIP

* `RuntimeState.attach_checkpoint(task_id, checkpoint)` stores lightweight metadata (`CheckpointRef`). It **never** writes disk files.
* `CheckpointManager.write_checkpoint()` writes durable `.chk` files to disk and returns a `CheckpointRef`.
* **Zero state duplication**.

---

## 7. CONCURRENCY & OPTIMISTIC LOCKING

* Monotonic integer `state_version` increments on every commit.
* **Race Condition Prevention**: If Worker A and Worker B propose transitions against `state_version = 0`, and Worker A commits first ($\to$ `version = 1`), Worker B's commit is rejected with `StaleTransitionProposal`. No silent state overwrites.

---

## 8. TEST VERIFICATION (50/50 Tests Passed)

We created a dedicated unit test suite in [`tests/unit/test_runtime_state_authority.py`](file:///E:/NALA-Project/NALA/tests/unit/test_runtime_state_authority.py):

| Test Case | Status | What It Proves |
| :--- | :--- | :--- |
| `test_session_creation_and_lookup` | ✅ PASSED | Session registry and duplicate prevention |
| `test_task_creation_and_initial_state` | ✅ PASSED | Task creation, initial `CREATED` state & `version=0` |
| `test_valid_lifecycle_transitions` | ✅ PASSED | Full path `CREATED` $\to$ `QUEUED` $\to$ `PLANNING` $\to$ `RUNNING` $\to$ `COMPLETED` |
| `test_failure_lifecycle` | ✅ PASSED | `RUNNING` $\to$ `FAILED` state transition |
| `test_invalid_structural_transition_rejected` | ✅ PASSED | Illegal transition (`CREATED` $\to$ `COMPLETED`) rejected |
| `test_optimistic_concurrency_rejection` | ✅ PASSED | Stale proposal rejected when state version advances |
| `test_monotonic_event_sequencing_and_queue` | ✅ PASSED | Strict monotonic sequence ($1, 2, 3$) & queue draining |
| `test_transition_history_and_provenance` | ✅ PASSED | Transition history and rich provenance retention |
| `test_checkpoint_reference_attachment` | ✅ PASSED | Attaching `CheckpointRef` to active tasks |
| `test_runtime_state_port_transition_adapter` | ✅ PASSED | `RuntimeStatePort.transition()` string/enum compatibility |

**Full Test Suite Execution**:

* `test_runtime_state_authority.py`: 10/10 passed (0.32s)
* `test_session_contract.py` + `test_checkpoint.py`: 40/40 passed (1.90s)
* **Total**: **50 / 50 PASSED**

---

## 9. EXACT GAPS RESOLVED

1. Fixed `TaskRequest` constructor mapping in `RuntimeState.create_task` (`mode` vs `execution_mode`).
2. Aligned `_state_to_event_type` and `attach_checkpoint` with `TaskEventType` in `contracts.py` (`CHECKPOINT_SAVED`).
3. Added `def transition(...)` method alias in `RuntimeState` to fully satisfy `nala_runner.py`'s `RuntimeStatePort`.

---

## 10. NEXT DEPENDENCY

The single next engineering action is **Step 2: Implement `nala_server/compatibility_adapter.py`** to translate canonical `TaskEvent`s into Socket.IO payloads (`step_update`, `ai_response`, `session_complete`) for the existing React UI! 🚀
