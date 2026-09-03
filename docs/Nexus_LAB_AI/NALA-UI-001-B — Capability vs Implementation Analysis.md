# 🔬 NALA Architecture Research Notebook — NALA-UI-001-B
**Title:** Capability vs. Implementation Analysis  
**Topic:** Deconstructing Competitor Mechanisms into Abstract Capabilities and Alternative Representations  
**Status:** 🟢 **ANALYSIS COMPLETE (LOCKED FOR WORKBENCH DERIVATION)**  

---

## 🧭 Objective
To ensure NALA never copies competitor mechanisms verbatim, we deconstruct every observed competitor feature into:
1. **The Specific Mechanism** (What they built)
2. **The Underlying Problem** (What broke without it)
3. **The Underlying Capability** (The universal need)
4. **Alternative Possible Representations** (How NALA can express it natively)

---

## 🔬 Deconstruction Table

| Observed Competitor Mechanism | Company | Underlying Problem | Underlying Capability | Alternative Representations |
| :--- | :--- | :--- | :--- | :--- |
| **Git Worktrees** | OpenAI Codex | Parallel agents editing code overwrite each other's uncommitted files and lock git index. | **Workspace / Execution Isolation** | • Temporary sandboxed directories<br>• Docker containers<br>• Virtual memory overlays<br>• In-memory branch forks |
| **App-Server JSON-RPC** | OpenAI Codex | Decoupling heavy background model execution from lightweight IDE/desktop client. | **Decoupled IPC Transport** | • WebSockets + Typed Events<br>• gRPC bidirectional streaming<br>• Unix Domain Sockets<br>• Redis / SQLite task queue |
| **`AGENTS.md` / `CLAUDE.md`** | Codex / Claude Code | User forced to re-prompt coding style, rules, and commands every new chat turn. | **Standing Persistent Instructions** | • Structured JSON/YAML contracts<br>• System prompt dynamic injectors<br>• Database-backed rule matrices<br>• Graph-based memory nodes |
| **`PreToolUse` Hooks (exit code 2)** | Claude Code | Model hallucinations or untrusted prompt injections attempting unauthorized shell commands. | **Deterministic Execution Governance** | • Semantic policy evaluator (e.g. Satya/Ṛta)<br>• Typed Approval Request State<br>• Pre-execution whitelist filter<br>• Kernel capability masks |
| **`/compact` Command** | Claude Code | Context window overflow during long-running multi-turn debug sessions. | **Context Lifecycle Management** | • Automated sliding-window summarizer<br>• Dronagiri Compactor (Vector snapshotting)<br>• Session Handoff Spores<br>• Hierarchical memory paging |
| **Project Memory / Scopes** | Claude Cowork | Knowledge gained in one sub-task is lost when switching tasks within the same project. | **Project-Scoped Memory Accumulation** | • `MEMORY.md` persistent file<br>• Embeddings index of task outputs<br>• Session State graph cache<br>• Checkpoint lineage database |
| **Screen Navigation / Computer Use** | Claude Cowork | Legacy desktop apps have no REST/MCP APIs or CLI interfaces available. | **Unstructured UI Interaction** | • Native OS Accessibility APIs<br>• Playwright/Puppeteer browser automation<br>• CLI wrappers for desktop tools<br>• MCP custom server bridges |
| **Spreadsheet Formula Generation** | Claude Cowork | Business users cannot verify or audit raw numbers emitted in Markdown text. | **Verifiable / Computable Deliverables** | • SQLite database files with SQL queries<br>• Executable Python scripts (`pandas`)<br>• Self-contained interactive HTML/JS widgets<br>• Jupyter Notebooks with visible outputs |

---

## 💡 Key Architectural Takeaway for NALA
1. **Never copy the file format or naming convention** (e.g., creating `NALA.md` just because others have `CLAUDE.md`).
2. **Focus on the capability**: NALA already has `core/harness/context_tracker.py` (DronagiriCompactor), `core/harness/checkpoint.py` (LSN Atomic Checkpointer), `core/safety/satya.py` (Policy Evaluator), and `nala_server/state.py` (Optimistic State Manager).
3. **The gap is UI representation**, not the missing capability!
