# 🔬 NALA Architecture Research Notebook — NALA-UI-001-D
**Title:** Long-Running Agent Kernel Requirements  
**Topic:** Formal Specification of the Minimum Autonomous Engine for Multi-Hour/Multi-Day Tasks  
**Status:** 🟢 **DERIVATION COMPLETE (LOCKED FOR WORKBENCH DERIVATION)**  

---

## 🧭 Objective
Determine the **exact mathematical and architectural requirements** that enable NALA to safely execute tasks across extended time horizons (hours/days), independent of client UI connections or process restarts.

---

## 🏛️ The 8 Pillars of the Long-Running Kernel

```text
                                 ┌─────────────────────────────┐
                                 │     1. GOAL PERSISTENCE     │
                                 │    (Intent & Acceptance)    │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │     2. TASK GRAPH RUNNER    │
                                 │    (DAG & Step Dispatch)    │
                                 └──────────────┬──────────────┘
                                                │
                         ┌──────────────────────┴──────────────────────┐
                         ▼                                             ▼
          ┌─────────────────────────────┐               ┌─────────────────────────────┐
          │  3. STATE & PROVENANCE LEDGER│              │ 4. DETERMINISTIC GOVERNANCE │
          │ (Optimistic Locks / LSN CPs)│               │  (Ṛta/Satya Approval Gates) │
          └──────────────┬──────────────┘               └──────────────┬──────────────┘
                         │                                             │
                         └──────────────────────┬──────────────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │   5. ISOLATED SUB-WORKERS   │
                                 │  (Context-Isolated Runners) │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │    6. COMPACTION & HANDOFF  │
                                 │   (Dronagiri Vector Paging) │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │  7. VERIFICATION FEEDBACK   │
                                 │   (Test & Assertion Loop)   │
                                 └──────────────┬──────────────┘
                                                │
                                                ▼
                                 ┌─────────────────────────────┐
                                 │ 8. ATOMIC PHYSICAL DELIVERY │
                                 │  (Artifacts & Local Files)  │
                                 └─────────────────────────────┘
```

---

## 📋 Kernel Requirements Derivation

### 1. Goal Persistence (Mission Intent)
- **Requirement:** A task goal cannot exist solely as a short-term chat prompt in volatile memory. It must be persisted in a durable record (`SessionState.goal`) with explicit acceptance criteria.
- **Justification:** If an agent runs for 6 hours, intermediate context accumulation will degrade the original objective unless the root goal is pinned outside the conversational sliding window.

### 2. Task Graph & Step Dispatcher (`NalaLoop`)
- **Requirement:** Complex objectives must be broken into a directed acyclic graph (DAG) of discrete `TaskStep` entries, where each step has defined inputs, dependencies, timeouts, and handlers.
- **Justification:** Monolithic execution loops cannot be paused, inspected, or recovered at intermediate points without losing all progress.

### 3. Checkpointing & Recovery Ledger (`CheckpointManager` + `state.py`)
- **Requirement:** State transitions must increment a monotonic Log Sequence Number (LSN) and write an atomic snapshot before and after every tool invocation.
- **Justification:** Guarantees crash-recovery with zero state corruption. On restart, NALA reloads the latest verified LSN and resumes without re-executing completed side-effects.

### 4. Deterministic Governance & Human Gateways (`Satya` / `ṚtaGovernor`)
- **Requirement:** High-risk actions (file deletion, external communications, financial mutations) must trigger a blocking `APPROVAL_REQUESTED` state.
- **Justification:** Prevents runaway execution and malicious prompt-injection compromise.

### 5. Context Lifecycle Management (`DronagiriCompactor`)
- **Requirement:** Continuous token monitoring that triggers sliding-window summarization or handoff spores before LLM context limits are exceeded.
- **Justification:** Eliminates hard context exhaustion errors during deep research or multi-file development.

### 6. Verification Loops
- **Requirement:** The engine must execute post-action validation (e.g. syntax checks, automated test suites, schema validation) before committing a step as completed.
- **Justification:** Prevents cascading errors from propagating down the task graph.

### 7. Detached Daemon Execution
- **Requirement:** The execution runner (`NalaRunner`) must run in a persistent background daemon decoupled from client WebSocket connections.
- **Justification:** Allows the user to close the browser, shut down their workstation, or switch devices while NALA continues executing autonomously.
