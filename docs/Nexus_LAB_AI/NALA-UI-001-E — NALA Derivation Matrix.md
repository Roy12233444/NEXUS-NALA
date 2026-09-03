# 🔬 NALA Architecture Research Notebook — NALA-UI-001-E
**Title:** NALA Derivation Matrix (ADOPT / ADAPT / REJECT / INVENT)  
**Methodology:** Evidence-Based Strategic Classification  
**Status:** 🟢 **DERIVATION COMPLETE (LOCKED FOR WORKBENCH DERIVATION)**  

---

## 🧭 Strategic Classification System
Every candidate capability discovered during research is classified into exactly one of four decisive buckets:

* 🟢 **`ADOPT`**: Fundamental industry patterns adopted as-is because they are universally necessary.
* 🔵 **`ADAPT`**: Valuable capabilities adapted to fit NALA's specific state/harness architecture.
* 🔴 **`REJECT`**: Features discarded because they are redundant, fragile, or inappropriate for NALA.
* 🟣 **`INVENT`**: Unique, differentiated NALA primitives born from our runtime state, checkpointing, and safety governor.

---

## 📊 Comprehensive NALA Derivation Table

| Capability / Feature | Decision | Originating Systems | NALA Architectural Rationale |
| :--- | :---: | :--- | :--- |
| **Real-Time Step & Thought Observability** | 🟢 **ADOPT** | Cowork, Codex, Claude Code | Essential for human trust during multi-step runs. UI must stream step narration, reasoning, and tool telemetry. |
| **Model Context Protocol (MCP) Client** | 🟢 **ADOPT** | Cowork, Codex, Claude Code | Industry standard for tool and external resource connectivity without vendor lock-in. |
| **Automated Verification Loops** | 🟢 **ADOPT** | Codex, Claude Code | Validating code/data with tests and linters post-edit prevents error accumulation. |
| **Physical Workspace Artifact Output** | 🟢 **ADOPT** | Cowork, Codex, Claude Code | Tangible files saved to disk (`.md`, `.py`, `.xlsx`) provide persistent value outside the chat stream. |
| **Persistent Project Instructions** | 🔵 **ADAPT** | Codex (`AGENTS.md`), Claude Code (`CLAUDE.md`) | Instead of ad-hoc markdown files, NALA adapts this into a structured **Project Context Contract** + `MEMORY.md`. |
| **Sub-Agent Context Isolation** | 🔵 **ADAPT** | Cowork, Claude Code | Adapted into NALA sub-worker threads that execute isolated task steps and report back through `TaskEvent.subagent_id`. |
| **Context Window Compaction** | 🔵 **ADAPT** | Claude Code (`/compact`) | Adapted into NALA's native `DronagiriCompactor` and `HandoffSpore` for automated token paging. |
| **Multi-Tiered Permission Model** | 🔵 **ADAPT** | Cowork, Codex, Claude Code | Adapted into NALA's `APPROVAL_REQUESTED` state machine gated by the Satya/Ṛta safety layer. |
| **Mandatory Git Worktree Isolation** | 🔴 **REJECT** | OpenAI Codex | Unnecessary overhead for non-git, research, analysis, and system administration workflows. Workspace folder isolation is sufficient. |
| **Screen Interaction / Computer Use** | 🔴 **REJECT** | Claude Cowork | Low reliability, high latency, and high error rate compared to native API connectors, CLI execution, and headless browsers. |
| **Chat-Only Ephemeral UI Shell** | 🔴 **REJECT** | Traditional Chatbots | A pure chat interface cannot represent DAG task graphs, background checkpoint lineages, or active approval queues. |
| **Checkpoint Lineage & Recovery Timeline** | 🟣 **INVENT** | Unique to NALA | Exposing NALA's LSN checkpoint ledger in the UI so users can inspect execution history, rewind, and resume from past states. |
| **Ṛta / Satya Safety Resonance Gauge** | 🟣 **INVENT** | Unique to NALA | Visual projection of real-time epistemic truthfulness and cognitive safety scores computed by `RtaGovernor` and `ContextAwareSatyaLayer`. |
| **Cognitive Provenance & Evidence Linking** | 🟣 **INVENT** | Unique to NALA | Every committed state transition in `state.py` links actor, reason, and empirical evidence references directly in the UI. |
| **Detached Session Reconnection Playback** | 🟣 **INVENT** | Unique to NALA | When a user reconnects after stepping away, the UI streams a compact playback of background milestones, checkpoints, and completed steps. |

---

## 🧬 Architectural Value Matrix

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           THE FOUR QUADRANTS OF NALA                            │
├─────────────────────────────────────────┬───────────────────────────────────────┤
│ 🟢 ADOPT (The Universal Standard)       │ 🔵 ADAPT (The NALA Translation)       │
│ • Live Step & Thought Stream            │ • Project Context & Memory Contracts  │
│ • Standard MCP Client Registry          │ • Context-Isolated Sub-Agent Workers  │
│ • Post-Step Verification Loops          │ • Dronagiri Vector Context Compaction │
│ • Concrete File Artifact Persistence    │ • Satya-Governed Approval Gateways    │
├─────────────────────────────────────────┼───────────────────────────────────────┤
│ 🔴 REJECT (The Clutter We Avoid)        │ 🟣 INVENT (The NALA Moat)             │
│ • Fragile Pixel Screen Clicking         │ • Checkpoint Lineage & State Timeline │
│ • Compulsory Git Worktree Complexity    │ • Ṛta / Satya Safety Resonance Gauge  │
│ • Ephemeral Chat-Only Shells            │ • State Transition Cognitive Provenance│
│ • Mock Timers & Fake Simulations        │ • Reconnection Milestone Playback     │
└─────────────────────────────────────────┴───────────────────────────────────────┘
```
