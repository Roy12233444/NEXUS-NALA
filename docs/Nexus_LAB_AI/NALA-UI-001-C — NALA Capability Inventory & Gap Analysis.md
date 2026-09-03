# 🔬 NALA Architecture Research Notebook — NALA-UI-001-C
**Title:** NALA Capability Inventory & Gap Analysis  
**Methodology:** Code-First Forensic Audit of NALA Server, Runtime Harness & Client Boundary  
**Status:** 🟢 **AUDIT COMPLETE (LOCKED FOR WORKBENCH DERIVATION)**  

---

## 🧭 The 5-Stage Maturity Classification
Never declare a capability "ready" just because a class exists in the repo. Every capability is audited against 5 strict operational stages:
1. **`DEFINED`**: Pydantic / dataclass contract exists in `contracts.py` or domain types.
2. **`IMPLEMENTED`**: Core algorithm / state transition logic is written and unit-tested.
3. **`CONNECTED`**: Server handlers (`handlers.py`/`nala_server.py`) dispatch into the engine.
4. **`EXECUTABLE`**: Real loop executes with actual model/tool invocations (not hardcoded mocks).
5. **`OBSERVABLE`**: Emits real-time typed events across WebSocket to the client UI.

---

## 🔍 Detailed Capability Inventory Table

| Capability | Maturity Stage | Source Files & Code Symbols | Real Execution Reality |
| :--- | :--- | :--- | :--- |
| **Authoritative State Transitions** | 🟢 **OBSERVABLE** (Full) | `nala_server/state.py` (`RuntimeState`), `nala_server/contracts.py` (`TaskState`, `TransitionProposal`) | Serialized transition locks, optimistic concurrency guards, transition event emission verified. |
| **Execution Loop Orchestration** | 🟢 **EXECUTABLE** (Backend) | `core/harness/nala_loop.py` (`NalaLoop`), `nala_server/nala_runner.py` (`NalaRunner`) | Multi-step task loop executes, handles step errors, pre/post checkpoints. |
| **Atomic Checkpointing** | 🟢 **EXECUTABLE** (Backend) | `core/harness/checkpoint.py` (`CheckpointManager`), `nala_server/nala_runner.py` | LSN monotonic logging with CRC32 integrity checks written to disk. |
| **Session Handoff & Compaction** | 🟢 **IMPLEMENTED** (Backend) | `core/harness/context_tracker.py` (`DronagiriCompactor`), `core/harness/session_handoff.py` (`HandoffSpore`) | Token tracking & context compaction implemented; triggers `ContextExhaustedSignal`. |
| **Socket.IO Event Translation** | 🟢 **CONNECTED** | `nala_server/compatibility_adapter.py` (`CompatibilityAdapter`), `nala_server/handlers.py` | Translates canonical `TaskEvent` into legacy UI event payloads. |
| **Prompt Submission -> Execution** | 🟢 **OBSERVABLE** (Chat) | `nala_server.py` (`submit_prompt`), `OllamaClient` | Direct prompt streams live chunks to UI; fallback routes through NalaRunner. |
| **Deterministic Safety Governance** | 🟡 **CONNECTED** | `core/safety/rta_governor.py`, `core/safety/context_aware_satya_layer.py`, `contracts.py` (`APPROVAL_REQUESTED`) | Backend governance daemon calculates Ṛta/Satya scores; approval state defined in contracts. |
| **Sub-Agent Context Isolation** | 🟡 **DEFINED / PARTIAL** | `contracts.py` (`subagent_id` field in TaskEvent) | Parent-child event correlation defined, but dynamic subagent spawning harness not yet exposed to UI. |
| **Mid-Flight Steering Queue** | 🟡 **CONNECTED** | `nala_server/handlers.py` (`pause_task`, `resume_task`, `cancel_task`) | Handler functions wired to `NalaRunner`; UI controls currently stripped down in minimal view. |
| **Physical Artifact Persistence** | 🟡 **CONNECTED** | `core/hands/sandbox/` (`SandboxManager`), `core/harness/session_contract.py` | Artifacts written to sandbox directory; UI needs rich artifact viewing projection. |
| **UI Projection of Runtime State** | 🔴 **MISSING (GAP)** | `src/components/` (Frontend React) | UI was previously a decorative mock dashboard, now stripped to minimal chat. Needs to become a **canonical projection of RuntimeState**. |

---

## 🚨 Critical Architectural Gap Identified

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            THE CORE NALA GAP                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ The NALA backend has an advanced, enterprise-grade runtime organism:       │
│   • NalaLoop (State Machine)                                                │
│   • RuntimeState (Authoritative Optimistic Concurrency Manager)             │
│   • CheckpointManager (LSN / Atomic Integrity Checkpointer)                 │
│   • Satya / Ṛta Safety Governor                                             │
│   • DronagiriCompactor (Context & Handoff Engine)                           │
│                                                                             │
│ BUT THE FRONTEND WAS PREVIOUSLY DISCONNECTED:                              │
│   • Old UI expected mock/hardcoded timer simulations.                       │
│   • Recent cleanup stripped the UI down to clean prompt/reply.              │
│   • THE REAL GAP: A clean, minimal Workbench UI that natively listens to    │
│     canonical TaskEvents (Planning, Steps, Tools, Approvals, Checkpoints)   │
│     and projects them with high aesthetic clarity!                          │
└─────────────────────────────────────────────────────────────────────────────┘
```
