# NALA SERVER REFACTOR — MASTER ARCHITECTURAL BRIEF

## 0. READ THIS FIRST

I am refactoring the NALA project so that it behaves as a real autonomous coding/execution system rather than a chatbot that merely generates answers.

The target experience is conceptually similar to the execution model of tools such as Codex / Claude Code / Cowork:

```text
User
 ↓
Task
 ↓
Plan
 ↓
Real tool execution
 ↓
Sandbox
 ↓
Observe
 ↓
Evaluate
 ↓
Retry / Replan when necessary
 ↓
Checkpoint
 ↓
Live execution events
 ↓
UI
 ↓
Final result
```

This is NOT a request to create a mock agent.

NALA must perform real work using the existing NALA execution infrastructure.

---

# 1. CURRENT PROJECT STATE

The project currently has a working monolithic backend:

```text
nala_server.py
```

The existing NALA system already contains working or partially working infrastructure including:

- NalaLoop
- session handling
- checkpointing
- recovery
- sandbox execution
- telemetry
- LLM communication
- event queue / streaming
- memory
- safety mechanisms
- long-duration execution
- 1-hour soak testing

The 1-hour soak test has already been tested separately and successfully demonstrates long-running execution, checkpoint creation, and recovery behavior.

IMPORTANT:

DO NOT destroy or blindly rewrite these working components.

The purpose of this refactor is to create a clean composition layer around them.

---

# 2. CURRENT UI ANALYSIS

The existing frontend has already been analyzed.

The UI contains substantial autonomous-system concepts:

- Chat
- Work mode
- Task Graph
- Tool Activity
- Sandbox / execution visualization
- Checkpoints
- Telemetry
- Memory
- Safety
- Ṛta
- Viveka
- Satya
- Pramāṇa
- Context budget
- Generations
- Recovery concepts
- Execution timelines
- File/artifact concepts

The frontend therefore already represents the intended NALA execution environment.

However, many of these UI surfaces are currently static, simulated, locally generated, or incompletely connected to the backend.

Do NOT interpret the existence of these components as proof that the corresponding runtime protocol already exists.

---

# 3. CURRENT UI ↔ BACKEND FINDINGS

The current frontend already communicates with the existing backend through Socket.IO.

The important current path is approximately:

```text
Chat UI
 ↓
submit_prompt
 ↓
Socket.IO
 ↓
existing nala_server.py
```

The backend then performs intent classification:

```text
submit_prompt
 ↓
classify_intent
 ├── CHAT
 └── TASK
```

The CHAT path intentionally bypasses the autonomous execution infrastructure.

Therefore:

```text
CHAT
 ↓
LLM response
```

does NOT mean:

```text
TASK
 ↓
NalaLoop
 ↓
Sandbox
 ↓
Checkpoint
```

This distinction must remain explicit.

---

# 4. CURRENT BACKEND / UI CONTRACT PROBLEMS

The analysis found several mismatches.

## 4.1 Session identity mismatch

The backend creates a real:

```text
session_id
```

and emits session-related information.

The frontend does not currently establish a complete authoritative execution identity around that session.

---

## 4.2 Missing task identity

There is no sufficiently strong shared:

```text
task_id
```

contract between UI and backend.

The future execution protocol must associate every event with:

```text
session_id
task_id
generation_id
step_id
```

where applicable.

---

## 4.3 Event contract mismatch

The backend internally produces execution events such as:

```text
step_event
```

and translates some events into Socket.IO events such as:

```text
step_update
session_complete
session_error
```

The UI has consumers for some execution concepts, but there is no single canonical event schema shared by the entire system.

---

## 4.4 Sandbox visibility mismatch

The backend can perform sandbox execution.

The UI contains terminal/execution concepts.

But there is not yet a complete runtime event contract for:

```text
sandbox.started
sandbox.output
sandbox.completed
sandbox.failed
```

Therefore real sandbox activity is not reliably represented in the UI.

---

## 4.5 Checkpoint visibility mismatch

The backend has real checkpoint infrastructure.

The UI has checkpoint visualization.

But the UI currently contains static/mock checkpoint information in places.

We need real checkpoint events to flow from NALA to the UI.

---

## 4.6 Recovery visibility mismatch

The backend contains recovery/resume functionality.

The UI does not yet have a complete recovery event/control protocol.

The future architecture must expose recovery state through the same task event stream.

---

## 4.7 Approval mismatch

The backend has an approval mechanism.

The UI does not yet have a complete corresponding approval interaction protocol.

This should eventually become:

```text
Agent requests approval
 ↓
task.paused
 ↓
UI displays approval
 ↓
User approves/rejects
 ↓
Backend resumes/rejects
```

---

## 4.8 Tool execution mismatch

The UI has Tool Activity and Tool Execution visualization.

The backend has tool-related execution concepts.

But there is not yet one canonical runtime protocol connecting:

```text
tool.started
tool.output
tool.completed
tool.failed
```

to the UI.

---

# 5. IMPORTANT EXECUTION FINDING

The existing backend contains a task path that reaches sandbox-related execution.

However, some parts of the current execution implementation are still simplified.

In particular, some tool execution structures are not yet equivalent to a full:

```text
Planner
 ↓
Task Graph
 ↓
Tool Dispatcher
 ↓
Real Tool
 ↓
Sandbox
 ↓
Observation
 ↓
Evaluation
 ↓
Replanning
```

loop.

Therefore:

DO NOT claim that NALA is already fully equivalent to Codex / Claude Code.

The refactor should create the architecture required to reach that behavior while preserving the existing working infrastructure.

---

# 6. WHY WE ARE CREATING `nala_server/`

The purpose of the new folder is NOT merely code organization.

It is to create the missing composition layer.

The current system contains many capable components:

```text
NalaLoop
Sandbox
Checkpointing
Recovery
Memory
LLM
Telemetry
Safety
UI
```

But they need a common execution protocol.

The new server structure provides that spine.

---

# 7. NEW ROOT-LEVEL FOLDER

Create exactly ONE new root-level backend folder:

```text
nala_server/
```

It must sit at the root of the NALA project.

Example:

```text
NALA/
├── nala_server/
├── existing NALA core
├── sandbox
├── checkpoint
├── memory
├── tests
└── ...
```

Do NOT create another nested `nala_server/nala_server/`.

---

# 8. NEW FILE STRUCTURE

Create:

```text
nala_server/
├── __init__.py
├── contracts.py
├── main.py
├── config.py
├── state.py
├── handlers.py
├── nala_runner.py
├── llm_client.py
└── telemetry.py
```

That is:

```text
1 new folder
9 new files
```

Do NOT create additional architectural folders unless explicitly requested later.

---

# 9. `contracts.py` — THE MOST IMPORTANT NEW FILE

This file defines the canonical communication language between UI and NALA.

It should contain the core contracts:

```text
TaskRequest
Task
TaskEvent
TaskState
TaskResult
CheckpointRef
```

These structures should be strongly typed and serializable.

The exact implementation should be derived from the existing NALA behavior.

Do not invent fields unnecessarily.

---

# 10. `TaskRequest`

Represents a request from the UI to NALA.

Conceptually:

```text
TaskRequest
├── session_id
├── prompt / goal
├── mode
├── client metadata
└── optional configuration
```

The exact fields should match the current frontend/backend requirements.

---

# 11. `Task`

Represents one autonomous execution.

Conceptually:

```text
Task
├── task_id
├── session_id
├── generation_id
├── goal
├── status
├── current_step
├── created_at
├── updated_at
└── checkpoint reference
```

This becomes the authoritative identity of a running task.

---

# 12. `TaskState`

Define explicit lifecycle states.

For example:

```text
CREATED
QUEUED
PLANNING
RUNNING
WAITING_APPROVAL
PAUSED
RECOVERING
COMPLETED
FAILED
CANCELLED
```

Do not add states merely for appearance.

Only use states required by the actual lifecycle.

---

# 13. `TaskEvent`

This is the backbone of live UI communication.

Every meaningful execution transition should produce a structured event.

Conceptually:

```text
TaskEvent
├── event_id
├── event_type
├── task_id
├── session_id
├── generation_id
├── step_id
├── timestamp
├── status
└── payload
```

The event schema must be serializable over Socket.IO.

---

# 14. CANONICAL EVENT VOCABULARY

The target event vocabulary should cover:

```text
task.created
task.started
task.completed
task.failed
task.cancelled

planning.started
planning.completed

step.started
step.completed
step.failed

tool.started
tool.output
tool.completed
tool.failed

sandbox.started
sandbox.output
sandbox.completed
sandbox.failed

checkpoint.saved

recovery.started
recovery.completed
recovery.failed

approval.requested
approval.received

telemetry.updated

session.completed
session.error
```

IMPORTANT:

Before implementing events, compare these with the existing event names in `nala_server.py`.

Do not duplicate equivalent events under different names without a reason.

Create one canonical mapping.

---

# 15. `CheckpointRef`

Represents the checkpoint associated with a task/event.

Conceptually:

```text
CheckpointRef
├── checkpoint_id
├── task_id
├── session_id
├── generation_id
├── step_id
├── sequence / LSN if available
├── timestamp
└── storage reference
```

Do not duplicate checkpoint storage logic.

This object should reference the existing checkpoint system.

---

# 16. `main.py` — SERVER ENTRYPOINT

Responsibilities:

- Create ASGI application
- Create/configure Socket.IO
- Register handlers
- Load configuration
- Initialize shared state
- Initialize runner
- Health endpoint
- Startup lifecycle
- Shutdown lifecycle

It must NOT contain:

- planning
- tool execution
- sandbox logic
- checkpoint implementation
- LLM reasoning
- task orchestration

Think:

```text
main.py = ignition / wiring
```

not the brain.

---

# 17. `config.py` — CONFIGURATION

Own:

- server host
- server port
- Ollama configuration
- Groq configuration
- model configuration
- concurrency limits
- checkpoint paths
- timeouts
- sandbox configuration
- environment variables

Use the project's existing configuration approach where possible.

Do not duplicate configuration unnecessarily.

---

# 18. `state.py` — AUTHORITATIVE RUNTIME STATE

This file manages runtime state.

It should own things such as:

```text
sessions
tasks
task states
current step
checkpoint references
approval state
execution metadata
```

Important rule:

There should be one authoritative state representation.

Avoid separate conflicting state in:

```text
handlers.py
nala_runner.py
telemetry.py
```

---

# 19. `handlers.py` — UI GATEWAY

This is the communication boundary.

Responsibilities:

```text
UI event
 ↓
validate
 ↓
TaskRequest
 ↓
nala_runner
```

and:

```text
TaskEvent
 ↓
Socket.IO
 ↓
UI
```

It should handle events such as:

```text
connect
disconnect
submit_prompt / submit_task
cancel_task
pause_task
resume_task
submit_approval
```

depending on what actually exists and is required.

It must NOT contain:

- planner logic
- sandbox execution
- tool execution
- checkpoint logic
- LLM logic
- complex orchestration

Keep it thin.

---

# 20. `nala_runner.py` — EXECUTION SPINE

This is the most important execution file.

Responsibilities:

```text
TaskRequest
 ↓
Task creation
 ↓
NalaLoop
 ↓
planning
 ↓
task execution
 ↓
tools
 ↓
sandbox
 ↓
observation
 ↓
evaluation
 ↓
checkpoint
 ↓
recovery / replanning
 ↓
TaskResult
```

It should integrate the existing NALA infrastructure rather than rewrite it.

The runner should produce `TaskEvent` objects throughout the lifecycle.

---

# 21. `llm_client.py`

This file owns model communication only.

Responsibilities:

- Ollama
- Groq
- streaming
- retries
- timeout
- provider errors
- model selection/fallback when appropriate

It must NOT own:

- task planning
- sandbox execution
- tool selection
- task lifecycle
- checkpointing

---

# 22. `telemetry.py`

Observe the runtime.

Track things such as:

```text
task duration
step duration
model latency
tool latency
sandbox duration
checkpoint timing
retry count
token usage
CPU/memory where available
```

Telemetry should observe the system.

It should not control execution.

---

# 23. PRESERVE EXISTING NALA CORE

The following must NOT be thrown away merely because we create the new server structure:

```text
NalaLoop
Sandbox
CheckpointManager
Recovery
Memory
Safety
Telemetry infrastructure
Soak-test infrastructure
```

The new server should wrap/combine these components.

Think:

```text
EXISTING NALA CORE
       +
NEW COMPOSITION LAYER
       =
REAL NALA RUNTIME
```

---

# 24. FUTURE EXECUTION FLOW

The target architecture is:

```text
                         USER
                           │
                           ▼
                         UI
                           │
                     TaskRequest
                           │
                           ▼
                    handlers.py
                           │
                           ▼
                   nala_runner.py
                           │
                     create Task
                           │
                           ▼
                        Planner
                           │
                           ▼
                     Task Graph
                           │
                           ▼
                     Dispatcher
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          File Tool    Code Tool     Test Tool
              │            │            │
              └────────────┼────────────┘
                           ▼
                        Sandbox
                           │
                           ▼
                       Observe
                           │
                           ▼
                       Evaluate
                       /       \
                    PASS       FAIL
                     │           │
                     ▼           ▼
                  Continue     Diagnose
                                 │
                                 ▼
                              Replan
                                 │
                                 ▼
                           Checkpoint
                                 │
                                 ▼
                           TaskEvent
                                 │
                                 ▼
                           handlers.py
                                 │
                                 ▼
                                UI
```

---

# 25. THE UI MUST EVENTUALLY CHANGE TOO

Do not only refactor the backend.

The frontend must eventually consume the new contracts.

The target is:

```text
UI
 ↓
TaskRequest
 ↓
NALA
 ↓
TaskEvent stream
 ↓
Redux / state
 ↓
Work interface
```

The UI should stop relying on static representations for runtime information.

---

# 26. CHAT VS WORK

This is an important UI change.

Currently Chat and Work share much of the same prompt interface.

That is not necessarily wrong at the input level, but their execution semantics must become different.

### CHAT

```text
Conversation
 ↓
LLM response
```

### WORK

```text
Task
 ↓
Plan
 ↓
Tools
 ↓
Sandbox
 ↓
Files
 ↓
Checkpoints
 ↓
Live execution
 ↓
Final result
```

The Work interface should eventually expose:

```text
Task
├── Plan
├── Live Task Graph
├── Current Step
├── Tool Activity
├── Terminal / Sandbox
├── Files / Changes
├── Checkpoints
├── Recovery
└── Final Result
```

Do not build this UI immediately.

First establish the backend contract.

---

# 27. REDUX / FRONTEND STATE

The existing frontend already has Redux/state concepts for:

```text
connection
mode
ritaScore
safety
tools
transcendent
```

Do not delete these.

Instead determine which runtime values should become consumers of the new `TaskEvent` stream.

Eventually the UI should have authoritative runtime state for:

```text
session_id
task_id
generation_id
task status
current step
task events
tool events
sandbox output
checkpoint state
recovery state
approval state
final result
```

---

# 28. FIRST END-TO-END ACCEPTANCE TEST

Do NOT start with a complicated coding task.

Use a deterministic task such as:

```text
Create a Python project that prints "Hello NALA".
```

Expected flow:

```text
UI
 ↓
TaskRequest
 ↓
task.created
 ↓
task.started
 ↓
planning.started
 ↓
planning.completed
 ↓
step.started
 ↓
tool.started
 ↓
sandbox.started
 ↓
sandbox.output
 ↓
sandbox.completed
 ↓
evaluation
 ↓
checkpoint.saved
 ↓
step.completed
 ↓
task.completed
 ↓
TaskResult
 ↓
UI
```

The system must actually create and execute the project.

No fake response.

No hard-coded success.

---

# 29. SUCCESS CRITERIA

The first milestone is NOT "beautiful UI".

The first milestone is:

```text
UI prompt
 ↓
real TaskRequest
 ↓
real task_id
 ↓
real NALA execution
 ↓
real sandbox/tool work
 ↓
real checkpoint
 ↓
real TaskEvent stream
 ↓
real UI updates
 ↓
real final result
```

If that works, we have established the NALA nervous system.

---

# 30. DO NOT BUILD YET

Do NOT add these yet:

```text
Vector RAG expansion
Multi-agent council
MCP ecosystem
Horizontal scaling
Redis adapter
PostgreSQL
Celery
Kubernetes
OAuth
Vault
Blockchain audit logs
Advanced model routing
```

Those are later phases.

First make the single-agent execution spine reliable.

---

# 31. FUTURE ROADMAP

After the core execution contract works:

```text
1. Task Contract
2. Server Composition
3. Task Identity
4. Event Stream
5. UI ↔ NALA Bridge
6. Chat / Work Separation
7. Real Work UI
8. Real End-to-End Execution
9. Pause / Resume / Recovery
10. Interactive Task Graph
11. Tool ecosystem
12. MCP
13. Memory expansion
14. Multi-agent execution
15. Scaling
16. Enterprise security
17. Edge / sovereign deployment
```

---

# 32. CRITICAL ENGINEERING RULE

DO NOT rewrite working code simply to make the architecture look cleaner.

For every existing component:

```text
Does it work?
 ↓
Keep it.
 ↓
Wrap it with the new contract.
```

Only rewrite when the existing implementation prevents the required execution behavior.

---

# 33. CRITICAL ANTI-MOCK RULE

NALA must never pretend to have performed an action it did not perform.

Bad:

```text
User: "Create a project."

NALA:
"Done! I created the project."
```

when nothing was created.

Correct:

```text
Task created
 ↓
Tool executed
 ↓
Sandbox executed
 ↓
Files created
 ↓
Tests executed
 ↓
Result observed
 ↓
NALA reports actual result
```

---

# 34. CRITICAL STATE RULE

Every runtime event must be attributable.

Whenever applicable:

```text
event_id
session_id
task_id
generation_id
step_id
timestamp
```

This gives us deterministic observability and recovery.

---

# 35. CRITICAL COMPOSITION RULE

The architecture must answer:

> What happens next?

For every execution stage.

Components should not merely exist independently.

The composition layer must define:

```text
input
 ↓
decision
 ↓
execution
 ↓
observation
 ↓
state transition
 ↓
event
 ↓
next action
```

That is the missing nervous system.

---

# 36. FINAL ARCHITECTURAL GOAL

We are building:

```text
                     NALA
                      │
              ┌───────┴────────┐
              │                │
          CONTROL PLANE    EXECUTION PLANE
              │                │
              UI           nala_runner
              │                │
           Redux          NalaLoop
              │                │
         TaskEvents ────────► Tools
                               │
                            Sandbox
                               │
                          Checkpoints
                               │
                           Recovery
                               │
                            Memory
                               │
                             LLM
```

The ultimate principle is:

> **NALA should not merely tell the user what it could do. NALA should perform the work, observe reality, preserve state, recover from failure, and show the user what actually happened.**

---

# INSTRUCTIONS TO ANTIGRAVITY

Before modifying code:

1. Inspect the existing `nala_server.py`.
2. Inspect the existing NalaLoop.
3. Inspect checkpoint/recovery implementation.
4. Inspect sandbox implementation.
5. Inspect existing Socket.IO event names.
6. Inspect the already-identified UI communication files.
7. Map existing behavior to the new contracts.
8. Produce a migration plan.
9. Identify what can be preserved.
10. Identify exact files that must change.

DO NOT immediately rewrite everything.

DO NOT remove working functionality.

DO NOT create duplicate implementations of sandbox/checkpoint/recovery.

DO NOT invent a second NALA execution engine.

The new `nala_server/` package must become the **composition and protocol layer around the existing NALA core**.

The first implementation milestone is:

```text
TaskRequest
 → Task
 → NalaLoop
 → TaskEvent stream
 → TaskResult
```

with one real end-to-end task successfully executed through the UI.

Only after that milestone passes should we proceed to the larger Codex/CoWork-style capabilities.