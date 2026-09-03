As a **First-Principles Frontier AI Lab**, Nexus Lab AI follows a clear rule:

> **"Borrow commodity plumbing so we save time; Build frontier breakthroughs from ground-up so NALA dominates."**

Here is the exact division of **What We Use** vs. **What We Build From Ground-Up**:

---

# 📦 1. What We USE / LEVERAGE (Commodity Plumbing)

*No need to waste time re-inventing basic infrastructure:*

1. **File Patch Format (`apply_patch`)**: Use standard Git-style unified diff parsing (`*** Begin Patch ... ***`) for line-by-line file edits.
2. **Model Context Protocol (MCP)**: Use standard MCP tool schemas so NALA connects to external tools (databases, browsers, search APIs).
3. **LLM REST Payloads**: Use standard HTTP streaming payloads for Ollama (`http://localhost:11434`), LM Studio, and OpenAI endpoints.
4. **UI Primitives**: Use `xterm.js` for the terminal and `@monaco-editor/react` for diff rendering.

---

# 🔬 2. What We BUILD FROM GROUND-UP (Nexus Lab Frontier Breakthroughs)

*This is where Nexus Lab AI innovates first-principles AI science:*

### 🛡️ **Breakthrough 1: Vedic Epistemic Governance (Viveka & Satya Runtimes)**

* **The Problem in Codex/Devin**: Existing agents rely purely on model alignment prompts. If the LLM gets confused, it runs bad commands.
* **Nexus Lab First-Principle**: **Runtime Epistemic Control**.
  * **AdaptiveVivekaGate**: Dynamic mathematical discrimination gates (`MINIMAL`, `BALANCED`, `MAXIMUM` strictness).
  * **ContextAwareSatyaLayer**: Mathematical scoring of truthfulness, consistency rate, and contradiction counts before code commits.

---

### 🧬 **Breakthrough 2: Capability Cortex (CCX) & Dependency Graphs (CDG)**

* **The Problem in Codex/Devin**: Standard planners treat tools as flat, independent lists. When an API or tool fails, the agent crashes.
* **Nexus Lab First-Principle**: **Capability Graph Abstraction** $G = (C, E)$.
  * Decouples *what NALA needs to do* from *how tools execute*.
  * Automatic **graceful degradation & capability substitution** (e.g., `Web API` ➔ `Local Knowledge RAG Cache`) with zero crash.
  * Reliability-aware path optimizer: $\min (\text{Cost} + \text{Latency} + \text{FailureRisk})$.

---

### 🔄 **Breakthrough 3: LSN Journaling & Handoff Spore Engine**

* **The Problem in Codex/Devin**: If the process crashes or restarts, state and context are corrupted or lost.
* **Nexus Lab First-Principle**: **Log Sequence Number (LSN) Crash Survival**.
  * `CheckpointManager` with UTC-aware Pydantic v2 state matrices and DFS cycle detection.
  * **Session Handoff Spores**: NALA can hand off running tasks across processes and machines seamlessly.

---

### 🔒 **Breakthrough 4: Kernel Job Object Isolation + PEP 578 Audit Hooks**

* **The Problem in Codex/Devin**: Docker containers are heavy; simple Python scripts can leak memory or bypass file restrictions.
* **Nexus Lab First-Principle**: **Kernel-Level Resource Containment**.
  * Windows Kernel Job Objects enforcing strict **256MB RSS memory caps**.
  * CPython **PEP 578 audit hooks** capturing raw C-level syscalls, socket creation, and filesystem access.

---

### 📌 Summary Architecture

```text
  [ USER DIRECTIVE ]
          │
          ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  NEXUS FRONTIER ENGINE (BUILD FROM GROUND-UP)              │
  │  • Capability Cortex (CCX Graph Resiliency)                 │
  │  • Vedic Epistemic Governance (Viveka Gate & Satya Layer)   │
  │  • LSN Checkpoint Manager & Handoff Spores                  │
  │  • Kernel Job Object Sandbox + PEP 578 Syscall Hooks        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  COMMODITY PLUMBING (LEVERAGE / USE)                        │
  │  • File Patching (apply_patch)                              │
  │  • MCP Tool Protocols                                       │
  │  • Ollama / vLLM / OpenAI REST Payloads                      │
  │  • Monaco Diff & xterm.js UI Controls                       │
  └─────────────────────────────────────────────────────────────┘
```

This strategy gives NALA **world-class speed today** and **unmatched frontier intelligence tomorrow**! 🚀
