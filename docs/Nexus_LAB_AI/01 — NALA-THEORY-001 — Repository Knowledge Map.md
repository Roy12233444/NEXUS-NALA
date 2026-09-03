# 🗺️ NALA-THEORY-001 — Repository Knowledge Map
**Classification:** Core Theory & Architecture Mapping  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **VERIFIED AGAINST PHYSICAL REPOSITORY CODE**

---

## 1. Executive Mission & Evidence Methodology

This document maps every physical subsystem, class, file, and test suite in NALA directly to the foundational theories of Computer Science, AI/ML, Distributed Systems, Operating Systems, Mathematics, and Reliability Engineering that govern its operation.

### Evidence Classification Standard:
* **`[FACT]`**: Directly verified in repository code, classes, functions, or schemas.
* **`[INFERENCE]`**: Logical architectural necessity derived from implementation behavior.
* **`[THEORY]`**: Foundational academic/theoretical concept required to explain *why* the implementation works.
* **`[UNVERIFIED]`**: Proposed or target capability not yet backed by physical code.

---

## 2. Comprehensive Subsystem-to-Theory Map

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NALA REPOSITORY ARCHITECTURE                                  │
├───────────────────┬──────────────────────────────────┬───────────────────────────────────────────┤
│ Domain / Layer    │ Physical File / Component        │ Underlying Theoretical Foundations        │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 1. Brain & Plan   │ core/brain/planner.py            │ Graph Theory, DAGs, Tarjan's DFS,         │
│                   │ core/brain/saptacore_council.py  │ Topological Sort, State Space Search,     │
│                   │ core/brain/judge.py              │ Multi-Agent Consensus, Social Choice      │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 2. Memory & RAG   │ core/brain/memory_service.py     │ Vector Spaces, Dot Product, Linear Alg,   │
│                   │ core/session/amp_client.py       │ Recency Decay, Optimistic Concurrency,   │
│                   │ data/memory/MEMORY.md            │ Deduplication (Set Theory, SHA-256)       │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 3. Epistemology   │ core/interaction/pramana_router  │ Formal Epistemology, Bayesian Update,     │
│    & Cognition    │ core/safety/rta_feedback_loop.py │ Calibration, Hysteresis, Control Theory,  │
│                   │ core/safety/rta_governor.py      │ Dynamic Modulation, State Estimators      │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 4. Safety & Gates │ core/safety/adaptive_viveka_gate │ Capability-Based Security, Least Privilege│
│                   │ core/safety/satya.py             │ Invariant Validation, Lattice Refinement, │
│                   │ core/safety/circuit_breaker.py   │ Circuit Breaker Pattern, Fault Tolerance  │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 5. Execution Hands│ core/hands/tool_registry.py      │ Dynamic Dispatch, Parameter Schema Typing,│
│    & Isolation    │ core/hands/sandbox.py            │ OS Sandboxing, Process Isolation, IPC,    │
│                   │ core/hands/model_router.py       │ Seccomp/Namespaces, Latency Profiling     │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 6. Harness & Loop │ core/harness/nala_loop.py        │ Event Loops, Re-entrancy, State Machines, │
│                   │ core/harness/session_contract.py │ Serializable Contracts, Type Invariants,  │
│                   │ core/harness/context_tracker.py  │ Token Budgeting, Dynamic Compaction       │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 7. Persistence    │ core/harness/checkpoint.py       │ Write-Ahead Logging (WAL), Log Sequence   │
│    & Recovery     │ core/harness/recovery.py         │ Numbers (LSN), Atomic File Replacement,   │
│                   │ core/harness/recovery_engine.py  │ ARIES Recovery, Idempotency, SHA-256 Hash │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 8. Server & State │ nala_server/state.py             │ Centralized State Authority, Mutex Locks, │
│    Authority      │ nala_server/contracts.py         │ Transition Guards, Optimistic Concurrency,│
│                   │ nala_server/nala_runner.py       │ Non-blocking Asynchronous Worker Threads  │
├───────────────────┼──────────────────────────────────┼───────────────────────────────────────────┤
│ 9. Transport & UI │ nala_server.py (Socket.IO)       │ Asynchronous I/O, WebSocket Framing,      │
│    Integration    │ src/services/websocketService.ts │ Backpressure, Event-Driven Architecture,  │
│                   │ src/components/features/chat/    │ Reactive UI, Unidirectional Data Flow     │
└───────────────────┴──────────────────────────────────┴───────────────────────────────────────────┘
```

---

## 3. Detailed Component Decomposition & Theoretical Grounding

### 🧠 1. Cognitive Brain & Planning Engine
* **Physical Files**:
  - [`core/brain/planner.py`](file:///E:/NALA-Project/NALA/core/brain/planner.py)
  - [`core/harness/session_contract.py`](file:///E:/NALA-Project/NALA/core/harness/session_contract.py) (`TaskGraph`, `TaskStep`)
  - [`tests/unit/test_planner.py`](file:///E:/NALA-Project/NALA/tests/unit/test_planner.py)
* **What it Actually Does** `[FACT]`:
  - `Planner.create_plan(goal: str)` decomposes natural language goals into a `TaskGraph` containing discrete `TaskStep` objects.
  - Computes dependency graphs where each step contains `dependencies: List[str]`.
  - Executes cycle detection before execution using Depth-First Search (`DFS`) to prevent infinite execution loops.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Graph Theory**: Directed Acyclic Graphs ($G = (V, E)$), In-Degree/Out-Degree, Topological Sorting ($O(|V| + |E|)$).
  2. **Automated Planning**: STRIPS/PDDL classical planning, hierarchical task networks (HTN), goal decomposition trees.
  3. **Algorithm Design**: Tarjan's Strongly Connected Components, Cycle Detection Algorithms.
  4. **Scheduling Theory**: Critical Path Method (CPM), dependency-constrained task scheduling.

---

### 💾 2. Memory & Knowledge Representation
* **Physical Files**:
  - [`core/brain/memory_service.py`](file:///E:/NALA-Project/NALA/core/brain/memory_service.py)
  - [`core/session/amp_client.py`](file:///E:/NALA-Project/NALA/core/session/amp_client.py)
  - [`data/memory/MEMORY.md`](file:///E:/NALA-Project/NALA/memory/MEMORY.md)
  - [`tests/unit/test_memory_service.py`](file:///E:/NALA-Project/NALA/tests/unit/test_memory_service.py)
* **What it Actually Does** `[FACT]`:
  - Persists bullet-point facts to disk in Markdown format (`memory/MEMORY.md`).
  - `_revision_token(content)` computes SHA-256 checksums to detect concurrent write conflicts.
  - `_normalize(text)` lowercases and strips whitespace to perform $O(1)$ set-based deduplication.
  - `recall(max_chars=4000)` extracts facts within token budget constraints and injects them into the Planner.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Information Retrieval (IR)**: Vector Space Models, TF-IDF, semantic dense embeddings, Cosine Similarity ($ \cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} $).
  2. **Linear Algebra**: Inner product spaces, vector norms, metric spaces, Euclidean distance ($L_2$).
  3. **Concurrency Control**: Optimistic Concurrency Control (OCC), atomic compare-and-swap (CAS), revision tokens.
  4. **Data Management**: Append-only storage, compaction policies, recency decay algorithms.

---

### 👁️ 3. Pramāṇa Epistemic Routing & Dynamic Governance
* **Physical Files**:
  - [`core/interaction/pramana_router.py`](file:///E:/NALA-Project/NALA/core/interaction/pramana_router.py)
  - [`core/safety/rta_feedback_loop.py`](file:///E:/NALA-Project/NALA/core/safety/rta_feedback_loop.py)
  - [`core/safety/rta_governor.py`](file:///E:/NALA-Project/NALA/core/safety/rta_governor.py)
  - [`tests/unit/test_pramana_router.py`](file:///E:/NALA-Project/NALA/tests/unit/test_pramana_router.py)
* **What it Actually Does** `[FACT]`:
  - Maps execution intent across 6 classical epistemic pathways: *Pratyakṣa* (Perception), *Anumāna* (Inference), *Śabda* (Testimony), *Upamāna* (Analogy), *Arthāpatti* (Postulation), *Anupalabdhi* (Non-Apprehension).
  - Routes model modality (Gaṇeśa, Sarasvatī, Śiva) dynamically based on real-time `Ṛta-Score` ($[0.0, 1.0]$).
  - Implements hysteresis window buffers (`deque(maxlen=10)`) to prevent high-frequency thrashing between operational states.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Epistemology & Philosophy of AI**: Foundationalism, coherentism, reliabilism, sources of justified true belief.
  2. **Probability & Decision Theory**: Bayesian belief updating ($P(H|E) = \frac{P(E|H)P(H)}{P(E)}$), calibration curves, Brier scores.
  3. **Control Theory & Dynamical Systems**: Feedback control loops, PID controllers, Hysteresis, State Estimation, Bang-Bang control vs Smooth modulation.
  4. **Signal Processing**: Moving average filters, noise reduction, thresholding algorithms.

---

### 🛡️ 4. Safety Gates, Satya Invariants & Circuit Breakers
* **Physical Files**:
  - [`core/safety/adaptive_viveka_gate.py`](file:///E:/NALA-Project/NALA/core/safety/adaptive_viveka_gate.py)
  - [`core/safety/satya.py`](file:///E:/NALA-Project/NALA/core/safety/satya.py)
  - [`core/safety/circuit_breaker.py`](file:///E:/NALA-Project/NALA/core/safety/circuit_breaker.py)
  - [`tests/unit/test_adaptive_viveka_gate.py`](file:///E:/NALA-Project/NALA/tests/unit/test_adaptive_viveka_gate.py)
* **What it Actually Does** `[FACT]`:
  - `AdaptiveVivekaGate` evaluates tool requests against static prohibited path regexes (`/etc/passwd`, `system32`, `..`) and destructive commands (`rm -rf /`, `format`).
  - Returns canonical `VivekaDecision`: `ALLOW`, `APPROVAL_REQUIRED`, `DENY`.
  - `CircuitBreaker` tracks consecutive failure counts and transitions between `CLOSED`, `OPEN`, and `HALF_OPEN` states.
  - `SatyaLayer` evaluates consistency and truthfulness metrics across execution outputs.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Computer Security & Access Control**: Principle of Least Privilege, Access Control Lists (ACLs), Capability-based security, Reference Monitors.
  2. **Formal Verification & Invariants**: Safety invariants ($G(P)$ in LTL), preconditions, postconditions, Hoare logic ($ \{P\} C \{Q\} $).
  3. **Fault-Tolerant Distributed Systems**: Circuit Breaker Pattern (Nygard), bulkhead isolation, fail-fast mechanisms.
  4. **AI Alignment & Guardrails**: Input sanitization, prompt injection defenses, execution blast-radius containment.

---

### ✋ 5. Execution Hands, Tool Registry & Sandbox Isolation
* **Physical Files**:
  - [`core/hands/tool_registry.py`](file:///E:/NALA-Project/NALA/core/hands/tool_registry.py)
  - [`core/hands/sandbox.py`](file:///E:/NALA-Project/NALA/core/hands/sandbox.py)
  - [`core/hands/sandbox_windows.py`](file:///E:/NALA-Project/NALA/core/hands/sandbox_windows.py)
  - [`core/hands/sandbox_seccomp.py`](file:///E:/NALA-Project/NALA/core/hands/sandbox_seccomp.py)
  - [`core/hands/model_router.py`](file:///E:/NALA-Project/NALA/core/hands/model_router.py)
  - [`tests/unit/test_tool_registry.py`](file:///E:/NALA-Project/NALA/tests/unit/test_tool_registry.py)
* **What it Actually Does** `[FACT]`:
  - Discovers, registers, and validates tools with strict parameter typing, execution timeouts, and latency tracking.
  - Spawns isolated subprocesses in dedicated working directories (`demo_files/` or sandboxed scratch folders).
  - Enforces OS-level containment via process restriction tokens, environment variable sanitization, and seccomp filters.
  - Routes model generation between local Ollama instances, Groq, and fallback providers.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Operating Systems**: Process spawning (`fork`/`exec`), IPC (pipes, stdin/stdout), Environment isolation, Working directory scoping.
  2. **OS Security & Kernel Primitives**: Linux Seccomp (Secure Computing Mode), Namespaces, cgroups, Windows Job Objects / Restricted Tokens.
  3. **Type Systems & API Contracts**: Dynamic vs Static dispatch, JSON Schema validation, serialization/deserialization boundaries.
  4. **Performance Engineering**: Subprocess execution overhead, I/O multiplexing, throughput vs latency trade-offs.

---

### 💾 6. Checkpoints, Write-Ahead Logs & Self-Healing Recovery
* **Physical Files**:
  - [`core/harness/checkpoint.py`](file:///E:/NALA-Project/NALA/core/harness/checkpoint.py)
  - [`core/harness/recovery.py`](file:///E:/NALA-Project/NALA/core/harness/recovery.py)
  - [`core/harness/recovery_engine.py`](file:///E:/NALA-Project/NALA/core/harness/recovery_engine.py)
  - [`tests/unit/test_checkpoint.py`](file:///E:/NALA-Project/NALA/tests/unit/test_checkpoint.py)
  - [`tests/unit/test_crash_recovery.py`](file:///E:/NALA-Project/NALA/tests/unit/test_crash_recovery.py)
  - [`tests/unit/test_recovery_engine.py`](file:///E:/NALA-Project/NALA/tests/unit/test_recovery_engine.py)
* **What it Actually Does** `[FACT]`:
  - Enforces atomic state persistence: writes to `.tmp` file $\to$ invokes `os.fsync()` $\to$ executes atomic `os.replace()`.
  - Maintains monotonic Log Sequence Numbers (`LSN-1`, `LSN-2`, etc.) and append-only `.jsonl` WAL logs.
  - `PhysicalEvidenceCorroborator` reads physical bytes from disk and computes cryptographic SHA-256 hashes.
  - `RecoveryEngine` classifies crashes into 5 failure types, applies ARIES-style redo logging, tracks durable retry counts in `metadata`, and halts at `max_attempts=3`.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Database Systems & Transaction Processing**: ACID properties (Atomicity, Consistency, Isolation, Durability), Write-Ahead Logging (WAL).
  2. **Database Recovery Algorithms**: ARIES (Algorithm for Recovery and Isolation Exploiting Semantics) — Analysis, Redo, Undo phases.
  3. **Storage Systems & File I/O**: Atomic file replacement semantics, filesystem flush guarantees (`fsync`), POSIX atomicity guarantees.
  4. **Cryptography & Integrity**: Cryptographic hash functions (SHA-256), collision resistance, Merkle proofs, content-addressed integrity.

---

### ⚡ 7. Server State Authority, Runner & Asynchronous Event Spine
* **Physical Files**:
  - [`nala_server/state.py`](file:///E:/NALA-Project/NALA/nala_server/state.py)
  - [`nala_server/contracts.py`](file:///E:/NALA-Project/NALA/nala_server/contracts.py)
  - [`nala_server/nala_runner.py`](file:///E:/NALA-Project/NALA/nala_server/nala_runner.py)
  - [`nala_server/compatibility_adapter.py`](file:///E:/NALA-Project/NALA/nala_server/compatibility_adapter.py)
  - [`nala_server.py`](file:///E:/NALA-Project/NALA/nala_server.py)
  - [`tests/unit/test_runtime_state_authority.py`](file:///E:/NALA-Project/NALA/tests/unit/test_runtime_state_authority.py)
  - [`tests/unit/test_compatibility_adapter.py`](file:///E:/NALA-Project/NALA/tests/unit/test_compatibility_adapter.py)
* **What it Actually Does** `[FACT]`:
  - `RuntimeState` serves as the sole thread-safe authority for task/session state transitions protected by `threading.RLock()`.
  - Rejects stale transition proposals via `expected_state_version` optimistic locking checks.
  - `NalaRunner` coordinates execution in dedicated worker threads, managing task lifecycles (`QUEUED` $\to$ `RUNNING` $\to$ `COMPLETED`).
  - Emits typed `TaskEvent` objects through `server_state.event_queue` to Socket.IO clients on port 3001.
* **Underlying Theoretical Foundations** `[THEORY]`:
  1. **Concurrency & Synchronization**: Mutual exclusion (Mutex/RLock), race condition prevention, thread safety, deadlock freedom.
  2. **State Machine Theory**: Deterministic Finite Automata (DFA), state transition matrices, illegal transition guards.
  3. **Distributed Systems & Messaging**: Event-Driven Architecture (EDA), producer-consumer pattern, message ordering, pub-sub.
  4. **Network Protocols & Asynchronous I/O**: WebSocket RFC 6455, framing, full-duplex communication, ASGI event loop.

---

*This concludes the Physical Repository Knowledge Map. Proceed to Theory Dependency Graph.* 🗺️🔬⚡
