# 🎓 NALA-THEORY-001 — Master Curriculum
**Classification:** Complete Personal AI/ML Systems Theory Curriculum  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **CANONICAL LEARNING CURRICULUM**

---

## 1. Curriculum Architecture & Pedagogical Protocol

This Master Curriculum transforms the NALA codebase into an elite, private university-level laboratory for mastering AI/ML, distributed systems, operating systems, and reliability engineering.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       THE 3-TIER EVALUATION PROTOCOL                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. 30-SECOND EXPLANATION : High-level intuitive synthesis (Executive)      │
│  2. 2-MINUTE DRILL        : Mechanical & algorithmic breakdown (Engineer)   │
│  3. DEEP-DIVE PROOF       : Mathematical derivation, code tracing, and      │
│                             adversarial failure analysis (Principal/Scientist)│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 6-Course Curriculum Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NALA CORE CURRICULUM MODULES                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  COURSE 101: Linear Algebra, Metric Spaces & Vector Retrieval               │
│  COURSE 201: Operating Systems, Storage Physics & Crash Durability          │
│  COURSE 301: Concurrency, State Authority & Distributed Event Spines        │
│  COURSE 401: Graph Theory, Automated Planning & Execution DAGs              │
│  COURSE 501: Formal Epistemology, Uncertainty & Closed-Loop Control         │
│  COURSE 601: AI Safety, Capability Sandboxing & Principal Architecture      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Course Modules & Evaluation Standards

---

### 📖 COURSE 101: Linear Algebra, Metric Spaces & Vector Retrieval
* **Description**: Mathematical foundations of high-dimensional vector representations, cosine distance metrics, and persistent semantic memory systems.
* **Core Topics**:
  - Vector spaces ($\mathbb{R}^d$), Euclidean norms ($L_2$), and inner products.
  - Cosine similarity derivation and scale-invariance properties.
  - Flat-file semantic storage, deduplication, and SHA-256 revision tokens.
* **Evaluation Standards**:
  - *30-Second*: Can you explain cosine similarity without mentioning code?
  - *2-Minute*: Can you explain why Cosine Similarity is scale-invariant while Euclidean distance is sensitive to magnitude?
  - *Deep Dive*: Can you derive $\cos(\theta)$ mathematically, trace `_revision_token()` in `memory_service.py`, and explain how OCC prevents lost updates?

---

### 📖 COURSE 201: Operating Systems, Storage Physics & Crash Durability
* **Description**: Storage engine physics, operating system page cache semantics, Write-Ahead Logging (WAL), and ARIES database crash recovery.
* **Core Topics**:
  - POSIX file I/O, `fsync()`, and atomic temporary file replacement.
  - Monotonic Log Sequence Numbers (LSNs) and append-only `.jsonl` logging.
  - ARIES crash recovery algorithm (Analysis $\to$ Redo $\to$ Undo).
  - State rewind vs external side-effect compensation.
* **Evaluation Standards**:
  - *30-Second*: Why does a crash not corrupt NALA's checkpoints?
  - *2-Minute*: Trace the exact sequence of `tmp` $\to$ `fsync` $\to$ `replace` and explain torn-write prevention.
  - *Deep Dive*: Derive the ARIES recovery process for NALA, prove why external disk writes cannot be undone via LSN rewind alone, and design a compensating transaction protocol.

---

### 📖 COURSE 301: Concurrency, State Authority & Distributed Event Spines
* **Description**: Multi-threaded state management, mutual exclusion, deterministic finite automata (DFA), and real-time asynchronous event streaming.
* **Core Topics**:
  - Re-entrant mutex locking (`threading.RLock`) and critical sections.
  - Centralized state authority and optimistic state versioning (`expected_state_version`).
  - Event-driven architecture, producer-consumer queues, and WebSocket framing.
* **Evaluation Standards**:
  - *30-Second*: Why can only `RuntimeState` change a task's status?
  - *2-Minute*: How does `expected_state_version` reject stale transition proposals from delayed worker threads?
  - *Deep Dive*: Trace `RuntimeState.commit_transition()` in `state.py`, prove deadlock freedom, and analyze reconnection state loss over WebSockets.

---

### 📖 COURSE 401: Graph Theory, Automated Planning & Execution DAGs
* **Description**: Graph theoretical foundations of dynamic goal planning, cycle detection algorithms, and dependency-constrained execution.
* **Core Topics**:
  - Directed Acyclic Graphs (DAGs) and in-degree/out-degree properties.
  - Tarjan's Strongly Connected Components and DFS back-edge cycle detection.
  - Topological sorting and critical path scheduling.
* **Evaluation Standards**:
  - *30-Second*: What is a DAG and why does NALA's planner require one?
  - *2-Minute*: How does DFS detect circular dependencies in $O(|V| + |E|)$ time?
  - *Deep Dive*: Write the pseudocode for NALA's plan topology validator, compute space/time complexity, and explain dynamic replanning on step failure.

---

### 📖 COURSE 501: Formal Epistemology, Uncertainty & Closed-Loop Control
* **Description**: The 6 classical Pramāṇas, out-of-band cryptographic proof, Bayesian probability, and dynamical feedback control loops.
* **Core Topics**:
  - Classical Epistemology: Pratyakṣa, Anumāna, Śabda, Upamāna, Arthāpatti, Anupalabdhi.
  - Out-of-band cryptographic verification via SHA-256 disk readback.
  - Feedback control loops, PID modulation, and hysteresis window buffers.
* **Evaluation Standards**:
  - *30-Second*: What is the difference between an AI claim and physical evidence?
  - *2-Minute*: Explain how `PhysicalEvidenceCorroborator` proves whether a file exists and matches disk bytes.
  - *Deep Dive*: Map all 6 Pramāṇas to NALA code, derive Bayesian belief updates for tool outputs, and prove how hysteresis prevents thrashing in model routing.

---

### 📖 COURSE 601: AI Safety, Capability Sandboxing & Principal Architecture
* **Description**: Reference monitor security, kernel-enforced sandboxing (seccomp/job tokens), runaway loop circuit breakers, and sovereign autonomous systems design.
* **Core Topics**:
  - Reference monitors, access control, and least privilege.
  - OS subprocess sandboxing, working directory isolation, and seccomp-bpf filters.
  - Circuit Breakers and durable runaway loop prevention.
  - Sovereign model independence and long-running autonomous architecture.
* **Evaluation Standards**:
  - *30-Second*: How does NALA stop an AI from deleting the hard drive?
  - *2-Minute*: Explain how `AdaptiveVivekaGate` intercepts path traversal (`..`) and destructive commands (`rm -rf`).
  - *Deep Dive*: Defend the complete end-to-end NALA architecture against a hostile panel of distributed systems and security experts.

---

*This concludes the Master Curriculum. Proceed to the Final Master Report.* 🎓🏛️⚡
