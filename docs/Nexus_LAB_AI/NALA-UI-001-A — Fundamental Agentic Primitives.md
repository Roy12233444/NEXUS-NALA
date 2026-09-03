# 🔬 NALA Architecture Research Notebook — NALA-UI-001-A
**Title:** Fundamental Agentic Primitives  
**Source Evidence:** `COWORK #001`, `COWORK #002`, `COWORK #003` (Cowork, Codex, Claude Code)  
**Status:** 🟢 **SYNTHESIS COMPLETE (LOCKED FOR WORKBENCH DERIVATION)**  

---

## 🧭 Objective & Evaluation Framework
The goal is to determine which agentic capabilities across Claude Cowork, OpenAI Codex, and Anthropic Claude Code are **fundamentally required** for any autonomous long-running workbench, versus which are merely convenient product-specific choices.

### The 4 Rigorous Filter Tests
1. **Test A (Cross-System Recurrence):** Does the primitive appear across 2 or more mature independent systems?
2. **Test B (The "Remove It" Test):** If this primitive is completely removed, can a long-running autonomous system still safely, reliably, and coherently complete multi-hour/multi-day work?
3. **Test C (Architectural Necessity):** Is it mathematically/logically necessary for autonomous state transitions and human trust?
4. **Test D (Alternative Implementations):** Does the underlying capability express itself in diverse concrete forms?

---

## 📊 Universal Primitive Evaluation Matrix

| # | Primitive | Cowork | Codex | Claude Code | Fundamental? | Architectural Justification ("Remove It" Test) |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **Execution Engine** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without execution, an agent cannot produce state transitions or mutate reality.* |
| **2** | **Asynchronous / Long-Running Runner** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without asynchronous detachment, execution terminates the moment UI closes or network drops.* |
| **3** | **Authoritative State Persistence** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without persistence, memory of past steps, decisions, and variable bindings vanishes on restart.* |
| **4** | **Step-by-Step Observability** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without live step/reasoning visibility, the user is blind and cannot trust long autonomous runs.* |
| **5** | **Mid-Flight Steering / Intervention** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without mid-task steering, a slight initial misunderstanding cascades into hours of wasted work.* |
| **6** | **Deterministic Safety & Governance** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without hard approval gates (e.g. deletion/payments), autonomous systems pose catastrophic operational risk.* |
| **7** | **Sub-Agent Context Isolation** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without isolated context windows for sub-tasks, large searches rapidly exhaust the main context window.* |
| **8** | **Verification & Self-Correction** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without post-step verification (tests, lints, checks), hallucinated errors compound uncontrollably.* |
| **9** | **Physical Deliverable Persistence** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without concrete artifacts saved to disk, work has no persistent utility outside the chat bubble.* |
| **10** | **Context Compaction / Truncation** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without automated compaction/checkpointing, multi-day tasks hit hard LLM context limits and abort.* |
| **11** | **Epistemic Silence / Ambiguity Handling**| ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without explicit reporting of gaps/silence, models guess and invent fake facts/paths.* |
| **12** | **External Tool & MCP Protocol** | ✓ | ✓ | ✓ | **YES (FUNDAMENTAL)** | *Without tool interoperability, the agent is trapped in a closed, frozen sandbox.* |
| **13** | **Git Worktrees** | ✗ | ✓ | ✗ | **NO (IMPLEMENTATION)** | *Worktrees are Codex's specific solution for parallel code branches; not needed for non-git tasks.* |
| **14** | **`AGENTS.md` / `CLAUDE.md`** | ✗ | ✓ | ✓ | **NO (IMPLEMENTATION)** | *Specific markdown filenames are file-level conventions; the fundamental capability is "Persistent Instructions".* |
| **15** | **JSON-RPC App-Server** | ✗ | ✓ | ✗ | **NO (IMPLEMENTATION)** | *JSON-RPC is an IPC wire protocol choice; WebSockets, gRPC, or async queues solve the same transport problem.* |
| **16** | **Screen Interaction / Computer Use** | ✓ | ✗ | ✗ | **NO (IMPLEMENTATION)** | *Direct UI pixel clicking is a high-friction fallback when APIs/CLI connectors are absent.* |

---

## 🧬 Summary of True Fundamental Agentic Primitives

From this hostile evaluation, exactly **12 True Fundamental Primitives** emerge:

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    THE 12 FUNDAMENTAL AGENTIC WORKBENCH PRIMITIVES              │
├─────────────────────────┬───────────────────────────────────────────────────────┤
│ 1. Execution Engine     │ Multi-step tool-invoking loop driving reality state   │
│ 2. Asynchronous Runner  │ Decoupled runner surviving UI/client disconnections   │
│ 3. State Persistence    │ Authoritative state ledger + atomic checkpointing     │
│ 4. Step Observability   │ Transparent step narration, tool telemetry & reasoning│
│ 5. Mid-Flight Steering  │ Human pause, abort, message injection & direction     │
│ 6. Deterministic Policy │ Hard approval gates for irreversible/risky mutations  │
│ 7. Context Isolation    │ Sub-agents running in dedicated unpolluted contexts   │
│ 8. Verification Loop    │ Feedback loops (tests, linters, semantic assertions)  │
│ 9. Concrete Deliverable │ Real files written to workspace / disk                │
│ 10. Context Compaction  │ Pruning, summarization & handoff across token limits  │
│ 11. Epistemic Guard     │ Explicit flagging of omissions, gaps & missing sources│
│ 12. Extensible Tools    │ Dynamic tool registry & standard protocol (e.g. MCP)  │
└─────────────────────────┴───────────────────────────────────────────────────────┘
```
