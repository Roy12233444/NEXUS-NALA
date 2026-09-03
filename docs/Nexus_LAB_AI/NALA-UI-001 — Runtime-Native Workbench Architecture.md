# 🏛️ NALA-UI-001 — Runtime-Native Workbench Architecture
**Document Version:** 1.0.0 (Canonical Master Specification)  
**Author:** Nexus Lab AI Research Lab  
**Input Studies:** `COWORK #001`, `COWORK #002`, `COWORK #003`, `NALA-UI-001-A` through `NALA-UI-001-F`  
**Status:** 🔒 **CANONICAL ARCHITECTURE SPECIFICATION (FROZEN FOR IMPLEMENTATION)**  

---

## 🧭 Executive Summary & Canonical Definition

### Canonical Definition of NALA:
> **NALA is a long-running autonomous execution environment with persistent task state, atomic checkpoint recovery, real-time step observability, deterministic safety governance, and a runtime-native workbench interface.**

The NALA Workbench is not a decorative chatbot shell or a static dashboard. It is a **real-time, bidirectional visual projection of NALA's authoritative `RuntimeState` and `NalaRunner` event stream**, designed with the foundational principle:
> **"Complex Architecture Underneath. Simple, Effortless Interaction Above."**

---

## 🏗️ Architectural Topology

```text
                               ┌─────────────────────────────────────────┐
                               │             NALA WORKBENCH              │
                               │      (Human Steering & Observability)   │
                               └────────────────────┬────────────────────┘
                                                    │
                                   [Canonical Socket.IO Event Stream]
                                   [contracts.py / compatibility_adapter]
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │               NALA SERVER               │
                               │        (Modular Request Handlers)       │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │               NALA RUNNER               │
                               │        (Coordination & Dispatch)        │
                               └───────┬─────────────────────────┬───────┘
                                       │                         │
                                       ▼                         ▼
                        ┌────────────────────────┐    ┌────────────────────────┐
                        │     RUNTIMESTATE       │    │     SATYA / ṚTA        │
                        │  (Authoritative Truth, │    │    SAFETY GOVERNOR     │
                        │   Optimistic Locks)    │    │   (Dynamic Thresholds) │
                        └──────────────┬─────────┘    └────────────────────────┘
                                       │
                                       ▼
                        ┌────────────────────────┐
                        │        NALALOOP        │
                        │   (State Machine DAG,  │
                        │    Step Dispatcher)    │
                        └───────┬────────┬───────┘
                                │        │
                ┌───────────────┘        └───────────────┐
                ▼                                        ▼
 ┌─────────────────────────────┐          ┌─────────────────────────────┐
 │     CHECKPOINT MANAGER      │          │     DRONAGIRI COMPACTOR     │
 │  (Atomic LSN Snapshots on   │          │  (Sliding-Window Token      │
 │   Disk with CRC32 Checksum) │          │   Compaction & Spores)      │
 └─────────────────────────────┘          └─────────────────────────────┘
```

---

## 🧬 Summary of Derivations (ADOPT / ADAPT / REJECT / INVENT)

### 🟢 1. ADOPT (The Industry Fundamentals)
- **Live Step & Thought Observability:** Real-time stream of what the agent is thinking, planning, and doing.
- **Model Context Protocol (MCP):** Universal standard for external tool, database, and API integrations.
- **Automated Verification Loops:** Running post-edit test suites (`pytest`, `npm test`, linters) before marking steps complete.
- **Physical Workspace Artifact Output:** Concrete files written directly to disk (`.md`, `.py`, `.xlsx`).

### 🔵 2. ADAPT (The NALA Runtime Translations)
- **Persistent Project Instructions:** Adapted from `AGENTS.md`/`CLAUDE.md` into NALA's structured **Project Context Contract** + `MEMORY.md`.
- **Sub-Agent Context Isolation:** Adapted into NALA sub-worker threads that execute isolated sub-tasks with scoped toolsets.
- **Context Compaction:** Adapted into NALA's native `DronagiriCompactor` and `HandoffSpore` for vector-backed memory paging.
- **Multi-Tiered Permissions:** Adapted into NALA's `APPROVAL_REQUESTED` state machine gated by the Satya/Ṛta safety governor.

### 🔴 3. REJECT (The Clutter & Fragility We Discard)
- **Compulsory Git Worktrees:** Discarded as a universal requirement; simple workspace folder sandboxing is lighter and universal.
- **Pixel-Based Screen Clicking (Computer Use):** Discarded as primary tool due to high latency and error rates compared to native APIs, CLI, and headless tools.
- **Ephemeral Chat-Only Shells:** Discarded because chatbots cannot represent DAG task graphs, checkpoint lineages, or active approval queues.

### 🟣 4. INVENT (The Unique NALA Moat)
- **Checkpoint Lineage & Time-Travel Timeline:** Exposing NALA's LSN checkpoint ledger in the UI so users can inspect execution history, rewind, and resume from past states.
- **Ṛta / Satya Safety Resonance Gauge:** Real-time visual projection of epistemic truthfulness and cognitive safety scores computed by the safety governor.
- **Cognitive Provenance & Evidence Linking:** Every state transition in `RuntimeState` binds actor, reason, and empirical evidence directly to UI event badges.
- **Reconnection Milestone Playback:** Compact replay of background milestones when a user reconnects after stepping away.

---

## 🖥️ Workbench Information Hierarchy & Control Surface

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  NALA WORKBENCH                                                   Ṛta: 0.98 (Nominal)  │
├──────────────┬──────────────────────────────────────────────────────────┬──────────────┤
│  WORKSPACE   │                     EXECUTION STAGE                      │  GOVERNANCE  │
│  (Collapsible│                                                          │  (On-Demand) │
│              │  🎯 GOAL: Autonomous Benchmark Synthesis                │              │
│  📁 Projects │  ──────────────────────────────────────────────────────  │  ⚠️ APPROVAL │
│  📜 Tasks    │  📋 PLAN:                                                │     QUEUE    │
│  💾 Memory   │  [✓] 1. Ingest primary source documents                 │              │
│  🔄 Lineage  │  [▶] 2. Extract technical feature matrices (RUNNING)     │  Delete file │
│     (LSN 42) │  [ ] 3. Compile comparative markdown report              │  test.tmp?   │
│              │  ──────────────────────────────────────────────────────  │  [Approve]   │
│              │  💬 LIVE EXECUTION & REASONING:                          │  [Reject]    │
│              │  ├─ Thinking: Parsing extraction tables...               │              │
│              │  ├─ Tool: ripgrep search 'sub-agents' (200ms)            │  🛡️ SATYA    │
│              │  └─ Output: Found 14 matches in docs/                    │     LAYER    │
│              │  ──────────────────────────────────────────────────────  │  Truth: 99%  │
│              │  📄 ARTIFACT: benchmark_matrix.md (Preview)              │  Health: 100%│
│              │  ──────────────────────────────────────────────────────  │              │
│              │  [ ⌨️ Enter prompt, command, or mid-flight steer...    ] │              │
└──────────────┴──────────────────────────────────────────────────────────┴──────────────┘
```

---

## 🧪 Hostile Architecture Validation (The 10 Critical Stress Tests)

| # | Stress Test | Architectural Mechanism | Validation Verdict |
| :--- | :--- | :--- | :---: |
| **1** | **Browser Closure / Disconnect** | `NalaRunner` executes inside background daemon; state persisted to disk independently of Socket.IO client. | 🟢 **PASS** |
| **2** | **Server Process Crash / Restart** | `CheckpointManager` logs monotonic LSNs with CRC32 integrity; on reboot, NALA reloads latest valid snapshot and resumes. | 🟢 **PASS** |
| **3** | **Execution Observability** | Canonical `TaskEvent` stream broadcasts step headers, reasoning thoughts, tool calls, and output telemetry in real-time. | 🟢 **PASS** |
| **4** | **Mid-Flight Human Steering** | Socket.IO `steer_task` pushes directive into `RuntimeState.steering_queue`, evaluated by `NalaLoop` at next step boundary. | 🟢 **PASS** |
| **5** | **Failure Recovery & Rollback** | Step failure sets `TaskState.RECOVERING`; engine attempts automated recovery or rewinds to previous verified checkpoint. | 🟢 **PASS** |
| **6** | **Client Reconnection** | On connect, UI queries `RuntimeState` snapshot and receives milestone replay of events completed during absence. | 🟢 **PASS** |
| **7** | **Physical Artifact Persistence** | Artifacts are written to local disk in workspace directory (`.md`, `.xlsx`, `.py`) with live preview links. | 🟢 **PASS** |
| **8** | **Context Window Exhaustion** | `ContextTracker` detects token limits and triggers `DronagiriCompactor` sliding-window summarization / `HandoffSpore`. | 🟢 **PASS** |
| **9** | **Cognitive Simplicity** | 4-tier visibility model keeps raw telemetry hidden in collapsible drawers while keeping goal, plan, and thoughts front-and-center. | 🟢 **PASS** |
| **10**| **Extensibility without UI Rewrite** | UI listens exclusively to canonical `TaskEventType` contracts; adding tools or skills requires zero frontend redesign. | 🟢 **PASS** |

---

## 🛑 Architecture Freeze & Readiness Checklist

- [x] COWORK #001, #002, #003 synthesized and cross-referenced
- [x] Universal primitives separated from implementation choices (`NALA-UI-001-A`, `NALA-UI-001-B`)
- [x] Real NALA codebase audited across 5 maturity stages (`NALA-UI-001-C`)
- [x] Long-running agent kernel requirements specified (`NALA-UI-001-D`)
- [x] ADOPT / ADAPT / REJECT / INVENT derivation matrix completed (`NALA-UI-001-E`)
- [x] Candidate NALA Workbench UI layout and contract derived (`NALA-UI-001-F`)
- [x] Canonical master specification frozen in `NALA-UI-001 — Runtime-Native Workbench Architecture.md`
- [x] Hostile validation passed across all 10 stress tests
- [x] **Zero NALA UI code modified**
- [x] **Zero NALA backend code modified**

---

```text
================================================================================
NALA-UI-001 — CROSS-SYSTEM SYNTHESIS & NALA CAPABILITY DERIVATION
================================================================================
RESEARCH CORPUS:            🟢 COMPLETE (Cowork, Codex, Claude Code)
PRIMITIVE MAP:              🟢 COMPLETE (12 Fundamental Primitives)
CAPABILITY AUDIT:           🟢 COMPLETE (Code-First Maturity Audit)
DERIVATION MATRIX:          🟢 COMPLETE (Adopt, Adapt, Reject, Invent)
WORKBENCH ARCHITECTURE:     🟢 COMPLETE (Runtime-Native Projection)
HOSTILE VALIDATION:         🟢 PASSED (10/10 Stress Tests)
ARCHITECTURE STATE:         🔒 FROZEN FOR IMPLEMENTATION
NALA CODE MODIFICATIONS:    0
NALA UI MODIFICATIONS:      0
NEXT STAGE:                 PHASED NALA WORKBENCH IMPLEMENTATION
================================================================================
```
