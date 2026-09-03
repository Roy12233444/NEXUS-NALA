# 🔬 NALA-UI-RESEARCH-003: Runtime Truth & UI Primitive Contract Verification

**Document Version:** `1.0.0-AUTHORITATIVE`  
**Classification:** Pre-Design Forensic Verification Gate (No Implementation / Inspection Only)  
**Status:** 🟢 **VERIFIED AGAINST LAPTOP PHYSICAL REPOSITORY**  
**Date:** August 29, 2026  
**Auditor:** Principal Frontend Architect & UI Systems Forensic Engineer  
**Governing Law:** *"If the runtime cannot prove it, the UI cannot claim it. Do not design what we wish NALA could do. Determine what the real NALA runtime can prove it does."*

---

# 1. Executive Mission & Verification Mandate

This research represents the **final forensic gate** before transitioning NALA UI research into an authoritative workbench architecture.

```text
NALA-UI-RESEARCH-001 (Observed Patterns: Claude Cowork, Codex, Devin)
        +
NALA-UI-RESEARCH-002 (Hostile Attack: State vs Side Effect, Swarm Inflation, Approval Gaps)
        ↓
    COMPARED DIRECTLY AGAINST
        ↓
PHYSICAL NALA REPOSITORY (nala_server/, core/, src/, tests/)
        ↓
RUNTIME TRUTH & UI PRIMITIVE CONTRACT MATRIX
```

### Governing Execution Invariants:
* ❌ **Zero React Redesign / Zero CSS / Zero Wireframes**
* ❌ **Zero Mock Runtime State / Zero Fake Events**
* ❌ **Zero Semantic Inflation**: If a concept exists only as a docstring or placeholder enum, it is classified as `🔴 ABSENT` or `⚫ FORBIDDEN TO REPRESENT`.
* 🟢 **Authoritative Provenance**: Every UI primitive must trace directly to a physical line of code, an authoritative state field in `RuntimeState`, or a canonical event in `contracts.py`.

---

# 2. Runtime Authority Map (End-to-End Execution Trace)

The exact execution path traced through the active repository from user input to frontend rendering:

```text
[ 1. USER PROMPT INPUT ]
    │  User enters directive in ChatSection composer pill
    ▼
[ 2. FRONTEND CLIENT DISPATCH ]
    │  File: src/components/features/chat/ChatSection.tsx (handleSend)
    │  Action: websocketService.emit('chat_message', { text, sessionId, mode })
    ▼
[ 3. TRANSPORT LAYER ]
    │  File: src/services/websocketService.ts -> Socket.IO (Port 3001)
    ▼
[ 4. ASYNC SERVER GATEWAY ]
    │  File: nala_server.py (@sio.on('chat_message'))
    │  Transformation: Intent Classification (classify_intent) -> TaskRequest creation
    ▼
[ 5. CANONICAL CONTRACT ]
    │  File: nala_server/contracts.py
    │  Dataclass: TaskRequest(request_id, session_id, prompt, mode=AUTONOMOUS)
    ▼
[ 6. STATE AUTHORITY COMMIT ]
    │  File: nala_server/state.py
    │  Class: RuntimeState.create_task(request) -> Task(task_id, state=CREATED)
    │  Invariant: ONLY RuntimeState commits canonical task state transitions
    ▼
[ 7. EXECUTION COORDINATOR ]
    │  File: nala_server/nala_runner.py
    │  Class: NalaRunner.start(task_id) -> Spawns worker thread, sets RunnerHandle
    │  Transition: RuntimeState.transition_task(task_id, TaskState.QUEUED -> TaskState.RUNNING)
    ▼
[ 8. REASONING & EXECUTION ENGINE ]
    │  File: core/harness/nala_loop.py -> NalaLoop.run()
    │  Handler: nala_server.py::custom_step_handler(step, session_state)
    │  ┌────────────────────────────────────────────────────────────────────────┐
    │  │ 002A Memory  : core/brain/memory_service.py (recall from MEMORY.md)    │
    │  │ 002B Planner : core/brain/planner.py (Planner.create_plan -> TaskGraph)│
    │  │ 002C Pramāṇa : core/interaction/pramana_router.py (route_epistemic_path)│
    │  │ 002D Safety  : core/safety/adaptive_viveka_gate.py & satya.py          │
    │  │ 002D Hands   : core/hands/tool_registry.py & sandbox.py                │
    │  │ 002F Checkpt : core/harness/checkpoint.py (CheckpointManager.write_*)  │
    │  │ 002G Healing : core/harness/recovery_engine.py (ARIES crash recovery)  │
    │  └────────────────────────────────────────────────────────────────────────┘
    ▼
[ 9. REAL PHYSICAL SIDE EFFECT ]
    │  Filesystem write / inspection on disk (e.g. demo_files/ or workspace)
    │  PhysicalEvidenceCorroborator computes real SHA-256 byte checksum
    ▼
[ 10. CANONICAL EVENT CREATION ]
    │  File: nala_server/contracts.py & compatibility_adapter.py
    │  Object: TaskEvent(event_type=STEP_COMPLETED, task_id, payload={verification, artifact})
    │  Queue: server_state.event_queue.put(('step_event', payload, session_id))
    ▼
[ 11. WEBSOCKET BROADCAST ]
    │  File: nala_server.py::event_publisher_loop() -> sio.emit('step_event', data)
    ▼
[ 12. FRONTEND INGESTION & PROJECTION ]
    │  File: src/services/websocketService.ts (dispatches to Redux + triggers listener)
    │  File: src/components/features/chat/ChatSection.tsx
    │  Render: Step Progress Timeline + Verification Card + SHA-256 Artifact Card
```

---

# 3. Runtime Truth Inventory

Forensic audit of every agentic and cognitive primitive across the codebase:

| Primitive | Exists in Code? | Exact Source File & Symbol | Authoritative Source of Truth | State Transition Mechanics |
| :--- | :---: | :--- | :--- | :--- |
| **Task** | **YES** | `nala_server/contracts.py::Task`<br>`nala_server/state.py::RuntimeState` | `RuntimeState.tasks[task_id]` | `CREATED` $\to$ `QUEUED` $\to$ `PLANNING` $\to$ `RUNNING` $\to$ `COMPLETED`/`FAILED` |
| **Goal / Objective** | **YES** | `core/harness/session_contract.py::SessionState.objective`<br>`contracts.py::Task.goal` | `SessionState.objective` | Immutable per session/task instance |
| **Plan** | **PARTIAL** | `core/brain/planner.py::Planner.create_plan()`<br>`session_contract.py::TaskGraph` | Ephemeral `TaskGraph.steps` in `SessionState` | Decomposed at planning step; flattened into step array |
| **Step** | **YES** | `core/harness/session_contract.py::TaskStep`<br>`contracts.py::TaskEvent.step_id` | `TaskStep.status` (`TaskStatus` enum) | `PENDING` $\to$ `RUNNING` $\to$ `SUCCESS` / `FAILED` |
| **Action** | **DERIVED** | `nala_server.py::execute_tools_via_sandbox` | Subroutine inside step handler | Executed sequentially; not a standalone DB entity |
| **Agent / Swarm** | **PARTIAL** | `core/brain/saptacore_council.py`<br>`fleet/coordinator.py` | Single orchestrator process | Executed as in-memory Python helper classes; **No distributed swarm** |
| **Tool** | **YES** | `core/hands/tool_registry.py::ToolRegistry`<br>`contracts.py::TaskEventType.TOOL_*` | `ToolRegistry._tools[tool_name]` | Registered $\to$ Selected $\to$ Validated $\to$ Executed $\to$ Result |
| **Approval** | **PARTIAL** | `nala_server/contracts.py::ApprovalRequest`<br>`nala_runner.py::_ApprovalWaiter` | In-memory `threading.Event` (RAM only) | Requested $\to$ Blocked in RAM $\to$ Approved/Rejected/Timeout |
| **Intervention** | **PARTIAL** | `nala_runner.py::NalaRunner.cancel()` | `RunnerHandle.cancel_event` | Cooperative flag set; **Pause is NOT implemented** |
| **Checkpoint** | **YES** | `core/harness/checkpoint.py::CheckpointManager` | On-disk `checkpoint_LSN_XXXXXX.json` | Atomic write (tmp $\to$ fsync $\to$ os.replace) with monotonic LSN |
| **Recovery** | **YES** | `core/harness/recovery_engine.py::RecoveryEngine` | Durable `session.metadata['recovery_state']` | Diagnose $\to$ Strategy (`RETRY`/`RESUME`/`CORROBORATE`/`SAFE_HALT`) |
| **Artifact** | **YES** | `nala_server.py::execute_tools_via_sandbox`<br>`contracts.py::TaskResult.artifacts` | Physical file on disk (`demo_files/`) | File written $\to$ Read back $\to$ Metadata/MIME extracted |
| **Verification** | **YES** | `core/harness/recovery.py::PhysicalEvidenceCorroborator` | Computed disk SHA-256 checksum | Disk readback $\to$ Hash computation $\to$ Strict string equality |
| **Memory** | **YES** | `core/brain/memory_service.py::MemoryService` | File on disk: `memory/MEMORY.md` | Bullet points appended with timestamps & deduplicated |
| **Claim** | **DERIVED** | `nala_server.py` (`ai_response` text) | LLM text stream / chat response | Generated by model; ungrounded until corroborated |
| **Evidence** | **YES** | `core/harness/recovery.py` | SHA-256 checksum + byte length | Extracted from physical OS filesystem readback |
| **Pramāṇa** | **PARTIAL / DERIVED** | `core/interaction/pramana_router.py::PramanaRouter` | `PramanaRouteResult.primary_pramana` | Regex/context heuristic routing $\to$ Emitted to Redux |
| **Viveka** | **YES** | `core/safety/adaptive_viveka_gate.py::AdaptiveVivekaGate` | `VivekaEvaluationResult.decision` | `ALLOW` / `APPROVAL_REQUIRED` / `DENY` |

---

# 4. The Event Spine Verification

Authoritative trace of the runtime event pipeline:

```text
Runtime State Mutation
       │  (state.py / nala_runner.py)
       ▼
TaskEvent Construction
       │  (contracts.py::TaskEvent.create)
       ▼
Event Queue Buffer
       │  (server_state.event_queue.put)
       ▼
Async Publisher Loop
       │  (nala_server.py::event_publisher_loop)
       ▼
Socket.IO Broadcast
       │  (sio.emit('step_event', payload))
       ▼
Client Ingestion
       │  (websocketService.ts)
       ▼
UI Local Projection
          (ChatSection.tsx)
```

### Canonical Event Inventory:

| Event Name (`TaskEventType`) | Producer | Payload Schema | Sequence / Ordering | Persistence | Replay Capability | UI Trustworthiness |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `task.created` | `RuntimeState` | `task_id, session_id, goal, mode` | Monotonic int | In-Memory (`state.py`) | YES (via `get_events`) | 🟢 Canonical Truth |
| `task.started` | `NalaRunner` | `task_id, session_id, timestamp` | Monotonic int | In-Memory (`state.py`) | YES (via `get_events`) | 🟢 Canonical Truth |
| `step.started` | `NalaLoop` | `step_id, description, details` | Monotonic int | WAL (`.jsonl`) | YES (via Checkpoint) | 🟢 Canonical Truth |
| `step.completed` | `NalaLoop` | `step_id, result, verification, artifact` | Monotonic int | WAL (`.jsonl`) | YES (via Checkpoint) | 🟢 Canonical Truth |
| `step.failed` | `NalaLoop` | `step_id, error, traceback` | Monotonic int | WAL (`.jsonl`) | YES (via Checkpoint) | 🟢 Canonical Truth |
| `tool.started` | `ToolRegistry` | `tool_name, action, arguments` | Ephemeral | In-Memory log | NO | 🟡 Partial |
| `tool.completed` | `ToolRegistry` | `tool_name, latency_ms, result` | Ephemeral | In-Memory log | NO | 🟡 Partial |
| `checkpoint.saved`| `CheckpointManager` | `lsn, checkpoint_id, hash, path` | Monotonic LSN | Disk JSON file | YES (Full restore) | 🟢 Canonical Truth |
| `recovery.started`| `RecoveryEngine` | `failure_type, strategy, attempt` | Ephemeral | In-Memory / Logs | NO | 🟡 Partial |
| `approval.requested`| `NalaRunner` | `req_id, task_id, step_id, reason` | Ephemeral | **RAM ONLY (Lost on crash)**| NO | 🟠 Ephemeral |
| `pramana.active` | `PramanaRouter` | `primary_pramana, confidence, reason` | Ephemeral | Redux slice only | NO | 🟠 Derived |
| `safety.updated` | `AdaptiveVivekaGate`| `strictness, satya_score, health` | Ephemeral | Redux slice only | NO | 🟡 Telemetry |

---

# 5. Task / Step / Action / Tool Semantics

Research-002 warned against semantic inflation. Here is the strict reality in NALA:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TASK (Canonical Durable Entity)                                          │
│    - Defined in contracts.py::Task & state.py::RuntimeState                 │
│    - Has unique task_id, lifecycle state, created_at, completed_at          │
│    - PERSISTENT in memory and persisted via durable checkpoint references.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. PLAN (Ephemeral Graph Decomposition)                                     │
│    - Generated by Planner.create_plan() as a List[TaskStep]                 │
│    - Stored inside SessionState.task_graph                                  │
│    - NOT a standalone relational entity; exists only as steps in a task.    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. STEP (Authoritative Execution Node)                                      │
│    - Defined in session_contract.py::TaskStep                               │
│    - Has step_id, status (PENDING/RUNNING/SUCCESS/FAILED), dependencies     │
│    - Checkpointed at every boundary with monotonic LSN increments.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. ACTION / TOOL EXECUTION (Subroutine Invocation)                          │
│    - Defined in core/hands/tool_registry.py::ToolRequest                    │
│    - Synchronously executed inside custom_step_handler                      │
│    - Produces a StepResult; does NOT exist as an independent persistent node│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. Approval Semantics Forensic Audit

Research-002 flagged fake approval dialogs. Here is the forensic reality of approvals in NALA today:

* **Does an Approval Primitive exist?** $\to$ **PARTIALLY (RAM ONLY)**.
* **Who requests approval?** $\to$ `NalaRunner` when `approval_required(step, session)` returns `True` or `AdaptiveVivekaGate` returns `VivekaDecision.APPROVAL_REQUIRED`.
* **Where is it stored?** $\to$ Inside `NalaRunner._approvals[req_id] = _ApprovalWaiter()` using an in-memory `threading.Event()`.
* **Can approval expire?** $\to$ `NalaRunner` accepts `approval_timeout_seconds`. If the timeout fires, it raises `ApprovalTimeout`.
* **Can it be audited?** $\to$ Emits `approval.requested` event; logged in server logs.
* **Can execution resume?** $\to$ Calling `submit_approval(req_id, approved=True)` unblocks the Python worker thread.
* **CRITICAL FLAW / CRASH INVARIANT**:
  > **If NALA crashes while waiting for approval, the `_ApprovalWaiter` thread is destroyed and the approval state is WIPED FROM RAM.** Upon restart, recovery reloads the last checkpoint (which was saved *before* the approval step) and must re-evaluate whether approval is needed.
* **UI IMPLICATION**: The UI must **never** represent approval as a durable, multi-day workflow queue. It is strictly an active, synchronous session modal.

---

# 7. Intervention Semantics (Pause / Resume / Cancel / Redirect)

| Intervention Command | Runtime Support Level | Physical Implementation in Codebase |
| :--- | :---: | :--- |
| **`cancel`** | **SUPPORTED (COOPERATIVE)** | `NalaRunner.cancel(task_id)` sets `handle.cancel_event`. Step handler checks this token and exits cleanly. |
| **`resume`** | **SUPPORTED (VIA RECOVERY)** | `NalaRunner.resume(task_id)` reloads checkpoint from disk via `recover_session()` and starts execution from last valid LSN. |
| **`retry`** | **SUPPORTED (AUTOMATIC)** | `RecoveryEngine.execute_recovery(error)` increments `attempt_count` in metadata and triggers step re-execution with exponential backoff. |
| **`pause`** | **🔴 NOT IMPLEMENTED** | `TaskState.PAUSED` exists in `contracts.py`, but **zero pause functions exist** in `NalaRunner` or `NalaLoop`. |
| **`redirect`** | **🔴 NOT IMPLEMENTED** | NALA cannot dynamically alter goal DAG topology while a step is mid-execution. |

---

# 8. Checkpoint & Recovery Forensic Audit (State vs Side Effect)

This resolves the **state rewind vs effect rewind** problem identified in Research-002:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE HARD PHYSICAL REALITY                          │
│                                                                             │
│  Restoring NALA's Checkpoint (LSN-2)                                        │
│  ═══════════════════════════════════                                        │
│  ✔ Restores SessionState in Python RAM                                      │
│  ✔ Restores Step Statuses (Step 3 returns to PENDING)                        │
│  ✔ Restores Token & Cost counters                                           │
│                                                                             │
│  DOES NOT AND CANNOT:                                                       │
│  ✖ Delete a file written to disk during Step 3                              │
│  ✖ Revert an external database row updated via tool                         │
│  ✖ Un-send an HTTP POST payload sent to a cloud API                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Forensic Checkpoint Analysis:
1. **Checkpoint Contents**: Contains `session_id`, `objective`, `task_graph` (all steps and statuses), `state_matrix` (telemetry), `checkpoint_meta` (LSN, hash, timestamp), and `metadata`.
2. **When Created**: Written atomically to `<base_dir>/<session_id>/checkpoint_LSN_XXXXXX.json` before and after every step boundary.
3. **Rollback vs Compensation**:
   - Rolling back to `LSN-1` is an **internal state rollback only**.
   - Side effects on disk require **compensating actions** (e.g. deleting corrupted output files).
4. **UI Rule**: The UI must **never** display a `"Rollback Execution"` button that implies external physical changes will be magically undone. It must clearly label state reversion as `"Restore State from Checkpoint (LSN-X)"`.

---

# 9. Pramāṇa, Evidence & Claim Verification

Addressing the **Kill-Critic Gate**: Preventing Epistemic Theater.

```text
[ UNGROUNDED CLAIM ]  ──►  LLM Text Output: "I have created the optimized server."
                                │ (Ungrounded assertion)
                                ▼
[ COGNITIVE ROUTE ]   ──►  PramanaRouter: Epistemic Route = PRATYAKSHA (Keyword trigger)
                                │ (Algorithmic classification)
                                ▼
[ PHYSICAL EVIDENCE ] ──►  PhysicalEvidenceCorroborator: Reads /demo_files/server.py
                                │ Computes SHA-256: 4f8a... (Real disk readback)
                                ▼
[ ATTESTED TRUTH ]    ──►  Verified Artifact Card in UI with real byte size & hash
```

### Authoritative Verification Criteria:
* **`PRATYAKSHA` (Direct Perception)**: 🟢 **VERIFIED ONLY** when `PhysicalEvidenceCorroborator` reads physical bytes from disk and hashes them.
* **`ANUMANA` (Inference)**: 🟡 **DERIVED** when logical code planning or DAG decomposition passes DFS cycle checks and Satya validation.
* **`SHABDA` (Testimony)**: 🟡 **DERIVED** when grounded in user input prompts or facts recalled from `memory/MEMORY.md`.
* **`UPAMANA` / `ARTHAPATTI` / `ANUPALABDHI`**: 🟠 **HEURISTIC** derived from regex matching on objectives.
* **UI Rule**: The UI must **never** render a green `"Verified Truth"` badge based solely on `PramanaRouteResult.confidence`. It may **only** render verification when backed by a real `SHA-256` artifact checksum.

---

# 10. Memory Subsystem Verification (002A)

* **Physical File**: `memory/MEMORY.md`
* **Storage Structure**: Flat Markdown bullet points with UTC date tags:
  ```markdown
  # Memory
  - (2026-08-28) Project NALA uses pure CSS design tokens and Socket.IO.
  - (2026-08-28) User requested authoritative verification for UI research.
  ```
* **Deduplication**: `_normalize(text)` lowercases and strips whitespace; exact matches are rejected.
* **Recall Mechanism**: `MemoryService.recall(max_chars=4000)` reads raw text and injects it into `session_state.metadata['recalled_memory']` during planning.
* **Persistence Scope**: Global / Project-scoped (persists across sessions in the repository).
* **Event Exposure**: 🔴 **ABSENT**. `MemoryService` does not emit WebSocket events. Memory updates are communicated via chat text confirmation.

---

# 11. Tool Subsystem Verification (002D)

The future UI must distinguish these **three distinct facts**:

```text
1. TOOL SELECTED   ──► Planner identifies candidate tool based on metadata & tags
2. TOOL INVOCATION ──► Viveka evaluates safety (ALLOW) & spawns execution sandbox
3. TOOL RESULT     ──► Execution finishes, exit code evaluated, stdout/stderr captured
```

* **Tool Registry**: `core/hands/tool_registry.py::ToolRegistry`
* **Sandbox Isolation**: `core/hands/sandbox.py::get_sandbox_manager()`
* **Permission Enforcement**: `AdaptiveVivekaGate` evaluates tool name, arguments, prohibited paths (`..`, `/etc/`, `system32`), and hostile commands (`rm -rf`, `format`).
* **Observable Data**: Tool name, action, latency ms, success rate, exit status.

---

# 12. Artifact Subsystem Verification (002F)

```text
MODEL CLAIM                   PHYSICAL ARTIFACT               VERIFIED ARTIFACT
"I wrote the report."   ≠   `demo_files/report.md`   ≠   File exists + Readback passed
                                                         + SHA-256 checksum matched
```

* **Physical Storage**: Real files written inside `demo_files/` or project workspace.
* **Identification**: File name, relative path, MIME type, byte size, creation timestamp.
* **Cryptographic Proof**: Python `hashlib.sha256(content.encode('utf-8')).hexdigest()`.
* **UI Projection**: `ChatSection.tsx` renders `nala-artifact-card` displaying the file name, byte size, and truncated SHA-256 checksum with copy-to-clipboard functionality.

---

# 13. Failure States & Boundary Behavior

| Failure Mode | Runtime Behavior | Emitted Event | Persistence | UI Representation |
| :--- | :--- | :--- | :---: | :--- |
| **Tool Execution Error** | Step handler catches exception; sets `StepResult.success=False` | `step_event` (`status=failed`) | Logged in WAL | Red `✕` status marker on step timeline |
| **Planner / Cycle Failure**| DFS cycle detector catches circular dependency | `session_error` | In-Memory | Error message bubble in chat |
| **Safety Violation (Viveka)**| `AdaptiveVivekaGate` returns `DENY` | `safety.updated` (`blocked`) | Logged | Step aborted; security halt notice |
| **Process Crash (`SIGKILL`)**| Process terminates immediately | None (at crash time) | Checkpoint on disk | On restart, loads checkpoint & resumes |
| **Corrupted Checkpoint** | `CheckpointIntegrityError` (SHA-256 mismatch) | `recovery.started` | Logged | Auto-fallback to `LSN - 1` |
| **Runaway Loop** | Attempt counter reaches `max_attempts=3` | `session_error` (`SAFE_HALT`) | Metadata | Safe Halt card; prevents infinite retry loop |
| **Socket Disconnect** | Server keeps running worker thread; client queues events | `disconnect` (client side) | Queued | Amber connection dot in header |

---

# 14. Reconnection & Replay Verification

* **Scenario**: Browser disconnects while NALA is executing a 10-step task.
* **Backend Truth**: NALA continues executing uninterrupted in its worker thread (`NalaRunner` / `NalaLoop`).
* **On Browser Reconnect**:
  - `websocketService.ts` reconnects automatically with exponential backoff.
  - **CURRENT LIMITATION**: `ChatSection.tsx` does not currently invoke a `fetch_session_history` REST call upon reconnect. Steps completed while the browser was offline are stored in `RuntimeState.events`, but are not automatically replayed into the React message state unless refreshed from a snapshot.
* **UI ARCHITECTURAL REQUIREMENT**: The new Control Center must implement an `INITIAL_STATE_SNAPSHOT` hydration call on WebSocket connection open.

---

# 15. Concurrency Capability Truth

* **Can NALA run multiple tasks concurrently today?** $\to$ **PARTIALLY (BOUNDED BY SESSION)**.
* **Physical Reality**:
  - `RuntimeState` can store multiple `Task` objects in memory simultaneously.
  - `NalaRunner` supports `max_concurrent_tasks` with a `threading.BoundedSemaphore`.
  - However, `custom_step_handler` in `nala_server.py` executes synchronously within a single session loop.
  - `ChatSection.tsx` has global socket listeners and would interleave multi-task events into the active message bubble.
* **VERDICT**: **No Multi-Agent Swarm View**. The UI must be scoped to **Single-Session / Active-Task Focus** with a session history drawer.

---

# 16. UI Primitive Contract Matrix

| Primitive | Runtime Exists? | Authoritative Source | Event Emitted | Persistent? | UI-Safe? | Proposed UI Treatment |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **Task** | 🟢 YES | `RuntimeState.tasks` | `task.created`, `task.started` | YES | 🟢 YES | **ADOPT**: Main execution unit with state badge |
| **Step** | 🟢 YES | `TaskStep.status` | `step.started`, `step.completed` | YES | 🟢 YES | **ADOPT**: Live execution progress timeline |
| **Plan** | 🟡 PARTIAL | `TaskGraph.steps` | `step_event` (`plan` array) | In Session | 🟢 YES | **ADOPT**: Collapsible execution plan card |
| **Artifact** | 🟢 YES | Physical file on disk | `step_event` (`artifact` obj) | YES | 🟢 YES | **ADOPT**: File card with size & SHA-256 |
| **Verification**| 🟢 YES | `PhysicalEvidenceCorroborator`| `step_event` (`verification` obj)| YES | 🟢 YES | **ADOPT**: `✓ RESULT VERIFIED` physical badge |
| **Checkpoint** | 🟢 YES | `CheckpointManager` (LSN) | `checkpoint.saved` | YES | 🟢 YES | **ADOPT**: Checkpoint timeline in Inspector |
| **Recovery** | 🟢 YES | `RecoveryEngine` | `recovery.*` | YES | 🟡 PARTIAL | **ADOPT**: Diagnostic recovery status badge |
| **Memory** | 🟢 YES | `memory/MEMORY.md` | Chat response only | YES | 🟡 PARTIAL | **ADOPT**: Read-only Memory Drawer/Modal |
| **Tool** | 🟢 YES | `ToolRegistry` | `tool.*`, `step_event` | In-Memory | 🟡 PARTIAL | **ADOPT**: Tool execution trace drawer |
| **Viveka Gate**| 🟢 YES | `AdaptiveVivekaGate` | `safety.updated` | In-Memory | 🟡 PARTIAL | **ADOPT**: Safety gauge in Inspector |
| **Approval** | 🟡 PARTIAL | `NalaRunner._approvals` | `approval.requested` | **RAM ONLY** | 🟡 CAUTION | **ADAPT**: Modal dialog (Active session only) |
| **Pramāṇa** | 🟠 DERIVED | `PramanaRouter` | `pramana.active` | Ephemeral | 🟡 CAUTION | **ADAPT**: Epistemic route indicator in Inspector |
| **Action** | 🟠 DERIVED | Internal step subroutines | `step_event` (`details`) | NO | 🟢 YES | **ADAPT**: Nested bullet under Step |
| **Cancel** | 🟢 YES | `handle.cancel_event` | `cancel_requested` | In-Memory | 🟢 YES | **ADAPT**: Cooperative "Stop Execution" button |
| **Pause** | 🔴 ABSENT | None | None | NO | 🔴 NO | **DEFER**: Do not build pause button |
| **Swarm** | 🔴 ABSENT | None | None | NO | 🔴 NO | **DEFER**: Do not build swarm view |

---

# 17. UI Truth Classification

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🟢 VERIFIED (Runtime exists + Authoritative + Observable)                   │
│    - Task Lifecycle (CREATED, QUEUED, RUNNING, COMPLETED, FAILED)          │
│    - TaskGraph Step Progress (Pending, Executing, Success, Failure)        │
│    - Physical File Artifacts (File Name, Byte Size, MIME Type)              │
│    - Physical SHA-256 Disk Verification Readback                           │
│    - Monotonic LSN Checkpoints & WAL Persistence                           │
│    - Memory Fact Bullet Persistence in MEMORY.md                            │
│    - Streaming AI Markdown Token Generation                                │
│    - Cooperative Task Cancellation                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟡 PARTIAL (Runtime exists but observability/durability is incomplete)      │
│    - Adaptive Viveka Safety Metrics & Strictness Gauges                    │
│    - Tool Registry Metadata, Latency & Predictions                         │
│    - Synchronous Human Approval Modals (RAM-bounded)                       │
│    - Bounded Self-Healing Recovery State & Attempt Counters                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🟠 DERIVED (Concept exists indirectly; no standalone entity)                │
│    - Pramāṇa Epistemic Routing (Classified via heuristics & RTA score)     │
│    - Action Details (Rendered as sub-bullets inside Step timeline)          │
│    - Execution Plan (Derived from ephemeral TaskGraph step array)          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔴 ABSENT (Not implemented in backend runtime)                              │
│    - Task Execution Pause                                                   │
│    - Mid-flight Goal DAG Redirection                                        │
│    - Multi-Agent Distributed Swarm Execution                                │
│    - Automatic REST Session Hydration on Reconnect                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚫ FORBIDDEN TO REPRESENT (UI would mislead user if shown today)             │
│    - ✖ "Rollback External Actions" Button (Violates side-effect physics)    │
│    - ✖ Fake Multi-Agent 3D Swarm Graph                                     │
│    - ✖ "Pause & Edit Code Mid-Step" Controls                                │
│    - ✖ Pramāṇa "100% Mathematical Proof" Badge without SHA-256 Hash        │
│    - ✖ Multi-day Offline Durable Approval Queue                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 18. Runtime → UI Contract Mapping

For every **🟢 VERIFIED** and **🟡 PARTIAL** primitive, the authoritative contract mapping:

```text
1. TASK STATE
   Runtime: RuntimeState.tasks[id].state == TaskState.RUNNING
   Event  : TaskEvent(event_type=TASK_STARTED)
   UI     : Header Status Indicator shows "Running Mission..." (Pulsing Indigo)

2. STEP PROGRESS
   Runtime: TaskStep(step_id='step_2', status=TaskStatus.RUNNING)
   Event  : TaskEvent(event_type=STEP_STARTED, step_id='step_2')
   UI     : Timeline Item #2 shows active spinning indicator with elapsed seconds

3. PHYSICAL ARTIFACT & VERIFICATION
   Runtime: PhysicalEvidenceCorroborator hashes demo_files/output.py -> SHA-256
   Event  : TaskEvent(event_type=STEP_COMPLETED, payload={artifact, verification})
   UI     : Renders "✓ RESULT VERIFIED" Badge + Artifact Card (output.py, 1.2 KB, SHA-256: 4f8a...)

4. CHECKPOINT COMMIT
   Runtime: CheckpointManager.write_checkpoint() -> LSN-4 written to disk
   Event  : TaskEvent(event_type=CHECKPOINT_SAVED, payload={lsn: 4})
   UI     : Inspector Checkpoint Timeline adds "Checkpoint LSN-4 (Atomic Commit)"

5. RECOVERY & RETRY
   Runtime: RecoveryEngine diagnoses crash -> selects RETRY (Attempt 1/3)
   Event  : TaskEvent(event_type=RECOVERY_STARTED, payload={attempt: 1, max: 3})
   UI     : Step Item displays amber warning "Retrying Step (Attempt 1/3)..."
```

---

# 19. Authoritative "Do Not Build Yet" List

The following UI components and surfaces are **strictly forbidden** until backend runtime support is implemented and mathematically proven:

1. ❌ **No "Pause Execution" Button**: The runtime cannot pause an active thread or async task safely without checkpoint boundary corruption.
2. ❌ **No "Undo / Rollback External Changes" Button**: Checkpoints restore internal RAM state, not external filesystem or database mutations.
3. ❌ **No Multi-Agent Swarm Visualization**: NALA runs as a unified single orchestrator with cognitive subroutines, not a multi-node peer-to-peer swarm.
4. ❌ **No Epistemic "Proof" Badge on Pure LLM Claims**: Only render mathematical verification badges when backed by physical disk readback checksums.
5. ❌ **No Persistent Multi-Day Approval Inbox**: Approvals are active memory waiters; long-running offline approvals require durable async queues (002H).
6. ❌ **No Inferred Execution States**: The UI must never show a spinner based on an assumed message state; it must update exclusively on canonical `TaskEvent`s.

---

# 20. NALA-UI-RESEARCH-003 Final Verdict

### Architectural Verdict: 🟢 **PASS — READY FOR CONTROL CENTER WORKSPACE DESIGN**

The forensic inspection of the physical NALA repository proves:
1. **The Core Runtime Truth is Powerful & Real**: NALA possesses genuine, verifiable primitives for Tasks, Steps, Monotonic Checkpoints, Physical SHA-256 Verification, Flat-File Memory, Sandboxed Tools, and Self-Healing Crash Recovery.
2. **The Execution Path is Clean & Traceable**: Every user prompt flows through `TaskRequest` $\to$ `RuntimeState` $\to$ `NalaRunner` $\to$ `NalaLoop` $\to$ `TaskEvent` $\to$ `UI`.
3. **The Boundaries are Clear**: By strictly forbidding ungrounded features (Pause, Swarm, Effect Rollback) and adopting a **3-Zone Collapsible Workspace** (Left History Drawer, Center Conversational & Execution Stream, Right Collapsible Inspector), NALA will deliver an industry-leading, professional, and epistemically truthful AI Control Center.
