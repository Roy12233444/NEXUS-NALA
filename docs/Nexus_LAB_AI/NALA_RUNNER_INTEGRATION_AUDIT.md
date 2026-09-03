# NALA Runner Integration Audit
**Date**: August 14, 2026  
**Status**: FORENSIC INTEGRATION AUDIT COMPLETE — EVIDENCE-BASED INVESTIGATION  
**Scope**: `contracts.py`, `state.py`, `nala_runner.py`, `nala_loop.py`, `session_contract.py`, `checkpoint.py`

---

## EXECUTIVE SUMMARY

This audit performs a forensic inspection of the end-to-end execution chain:

```text
TaskRequest / Task
       ↓
RuntimeState (state.py)
       ↓
NalaRunner (nala_runner.py)
       ↓
NalaLoop (core/harness/nala_loop.py)
       ↓
TaskEvent (contracts.py / compatibility_adapter.py)
```

---

## 14-POINT FORENSIC EVIDENCE INVESTIGATION

### 1. Where the Task object is created
* **FILE**: `nala_server/state.py`
* **CLASS/FUNCTION**: `RuntimeState.create_task(self, request: TaskRequest) -> Task`
* **EVIDENCE**: Lines 1135–1146:
  ```python
  mode_val = getattr(request, "mode", getattr(request, "execution_mode", ExecutionMode.AUTONOMOUS))
  task = Task(
      task_id=task_id,
      session_id=session_id,
      request_id=getattr(request, "request_id", None),
      goal=request.prompt,
      mode=mode_val,
      state=TaskState.CREATED,
  )
  ```
* **WHAT IT PROVES**: Canonical `Task` instances are created exclusively inside `RuntimeState.create_task()` from incoming `TaskRequest` schemas.

---

### 2. Where that Task is registered in RuntimeState/TaskRegistry
* **FILE**: `nala_server/state.py`
* **CLASS/FUNCTION**: `RuntimeState.create_task`
* **EVIDENCE**: Lines 1147–1165:
  ```python
  self._tasks[task_id] = task
  self._session_tasks[session_id].append(task_id)
  session.active_task_ids.add(task_id)
  session.touch()
  self._state_versions[task_id] = 0
  self._event_sequences[task_id] = 0
  self._created_tasks += 1
  ```
* **WHAT IT PROVES**: The task is registered in `self._tasks`, indexed under `_session_tasks`, associated with `session.active_task_ids`, initialized with `state_version = 0`, and sequenced at `0`.

---

### 3. The exact task_id generated/assigned
* **FILE**: `nala_server/contracts.py` & `nala_server/state.py`
* **CLASS/FUNCTION**: `TaskRequest` / `Task`
* **EVIDENCE**: `contracts.py:240-244` & `state.py:1095`:
  ```python
  task_id = request.task_id or str(uuid.uuid4())
  ```
* **WHAT IT PROVES**: `task_id` is an immutable UUID string generated at request ingress and preserved throughout the lifecycle.

---

### 4. How NalaRunner receives the task/task_id
* **FILE**: `nala_server/nala_runner.py`
* **CLASS/FUNCTION**: `NalaRunner.start(self, task_id: str, ...)` & `NalaRunner.run(self, task_id: str, ...)`
* **EVIDENCE**: Lines 652–675, 732–755:
  ```python
  def start(self, task_id: str, *, recover: bool = False, daemon: bool = True) -> RunnerHandle:
      task = self._get_task(task_id)
      session_id = self._extract_session_id(task)
  ```
* **WHAT IT PROVES**: `NalaRunner` is invoked solely with `task_id` (a string) and looks up the task from the injected `RuntimeStatePort`.

---

### 5. Whether NalaRunner retrieves authoritative Task or creates/maintains a duplicate
* **FILE**: `nala_server/nala_runner.py`
* **CLASS/FUNCTION**: `NalaRunner._get_task(self, task_id: str)` & `RunnerHandle`
* **EVIDENCE**: Lines 1864–1876:
  ```python
  def _get_task(self, task_id: str) -> Any:
      task = self.state.get_task(task_id)
      if task is None:
          raise TaskNotFoundError(f"Task not found: {task_id}")
      return task
  ```
* **WHAT IT PROVES**: `NalaRunner` does **NOT** maintain a duplicate `Task` record. It queries `state.get_task(task_id)` and only holds an ephemeral execution context (`RunnerHandle`) containing thread objects and cancellation primitives.

---

### 6. Exact function where NalaRunner starts NalaLoop
* **FILE**: `nala_server/nala_runner.py`
* **CLASS/FUNCTION**: `NalaRunner._execute(self, handle: RunnerHandle)`
* **EVIDENCE**: Lines 1055–1095:
  ```python
  nala_loop = self._build_loop(
      handle=handle,
      session_id=session_id,
      session_state=session_state,
      checkpoint_manager=checkpoint_manager,
      tracker=tracker,
      compactor=compactor,
      hooks=loop_hooks,
  )
  handle.nala_loop = nala_loop
  ...
  status = nala_loop.run()
  ```
* **WHAT IT PROVES**: `NalaRunner._execute` builds `NalaLoop` via `_build_loop()` and triggers synchronous execution in the worker thread via `status = nala_loop.run()`.

---

### 7. How NalaLoop receives the task/context
* **FILE**: `nala_server/nala_runner.py` & `core/harness/nala_loop.py`
* **CLASS/FUNCTION**: `NalaRunner._build_loop`
* **EVIDENCE**: Lines 1158–1169:
  ```python
  nala_loop = NalaLoop(
      session=session_state,
      checkpoint_manager=checkpoint_manager,
      context_tracker=tracker,
      compactor=compactor,
      hooks=hooks,
  )
  nala_loop.set_default_handler(self._step_handler)
  ```
* **WHAT IT PROVES**: `NalaLoop` receives `SessionState`, `CheckpointManager`, `ContextTracker`, `DronagiriCompactor`, and `LoopHooks`, with `_step_handler` attached as the default execution handler.

---

### 8. Where execution state is updated
* **FILE**: `nala_server/nala_runner.py` & `nala_server/state.py`
* **CLASS/FUNCTION**: `NalaRunner._transition()` $\to$ `RuntimeState.transition()` $\to$ `RuntimeState.commit_transition()`
* **EVIDENCE**:
  - `nala_runner.py:701`: `self._transition(task_id, "QUEUED")`
  - `nala_runner.py:1015`: `self._transition(handle.task_id, "PLANNING")`
  - `nala_runner.py:1074`: `self._transition(handle.task_id, "RUNNING")`
  - `nala_runner.py:1530`: `self._transition(handle.task_id, "COMPLETED")`
  - `nala_runner.py:1610`: `self._transition(handle.task_id, "FAILED")`
  - `nala_runner.py:1720`: `self._transition(handle.task_id, "CANCELLED")`
  - `state.py:1454`: `task.state = proposal.to_state` (committed under `self._lock`).
* **WHAT IT PROVES**: `NalaRunner` does not mutate state locally. Every phase transition routes directly through `RuntimeState.transition()` $\to$ `commit_transition()`.

---

### 9. Where TaskEvent is created
* **FILE**: `nala_server/state.py`
* **CLASS/FUNCTION**: `RuntimeState._build_event` & `RuntimeState._publish_event`
* **EVIDENCE**: Lines 2065–2110:
  ```python
  def _build_event(self, event_type: TaskEventType, task: Task, ...) -> TaskEvent:
      self._event_sequences[task.task_id] += 1
      return task_event(
          event_type,
          task,
          message=message,
          payload=payload,
          sequence=self._event_sequences[task.task_id],
      )
  ```
* **WHAT IT PROVES**: Canonical `TaskEvent` objects are constructed inside `RuntimeState._build_event()` upon committed state transitions, assigned strict monotonic sequence numbers, and enqueued into `_event_queue`.

---

### 10. Whether TaskEvent represents the same task_id from RuntimeState
* **FILE**: `nala_server/state.py` & `nala_server/contracts.py`
* **CLASS/FUNCTION**: `RuntimeState._build_event` / `task_event`
* **EVIDENCE**: `state.py:2075` & `contracts.py:463-477`:
  ```python
  return cls(
      event_type=event_type,
      session_id=session_id,
      task_id=task_id,
      ...
  )
  ```
* **WHAT IT PROVES**: `TaskEvent.task_id` is identically equal to `Task.task_id`.

---

### 11. Exact Lifecycle Trace
```text
1. CREATED           ───► state.create_task(request)
2. QUEUED            ───► runner.start(task_id) -> state.transition("QUEUED")
3. PLANNING          ───► runner._execute() -> state.transition("PLANNING")
4. RUNNING           ───► runner._execute() -> state.transition("RUNNING") -> nala_loop.run()
5. COMPLETED/FAILED  ───► runner._complete() / _failed() -> state.transition("COMPLETED" / "FAILED")
```

---

### 12. Direct Task.state Mutations Outside RuntimeState
* **FORENSIC RESULT**: **ZERO direct assignments to `task.state` exist anywhere outside `RuntimeState.commit_transition()`**.

---

### 13. Duplicate Task/State Representation
* **FORENSIC RESULT**:
  - `RunnerHandle.phase` is an ephemeral diagnostic enumeration (`RunnerPhase`) explicitly decoupled from domain truth.
  - `SessionRecord` in `state.py` is the server registry; `SessionState` in `core/harness` is the execution state.

---

### 14. Broken or Incomplete Connections in `nala_runner.py`
1. **`step_handler` Injection Requirement**:
   `nala_runner.py:1313-1317`: `_step_handler` requires an injected handler callable (`self.step_handler`). In `nala_server.py`, the existing step handler is `custom_step_handler`.
2. **`SessionRecord` vs `SessionState` Type Bridge**:
   In `nala_runner.py:1007`, `session_state = self._get_session(session_id)`. `RuntimeState.get_session()` returns `SessionRecord`. `NalaLoop` expects `core.harness.session_contract.SessionState`. When `SessionRecord.runtime_refs["session_state"]` is present, it must be extracted or initialized.
3. **Event Transport Bridge**:
   `nala_runner.py` emits `RunnerEvent` locally. The canonical stream for Socket.IO is the `RuntimeState._event_queue`, which connects to `compatibility_adapter.py`.

---

## 🎯 FINAL VERDICT

### **B. CONNECTED BUT INCOMPLETE**

### 🔑 The SINGLE Most Important Missing Piece:
**The `SessionRecord` $\leftrightarrow$ `SessionState` runtime bridge and `step_handler` attachment when constructing `NalaRunner` in `nala_server.py`.**

Specifically:
When `nala_server.py` creates a session, it must attach the `SessionState` instance to `runtime_state.attach_runtime_ref(session_id, "session_state", session_state)`, and pass `custom_step_handler` into `build_nala_runner(state=runtime_state, step_handler=custom_step_handler)`.
