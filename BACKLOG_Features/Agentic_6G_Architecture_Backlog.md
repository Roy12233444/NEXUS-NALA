# Backlog Feature Specification: Integrating Agentic AI-Native 6G Architecture into NALA

This backlog plan outlines the architectural integration of the research findings from `6G Needs Agents: Toward Agentic AI-Native Networks for Autonomous Intelligence` into the NALA (Nexus Autonomous Long-Running Agent) execution loop.

The core objective is to transition NALA from a single-agent linear execution cycle into a **policy-governed, distributed multi-agent semantic control plane** layered above deterministic code execution and workspace execution boundaries.

---

## 🗺️ Architectural Mapping (The 4 Layers of NALA)

To align NALA with the paper's proposed AI-native control framework, we will map NALA's components to the four layers:

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: DISTRIBUTED MULTI-AGENT FABRIC                                           │
│ Local Device/Edge Agent (SmolLM/LLaMA) ←─ Async Inter-Agent ─→ Remote Core Agent   │
├───────────────────────────────────────────────────────────────────────────────────┤
│ LAYER 3: AGENTIC REASONING LAYER                                                 │
│ Intent Decomposer  ←───  SAHOO Validation Gates  ───→  AST Reflection & Audit     │
├───────────────────────────────────────────────────────────────────────────────────┤
│ LAYER 2: SEMANTIC ABSTRACTION LAYER                                               │
│ Intent / Task Graph  ←───  Knowledge Graph & Memory  ───→  Trust & Policy Constraints │
├───────────────────────────────────────────────────────────────────────────────────┤
│ LAYER 1: DETERMINISTIC INFRASTRUCTURE LAYER                                       │
│ Python Sandbox Execution  ←───  Git VCS Workspace  ───→  Terminal Command Shell   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Backlog Implementation Roadmap

### 📦 Phase 1: Semantic State & Intent Abstraction

#### `FEAT-6G-001` — The Semantic State Matrix ($S_t$)
* **Objective:** Define a formal, schema-validated representation of NALA's cognitive and workspace environment state at any time step $t$.
* **Implementation Details:**
  * Define the state vector as:
    $$S_t = \{I_t, K_t, P_t, T_t, U_t, G_t\}$$
    * $I_t$: Structured Intent (Goal decomposition, target file paths).
    * $K_t$: Cross-domain Context (JIT AST schema, active imports, recent variables).
    * $P_t$: Policy Constraints (Write-restricted folders, blocked system calls).
    * $T_t$: Trust & Integrity Score (Based on static analysis/STAI output).
    * $U_t$: Execution Uncertainty (Telemetry tracking of error counts and causal residuals).
    * $G_t$: Workspace Git status & LSN state.
  * Save the state matrix in a thread-safe SQLite database table alongside the existing session ledger.

#### `FEAT-6G-002` — Intent Interpretation & Goal Decomposition
* **Objective:** Translate high-level user instructions into a structured directed acyclic task graph (DAG).
* **Implementation Details:**
  * Implement an `IntentDecomposer` module that processes user inputs.
  * Decompose tasks into isolated subtasks with explicit pre-conditions, tool requirements, and post-conditions.

---

### 📦 Phase 2: Split Inference & Multi-Agent Coordination

#### `FEAT-6G-003` — Edge-Core Split Inference Router
* **Objective:** Optimize latency and compute cost by routing simple validation tasks to lightweight local models and complex planning to large core models.
* **Implementation Details:**
  * **Edge Agent:** Configured to run sub-1B/3B parameters (e.g. `SmolLM2-135M` or `LLaMA-3.2-1B` in Ollama). Automatically processes low-complexity tasks:
    * Regex code syntax correction
    * File read formatting
    * Initial AST analysis
  * **Core Agent:** Configured with highly capable large models (e.g. `Qwen-27B` or `DeepSeek-R1`). Handles:
    * Multi-step debugging logic
    * Multi-file dependency architecture planning
    * Conflict resolution during Git merges
  * Implement an `InferenceRouter` that monitors token usage and task category to dynamically delegate reasoning.

#### `FEAT-6G-004` — Distributed Multi-Agent Coordination Protocol
* **Objective:** Divide loops into distinct, specialized role-based agents instead of a monolithic orchestrator thread.
* **Implementation Details:**
  * Implement three active agent profiles:
    * **Architect Agent:** Reads intent, plans file changes, builds state.
    * **Developer Agent:** Surgical file splicing, local edge code generation.
    * **Critic Agent:** Computes STAI, analyzes test logs, checks constraints.
  * Exchange state packets containing serialized JSON sub-states asynchronously.

---

### 📦 Phase 3: Bounded Autonomy, Trust & Safety Guardrails

#### `FEAT-6G-005` — Policy-Governed SAHOO Validation Gates
* **Objective:** Enforce policy boundaries at the boundary of Layer 1 (Infrastructure) execution using the **SAHOO** (Self-Alignment Hierarchical Orchestration Override) validation engine.
* **Implementation Details:**
  * Build a 6-Gate verification chain:
    1. **Syntax Gate:** Verifies code syntax compiles.
    2. **Imports Gate:** Denies imports of dangerous/blocked packages.
    3. **Trust Gate:** Verifies the structural similarity (STAI) is within bounds.
    4. **Safety Gate:** Simulates execution in a jailed subprocess.
    5. **Goal Drift Gate:** Computes cosine distance deviation to ensure semantic alignment.
    6. **Causal Convergence Gate:** Halts execution if the loop exhibits infinite error regression ($R_k \geq 0.95$).

#### `FEAT-6G-006` — Digital Twin Workspace Sandboxing (Pre-Validation)
* **Objective:** Prevent agents from writing corrupted or broken code directly to the source directory before testing.
* **Implementation Details:**
  * Implement a `WorkspaceMirror` utility.
  * When a write action is proposed, clone the target file and dependencies to a sandboxed `/twin_jail/` folder.
  * Run tests within the jail first. If tests pass, perform an atomic `os.replace` to commit to the main workspace.

---

## 📊 Verification Plan

### Simulated Benchmarking (NALA-Bench)
* Adapt the paper's **6G-Bench** concept into a local evaluation harness for code tasks:
  * Seed 50 complex programming challenges (e.g. involving infinite loops, resource leaks, syntax regressions).
  * Run NALA across quantized models (Q4, Q8, FP16) to verify that local edge agents handle syntax, while core agents resolve architectural bugs.
  * Measure key performance trade-offs: **Inference Latency vs. Success Rate vs. VRAM footprint**.
