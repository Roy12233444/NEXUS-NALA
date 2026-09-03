# 🧬 NALA — Official Product & Systems Documentation
**Nexus Autonomous Logic Architecture**  
*The Foundational Systems Layer for Long-Running, Self-Healing, and Sovereign Autonomous AI Organisms*

---

**Company:** Nexus LAB AI  
**Founder & Principal Systems Architect:** Sourav Ray  
**Classification:** Official Product & Technical Specification  
**Document Version:** `2.0.0-PROD`  
**Repository:** [https://github.com/Roy12233444/NALA-Project](https://github.com/Roy12233444/NALA-Project)  
**Status:** 🟢 **PRODUCTION & EVALUATION READY (113/113 PASSING TESTS)**

---

## 1. Executive Summary & Core Value Proposition

The vast majority of modern "AI agent" frameworks are superficial prompt wrappers built over third-party APIs. When deployed in complex, multi-hour enterprise workflows, they inevitably suffer from **silent execution drift, context window exhaustion, inability to recover from process crashes, security sandbox escapes, and complete hallucination of success without physical evidence**.

**NALA (Nexus Autonomous Logic Architecture)** is an original, first-principles AI systems engine built from the ground up to solve these structural failure modes. NALA provides the deterministic operating infrastructure beneath autonomous agents—combining:
1. **Durable Transactional Persistence**: ARIES-style database recovery, monotonic Log Sequence Numbers (LSNs), and Write-Ahead Logging (WAL) that guarantee zero-corruption crash recovery.
2. **Mathematical Epistemic Verification (Pramāṇa)**: Strict separation between probabilistic LLM assertions and physical, cryptographic SHA-256 disk readback evidence.
3. **Deterministic Safety Gating (Adaptive Viveka)**: Kernel-level process isolation, non-bypassable reference monitors, and destructive command interception.
4. **Graph-Theoretic Dynamic Planning**: Directed Acyclic Graph (DAG) goal decomposition with pre-flight cycle detection ($O(|V| + |E|)$).
5. **Crash-Resilient Working Memory**: Flat-file semantic storage with $O(1)$ set deduplication, atomic POSIX file replacement, and SHA-256 Optimistic Concurrency Control (OCC).

> **Core Philosophy**: *"Complexity belongs in the system. Clarity belongs in the interface. Roots before fruits."*

---

## 2. The Structural Industry Gap

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT STATE vs NALA ARCHITECTURE                     │
├────────────────────────────┬────────────────────────────────────────────────┤
│ Conventional Agent Tools   │ NALA Autonomous Systems Engine                 │
├────────────────────────────┼────────────────────────────────────────────────┤
│ Volatile in-memory state   │ Monotonic on-disk LSN Checkpoints & WAL        │
│ Halts or dies on crash     │ Automated ARIES-style crash recovery engine    │
│ Trust based on model tone  │ Cryptographic SHA-256 byte readback evidence   │
│ Naive vector DB overhead   │ High-speed atomic flat-file memory + OCC       │
│ Superficial string prompts │ Capability-based Viveka security gateway       │
│ Linear, rigid chat logs    │ Dynamic DAG planning & step timeline streams   │
│ Foreign cloud dependence   │ 100% sovereign, local & on-premise executable  │
└────────────────────────────┴────────────────────────────────────────────────┘
```

---

## 3. The 4-Layer Systems Architecture

NALA is architected across four cleanly separated, decoupled operational domains:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. BRAIN (Cognitive & Deliberative Core)                                    │
│    - Dynamic Planner (TaskGraph, DAG decomposition, Tarjan's DFS cycles)   │
│    - MemoryService (Flat-file markdown, O(1) deduplication, OCC revision)  │
│    - Saptacore Council & Ṛta Validator (Epistemic consensus & validation)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. HANDS (Execution, Isolation & Model Routing)                             │
│    - Tool Registry (Dynamic parameter typing, schema validation, latency)   │
│    - Sandbox Manager (Subprocess containment, Linux seccomp, Windows tokens)│
│    - Model Router (Local Ollama, Groq, cloud APIs with normalized output)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. SESSION & HARNESS (Durability, Lifecycle & Recovery)                     │
│    - NalaLoop (Asynchronous event-driven execution coordinator)             │
│    - CheckpointManager (Monotonic LSNs, atomic .tmp -> fsync -> replace)   │
│    - RecoveryEngine (ARIES crash recovery, durable retry circuit breaker)   │
│    - PhysicalEvidenceCorroborator (SHA-256 byte verification on disk)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. SAFETY & GOVERNANCE (Boundary Control & Invariant Enforcement)           │
│    - Adaptive Viveka Gate (Reference monitor: ALLOW / APPROVE / DENY)       │
│    - Satya Layer (Truthfulness verification & output invariant validation)  │
│    - Circuit Breaker (Fail-fast threshold protection against loops)         │
│    - Pramāṇa Router (6-channel epistemic knowledge classification)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Core Subsystems Deep-Dive (002A – 002G)

### 🔹 002A: Semantic Working Memory (`MemoryService`)
* **Physical Implementation**: [`core/brain/memory_service.py`](file:///E:/NALA-Project/NALA/core/brain/memory_service.py) $\to$ [`memory/MEMORY.md`](file:///E:/NALA-Project/NALA/memory/MEMORY.md)
* **Mechanics**:
  - **Human-Auditable Format**: Stores persistent facts as ISO date-stamped bullet points (`- (YYYY-MM-DD) Fact`).
  - **$O(1)$ Deduplication**: Pre-normalizes incoming text (lowercasing, symbol stripping) and checks an in-memory hash set to prevent memory pollution.
  - **Sliding Window Boundary**: Enforces a strict `MAX_FACTS = 300` boundary, automatically pruning the oldest facts to protect the LLM context window.
  - **Atomic Replacement**: Writes content to `.tmp_{pid}_{ts}` $\to$ executes POSIX `os.replace()` to guarantee zero torn writes upon system crash.
  - **Optimistic Concurrency Control (OCC)**: `_revision_token(content)` computes a cryptographic SHA-256 hash. Commits execute via compare-and-swap (`replace_if_revision`), rejecting stale concurrent edits.

---

### 🔹 002B: Dynamic Goal Planning & DAG Engine (`Planner`)
* **Physical Implementation**: [`core/brain/planner.py`](file:///E:/NALA-Project/NALA/core/brain/planner.py), [`core/harness/session_contract.py`](file:///E:/NALA-Project/NALA/core/harness/session_contract.py)
* **Mechanics**:
  - Decomposes high-entropy natural language goals into a structured `TaskGraph` composed of discrete `TaskStep` nodes.
  - **Pre-Flight Cycle Detection**: Employs Depth-First Search (`DFS`) back-edge detection with $O(|V| + |E|)$ time complexity to mathematically prove acyclicity before execution begins.
  - **Dependency Scheduling**: Resolves prerequisites dynamically; steps execute only when all upstream `dependencies: List[str]` transition to `COMPLETED`.

---

### 🔹 002C: Pramāṇa Epistemic Routing & Verification
* **Physical Implementation**: [`core/interaction/pramana_router.py`](file:///E:/NALA-Project/NALA/core/interaction/pramana_router.py), [`core/harness/recovery.py`](file:///E:/NALA-Project/NALA/core/harness/recovery.py)
* **Mechanics**:
  - Grounded in classical Indian epistemology, classifying all machine reasoning across 6 channels:
    1. **Pratyakṣa (Direct Perception)**: Real-time environmental sensor data and disk byte reads.
    2. **Anumāna (Inference)**: Deductive and inductive reasoning generated by large language models.
    3. **Śabda (Testimony)**: External API documentation, recalled user memory, and developer rules.
    4. **Upamāna (Analogy)**: Structural schema matching and comparative code patterns.
    5. **Arthāpatti (Postulation)**: Hypothesis testing when resolving missing dependencies.
    6. **Anupalabdhi (Non-Apprehension)**: Formal verification that an error or file is absent.
  - **Physical Corroboration**: `PhysicalEvidenceCorroborator` reads physical bytes directly from disk, computes the actual SHA-256 hash, and verifies byte parity. **NALA strictly forbids rendering green "Verified" badges based on LLM self-reported confidence.**

---

### 🔹 002D: Adaptive Viveka Gate & Sandbox Isolation
* **Physical Implementation**: [`core/safety/adaptive_viveka_gate.py`](file:///E:/NALA-Project/NALA/core/safety/adaptive_viveka_gate.py), [`core/hands/sandbox.py`](file:///E:/NALA-Project/NALA/core/hands/sandbox.py)
* **Mechanics**:
  - **Reference Monitor**: Enforces complete mediation over all tool calls before execution.
  - **Tri-State Decision Matrix**: Classifies actions into `ALLOW` (safe read-only), `APPROVAL_REQUIRED` (destructive or high-risk), and `DENY` (prohibited security boundaries).
  - **Static Pattern Interception**: Traps path traversal attacks (`..`), sensitive system files (`/etc/passwd`, `C:\Windows\System32`), and destructive commands (`rm -rf /`, `format`).
  - **OS-Level Containment**: Executes tools in sandboxed child processes using isolated working directories, environment variable scrubbing, and platform-specific containment (Linux seccomp syscall filters / Windows restricted job tokens).

---

### 🔹 002E: Cross-Core Runtime Orchestration (`NalaRunner`)
* **Physical Implementation**: [`nala_server/nala_runner.py`](file:///E:/NALA-Project/NALA/nala_server/nala_runner.py), [`nala_server/state.py`](file:///E:/NALA-Project/NALA/nala_server/state.py)
* **Mechanics**:
  - Executes long-running tasks in dedicated, non-blocking background worker threads.
  - **Thread-Safe State Authority**: Centralizes state transitions in `RuntimeState`, guarded by re-entrant mutex locks (`threading.RLock()`).
  - **Optimistic State Versioning**: Validates `expected_state_version` on every transition proposal, preventing race conditions from asynchronous workers.
  - **Cooperative Cancellation**: Gracefully halts execution at safe step boundaries via `cancel_event`, avoiding thread corruption and ensuring consistent on-disk state.

---

### 🔹 002F: Durable Checkpoints & Write-Ahead Logging
* **Physical Implementation**: [`core/harness/checkpoint.py`](file:///E:/NALA-Project/NALA/core/harness/checkpoint.py)
* **Mechanics**:
  - **Monotonic LSNs**: Generates strictly increasing Log Sequence Numbers (`LSN-000001`, `LSN-000002`, etc.) per session.
  - **Append-Only WAL**: Records state transitions to `.jsonl` write-ahead logs prior to memory commit.
  - **Zero-Corruption Persistence**: Every snapshot writes to `.tmp` $\to$ calls `os.fsync()` (forcing disk controller write-through) $\to$ performs atomic `os.replace()`.
  - **State Rewind Discipline**: UI and system strictly distinguish **Internal State Rewind** (reverting RAM session variables) from **External Effect Rollback** (which requires compensating transactions).

---

### 🔹 002G: Self-Healing Recovery Engine (`RecoveryEngine`)
* **Physical Implementation**: [`core/harness/recovery_engine.py`](file:///E:/NALA-Project/NALA/core/harness/recovery_engine.py)
* **Mechanics**:
  - **ARIES Crash Recovery Adaptation**: Executes 3 distinct recovery phases upon process resurrection:
    1. *Analysis Phase*: Scans checkpoints and WAL logs to reconstruct active task state.
    2. *Redo Phase*: Re-applies committed operations up to the last stable LSN.
    3. *Undo Phase*: Reverts incomplete or uncommitted active steps to a clean state.
  - **Durable Attempt Tracking**: Stores retry counts inside persistent checkpoint metadata—preventing infinite restart loops upon server reboot.
  - **Circuit Breaker Halting**: Bounded retry budget (`max_attempts=3`). If exhausted, the system transitions to `HALTED` and surfaces an asynchronous intervention request.

---

## 5. Control Center & Information Architecture

NALA abandons the fragile "chatbot-as-shell" paradigm in favor of an integrated, spatial command center governed by **5 Cognitive Axioms**:

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ TOP STATUS BAR (56px) ]  •  🧬 NALA Control Center  •  Status: 🔵 RUNNING (Step 2/4)  •  Burn: $0.02  •  [ ⏹ Cancel ]│
├─────────────────────────┬───────────────────────────────────────────────────────────┬──────────────────────────────────┤
│ ZONE 1: LEFT DRAWER     │ ZONE 2: CENTER MISSION SURFACE                            │ ZONE 3: RIGHT INSPECTOR          │
│ (Collapsible History)   │ (Primary Conversational & Execution Stream)               │ (Collapsible Telemetry)          │
│ Width: 260px - 300px    │ Flexible Width (Min 600px)                                │ Width: 320px - 380px             │
│                         │                                                           │                                  │
│ • Active Missions       │ 💬 Human Directive Input                                  │ 👁️ Pramāṇa Epistemic Route      │
│ • Checkpoint Lineage    │ 📋 Co-Planning Execution DAG (4 Steps)                    │ 🛡️ Adaptive Viveka Score        │
│ • Context Memory Facts  │ ⏳ Live Progress Timeline with Active Timers              │ ⚡ Tool Registry & Sandbox Latency│
│ • Asynchronous Inbox    │ 📄 Verified Artifact Cards (SHA-256 Readback)             │ 💾 Monotonic LSN Ledger          │
│                         │ 💬 Executive Markdown Synthesis                           │ 🧠 Injected Working Facts        │
└─────────────────────────┴───────────────────────────────────────────────────────────┴──────────────────────────────────┘
```

### The 13 Formal Typed Primitives
Every entity rendered in the UI maps to a strict, typed schema:
1. `MissionPrimitive`: Overarching objective container.
2. `TaskPrimitive`: Allocated compute thread.
3. `PlanPrimitive`: Dynamic DAG topology model.
4. `ExecutionStepPrimitive`: Semantic milestone node.
5. `ActionPrimitive`: Specific tool invocation instance.
6. `ApprovalRecordPrimitive`: Cryptographic human-authorization record.
7. `InterventionPrimitive`: Asynchronous yield-state request.
8. `CheckpointPrimitive`: Durable LSN snapshot record.
9. `RecoveryPrimitive`: Self-healing diagnosis and strategy log.
10. `ArtifactPrimitive`: Physical typed file with SHA-256 hash.
11. `VerificationPrimitive`: Cryptographic attestation audit record.
12. `MemoryFactPrimitive`: Content-addressed working fact.
13. `CompletionPrimitive`: Formal packaging and playbook extraction.

---

## 6. API, WebSocket & State Machine Contracts

### Central State Machine Transitions (`TaskState`)
Enforced deterministically by `RuntimeState.commit_transition()` in [`nala_server/state.py`](file:///E:/NALA-Project/NALA/nala_server/state.py):

```text
    ┌──────────┐
    │ CREATED  │
    └────┬─────┘
         ▼
    ┌──────────┐
    │  QUEUED  │
    └────┬─────┘
         ▼
    ┌──────────┐      Wait Approval      ┌──────────────────┐
    │ RUNNING  │ ──────────────────────► │ WAITING_APPROVAL │
    └────┬─────┘ ◄────────────────────── └──────────────────┘
         │               Approved
         ├─────────────────────────────────────────┐
         ▼                                         ▼
   ┌───────────┐                             ┌──────────┐
   │ COMPLETED │                             │  FAILED  │
   └───────────┘                             └──────────┘
```

### Real-Time WebSocket Event Spine
The backend communicates with client interfaces over full-duplex WebSockets on port `3001` using canonical `TaskEvent` structures:
* `task_created` / `task_started`: Emitted upon task lifecycle transitions.
* `step_started` / `step_progress` / `step_completed`: Real-time streaming of step progress and execution latency.
* `approval_required`: High-friction payload dispatched when the Viveka Gate traps a critical operation.
* `artifact_generated`: Broadcast when `PhysicalEvidenceCorroborator` confirms file integrity.
* `task_completed` / `task_failed` / `task_cancelled`: Final terminal state envelopes with execution metrics.

---

## 7. Verification & Empirical Proof

NALA enforces an uncompromising engineering test discipline. Every invariant is backed by automated pytest suites:

```text
============================= TEST SUITE EXECUTION SUMMARY =============================
Directory: tests/unit/ & tests/integration/
Total Automated Tests: 113
Passing Tests:         113 (100% Pass Rate)
Execution Time:        ~1.58 seconds

Key Verified Modules:
✔ test_checkpoint.py                -> Monotonic LSN increments & atomic .tmp replace
✔ test_crash_recovery.py            -> Full ARIES recovery from SIGKILL simulation
✔ test_recovery_engine.py           -> Durable attempt tracking & circuit breaker halting
✔ test_runtime_state_authority.py   -> Mutex concurrency & optimistic version rejection
✔ test_memory_service.py            -> O(1) deduplication & SHA-256 OCC revision tokens
✔ test_planner.py                   -> Dynamic DAG generation & DFS cycle detection
✔ test_pramana_router.py            -> 6-channel epistemic routing & hysteresis stability
✔ test_adaptive_viveka_gate.py      -> Path traversal blocking & least-privilege gating
✔ test_tool_registry.py             -> Schema validation & execution timeout isolation
✔ test_nala_loop.py                 -> End-to-end autonomous perception-planning-action loop
========================================================================================
```

---

## 8. Deployment & Quick Start Guide

### Prerequisites
* **Operating System**: Windows 10/11, Ubuntu 22.04+, or macOS
* **Python**: Python 3.11 or 3.12
* **Node.js**: v18.0.0+ (for Control Center UI)
* **Local LLM Runner (Optional)**: Ollama (for 100% sovereign offline execution)

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Roy12233444/NALA-Project.git
cd NALA-Project/NALA

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install UI dependencies
npm install
```

### 2. Running Automated Verification
```bash
# Execute full test suite to verify system integrity
pytest tests/unit tests/integration -v
```

### 3. Launching the Backend Server
```bash
# Starts the authoritative Socket.IO runtime server on port 3001
python nala_server.py
```

### 4. Launching the Control Center UI
```bash
# Starts the Vite React frontend on port 5173
npm run dev
```

---

## 9. Enterprise Security, Sovereignty & Compliance

1. **Air-Gapped Operation**: NALA can run 100% disconnected from the public internet using local Ollama models and internal file stores—protecting sensitive enterprise and government intellectual property.
2. **Deterministic Audit Trails**: Every action, tool invocation, safety check, and state transition is permanently recorded in append-only WAL logs and cryptographic LSN files.
3. **Defense-in-Depth Confinement**: No tool can execute arbitrary host commands without passing through the static regex validator, the Viveka LLM judge, and the operating system sandbox.
4. **Data Sovereignty by Design**: Working memory is stored as local markdown files under customer control, avoiding vendor lock-in and foreign cloud dependence.

---

## 10. Future Roadmap & Horizons

* **002H: Multi-Day Continuous Autonomy**: Long-horizon task scheduling, durable asynchronous sleep-wake loops, and distributed heartbeat monitoring.
* **Anjaneya Memory Protocol (AMP)**: Binary vector index format (`.nexus_idx`) supporting sub-millisecond local nearest-neighbor search over 100,000+ facts.
* **Chiranjeevi Playbook Extraction**: Automatically compiling successfully completed mission DAGs into reusable, deterministic Standard Operating Procedures (SOPs).
* **Ether Distributed Edge Mesh**: Peer-to-peer multi-agent consensus across heterogeneous edge devices and next-generation networks.

---

## 11. Contact & Corporate Information

**Nexus LAB AI**  
*Building the Foundations of Sovereign Intelligence*

* **Founder & Systems Architect:** Sourav Ray
* **Email:** `sourav@nexuslabai.com`
* **GitHub Organization:** [https://github.com/Roy12233444](https://github.com/Roy12233444)
* **Project Repository:** [https://github.com/Roy12233444/NALA-Project](https://github.com/Roy12233444/NALA-Project)
* **Location:** India

---
*Roots before fruits.* 🧬📐⚔️🚀
