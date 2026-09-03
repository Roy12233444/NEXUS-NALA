# 🔬 NALA Architecture Research Notebook — COWORK #003 (Part B)
**System:** Anthropic Claude Code  
**Topic:** Claude Code Forensic Benchmark Audit  
**Primary Sources:** Official Anthropic Claude Code Documentation (`code.claude.com`, `docs.claude.com`)  
**Status:** 🟢 **OBSERVATION COMPLETE (LOCKED FOR NEXT STAGE)**  

---

## 🧭 Source Boundary & Epistemic Principles
* **Primary Source Domain:** `code.claude.com`, `docs.claude.com`, `anthropic.com`.
* **Corroborated Official Sources:**
  * *Claude Code Architecture & Overview* (`code.claude.com/docs/en/architecture`)
  * *Sub-Agents Architecture Specification* (`code.claude.com/docs/en/sub-agents`)
  * *Hooks Lifecycle Specification* (`code.claude.com/docs/en/hooks`)
  * *Permissions & Sandboxing Guide* (`code.claude.com/docs/en/permissions`)
  * *Skills & Plugin Bundling* (`code.claude.com/docs/en/skills`, `code.claude.com/docs/en/plugins`)
* **Evidence Classification:**
  * 🟢 **`DOCUMENTED`**: Explicitly stated in official sources.
  * 🟡 **`ENGINEERING INFERENCE`**: Deductions regarding runtime and UI primitives necessary to deliver the documented behavior.
  * ⚪ **`UNKNOWN — NOT DOCUMENTED IN SOURCE`**: Unstated internal mechanisms.
  * 🔴 **`DO NOT CLAIM`**: Unsubstantiated claims about private server architectures.

---

## 🔬 22-Dimension Forensic Audit — Anthropic Claude Code

### 1️⃣ Mental Model
- 🟢 **`DOCUMENTED`**: Claude Code is an **agentic engineering workbench and CLI** that operates directly inside the developer's terminal, filesystem, and IDE. It executes a full agent loop: reasoning, invoking tools, modifying source code, running build/test commands, and iterating until the task is verified.

### 2️⃣ Unit of Work
- 🟢 **`DOCUMENTED`**: The fundamental unit of work is the **Agentic Session / Turn**, within which the agent executes multi-step tool call sequences and can spawn isolated **Sub-Agent Runs**.

### 3️⃣ Goal / Task Representation
- 🟢 **`DOCUMENTED`**: Tasks are submitted as natural language requests, slash commands (e.g. `/review`, `/test`), or headless batch prompts (`claude -p "..."`). Standing project context is loaded from `CLAUDE.md` and `.claude/` directories.

### 4️⃣ Planning & Plan Review
- 🟢 **`DOCUMENTED`**: Claude Code supports dedicated planning modes where it explores the codebase, forms a structured technical plan, and can pause for user validation before executing destructive code modifications.

### 5️⃣ Execution Loop & Tool Use
- 🟢 **`DOCUMENTED`**: Follows a strict model-tool loop:
  `Prompt / Context ──► Model Thought ──► Tool Call (PreToolUse Hook) ──► Tool Execution ──► Tool Result (PostToolUse Hook) ──► Next Step / Completion`.
  Built-in tools include `Bash`, `FileEdit`, `FileWrite`, `ViewFile`, `Grep`, `Glob`, and `MCP` tools.

### 6️⃣ Long-Running & Async Behavior
- 🟢 **`DOCUMENTED`**: Sessions can execute long sequences of tool actions. Supports asynchronous background bash commands, long-running dev servers, and persistent session state.

### 7️⃣ Progress Visibility & Feedback Granularity
- 🟢 **`DOCUMENTED`**: Rich terminal and IDE output displaying step headers, tool call parameters, live stdout/stderr streams, diff snippets, and reasoning blocks.

### 8️⃣ User Steering & Mid-Flight Control
- 🟢 **`DOCUMENTED`**: Users can interrupt active tool loops (`Ctrl+C` / escape), inject steering messages, or configure `PreToolUse` hooks to intercept and block actions dynamically.

### 9️⃣ User Absence & Background Execution
- 🟢 **`DOCUMENTED`**: Can execute headlessly via CLI flags or run in background terminal multiplexers. When completed, outputs exit codes and artifact summaries.

### 🔟 Sub-Agents & Parallel Workers
- 🟢 **`DOCUMENTED`**: First-class **Sub-Agents** (`code.claude.com/docs/en/sub-agents`).
  - Runs in an **isolated context window** to prevent main conversation context bloat.
  - Configured with a **custom system prompt**, **scoped tool access**, and **independent permissions**.
  - Sub-agents report synthesized results back to the primary orchestrator.

### 1️⃣1️⃣ Skills / Playbooks
- 🟢 **`DOCUMENTED`**: Extensible via `SKILL.md` files located in project or plugin `skills/` directories. Skills provide specialized prompt instructions and tool combinations loaded on demand when relevant.

### 1️⃣2️⃣ Tools & MCP / Connectors
- 🟢 **`DOCUMENTED`**: Full **Model Context Protocol (MCP)** client support. Can connect to local or remote MCP servers to expose external databases, issue trackers, and third-party APIs.

### 1️⃣3️⃣ Files, Worktrees & Artifacts
- 🟢 **`DOCUMENTED`**: Directly reads, edits, and creates files in the workspace. Formats changes as diffs and validates syntax before committing changes.

### 1️⃣4️⃣ Permissions & Approval Gates
- 🟢 **`DOCUMENTED`**: Three-tier permission architecture:
  - Declarative allow/deny rules (e.g. auto-approve read tools, prompt on write tools).
  - Interactive approval prompts when an unapproved tool is requested.
  - Sub-agents inherit or scope parent permissions.

### 1️⃣5️⃣ Sandboxing, Security & Network Access
- 🟢 **`DOCUMENTED`**: Commands run within the local workspace directory. Risky operations (network calls, external system changes) trigger permission confirmation gates.

### 1️⃣6️⃣ Uncertainty, Gaps & Ambiguity Handling
- 🟢 **`DOCUMENTED`**: When specifications are ambiguous or requirements incomplete, Claude Code halts and asks clarifying questions rather than guessing.

### 1️⃣7️⃣ Verification & Testing
- 🟢 **`DOCUMENTED`**: Core engineering philosophy revolves around **verification loops**: after making edits, Claude Code automatically runs project linters, typecheckers, and test suites (e.g. `npm test`, `pytest`, `cargo test`) to confirm fixes.

### 1️⃣8️⃣ Completion & Review
- 🟢 **`DOCUMENTED`**: Completes tasks by providing a concise summary of changes, modified files, test output validation, and git status.

### 1️⃣9️⃣ Memory, Context Compaction & Continuity
- 🟢 **`DOCUMENTED`**:
  - Standing repository memory via `CLAUDE.md`.
  - Context window management via automatic and manual `/compact` compaction.
  - Hook lifecycle tracking on compaction events.

### 2️⃣0️⃣ Handoff & Integrations
- 🟢 **`DOCUMENTED`**: Seamless handoff from Claude Cowork (Cowork offers to launch Claude Code when repository engineering work is detected); IDE extensions (VS Code, JetBrains).

### 2️⃣1️⃣ Project / Workspace Model
- 🟢 **`DOCUMENTED`**: Project root anchored by `.claude/` directory, containing `settings.json`, hooks, skills, and custom subagents.

### 2️⃣2️⃣ Automation & Lifecycle Hooks
- 🟢 **`DOCUMENTED`**: **Deterministic Hook Lifecycle** (`code.claude.com/docs/en/hooks`):
  - **Session Cadence:** `SessionStart`, `SessionEnd`.
  - **Turn Cadence:** `UserPromptSubmit`, `Stop`, `StopFailure`.
  - **Tool Cadence:** `PreToolUse` (can block execution by exiting with code `2`), `PostToolUse` (fires after success for formatting/auditing).

---

## ⚙️ Architectural Implication Analysis (Claude Code)

| Feature | Behavior | User Problem Solved | Runtime Implication | UI Implication |
| :--- | :--- | :--- | :--- | :--- |
| **Deterministic Hooks** | `PreToolUse` & `PostToolUse` shell triggers | Strict policy enforcement and automated post-edit formatting | Runtime must execute synchronous hook before and after tool calls | Tool call badge shows pre/post hook execution status |
| **Sub-Agent Isolation** | Independent context window per sub-worker | Context window exhaustion during large code searches | Must spawn isolated LLM conversation threads with pruned tools | Nested/indented sub-agent progress block in UI stream |
| **Verification Loop** | Auto-executing test runners post-edit | Broken code committed without validation | Runtime executes test commands and inspects exit code/stderr | Test execution status pill (green check / red fail) |
| **Context Compaction** | `/compact` memory summarization | Session truncation during long-running tasks | Summarization pipeline that condenses historical turns | Visual compaction indicator in conversation stream |
