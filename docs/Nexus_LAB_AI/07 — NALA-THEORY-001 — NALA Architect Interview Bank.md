# 🏛️ NALA-THEORY-001 — NALA Architect Interview Bank
**Classification:** Hostile Principal Systems Architect Oral Examination  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **GROUNDED IN NALA ARCHITECTURE**

---

## 1. Overview & Interview Protocol

This interview bank is designed to test a candidate's deep structural understanding of NALA's systems architecture, reliability physics, and theoretical foundations.

### The Hostile Interview Standard:
* **No buzzword answers**: High-level claims ("We use AI to optimize it") receive immediate score failure.
* **First-principles derivations**: Answers must cite operating system primitives, data invariants, concurrency locks, and failure modes.
* **Code grounding**: Every architectural answer must map to how NALA implements or bounds the concept in code.

---

## 2. The 15 Core Architect Interview Questions

---

### `INT-01`: State Persistence vs In-Memory Context
* **Question**: *"Why does NALA require durable on-disk checkpoints (LSN snapshots) rather than relying on the LLM's active context window or in-memory Python session objects?"*
* **Ideal Answer Scope**:
  - Distinguishes ephemeral volatile RAM from durable non-volatile disk.
  - Explains process death scenarios (`SIGKILL`, OOM, power loss, server reboot).
  - Demonstrates that context windows have finite token boundaries and cost constraints, while durable checkpoints enable infinite session continuity across restarts.

---

### `INT-02`: State Rewind vs External Effect Rollback
* **Question**: *"If NALA crashes during Step 4 and resumes from Checkpoint LSN-3, why does this NOT automatically undo the file writes or HTTP requests executed during Step 4? How must a production agent handle external side-effect compensation?"*
* **Ideal Answer Scope**:
  - Explains the fundamental distributed systems boundary between internal process memory and external un-coordinated world state.
  - Explains the concept of Compensating Transactions (Saga Pattern) versus database internal rollback.
  - Demonstrates why NALA's UI must explicitly warn the user that LSN restore is an internal state rewind only.

---

### `INT-03`: Authoritative State Authority vs Event Ingestion
* **Question**: *"Why does NALA enforce that `RuntimeState` in `nala_server/state.py` is the single source of truth, and why is an event stream (Socket.IO / `TaskEvent`) considered a downstream observation rather than the state itself?"*
* **Ideal Answer Scope**:
  - Explains the dual-write problem and split-brain state hazards.
  - Shows that events can be dropped, reordered, or delayed over network transports.
  - Proves that `RuntimeState` with mutex locking (`threading.RLock`) provides serializability and prevents illegal state transitions.

---

### `INT-04`: Epistemic Grounding vs LLM Self-Reported Confidence
* **Question**: *"Why is an LLM's assertion of confidence (e.g., 'I am 100% sure the script ran') scientifically ungrounded as an epistemic claim, and how does NALA achieve genuine Pratyakṣa (direct perception) verification?"*
* **Ideal Answer Scope**:
  - Explains that next-token generation probabilities reflect training corpus statistical likelihoods, not environmental truth.
  - Explains NALA's `PhysicalEvidenceCorroborator` out-of-band disk readback and cryptographic SHA-256 hashing.
  - Shows that truth is established through physical evidence, not model persona or confident tone.

---

### `INT-05`: Monotonic LSNs and Torn-Write Prevention
* **Question**: *"Explain the exact failure mode that occurs if a storage engine writes checkpoint JSON directly to `checkpoint.json` without using a `.tmp` file and `fsync()`. How does NALA guarantee zero-corruption persistence?"*
* **Ideal Answer Scope**:
  - Explains OS page caching, multi-sector disk writes, and power failure mid-write resulting in partial/corrupted JSON.
  - Details NALA's three-step atomic sequence: write to `.tmp_pid_ts` $\to$ `os.fsync()` $\to$ atomic `os.replace()`.
  - Explains POSIX atomic rename guarantees.

---

### `INT-06`: Cycle Detection in Goal Decomposition
* **Question**: *"Why must an autonomous execution plan be validated for acyclicity before execution begins, and what computational algorithm does NALA's planner employ to guarantee deadlock-free DAGs?"*
* **Ideal Answer Scope**:
  - Proves that a cyclic dependency ($A \to B \to A$) results in permanent deadlock in dependency-constrained schedulers.
  - Explains Depth-First Search (DFS) call stack tracking or Tarjan's Strongly Connected Components algorithm in $O(|V| + |E|)$ time.

---

### `INT-07`: Memory Deduplication & Optimistic Concurrency
* **Question**: *"How does NALA's `MemoryService` maintain a flat-file Markdown memory repository without suffering from lost-update anomalies when multiple subagents record facts simultaneously?"*
* **Ideal Answer Scope**:
  - Explains Optimistic Concurrency Control (OCC) using SHA-256 revision tokens (`_revision_token`).
  - Explains compare-on-write validation and atomic file replacement.
  - Shows how string normalization and set hashing prevent fact duplication.

---

### `INT-08`: Autonomous Agent vs Conversational Chatbot
* **Question**: *"From a distributed systems and control theory perspective, what fundamental architectural properties distinguish an autonomous computational organism (like NALA) from a generative conversational chatbot (like ChatGPT web)?"*
* **Ideal Answer Scope**:
  - Chatbot: Stateless request-reply, transient memory, zero side-effect verification, synchronous human-waiting loop.
  - Autonomous Organism: Goal-directed DAG planning, durable state machines, closed-loop feedback control, sandboxed tool execution, self-healing recovery, out-of-band physical verification.

---

### `INT-09`: Sandbox Security Boundaries
* **Question**: *"Why is setting `cwd="/path/to/sandbox"` in a Python `subprocess.Popen` call insufficient to guarantee secure sandbox containment, and what kernel primitives must be engaged to prevent host system compromise?"*
* **Ideal Answer Scope**:
  - Identifies escape vectors: symlink traversal, `..` directory navigation, raw socket network exfiltration, fork bombs.
  - Explains OS-level isolation: Linux Seccomp-BPF (syscall filtering), cgroups (resource limits), Windows Restricted Tokens and Job Objects.

---

### `INT-10`: Runaway Loop Prevention and Bounded Halting
* **Question**: *"How does NALA prevent an infinite self-healing recovery loop when a task repeatedly encounters a deterministic, non-recoverable error, and why must the attempt counter survive process death?"*
* **Ideal Answer Scope**:
  - Explains `RecoveryEngine` bounded retry policy (`max_attempts=3`).
  - Shows that storing attempt counts in volatile memory resets the counter to 0 upon process crash, causing an infinite restart storm.
  - Proves the necessity of storing attempt counts inside persistent checkpoint metadata.

---

### `INT-11`: Hysteresis in Dynamic Model Routing
* **Question**: *"Why does NALA's `PramanaRouter` use a moving-window hysteresis buffer on the real-time `Ṛta-Score` when switching model modalities (Gaṇeśa $\leftrightarrow$ Sarasvatī $\leftrightarrow$ Śiva), and what instability occurs in a bang-bang controller without hysteresis?"*
* **Ideal Answer Scope**:
  - Defines the "chattering" / "thrashing" phenomenon in control systems when inputs fluctuate around a boundary threshold.
  - Explains how hysteresis buffers (`deque(maxlen=10)`) create asymmetric transition thresholds to stabilize model state.

---

### `INT-12`: Cooperative Cancellation vs Hard Process Killing
* **Question**: *"Why does `NalaRunner.cancel()` utilize a cooperative `cancel_event` flag rather than executing `thread.terminate()` or `os.kill(SIGKILL)` on the worker thread?"*
* **Ideal Answer Scope**:
  - Explains that abruptly terminating a thread mid-execution leaves mutex locks permanently held (deadlock) and can corrupt in-flight I/O descriptors.
  - Proves that cooperative cancellation allows the worker to complete or rollback the active step to a clean, consistent LSN checkpoint boundary.

---

### `INT-13`: Asynchronous Yield State vs Blocking Modals
* **Question**: *"Why does NALA design human intervention as an asynchronous yield state rather than a synchronous UI-blocking modal, and how does this support multi-task supervision in long-running operations?"*
* **Ideal Answer Scope**:
  - Explains that synchronous blocking popups destroy human flow state and freeze independent parallel workstreams.
  - Explains the Dual-Track model: non-blocking ambiguities go to a batchable inbox, while critical blockers park only the dependent DAG node.

---

### `INT-14`: Context Window Budgeting and Compaction
* **Question**: *"What is the difference between lossy and lossless context compaction, and how does NALA's `DronagiriCompactor` preserve critical goal constraints while discarding ephemeral execution traces?"*
* **Ideal Answer Scope**:
  - Lossless: Exact token pruning, tool call deduplication.
  - Lossy: Semantic summarization of completed milestones.
  - Explains attention degradation in LLMs when context approaches window ceilings and how structured compaction preserves operational focus.

---

### `INT-15`: Model Independence and Clean Middleware
* **Question**: *"How does NALA guarantee model independence, ensuring that the cognitive reasoning engine, safety gates, and storage harnesses operate identically regardless of whether Ollama, Groq, or a cloud API powers the step handler?"*
* **Ideal Answer Scope**:
  - Explains the decoupling of model generation from domain state.
  - Shows that `ModelRouter` normalizes outputs into canonical schemas (`StepResult`, `TaskResult`).
  - Proves that verification, recovery, and safety logic are enforced by deterministic Python code, never by the model itself.

---

*This concludes the Architect Interview Bank. Proceed to Learning Roadmap.* 🏛️🧠⚡
