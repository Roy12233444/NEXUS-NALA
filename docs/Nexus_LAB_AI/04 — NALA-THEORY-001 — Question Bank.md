# ❓ NALA-THEORY-001 — Question Bank
**Classification:** Grounded Technical & Theoretical Question Bank  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **GROUNDED IN NALA CODE EVIDENCE**

---

## 1. Overview & Question Taxonomy

This Question Bank transforms NALA into a personalized oral examination laboratory. Every question connects directly to physical repository evidence, foundational computer science mathematics, systems theory, and engineering failure analysis.

### Question Type Classification:
* **TYPE A**: Definitions & Fundamentals
* **TYPE B**: Mechanics & How it Works
* **TYPE C**: Architectural Rationales & Why
* **TYPE D**: Mathematical Derivations & Formalisms
* **TYPE E**: Implementation & Code Analysis
* **TYPE F**: Failure Analysis & Edge Cases
* **TYPE G**: Engineering Trade-offs
* **TYPE H**: System Boundaries & Invariants
* **TYPE I**: Adversarial Attacks & Vulnerabilities
* **TYPE J**: Design Alternatives
* **TYPE K**: First-Principles Systems Derivations
* **TYPE L**: 60-Second Oral Examination
* **TYPE M**: Cross-Domain Synthesis
* **TYPE N**: Frontier Research Gaps

---

## 2. Core Question Bank

---

### 🔹 Module 1: Graph Theory, Planning & Goal Decomposition

#### `NALA-Q001`
* **Category**: J (Planning & Graph Theory) | **Subsystem**: `core/brain/planner.py`
* **Evidence**: [`core/brain/planner.py::Planner.create_plan`](file:///E:/NALA-Project/NALA/core/brain/planner.py#L45-L70), [`core/harness/session_contract.py::TaskGraph`](file:///E:/NALA-Project/NALA/core/harness/session_contract.py#L120-L150)
* **Concept**: Directed Acyclic Graphs (DAGs) and Invariant Properties
* **Difficulty**: Level 1 (Fundamentals) | **Type**: TYPE A (Definition)
* **Prerequisites**: Basic Set Theory
* **Question**: *What mathematical properties formally define a Directed Acyclic Graph (DAG), and why must an autonomous execution plan satisfy the acyclic property rather than permitting arbitrary cyclic digraph topologies?*
* **Why it Matters**: Ensures the engineer understands the mathematical guarantees required to execute tasks without infinite non-terminating loops.
* **Expected Outcome**: Clear definition of $G = (V, E)$, absence of directed closed walks, and the necessity of well-founded execution orderings.

---

#### `NALA-Q002`
* **Category**: J (Planning) / K (Search) | **Subsystem**: `core/brain/planner.py`
* **Evidence**: [`core/brain/planner.py::validate_plan_topology`](file:///E:/NALA-Project/NALA/core/brain/planner.py#L85-L115), [`tests/unit/test_planner.py`](file:///E:/NALA-Project/NALA/tests/unit/test_planner.py)
* **Concept**: Depth-First Search Cycle Detection & Tarjan's SCC Algorithm
* **Difficulty**: Level 2 (Mechanisms) | **Type**: TYPE B (Mechanism)
* **Prerequisites**: `NALA-Q001`
* **Question**: *How does NALA detect circular step dependencies during pre-flight goal validation, and what is the computational time and space complexity of DFS-based back-edge detection versus Kahn's topological sort?*
* **Why it Matters**: Cycle detection is the primary defense against planner-generated deadlocks before compute resources are spent.
* **Expected Outcome**: Ability to trace DFS recursive call stacks, identify tree edges vs back edges, and compute $O(|V| + |E|)$ complexity.

---

#### `NALA-Q003`
* **Category**: J (Planning) / T (Software Architecture) | **Subsystem**: `core/brain/planner.py`
* **Evidence**: [`core/harness/session_contract.py::TaskStep.dependencies`](file:///E:/NALA-Project/NALA/core/harness/session_contract.py#L160-L180), [`core/harness/nala_loop.py`](file:///E:/NALA-Project/NALA/core/harness/nala_loop.py#L210-L240)
* **Concept**: Dependency-Constrained Execution & Critical Path Scheduling
* **Difficulty**: Level 4 (Engineering Trade-offs) | **Type**: TYPE G (Trade-off)
* **Prerequisites**: `NALA-Q002`
* **Question**: *Why does NALA represent plans as a dependency graph of `TaskStep` objects rather than a flat linear list of actions, and what concurrency trade-offs arise when scheduling non-dependent sibling steps in parallel versus strictly sequentially?*
* **Why it Matters**: Connects graph theory to execution concurrency, race condition prevention, and resource scheduling.
* **Expected Outcome**: Analysis of parallel speedup vs race condition hazards on shared filesystems.

---

### 🔹 Module 2: Memory Systems, Linear Algebra & Information Retrieval

#### `NALA-Q004`
* **Category**: A (Mathematics) / M (Information Retrieval) | **Subsystem**: `core/session/amp_client.py`
* **Evidence**: [`core/session/amp_client.py::cosine_similarity`](file:///E:/NALA-Project/NALA/core/session/amp_client.py#L110-L130), [`tests/unit/test_memory_service.py`](file:///E:/NALA-Project/NALA/tests/unit/test_memory_service.py)
* **Concept**: Vector Spaces, Dot Products & Cosine Similarity
* **Difficulty**: Level 2 (Mechanisms) | **Type**: TYPE D (Mathematical)
* **Prerequisites**: Linear Algebra Basics
* **Question**: *Derive the mathematical formulation of Cosine Similarity between two dense embedding vectors $\mathbf{u}, \mathbf{v} \in \mathbb{R}^d$. Why is the cosine angle preferred over Euclidean distance ($L_2$ norm) when comparing semantic representations produced by normalized neural embedding models?*
* **Why it Matters**: Vector similarity is the mathematical engine of semantic memory retrieval in modern agentic architectures.
* **Expected Outcome**: Formal derivation $\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$ and understanding of scale-invariance in hyperspherical embeddings.

---

#### `NALA-Q005`
* **Category**: M (Information Retrieval) / P (Concurrency) | **Subsystem**: `core/brain/memory_service.py`
* **Evidence**: [`core/brain/memory_service.py::_revision_token`](file:///E:/NALA-Project/NALA/core/brain/memory_service.py#L31-L35), [`core/brain/memory_service.py::_write_raw`](file:///E:/NALA-Project/NALA/core/brain/memory_service.py#L77-L88)
* **Concept**: Optimistic Concurrency Control (OCC) via SHA-256 Revision Tokens
* **Difficulty**: Level 3 (Applied NALA) | **Type**: TYPE E (Implementation)
* **Prerequisites**: `NALA-Q004`, Cryptographic Hash Functions
* **Question**: *How does `MemoryService` in `core/brain/memory_service.py` prevent lost-update anomalies during concurrent agent fact captures, and how does its atomic write pattern (`.tmp` $\to$ `os.replace()`) guarantee memory integrity against process crashes?*
* **Why it Matters**: Demonstrates how flat-file storage can achieve ACID-like atomicity and optimistic concurrency without a heavy relational database.
* **Expected Outcome**: Explanation of SHA-256 revision tokens, compare-and-swap semantics, and POSIX atomic filesystem replacement.

---

#### `NALA-Q006`
* **Category**: M (Information Retrieval) / I (AI Agents) | **Subsystem**: `core/brain/memory_service.py`
* **Evidence**: [`core/brain/memory_service.py::recall`](file:///E:/NALA-Project/NALA/core/brain/memory_service.py#L120-L145), [`core/harness/context_tracker.py`](file:///E:/NALA-Project/NALA/core/harness/context_tracker.py#L200-L240)
* **Concept**: Memory Pollution, Token Budgeting & Recency Decay
* **Difficulty**: Level 5 (Architecture) | **Type**: TYPE F (Failure Analysis)
* **Prerequisites**: `NALA-Q005`
* **Question**: *What failure modes emerge when an autonomous agent continuously appends unstructured facts to long-term memory over weeks of execution, and why is pure semantic similarity retrieval vulnerable to "retrieval poisoning" without recency decay and deduplication?*
* **Why it Matters**: Crucial for understanding why naive RAG fails in multi-day autonomous agents.
* **Expected Outcome**: Analysis of context window dilution, conflicting memory facts, and the necessity of compaction heuristics.

---

### 🔹 Module 3: Epistemology, Uncertainty & Closed-Loop Control

#### `NALA-Q007`
* **Category**: L (Epistemology) / W (AI Safety) | **Subsystem**: `core/interaction/pramana_router.py`
* **Evidence**: [`core/interaction/pramana_router.py::PramanaType`](file:///E:/NALA-Project/NALA/core/interaction/pramana_router.py#L65-L73), [`core/interaction/pramana_router.py::route_epistemic_path`](file:///E:/NALA-Project/NALA/core/interaction/pramana_router.py#L140-L180)
* **Concept**: Six-Prāmāṇic Epistemic Reasoning & Knowledge Classification
* **Difficulty**: Level 2 (Mechanisms) | **Type**: TYPE A (Definition)
* **Prerequisites**: Epistemology Basics
* **Question**: *Define the six classical Pramāṇas implemented in NALA (*Pratyakṣa*, *Anumāna*, *Śabda*, *Upamāna*, *Arthāpatti*, *Anupalabdhi*), and explain how each maps to a distinct computational observation mechanism within NALA's cognitive runtime.*
* **Why it Matters**: Connects classical Indian epistemology to modern computational verification.
* **Expected Outcome**: Exact mapping: Pratyakṣa = Disk readback; Anumāna = LLM logical inference; Śabda = User/Memory testimony; Upamāna = Structural comparison; Arthāpatti = Hypothesis resolution; Anupalabdhi = Proof of absence.

---

#### `NALA-Q008`
* **Category**: B (Probability) / W (AI Safety) | **Subsystem**: `core/safety/satya.py`
* **Evidence**: [`core/safety/satya.py::SatyaLayer.validate_output_truthfulness`](file:///E:/NALA-Project/NALA/core/safety/satya.py#L80-L110), [`core/harness/recovery.py::PhysicalEvidenceCorroborator`](file:///E:/NALA-Project/NALA/core/harness/recovery.py#L50-L85)
* **Concept**: Epistemic Attestation vs Self-Reported Model Confidence
* **Difficulty**: Level 5 (Architecture) | **Type**: TYPE I (Adversarial)
* **Prerequisites**: `NALA-Q007`
* **Question**: *Why is an LLM's self-reported probability (e.g., "I am 99% certain this file was written") scientifically ungrounded as an epistemic claim, and how does NALA's `PhysicalEvidenceCorroborator` enforce mathematical truth over probabilistic claims using cryptographic SHA-256 readback?*
* **Why it Matters**: Core to preventing "Epistemic Theater" in AI agent systems.
* **Expected Outcome**: Understanding the disconnect between next-token generation probabilities and physical ground truth, and the role of out-of-band cryptographic corroboration.

---

#### `NALA-Q009`
* **Category**: C (Control Theory) / T (Software Architecture) | **Subsystem**: `core/safety/rta_feedback_loop.py`
* **Evidence**: [`core/safety/rta_feedback_loop.py::RTAFeedbackLoop`](file:///E:/NALA-Project/NALA/core/safety/rta_feedback_loop.py#L40-L90), [`core/interaction/pramana_router.py`](file:///E:/NALA-Project/NALA/core/interaction/pramana_router.py#L20-L45)
* **Concept**: Hysteresis, State Buffering & Thrashing Prevention in Dynamic Control
* **Difficulty**: Level 4 (Engineering Trade-offs) | **Type**: TYPE B (Mechanism)
* **Prerequisites**: Feedback Control Basics
* **Question**: *How does NALA's `PramanaRouter` use hysteresis window buffers (`deque(maxlen=10)`) on the real-time `Ṛta-Score` to prevent high-frequency thrashing between model modalities (Gaṇeśa, Sarasvatī, Śiva), and what instability occurs in a control system without hysteresis?*
* **Why it Matters**: Fundamental control theory concept applied to dynamic LLM model routing and safety state modulation.
* **Expected Outcome**: Mathematical explanation of hysteresis thresholds, state switching lag, and stability in closed-loop feedback systems.

---

### 🔹 Module 4: Storage Durability, Write-Ahead Logging & ARIES Crash Recovery

#### `NALA-Q010`
* **Category**: R (Databases) / U (Reliability Engineering) | **Subsystem**: `core/harness/checkpoint.py`
* **Evidence**: [`core/harness/checkpoint.py::CheckpointManager.write_checkpoint`](file:///E:/NALA-Project/NALA/core/harness/checkpoint.py#L210-L260), [`tests/unit/test_checkpoint.py`](file:///E:/NALA-Project/NALA/tests/unit/test_checkpoint.py)
* **Concept**: Monotonic Log Sequence Numbers (LSN) & Atomic File Operations
* **Difficulty**: Level 3 (Applied NALA) | **Type**: TYPE E (Implementation)
* **Prerequisites**: Operating System File I/O
* **Question**: *Trace the exact step-by-step sequence of OS syscalls executed by `CheckpointManager.write_checkpoint()` when writing an LSN snapshot to disk. Why is `os.fsync()` mandatory before calling `os.replace()`, and what happens during a sudden power loss if `fsync` is omitted?*
* **Why it Matters**: Teaches how real production storage engines achieve zero-corruption crash guarantees.
* **Expected Outcome**: Identification of OS page cache buffering, dirty page flushing via `fsync`, directory entry updates via atomic rename, and torn-write prevention.

---

#### `NALA-Q011`
* **Category**: R (Databases) / U (Reliability Engineering) | **Subsystem**: `core/harness/recovery_engine.py`
* **Evidence**: [`core/harness/recovery_engine.py::RecoveryEngine`](file:///E:/NALA-Project/NALA/core/harness/recovery_engine.py#L80-L160), [`core/harness/recovery.py::recover_session`](file:///E:/NALA-Project/NALA/core/harness/recovery.py#L120-L170)
* **Concept**: ARIES Database Crash Recovery Algorithm (Analysis, Redo, Undo)
* **Difficulty**: Level 6 (Failure Analysis) | **Type**: TYPE M (Cross-Domain)
* **Prerequisites**: `NALA-Q010`, Transaction Processing Basics
* **Question**: *How does NALA adapt the classical ARIES database recovery algorithm (Analysis $\to$ Redo $\to$ Undo) to recover an interrupted autonomous agent session from disk checkpoints, and why does restoring an LSN snapshot in RAM NOT automatically rollback external side effects on disk?*
* **Why it Matters**: Resolves the foundational systems boundary between internal state recovery and external world compensation.
* **Expected Outcome**: Rigorous distinction between state idempotency, WAL log replay, and the impossibility of generic external effect rollback without compensating actions.

---

#### `NALA-Q012`
* **Category**: U (Reliability Engineering) | **Subsystem**: `core/harness/recovery_engine.py`
* **Evidence**: [`core/harness/recovery_engine.py::RecoveryState`](file:///E:/NALA-Project/NALA/core/harness/recovery_engine.py#L40-L75), [`tests/integration/test_self_healing_runtime.py`](file:///E:/NALA-Project/NALA/tests/integration/test_self_healing_runtime.py)
* **Concept**: Durable Attempt Tracking & Runaway Loop Bounded Halting
* **Difficulty**: Level 4 (Engineering Trade-offs) | **Type**: TYPE F (Failure Analysis)
* **Prerequisites**: `NALA-Q011`
* **Question**: *Why must the `attempt_count` in NALA's `RecoveryEngine` be persisted inside durable checkpoint metadata rather than tracked as an in-memory Python variable, and how does this prevent an infinite crash-restart loop when a task repeatedly encounters a deterministic segmentation fault?*
* **Why it Matters**: Demonstrates understanding of state survival across hard OS process crashes (`SIGKILL`).
* **Expected Outcome**: Proof that in-memory counters reset to 0 on process resurrection, leading to infinite loops without durable metadata state.

---

### 🔹 Module 5: Security, Reference Monitors & Subprocess Isolation

#### `NALA-Q013`
* **Category**: S (Security) / O (Operating Systems) | **Subsystem**: `core/safety/adaptive_viveka_gate.py`
* **Evidence**: [`core/safety/adaptive_viveka_gate.py::AdaptiveVivekaGate`](file:///E:/NALA-Project/NALA/core/safety/adaptive_viveka_gate.py#L90-L150), [`core/safety/adaptive_viveka_gate.py::_PROHIBITED_PATH_PATTERNS`](file:///E:/NALA-Project/NALA/core/safety/adaptive_viveka_gate.py#L76-L92)
* **Concept**: Reference Monitors, Least Privilege & Static Pattern Interception
* **Difficulty**: Level 3 (Applied NALA) | **Type**: TYPE B (Mechanism)
* **Prerequisites**: Security Fundamentals
* **Question**: *What is the formal definition of a Reference Monitor in computer security, and how does `AdaptiveVivekaGate` implement non-bypassable policy evaluation over tool requests before they reach the execution sandbox?*
* **Why it Matters**: Core to understanding authorization boundaries and defense-in-depth in agent systems.
* **Expected Outcome**: Properties of a reference monitor (complete mediation, tamper-proof, verifiable) and how Viveka evaluates path traversal and destructive commands.

---

#### `NALA-Q014`
* **Category**: S (Security) / O (Operating Systems) | **Subsystem**: `core/hands/sandbox.py`
* **Evidence**: [`core/hands/sandbox.py::execute_in_sandbox`](file:///E:/NALA-Project/NALA/core/hands/sandbox.py#L120-L180), [`core/hands/sandbox_seccomp.py`](file:///E:/NALA-Project/NALA/core/hands/sandbox_seccomp.py)
* **Concept**: Process Isolation, System Call Filtering (Seccomp-BPF) & Working Directory Containment
* **Difficulty**: Level 5 (Architecture) | **Type**: TYPE G (Trade-off)
* **Prerequisites**: `NALA-Q013`, Linux/Windows Kernel Primitives
* **Question**: *Compare the containment guarantees of working-directory scoping in Python `subprocess.Popen(cwd=...)` versus kernel-enforced system call filtering via Linux `seccomp-bpf` or Windows Restricted Tokens. What attack vectors bypass simple directory scoping?*
* **Why it Matters**: Distinguishes superficial application-level confinement from genuine kernel-enforced sandbox security.
* **Expected Outcome**: Understanding symlink attacks, relative path traversals, raw socket creation, and how seccomp traps unauthorized `execve` / `open` syscalls.

---

### 🔹 Module 6: Concurrency, State Authority & Event Spines

#### `NALA-Q015`
* **Category**: P (Concurrency) / T (Software Architecture) | **Subsystem**: `nala_server/state.py`
* **Evidence**: [`nala_server/state.py::RuntimeState`](file:///E:/NALA-Project/NALA/nala_server/state.py#L730-L820), [`tests/unit/test_runtime_state_authority.py`](file:///E:/NALA-Project/NALA/tests/unit/test_runtime_state_authority.py)
* **Concept**: Centralized State Authority, Mutex Synchronization & Optimistic State Versioning
* **Difficulty**: Level 4 (Engineering Trade-offs) | **Type**: TYPE C (Why)
* **Prerequisites**: Concurrency & Thread Synchronization
* **Question**: *Why does NALA mandate that `RuntimeState` is the sole entity permitted to commit task state changes, and how does the `expected_state_version` parameter in `TransitionProposal` prevent race conditions when asynchronous worker threads attempt concurrent state mutations?*
* **Why it Matters**: Essential for building robust, deterministic state machines in multi-threaded asynchronous servers.
* **Expected Outcome**: Explanation of single-source-of-truth invariants, atomic lock-guarded transitions, and rejection of stale proposals ($V_{\text{actual}} \neq V_{\text{expected}}$).

---

#### `NALA-Q016`
* **Category**: Q (Networking) / T (Software Architecture) | **Subsystem**: `nala_server.py` / `src/services/websocketService.ts`
* **Evidence**: [`nala_server.py::event_publisher_loop`](file:///E:/NALA-Project/NALA/nala_server.py#L310-L360), [`src/services/websocketService.ts`](file:///E:/NALA-Project/NALA/src/services/websocketService.ts#L80-L130)
* **Concept**: Event-Driven Architecture, Backpressure & Reconnection Resynchronization
* **Difficulty**: Level 5 (Architecture) | **Type**: TYPE F (Failure Analysis)
* **Prerequisites**: `NALA-Q015`, WebSocket Protocols
* **Question**: *What happens to client-side state when the WebSocket connection between the React UI and `nala_server.py` drops during a 10-minute autonomous step, and why must the UI perform an explicit state snapshot hydration upon reconnection rather than relying exclusively on real-time broadcast events?*
* **Why it Matters**: Core to building production-grade, long-running agent control interfaces that survive network drops.
* **Expected Outcome**: Understanding message queue buffering, loss of in-flight broadcasts, and the necessity of initial state hydration contracts.

---

*This concludes the Core Question Bank. Proceed to Prerequisite Learning Graph.* ❓🧠⚡
