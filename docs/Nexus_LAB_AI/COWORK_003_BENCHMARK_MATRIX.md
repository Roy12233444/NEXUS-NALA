# 🔬 NALA Architecture Benchmark Synthesis — COWORK #003 (Part C)
**Topic:** Tri-System Comparative Matrix (Claude Cowork vs. OpenAI Codex vs. Anthropic Claude Code)  
**Primary Sources:** Official Anthropic & OpenAI Documentation (Extracted & Recursively Inspected)  
**Status:** 🟢 **BENCHMARK COMPLETE (LOCKED FOR NEXT STAGE)**  

---

## 🧭 Source Boundary & Research Methodology
* **Cowork Primary Sources:** `claude-co-work.pdf` + Official Support Articles (`13364135`, `14128542`, `13854387`, `14116274`).
* **Codex Primary Sources:** OpenAI Developer Docs, Codex App-Server JSON-RPC specs, `AGENTS.md` specs.
* **Claude Code Primary Sources:** `code.claude.com` (Sub-agents, Hooks, Permissions, Skills, Plugins).
* **Strict Discipline:** Evidence classified as 🟢 `DOCUMENTED`, 🟡 `ENGINEERING INFERENCE`, ⚪ `UNKNOWN`. No NALA design decisions or code modifications are made in this document.

---

## 📊 Comprehensive 22-Dimension Cross-System Benchmark Matrix

| # | Dimension | Claude Cowork (Knowledge Work) | OpenAI Codex (Coding Center) | Anthropic Claude Code (CLI/IDE) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Mental Model** | Knowledge worker outcome assistant; cross-app research & synthesis. | Multi-agent software engineering command center across repos. | Terminal/IDE autonomous developer loop with deep tool execution. |
| **2** | **Unit of Work** | **Task / Project Run** (Outcome-oriented). | **Task / Thread** bound to a Git Worktree. | **Session / Turn** with sub-agent runs. |
| **3** | **Goal Representation** | Natural language outcome + folder context + templates. | Natural language issue/task + `AGENTS.md` + `PLANS.md`. | Natural language prompt + slash commands + `CLAUDE.md`. |
| **4** | **Planning** | Early plan sharing recommended for user alignment. | Structured multi-file implementation plan before edits. | Upfront planning mode with architecture exploration. |
| **5** | **Execution Loop** | Step narration with reasoning + tool calls (MCP/Browser/Screen). | Bidirectional JSON-RPC agent loop via Codex App-Server. | Model-tool loop with deterministic pre/post lifecycle hooks. |
| **6** | **Long-Running Execution** | Runs asynchronously; user can close window or step away. | Executes in background worktrees across concurrent tasks. | Multi-turn long sessions with background bash daemons. |
| **7** | **Progress Visibility** | Live step walkthrough + surfaced thought reasoning. | Real-time tool stream, command outputs, diff reviews. | Step headers, tool inputs/outputs, live stdout/stderr streams. |
| **8** | **User Steering** | Mid-task course correction & in-place conversation editing. | Pause, abort, or inject steering messages into active thread. | Interactive interrupt (`Ctrl+C`), message injection, hook gates. |
| **9** | **User Absence** | Persisted cloud execution; returns to finished deliverables. | Asynchronous background worktrees; notifies on completion. | Headless execution mode (`claude -p`) or background terminal. |
| **10** | **Sub-Agents** | Spun up automatically for complex multi-part tasks. | Concurrent parallel agents running in separate git worktrees. | First-class subagents with isolated context windows & tools. |
| **11** | **Skills / Playbooks** | Step-by-step markdown playbooks in plugin bundles. | Framework/lint instructions in `AGENTS.md` and custom skills. | `SKILL.md` playbooks dynamically loaded on demand. |
| **12** | **Tools & MCP** | Native MCP connectors (Slack, Drive, Gmail, Asana, GitHub). | Native MCP integration for developer APIs & issue trackers. | Native MCP client connecting local and remote servers. |
| **13** | **Files & Artifacts** | Real files on disk (`.md`, `.xlsx` formulas, `.pptx` slides). | Physical Git worktrees with unified reviewable diffs. | Direct workspace edits with syntax check and diff view. |
| **14** | **Permissions** | Read vs Write risk model; hard stops on delete, email, pay. | Tiered profiles (`read-only`, `workspace-write`, `danger`). | Declarative allow/deny rules + interactive prompt gates. |
| **15** | **Sandboxing** | Cloud container + local desktop folder scope grant. | Sandboxed local command execution with network limits. | Workspace-scoped sandbox with elevation prompts. |
| **16** | **Uncertainty & Gaps** | Upfront clarifying questions; flags ambiguity & silence. | Halts and prompts user when specs/files conflict. | Asks clarifying questions; avoids guessing missing paths. |
| **17** | **Verification** | Human review before shipping; formula check in Office. | Auto-executes project test suites (`pytest`, `npm test`). | Automatic verification loops (linters, typecheck, tests). |
| **18** | **Completion** | Persisted files on disk + inline citations to sources. | Passing tests + clean unified diff ready for commit/PR. | Summary walkthrough + test pass confirmation + diffs. |
| **19** | **Memory & Continuity** | Project-scoped memory accumulated across sessions. | Directory-level `AGENTS.md` + per-thread history. | `CLAUDE.md` memory + `/compact` context window compaction. |
| **20** | **Handoff** | Handoff to Claude Code for production repository work. | Integrations with IDEs (VS Code, JetBrains), CLI, PR reviews. | Terminal CLI, IDE extensions, GitHub PR integration. |
| **21** | **Project / Workspace** | Dedicated project workspaces with local folder bindings. | Multi-repository workspace with independent worktrees. | `.claude/` root with project `settings.json` & plugins. |
| **22** | **Automation** | Scheduled recurring tasks running remotely on cadence. | CI/CD automated triggers, PR bots, `codex exec`. | **Deterministic Lifecycle Hooks** (`Session`, `Turn`, `Tool`). |

---

## 🧠 Strategic Answers to the 7 Core Architectural Questions

### 1. What is the fundamental unit of work?
* **Cowork:** The **Outcome Deliverable** (e.g. a synthesized research brief, a comparison spreadsheet).
* **Codex:** The **Task Branch / Worktree** (an isolated git working tree solving an issue).
* **Claude Code:** The **Agentic Turn / Session** (a verified loop of tool execution and code edits).

### 2. What makes the work persistent?
* **Cowork:** Real files saved to local disk + project-scoped memory + remote cloud session ledger.
* **Codex:** Git branches/worktrees on disk + JSON-RPC thread state maintained by `codex app-server`.
* **Claude Code:** Filesystem state on disk + session logs + `CLAUDE.md` repository guidelines.

### 3. What does the user observe?
* **Cowork:** Step-by-step narration, surfaced reasoning, plan drafts, citations, and generated documents.
* **Codex:** Agent planning blocks, tool execution stream, terminal outputs, and reviewable unified diffs.
* **Claude Code:** Detailed CLI/IDE stream showing tool inputs, live stdout/stderr, diff snippets, and test outputs.

### 4. What can the user control?
* **Cowork:** Plan shaping upfront, mid-flight course-correction, in-place iteration, and permission gates (delete, email, pay).
* **Codex:** Pause/abort, thread message injection, approval queues, and worktree merge/discard.
* **Claude Code:** Direct interrupt (`Ctrl+C`), message injection, interactive permission prompts, and deterministic `PreToolUse` blocking hooks.

### 5. How does the system manage complexity?
* **Cowork:** Automated sub-agent decomposition, plugin skill bundling, and MCP connectors.
* **Codex:** Concurrent agents in isolated Git worktrees, `PLANS.md` breakdowns, and MCP tools.
* **Claude Code:** Sub-agents in **isolated context windows**, `SKILL.md` playbooks, and MCP server integrations.

### 6. How does it verify work?
* **Cowork:** Explicit human verification before shipping ("Review before you ship") + document citations.
* **Codex:** Automated execution of repository test runners inside the worktree before marking task complete.
* **Claude Code:** Automated verification loops executing linters, typecheckers, and unit tests post-edit.

### 7. How does continuity work?
* **Cowork:** Scoped project memory across tasks + in-place conversational editing.
* **Codex:** `AGENTS.md` instructions + persistent thread state + worktree preservation.
* **Claude Code:** `CLAUDE.md` guidelines + context compaction (`/compact`) + persistent session history.

---

## ⚙️ Universal Agentic Architecture Primitives Mapped

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   UNIVERSAL AGENTIC WORKBENCH RUNTIME PRIMITIVES                 │
├────────────────────────────┬─────────────────────────────────────────────────────┤
│ 1. Execution Engine        │ Detached runner / App-Server (JSON-RPC or daemon)   │
│ 2. Isolation Sandbox       │ Git Worktree (Code) / Temporary Container (Cloud)   │
│ 3. Sub-Agent Fabric        │ Isolated Context Windows with Scoped Tool Access    │
│ 4. Deterministic Shell     │ Pre/Post Tool Hooks & Hard Approval Gateways        │
│ 5. Memory & Context        │ Root Guidelines (AGENTS.md/CLAUDE.md) + Compaction  │
│ 6. Verification Engine     │ Post-Edit Test/Lint Feedback Loops                  │
│ 7. Persistence Layer       │ Tangible Files on Disk + Thread / Session Ledger    │
└────────────────────────────┴─────────────────────────────────────────────────────┘
```

---

## 🛑 Research Status & Verification Checklist

- [x] Official Codex sources identified (`openai.com`, developer specs)
- [x] Official Claude Code sources identified (`code.claude.com`, `docs.claude.com`)
- [x] Relevant sublinks extracted & recursively inspected
- [x] Official-domain boundary strictly enforced
- [x] Codex observations complete (`docs/Nexus_LAB_AI/COWORK_003_CODEX_OBSERVATION.md`)
- [x] Claude Code observations complete (`docs/Nexus_LAB_AI/COWORK_003_CLAUDE_CODE_OBSERVATION.md`)
- [x] Identical 22 observation dimensions used across all systems
- [x] Documented facts strictly separated from engineering inferences
- [x] Unknowns and non-claims explicitly designated
- [x] Skills, Sub-agents, Hooks, Permissions, Worktrees, and Verification deeply analyzed
- [x] Cross-system benchmark matrix created (`docs/Nexus_LAB_AI/COWORK_003_BENCHMARK_MATRIX.md`)
- [x] Zero NALA code modified
- [x] Zero NALA UI modified
- [x] No NALA architecture decisions made (locked for next phase)

---

```text
================================================
COWORK #003 CODEX + CLAUDE CODE BENCHMARK
================================================
SOURCE RESEARCH:            🟢 COMPLETE
OFFICIAL LINK ANALYSIS:     🟢 COMPLETE
CODEX OBSERVATION:          🟢 COMPLETE
CLAUDE CODE OBSERVATION:    🟢 COMPLETE
CROSS-SYSTEM MATRIX:        🟢 COMPLETE
NALA DESIGN DECISIONS:      🔒 NOT YET PERFORMED
NALA CODE CHANGES:          0
NALA UI CHANGES:            0
NEXT RESEARCH STAGE:        CROSS-SYSTEM SYNTHESIS & NALA DERIVATION
================================================
```
