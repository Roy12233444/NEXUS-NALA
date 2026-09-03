# 🗺️ NALA-THEORY-001 — Learning Roadmap
**Classification:** Phase-by-Phase Technical Mastery Trajectory  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **OPTIMIZED FOR FIRST-PRINCIPLES SYSTEMS MASTERY**

---

## 1. Roadmap Architecture & Mastery Philosophy

This learning roadmap provides a structured progression designed to build deep, unshakeable competence in AI/ML systems, distributed engineering, and reliability physics.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE 6-PHASE MASTERY ROADMAP                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: Mathematical Foundations & Formal Structures                      │
│  PHASE 2: Operating Systems, Storage Physics & Crash Durability             │
│  PHASE 3: Concurrency, State Authority & Event-Driven Systems               │
│  PHASE 4: Graph Theory, Automated Planning & Execution DAGs                 │
│  PHASE 5: Epistemology, Probabilistic Verification & Closed-Loop Control     │
│  PHASE 6: AI Safety, Sandbox Security & Principal System Architecture       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Phase Breakdown

---

### 📍 Phase 1: Mathematical Foundations & Formal Structures
* **Focus**: Vector spaces, norms, inner products, metric distances, and set-based deduplication.
* **Prerequisite Questions**: `NALA-Q004`, `INT-04`
* **Connected NALA Components**:
  - `core/session/amp_client.py`
  - `core/brain/memory_service.py`
* **Key Topics to Master**:
  1. Euclidean vs Non-Euclidean geometry in high-dimensional vector spaces.
  2. Mathematical properties of inner products and cosine similarity.
  3. Set theory, hashing, and collision-resistant deduplication.
  4. Vector normalization and scale-invariant distance metrics.
* **Expected Competence**: Ability to derive cosine similarity from first principles and explain why high-dimensional embeddings require normalized inner products.

---

### 📍 Phase 2: Operating Systems, Storage Physics & Crash Durability
* **Focus**: POSIX file I/O, page caching, atomic replacement, Write-Ahead Logging (WAL), and ARIES database crash recovery.
* **Prerequisite Questions**: `NALA-Q010`, `NALA-Q011`, `NALA-Q012`, `INT-01`, `INT-02`, `INT-05`, `INT-10`
* **Connected NALA Components**:
  - `core/harness/checkpoint.py`
  - `core/harness/recovery.py`
  - `core/harness/recovery_engine.py`
* **Key Topics to Master**:
  1. OS filesystem dirty page flushing and `fsync()` guarantees.
  2. POSIX atomic file replacement via temporary file renaming.
  3. Write-Ahead Logging (WAL) and monotonic Log Sequence Numbers (LSN).
  4. ARIES crash recovery algorithm (Analysis, Redo, Undo).
  5. The physical boundary between internal state rollback and external side-effect compensation.
* **Expected Competence**: Ability to design a zero-corruption persistence engine that survives sudden process termination (`SIGKILL`) and resumes execution without state duplication.

---

### 📍 Phase 3: Concurrency, State Authority & Event-Driven Systems
* **Focus**: Multi-threading, mutual exclusion, deterministic state machines, optimistic locking, and WebSocket transport.
* **Prerequisite Questions**: `NALA-Q015`, `NALA-Q016`, `INT-03`, `INT-12`
* **Connected NALA Components**:
  - `nala_server/state.py`
  - `nala_server/contracts.py`
  - `nala_server/nala_runner.py`
  - `nala_server.py`
* **Key Topics to Master**:
  1. Critical sections, race conditions, and re-entrant mutexes (`threading.RLock`).
  2. Deterministic Finite Automata (DFA) state machines and illegal transition guards.
  3. Optimistic concurrency control via `expected_state_version`.
  4. Event-Driven Architecture, backpressure, and WebSocket event synchronization.
* **Expected Competence**: Ability to architect a thread-safe, centralized state manager that coordinates asynchronous worker threads and delivers real-time telemetry to distributed clients.

---

### 📍 Phase 4: Graph Theory, Automated Planning & Execution DAGs
* **Focus**: Directed Acyclic Graphs, Tarjan's cycle detection, topological sorting, and dependency-constrained execution.
* **Prerequisite Questions**: `NALA-Q001`, `NALA-Q002`, `NALA-Q003`, `INT-06`
* **Connected NALA Components**:
  - `core/brain/planner.py`
  - `core/harness/session_contract.py` (`TaskGraph`, `TaskStep`)
  - `core/harness/nala_loop.py`
* **Key Topics to Master**:
  1. Mathematical definitions of acyclic directed graphs.
  2. Depth-First Search cycle detection and complexity analysis ($O(|V| + |E|)$).
  3. Topological sorting and dependency resolution.
  4. Hierarchical task networks and dynamic goal decomposition.
* **Expected Competence**: Ability to build a dynamic planning engine that decomposes unstructured natural language goals into validated, deadlock-free execution DAGs.

---

### 📍 Phase 5: Epistemology, Probabilistic Verification & Closed-Loop Control
* **Focus**: The 6 classical Pramāṇas, out-of-band cryptographic verification, Bayesian updating, and closed-loop hysteresis control.
* **Prerequisite Questions**: `NALA-Q007`, `NALA-Q008`, `NALA-Q009`, `INT-04`, `INT-11`
* **Connected NALA Components**:
  - `core/interaction/pramana_router.py`
  - `core/safety/rta_feedback_loop.py`
  - `core/safety/satya.py`
  - `core/harness/recovery.py` (`PhysicalEvidenceCorroborator`)
* **Key Topics to Master**:
  1. The Six Pramāṇas (Pratyakṣa, Anumāna, Śabda, Upamāna, Arthāpatti, Anupalabdhi).
  2. Cryptographic SHA-256 disk readback vs subjective LLM claims.
  3. Closed-loop dynamical feedback control and PID modulation.
  4. Hysteresis window buffers for preventing state thrashing in dynamic model routers.
* **Expected Competence**: Ability to design an epistemic grounding engine that separates probabilistic assertions from physical truth and stabilizes dynamic model transitions.

---

### 📍 Phase 6: AI Safety, Sandbox Security & Principal System Architecture
* **Focus**: Reference monitors, least privilege, OS subprocess isolation (seccomp/job objects), context budgeting, and long-running autonomous design.
* **Prerequisite Questions**: `NALA-Q006`, `NALA-Q013`, `NALA-Q014`, `INT-08`, `INT-09`, `INT-13`, `INT-14`, `INT-15`
* **Connected NALA Components**:
  - `core/safety/adaptive_viveka_gate.py`
  - `core/hands/sandbox.py`
  - `core/hands/model_router.py`
  - `core/harness/context_tracker.py`
* **Key Topics to Master**:
  1. Reference monitor architecture and non-bypassable security gateways.
  2. Linux Seccomp-BPF and Windows Restricted Tokens for kernel-level sandboxing.
  3. Lossy vs Lossless context window compaction and token budgeting.
  4. Model-independent middleware design and sovereign autonomous control.
* **Expected Competence**: Ability to articulate and defend the complete end-to-end architecture of an autonomous, self-healing, epistemically grounded computational organism.

---

*This concludes the Learning Roadmap. Proceed to Master Curriculum.* 🗺️🧠⚡
