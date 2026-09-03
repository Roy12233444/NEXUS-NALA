# 📚 NALA-THEORY-001 — AI ML Systems Concept Inventory
**Classification:** Categorized Theoretical Knowledge Inventory (Categories A–Z)  
**Project:** NALA (Nexus Autonomous Logic Architecture)  
**Author:** Principal AI/ML Systems Architect & Research Scientist  
**Date:** August 30, 2026  
**Status:** 🟢 **GROUNDED IN NALA IMPLEMENTATION**

---

## 1. Domain Taxonomy & Classification Index

Every concept implemented or required by NALA is cataloged into its authoritative academic and engineering domain:

* **Category A**: Mathematics & Linear Algebra
* **Category B**: Probability Theory
* **Category C**: Statistics & Calibration
* **Category D**: Machine Learning & Representation
* **Category G**: Large Language Models (LLMs) & Prompting
* **Category I**: AI Agents & Autonomous Organisms
* **Category J**: Planning & Graph Theory
* **Category K**: Search & Optimization
* **Category L**: Knowledge Representation & Epistemology
* **Category M**: Information Retrieval (IR) & Memory Systems
* **Category N**: Distributed Systems & Protocols
* **Category O**: Operating Systems & Subprocess Management
* **Category P**: Concurrency & Synchronization
* **Category Q**: Networking & WebSockets
* **Category R**: Databases & Transaction Recovery
* **Category S**: Security & Capability-Based Sandboxing
* **Category T**: Software Architecture & State Machines
* **Category U**: Reliability Engineering & Fault Tolerance
* **Category V**: Human-Agent Interaction (HCI)
* **Category W**: AI Safety & Alignment
* **Category Y**: Observability, Telemetry & Tracing

---

## 2. Exhaustive Concept Inventory

### Category A: Mathematics & Linear Algebra
| Concept ID | Theoretical Concept | Mathematical Formalism | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `MATH-01` | **Vector Spaces & Norms** | $V = \mathbb{R}^d, \|\mathbf{v}\|_2 = \sqrt{\sum_{i=1}^d v_i^2}$ | Dense vector embedding structures in `core/session/amp_client.py` |
| `MATH-02` | **Inner Product & Cosine Similarity** | $\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum u_i v_i}{\sqrt{\sum u_i^2}\sqrt{\sum v_i^2}}$ | Vector similarity calculation in `amp_client.py` and semantic memory search |
| `MATH-03` | **Set Theory & Normalization** | $S = \{x \in \mathcal{U} \mid P(x)\}, |S \cap S'|$ | $O(1)$ fact deduplication via `_normalize()` in `core/brain/memory_service.py` |
| `MATH-04` | **Metric Spaces & Distance Functions** | $d(x, y) \ge 0, d(x, y) = 0 \iff x=y, d(x, y) \le d(x, z) + d(z, y)$ | Distance calculation across embedding spaces in retrieval |

---

### Category B & C: Probability, Statistics & Calibration
| Concept ID | Theoretical Concept | Mathematical Formalism | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `PROB-01` | **Bayesian Belief Updating** | $P(H \mid E) = \frac{P(E \mid H) P(H)}{P(E)}$ | Epistemic confidence weighting in `core/interaction/pramana_router.py` |
| `PROB-02` | **Model Calibration & Brier Score** | $\text{BS} = \frac{1}{N} \sum_{t=1}^N (f_t - o_t)^2$ | `confidence_calibration` metric in `core/safety/adaptive_viveka_gate.py` |
| `PROB-03` | **Moving Average & Hysteresis Filtering** | $\bar{x}_t = \frac{1}{k} \sum_{i=0}^{k-1} x_{t-i}$ | `deque(maxlen=10)` buffer in `core/interaction/pramana_router.py` |
| `PROB-04` | **Feedback Control Loop Dynamics** | $u(t) = K_p e(t) + K_i \int e(\tau)d\tau + K_d \frac{de}{dt}$ | Dynamic safety modulation in `core/safety/rta_feedback_loop.py` |

---

### Category G & I: LLMs, Prompting & AI Agent Architecture
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `AGENT-01`| **Agentic Loop (Perceive-Plan-Act)** | Iterative state machine: $s_{t+1} = f(s_t, a_t, o_t)$ | Main execution loop in `core/harness/nala_loop.py` (`NalaLoop.run()`) |
| `AGENT-02`| **Token Budgeting & Compaction** | Context window constraint: $\sum \text{len}(m_i) \le C_{\max}$ | `core/harness/context_tracker.py` (`DronagiriCompactor`) |
| `AGENT-03`| **Model Routing & Fallback** | Dynamic provider selection based on latency/cost | `core/hands/model_router.py` (Ollama $\to$ Groq $\to$ Cloud API) |
| `AGENT-04`| **Intent Classification** | Mapping input space $\mathcal{X} \to \mathcal{I} = \{\text{chat}, \text{task}, \text{verify}\}$ | Regex & neural classifier in `core/intent/classifier.py` |

---

### Category J & K: Planning, Graph Theory & Search
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `PLAN-01` | **Directed Acyclic Graphs (DAGs)** | $G = (V, E)$ where $\nexists (v_0, \dots, v_k, v_0)$ | `core/harness/session_contract.py` (`TaskGraph`, `TaskStep`) |
| `PLAN-02` | **Cycle Detection (Tarjan's DFS)** | Depth-first traversal tracking back-edges in call stack | Pre-execution validation in `core/brain/planner.py` |
| `PLAN-03` | **Topological Ordering** | Linear ordering $\prec$ such that $(u, v) \in E \implies u \prec v$ | Step dependency resolution in `core/harness/nala_loop.py` |
| `PLAN-04` | **Hierarchical Goal Decomposition** | Transforming complex goal $G \to \{g_1, g_2, \dots, g_n\}$ | `Planner.create_plan()` in `core/brain/planner.py` |

---

### Category L & M: Knowledge Representation, Epistemology & Memory
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `EPIST-01`| **Six-Prāmāṇic Epistemology** | Epistemic pathways: Pratyakṣa, Anumāna, Śabda, Upamāna, Arthāpatti, Anupalabdhi | `core/interaction/pramana_router.py` (`PramanaRouter`) |
| `EPIST-02`| **Claim vs Physical Evidence** | Proposition $P$ vs Cryptographic Attestation $\text{Hash}(B)$ | `core/harness/recovery.py` (`PhysicalEvidenceCorroborator`) |
| `MEM-01`  | **Flat-File Semantic Memory** | Structured append-only persistent markdown facts | `core/brain/memory_service.py` (`memory/MEMORY.md`) |
| `MEM-02`  | **Optimistic Concurrency (Revision Tokens)** | $T_{\text{rev}} = \text{SHA256}(\text{Content})$, compare-on-write | `_revision_token()` in `core/brain/memory_service.py` |

---

### Category R & U: Databases, Transactions & Reliability Engineering
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `REL-01`  | **Write-Ahead Logging (WAL)** | Append mutations to log before updating state | Append-only `.jsonl` logging in `core/harness/checkpoint.py` |
| `REL-02`  | **Monotonic Log Sequence Numbers** | Strict monotonic ordering: $\text{LSN}_{t+1} > \text{LSN}_t$ | `checkpoint_LSN_XXXXXX.json` in `core/harness/checkpoint.py` |
| `REL-03`  | **Atomic File Replacement** | Write to `.tmp` $\to$ `os.fsync()` $\to$ atomic `os.replace()` | Atomic write pattern in `core/harness/checkpoint.py` |
| `REL-04`  | **ARIES Crash Recovery** | 3-Phase recovery: Analysis $\to$ Redo $\to$ Undo | `core/harness/recovery.py` & `recovery_engine.py` |
| `REL-05`  | **Bounded Retry & Exponential Backoff** | $T_{\text{wait}} = 2^{\text{attempt}} \cdot \text{base}$, $\text{attempt} \le \text{MAX}$ | `RecoveryEngine.execute_recovery()` with `max_attempts=3` |
| `REL-06`  | **Circuit Breaker Pattern** | States: `CLOSED` $\to$ `OPEN` $\to$ `HALF_OPEN` | `core/safety/circuit_breaker.py` (`CircuitBreaker`) |

---

### Category S & O: Security, Operating Systems & Sandboxing
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `SEC-01`  | **Reference Monitor & Safety Gates** | Enforcing non-bypassable mediation of all tool calls | `core/safety/adaptive_viveka_gate.py` (`AdaptiveVivekaGate`) |
| `SEC-02`  | **Principle of Least Privilege** | Confining process access to minimal required directories | Working directory isolation in `core/hands/sandbox.py` |
| `SEC-03`  | **Process Confinement (Seccomp/JobTokens)** | Restricting kernel syscalls and process execution tokens | `core/hands/sandbox_seccomp.py` & `sandbox_windows.py` |
| `SEC-04`  | **Prohibited Pattern Interception** | Path traversal (`..`) & destructive command (`rm -rf`) regexes | `_PROHIBITED_PATH_PATTERNS` in `adaptive_viveka_gate.py` |

---

### Category P, Q & T: Concurrency, Networking & State Authority
| Concept ID | Theoretical Concept | Formal Definition | NALA Physical Implementation |
| :--- | :--- | :--- | :--- |
| `CONC-01` | **Thread Safety & Mutual Exclusion** | Re-entrant mutex locks preventing data races | `threading.RLock()` guarding `RuntimeState` in `nala_server/state.py` |
| `CONC-02` | **Deterministic Finite Automata (DFA)** | Formally bounded state transitions: $\delta: S \times \Sigma \to S$ | `VALID_TRANSITIONS` matrix in `nala_server/state.py` |
| `CONC-03` | **Optimistic Locking via State Versioning** | State mutation validation: $\text{version}_{\text{actual}} == \text{version}_{\text{expected}}$ | `expected_state_version` in `nala_server/state.py` |
| `NET-01`  | **Event-Driven Architecture & Message Queues** | Decoupled producer-consumer pipeline via thread-safe queues | `server_state.event_queue.put()` in `nala_server.py` |
| `NET-02`  | **WebSocket Full-Duplex Framing** | Persistent bi-directional framing over TCP (RFC 6455) | Socket.IO server on port 3001 $\leftrightarrow$ `websocketService.ts` |

---

*This concludes the Concept Inventory. Proceed to Question Bank.* 📚🧬⚡
