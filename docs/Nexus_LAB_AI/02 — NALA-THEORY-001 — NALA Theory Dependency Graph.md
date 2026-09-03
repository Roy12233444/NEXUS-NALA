# 🕸️ NALA-THEORY-001 — NALA Theory Dependency Graph
**Classification:** Theoretical Dependency & Prerequisite Mapping  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **GROUNDED IN NALA ARCHITECTURAL CODE**

---

## 1. Executive Overview

This document formalizes the **Theory Dependency Graph** of NALA. Every node in this graph represents a fundamental mathematical, systems, or AI/ML theoretical concept that must be understood to explain *why* and *how* NALA's code operates.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            THE THEORY HIERARCHY                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Mathematical & Formal Foundations (Set Theory, Linear Alg, Logic) │
│  Layer 2: Core Computer Science Foundations (Graph Theory, OS, OS Security) │
│  Layer 3: Distributed Systems & Data Theory (WAL, ARIES, Consensus, EDA)    │
│  Layer 4: AI/ML & Cognitive Foundations (Embeddings, RAG, Bayesian Update) │
│  Layer 5: Applied NALA Implementation Mechanics (Checkpoints, Viveka, DAGs) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Branch Theory Dependency DAGs

### 🌳 Branch A: Goal Decomposition & Planning Engine

```text
Set Theory & Relations
    │
    ▼
Graph Theory (Vertices, Directed Edges, Adjacency)
    │
    ▼
Directed Acyclic Graphs (DAGs) & Path Properties
    │
    ▼
Cycle Detection Algorithms (Tarjan's SCC / DFS Back-edge Detection)
    │
    ▼
Topological Sorting ($O(|V| + |E|)$) & Dependency Resolution
    │
    ▼
Automated Planning Theory (Hierarchical Task Networks & STRIPS)
    │
    ▼
Scheduling Theory & Critical Path Analysis (CPM)
    │
    ▼
[ NALA Planner & TaskGraph (core/brain/planner.py) ]
```

---

### 🌳 Branch B: Memory, Embeddings & Semantic Retrieval

```text
Vector Spaces & Inner Product Spaces ($\mathbb{R}^d, \langle \mathbf{u}, \mathbf{v} \rangle$)
    │
    ▼
Vector Norms ($L_1, L_2$) & Metric Distances (Euclidean, Manhattan)
    │
    ▼
Cosine Similarity ($ \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} $) & Angular Metrics
    │
    ▼
High-Dimensional Geometry & The Curse of Dimensionality
    │
    ▼
Representation Learning & Dense Neural Embeddings
    │
    ▼
Approximate Nearest Neighbor (ANN) Indexing & Vector Search
    │
    ▼
Retrieval-Augmented Generation (RAG) & Context Window Budgeting
    │
    ▼
Optimistic Concurrency & Content-Addressed Revision Tokens (SHA-256)
    │
    ▼
[ NALA MemoryService & AMP Client (core/brain/memory_service.py) ]
```

---

### 🌳 Branch C: Epistemic Reasoning, Uncertainty & Feedback Control

```text
Formal Logic (Propositional & Predicate Calculus)
    │
    ▼
Probability Theory & Axioms of Kolmogorov
    │
    ▼
Conditional Probability & Bayes' Theorem ($P(H|E) = \frac{P(E|H)P(H)}{P(E)}$)
    │
    ▼
Epistemic Uncertainty vs Aleatoric Uncertainty
    │
    ▼
Model Calibration, Confidence Scoring & Brier Score Minimization
    │
    ▼
Classical Indian Epistemology (Pramāṇa-Vāda: Pratyakṣa, Anumāna, Śabda, etc.)
    │
    ▼
Dynamical Systems & Feedback Control Loops (PID / Closed-Loop Modulation)
    │
    ▼
Hysteresis & State Buffering (Thrashing Prevention in Mode Switching)
    │
    ▼
[ NALA PramanaRouter & RTA Feedback Loop (core/interaction/pramana_router.py) ]
```

---

### 🌳 Branch D: Storage Durability, WAL & Crash Recovery

```text
Operating System File I/O & Page Cache Subsystem
    │
    ▼
POSIX File Operations (open, write, fsync, rename, unlink)
    │
    ▼
Filesystem Crash Semantics & Non-Atomic Multi-Block Writes
    │
    ▼
Atomic File Replacement (Temporary file -> fsync -> atomic rename)
    │
    ▼
Transaction Processing & ACID Guarantees (Atomicity & Durability)
    │
    ▼
Write-Ahead Logging (WAL) & Log Sequence Numbers (Monotonic LSNs)
    │
    ▼
ARIES Database Recovery Algorithm (Analysis, Redo, Undo Phases)
    │
    ▼
Cryptographic Verification (SHA-256 Hash Chaining & Readback Proofs)
    │
    ▼
Self-Healing State Machines & Bounded Retry Policies (Exponential Backoff)
    │
    ▼
[ NALA CheckpointManager & RecoveryEngine (core/harness/checkpoint.py) ]
```

---

### 🌳 Branch E: Safety Gates, Capability Security & Sandboxing

```text
Formal Languages & Regular Expressions ($L(R)$, Automata Theory)
    │
    ▼
Access Control Models (Discretionary vs Mandatory vs Role-Based vs Attribute-Based)
    │
    ▼
Principle of Least Privilege & Confined Execution
    │
    ▼
Operating System Process Isolation (Address Spaces, File Descriptors, IPC)
    │
    ▼
Linux Seccomp-BPF & Windows Restricted Job Object Tokens
    │
    ▼
Safety Invariant Verification ($ \forall s \in S: \text{Valid}(s) $)
    │
    ▼
Circuit Breaker State Machine Pattern (Closed, Open, Half-Open)
    │
    ▼
[ NALA AdaptiveVivekaGate & SandboxManager (core/safety/adaptive_viveka_gate.py) ]
```

---

### 🌳 Branch F: State Authority, Concurrency & Real-Time Event Spine

```text
Concurrency Primitives (Threads, Processes, Coroutines, Mutexes, Semaphores)
    │
    ▼
Race Conditions, Critical Sections & Mutual Exclusion Theory (RLock)
    │
    ▼
Deterministic Finite Automata (DFA) & State Transition Invariants
    │
    ▼
Optimistic Locking & State Versioning (Rejecting Stale Proposals)
    │
    ▼
Event-Driven Architecture (EDA) & Producer-Consumer Queues
    │
    ▼
Asynchronous I/O (asyncio event loop, non-blocking I/O multiplexing)
    │
    ▼
Network Framing & Transport Layer (TCP Sockets, WebSocket RFC 6455)
    │
    ▼
[ NALA RuntimeState, NalaRunner & nala_server.py (nala_server/state.py) ]
```

---

## 3. Cross-Branch Theoretical Intersections

```text
                               ┌────────────────────────┐
                               │   Graph Theory & DAGs  │
                               └───────────┬────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
          ┌────────────────────────┐              ┌────────────────────────┐
          │     Planner (002B)     │              │  Orchestration (002E)  │
          └────────────┬───────────┘              └───────────┬────────────┘
                       │                                      │
                       └───────────────────┬──────────────────┘
                                           ▼
                               ┌────────────────────────┐
                               │  State Authority (002) │
                               └───────────┬────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
          ┌────────────────────────┐              ┌────────────────────────┐
          │  Safety Gates (002D)   │              │   Checkpoints (002F)   │
          └────────────┬───────────┘              └───────────┬────────────┘
                       │                                      │
                       ▼                                      ▼
          ┌────────────────────────┐              ┌────────────────────────┐
          │  Viveka / RTA Feedback │              │  ARIES Recovery (002G) │
          └────────────────────────┘              └────────────────────────┘
```

*This concludes the Theory Dependency Graph. Proceed to Concept Inventory.* 🕸️📐⚡
