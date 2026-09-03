# NALA Core Features & Architecture Genesis Report
**Document ID**: `NALA-CORE-GENESIS-001`  
**Classification**: Architectural Ground Truth & Founding Subsystems  
**Location**: `docs/Nexus_LAB_AI/NALA_Core_Features_Genesis_Report.md`  

---

## 1. Executive Overview: The Genesis of NALA

NALA (**Natural Advanced Linguistic Architecture**) was conceived from day one not merely as a simple chatbot or a thin LLM wrapper, but as a **transcendent, self-evolving, verifiable autonomous reasoning engine**.

From the very beginning of the project, the architecture in the [`core/`](file:///E:/NALA-Project/NALA/core) directory was engineered to bridge ancient **Vedic epistemological frameworks** with cutting-edge **modern distributed computing, sandboxing, and crash-resilient kernel harness design**.

The foundational features are organized into **7 core functional pillars**:

```text
                               ┌─────────────────────────────┐
                               │   USER / UI (Socket.IO)     │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                         ┌─────────────────────────────────────────┐
                         │       core/intent (Classifier)          │
                         └────────────────────┬────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
          [Conversational Chat]                             [Autonomous Task]
                     │                                                 │
                     ▼                                                 ▼
        ┌─────────────────────────┐                      ┌───────────────────────────┐
        │ core/interaction        │                      │ core/harness (NalaLoop)   │
        │ - Pramāṇa Router        │                      │ - TaskGraph Execution     │
        │ - Interaction Contract  │                      │ - Checkpoint & Recovery   │
        └─────────────────────────┘                      │ - Context Budget Tracker  │
                                                         └─────────────┬─────────────┘
                                                                       │
             ┌─────────────────────────────────────────────────────────┼───────────────────────────────────────────┐
             ▼                                                         ▼                                           ▼
┌──────────────────────────┐                             ┌───────────────────────────┐               ┌───────────────────────────┐
│ core/brain               │                             │ core/safety               │               │ core/hands                │
│ - Saptacore Council      │                             │ - Adaptive Viveka Gate    │               │ - Process Sandbox         │
│ - Memory Service         │ ◄─────────────────────────► │ - Context Satya Layer     │ ◄───────────► │ - Agama Tool Selector     │
│ - Planner & Dependency   │                             │ - Ṛta Governor & Feedback │               │ - Model Router (Ollama)   │
│ - Ṛta Validator          │                             │ - Circuit Breaker & Usha  │               │ - Tool Registry           │
└──────────────────────────┘                             └───────────────────────────┘               └───────────────────────────┘
```

---

## 2. Deep Dive: Core Foundational Subsystems

### 🧠 Pillar I: `core/brain` — Cognitive Reasoning & Memory
Located at [`core/brain/`](file:///E:/NALA-Project/NALA/core/brain), this subsystem serves as NALA's cognitive core.

1. **`memory_service.py` (Long-Term & Working Memory Engine)**:
   - Implements persistent Markdown and vector-like memory stored in [`memory/MEMORY.md`](file:///E:/NALA-Project/NALA/memory/MEMORY.md).
   - Manages episodic working memory buffers, cross-session knowledge persistence, semantic tagging, and compact summary generation.
2. **`saptacore_council.py` (7-Pillar Deliberative Council)**:
   - NALA’s multi-agent deliberative reasoning council incorporating 7 distinct faculties:
     - *Pramāṇa* (Epistemological validity)
     - *Viveka* (Discernment & Safety)
     - *Satya* (Truthfulness & Factuality)
     - *Ṛta* (Cosmic Order & System Equilibrium)
     - *Uṣā* (Dawn of Insight & Clarity)
     - *Duṣtara* (Overcoming Obstacles)
     - *Ānanda* (Harmonious Resolution)
3. **`planner.py` & `task_graph.py` (Goal Decomposition & Graph Execution)**:
   - Breaks complex user directives into directed acyclic graphs (DAG) of steps.
   - Performs DFS cycle checking, topological dependency ordering, and parallel execution candidacy analysis.
4. **`rta_validator.py` & `judge.py` (Reasoning Arbitration)**:
   - Validates mathematical proofs, logical claims, and outputs against ground truth criteria before finalizing.

---

### 🛡️ Pillar II: `core/safety` — The Vedic Governance & Safety Stack
Located at [`core/safety/`](file:///E:/NALA-Project/NALA/core/safety), this layer guarantees ethical alignment, hallucination elimination, and system resource governance.

1. **`adaptive_viveka_gate.py` (Viveka / Discernment Gate)**:
   - First-line security and prompt-injection firewall.
   - Dynamically adapts strictness based on user trust tiers and intent risk scores.
2. **`context_aware_satya_layer.py` (Satya / Truthfulness Layer)**:
   - Validates output truthfulness, internal consistency, and epistemic honesty.
   - Flags hallucinations and prevents the model from generating baseless assertions.
3. **`rta_governor.py` & `rta_feedback_loop.py` (Ṛta Cosmic Order Governor)**:
   - Real-time closed-loop PID-like feedback governor monitoring system balance.
   - Enforces the `SACRED_PAUSE` protocol if cognitive entropy or CPU/memory load exceeds safe bounds ($Ṛta > 0.95$).
4. **`circuit_breaker.py` & `usha.py`**:
   - Hardware and memory circuit breakers preventing infinite loops, token exhaustion, or recursive execution crashes.

---

### 🦾 Pillar III: `core/hands` — Sandboxing, Tools & Multi-Model Routing
Located at [`core/hands/`](file:///E:/NALA-Project/NALA/core/hands), this subsystem connects NALA's cognitive intentions to real-world actions.

1. **`sandbox.py`, `sandbox_windows.py`, `sandbox_linux.py`, `sandbox_seccomp.py`**:
   - Multi-platform isolated execution environment.
   - Restricts filesystem access, captures stdout/stderr, intercepts system calls via seccomp/Windows Job Objects, and isolates disk mutations.
2. **`tool_registry.py` & `executor.py`**:
   - Dynamic catalog of executable tools (filesystem operations, code executors, web research, memory querying).
   - Enforces timeout limits and return value validation.
3. **`agama_tool_selector.py` & `predictive_tool_selector.py`**:
   - Pre-evaluates objectives and selects the optimal tool sequence before execution.
4. **`model_router.py`**:
   - Intelligent local vs. cloud model routing. Seamlessly interfaces with local Ollama models (`qwen2.5-coder`, `deepseek-r1`, `llama3.2`) and high-throughput cloud providers (Groq) based on prompt complexity and latency targets.

---

### ⚙️ Pillar IV: `core/harness` — The Long-Running Agent Kernel
Located at [`core/harness/`](file:///E:/NALA-Project/NALA/core/harness), this represents the operational spine that makes NALA a true long-running agent.

1. **`nala_loop.py` (Authoritative Step Dispatcher)**:
   - The central deterministic runtime loop that steps through the `TaskGraph`, manages step transitions (`PENDING` ➔ `RUNNING` ➔ `SUCCESS` / `FAILED`), and coordinates telemetry.
2. **`checkpoint.py` (Sliding-Window WAL Checkpoint Manager)**:
   - Persists state checkpoints with incremental Log Sequence Numbers (`LSN_000001`, `LSN_000002`).
   - Ensures zero state loss even across sudden process termination.
3. **`recovery.py` (Self-Healing Recovery Engine)**:
   - On startup or crash detection, reconstructs session memory and TaskGraphs from the latest valid checkpoint.
4. **`context_tracker.py` (Context & Token Compaction Manager)**:
   - Tracks prompt tokens, projected context growth, ceiling limits (e.g. 121,600 tokens), warning thresholds, and triggers automatic context compaction.
5. **`session_contract.py` & `session_handoff.py`**:
   - Formal schema contracts defining `TaskStep`, `TaskGraph`, `SessionState`, and inter-session state handoffs.

---

### 🎯 Pillar V: `core/intent` — Intent Classification
Located at [`core/intent/`](file:///E:/NALA-Project/NALA/core/intent).

1. **`classifier.py`**:
   - Two-tier zero-latency intent classifier:
     - **Tier 1**: Lexical pattern matching and regex heuristics for immediate task vs. chat disambiguation.
     - **Tier 2**: Zero-shot local model intent evaluation for ambiguous natural language queries.

---

### 🤝 Pillar VI: `core/interaction` — Epistemological Routing & Contracts
Located at [`core/interaction/`](file:///E:/NALA-Project/NALA/core/interaction).

1. **`pramana_router.py` (The 6 Vedic Epistemological Paths)**:
   - Routes cognitive tasks through the appropriate epistemology:
     1. *Pratyakṣa* (Direct Observation / Perceptual data)
     2. *Anumāna* (Logical Inference & Deduction)
     3. *Upamāna* (Analogy & Comparison)
     4. *Arthāpatti* (Postulation & Hypothesis Generation)
     5. *Anupalabdhi* (Negative Proof & Proof by Absence)
     6. *Śabda / Āgama* (Authoritative Knowledge & Trusted Sources)
2. **`interaction_contract.py`**:
   - Manages interactive turns, human-in-the-loop approvals, and structured user feedback.

---

### 🌐 Pillar VII: `core/session` — Distributed Messaging & Audit
Located at [`core/session/`](file:///E:/NALA-Project/NALA/core/session).

1. **`amp_client.py` (Agent Messaging Protocol)**:
   - WebSocket and IPC message bus enabling multi-agent coordination.
2. **`event_log.py`**:
   - Cryptographic append-only audit trail logging all state transitions.

---

## 3. How Early Core Features Map to the Modern Workbench (`NALA-WB`)

The vertical slices built in the `NALA-WB-001` series directly expose and project these foundational core modules into the modern React Workbench UI:

| Foundational Core Module | Built In | Projected Through Workbench Slice | UI Component Exposed |
| :--- | :--- | :--- | :--- |
| **`core/harness/nala_loop.py`** | Inception | `NALA-WB-001A` & `001B` | Live execution loop & real-time event badges |
| **`core/harness/session_contract.py`** | Inception | `NALA-WB-001C` | Multi-task isolation & canonical `TaskID` |
| **`core/brain/planner.py` & `TaskGraph`** | Inception | `NALA-WB-001D` & `001E` | `EXECUTION PLAN` & `EXECUTION PROGRESS` timeline |
| **`core/safety/satya` & `core/hands/sandbox`** | Inception | `NALA-WB-001F` | `RESULT VERIFIED` & `ARTIFACT` cards |
| **`core/brain/memory_service.py`** | Inception | Next Slice | Long-term episodic memory & workspace recall |

---

## 4. Summary Matrix

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    NALA FOUNDATIONAL CORE STACK                         │
├───────────────────┬─────────────────────────────────────────────────────┤
│ Module Category   │ Primary Responsibilities                            │
├───────────────────┼─────────────────────────────────────────────────────┤
│ 🧠 core/brain     │ Multi-agent council, memory service, goal planning  │
│ 🛡️ core/safety    │ Viveka gate, Satya validator, Ṛta governor, pause   │
│ 🦾 core/hands     │ OS sandboxing, tool registry, model routing         │
│ ⚙️ core/harness   │ NalaLoop, LSN checkpoints, crash recovery, context  │
│ 🎯 core/intent    │ Two-tier conversational vs task intent classifier   │
│ 🤝 core/interaction│ 6 Pramāṇa epistemological router, user contracts    │
│ 🌐 core/session   │ Distributed AMP client, event ledger, session state │
└───────────────────┴─────────────────────────────────────────────────────┘
```

This master report is permanently stored in [`docs/Nexus_LAB_AI/NALA_Core_Features_Genesis_Report.md`](file:///E:/NALA-Project/NALA/docs/Nexus_LAB_AI/NALA_Core_Features_Genesis_Report.md).
