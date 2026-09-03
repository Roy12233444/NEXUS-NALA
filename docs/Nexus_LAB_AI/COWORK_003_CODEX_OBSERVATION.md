# 🔬 NALA Architecture Research Notebook — COWORK #003 (Part A)
**System:** OpenAI Codex (Codex App, Codex App-Server, Codex CLI)  
**Topic:** Codex Ecosystem Forensic Benchmark Audit  
**Primary Sources:** Official OpenAI Developer Documentation, OpenAI Product Announcements, Codex Client Protocol & App-Server Specifications  
**Status:** 🟢 **OBSERVATION COMPLETE (LOCKED FOR NEXT STAGE)**  

---

## 🧭 Source Boundary & Epistemic Principles
* **Primary Source Domain:** `openai.com`, `developers.openai.com`, `help.openai.com`.
* **Corroborated Official Sources:**
  * *OpenAI Codex Overview & Platform Documentation* (`developers.openai.com/codex`)
  * *Introducing the Codex App* (`openai.com/index/introducing-the-codex-app`)
  * *Codex App-Server JSON-RPC Protocol & Harness Specification*
  * *Codex Agent Configuration & `AGENTS.md` Specification*
* **Evidence Classification:**
  * 🟢 **`DOCUMENTED`**: Explicitly stated in official sources.
  * 🟡 **`ENGINEERING INFERENCE`**: Deductions regarding runtime and UI primitives necessary to deliver the documented behavior.
  * ⚪ **`UNKNOWN — NOT DOCUMENTED IN SOURCE`**: Unstated internal mechanisms.
  * 🔴 **`DO NOT CLAIM`**: Unsubstantiated claims about private server architectures.

---

## 🔬 22-Dimension Forensic Audit — OpenAI Codex

### 1️⃣ Mental Model
- 🟢 **`DOCUMENTED`**: Codex is positioned as an **autonomous multi-agent coding command center**. Rather than a single chatbot window, Codex acts as an orchestrator managing multiple coding agents operating concurrently across local and remote repositories.
- 🟡 **`ENGINEERING INFERENCE`**: The mental model shifts the developer from "authoring code with an autocomplete assistant" to "managing a team of asynchronous junior developers and reviewing their worktrees".

### 2️⃣ Unit of Work
- 🟢 **`DOCUMENTED`**: The fundamental unit of work is the **Task / Thread bound to a Git Worktree**. Each task represents a distinct objective (e.g. "Migrate auth to JWT", "Fix flaky test in CI") tied to an isolated branch or worktree.
- 🟡 **`ENGINEERING INFERENCE`**: Task isolation prevents git index locks and branch collision when multiple tasks run concurrently.

### 3️⃣ Goal / Task Representation
- 🟢 **`DOCUMENTED`**: Tasks are submitted as natural language objectives, optionally referencing specific files, issues, or PRs. Stable instructions are loaded from `AGENTS.md` (root and directory level) or `~/.codex/AGENTS.md`.
- 🟢 **`DOCUMENTED`**: Long-term implementation goals are organized by referencing structured plan files (e.g. `PLANS.md`).

### 4️⃣ Planning & Plan Review
- 🟢 **`DOCUMENTED`**: Codex constructs an internal implementation plan before executing multi-file edits and tool calls.
- 🟡 **`ENGINEERING INFERENCE`**: The planning step is exposed in the UI as collapsible step-by-step progress lists allowing early developer review before destructive file modifications.

### 5️⃣ Execution Loop & Tool Use
- 🟢 **`DOCUMENTED`**: Powered by the **Codex Harness** and **App-Server**. The agent runs a bidirectional JSON-RPC loop: receiving turn context, executing shell commands, file edits, ripgrep searches, and streaming status notifications back to the client.

### 6️⃣ Long-Running & Async Behavior
- 🟢 **`DOCUMENTED`**: Codex tasks are long-running and can execute asynchronously in the background. The developer can switch away or launch additional tasks while an active task is running.
- 🟡 **`ENGINEERING INFERENCE`**: Long-running execution is decoupled from the UI process; the local `codex app-server` maintains task state over JSON-RPC.

### 7️⃣ Progress Visibility & Feedback Granularity
- 🟢 **`DOCUMENTED`**: The UI streams real-time tool execution logs, file diffs, command outputs, and agent thoughts/narration.
- 🟢 **`DOCUMENTED`**: The App-Server protocol emits structured notification events for each step boundary.

### 8️⃣ User Steering & Mid-Flight Control
- 🟢 **`DOCUMENTED`**: Users can pause execution, send steering messages into the active thread, or abort the run.
- 🟢 **`DOCUMENTED`**: Approval queues allow developers to inspect and approve/deny actions before they run.

### 9️⃣ User Absence & Background Execution
- 🟢 **`DOCUMENTED`**: Tasks run locally or in cloud sessions without requiring active focus. When completed, tasks notify the user with ready diffs.
- 🟡 **`ENGINEERING INFERENCE`**: State is persisted on disk (worktree branches + thread logs) so UI restarts cleanly reconnect to in-progress or finished tasks.

### 🔟 Sub-Agents & Parallel Workers
- 🟢 **`DOCUMENTED`**: Codex natively supports **parallel agents running simultaneously**.
- 🟢 **`DOCUMENTED`**: To prevent "merge soup", each concurrent agent operates inside an isolated Git worktree checkout.

### 1️⃣1️⃣ Skills / Playbooks
- 🟢 **`DOCUMENTED`**: Supports modular skills and custom instructions extending capabilities for specific workflows, frameworks, or lint rules.

### 1️⃣2️⃣ Tools & MCP / Connectors
- 🟢 **`DOCUMENTED`**: Integrates with the **Model Context Protocol (MCP)** to connect external databases, issue trackers (GitHub, Jira), and developer APIs.
- 🟢 **`DOCUMENTED`**: Standard toolsuite includes bash command execution, file read/write/edit, grep/glob search.

### 1️⃣3️⃣ Files, Worktrees & Artifacts
- 🟢 **`DOCUMENTED`**: Uses Git worktrees as physical file sandboxes.
- 🟢 **`DOCUMENTED`**: Code changes are presented as reviewable unified diffs. The CLI provides `codex apply` to merge diffs generated from cloud chats into local working trees.

### 1️⃣4️⃣ Permissions & Approval Gates
- 🟢 **`DOCUMENTED`**: Least-privilege model with configurable permission profiles:
  - `read-only`: Agent can inspect code but cannot write or execute unsafe scripts.
  - `workspace-write`: Agent can modify files within the repo workspace.
  - `danger-full-access`: Full access with network/shell execution.
- 🟢 **`DOCUMENTED`**: Sensitive shell commands or actions outside the workspace trigger explicit interactive approval prompts in the UI approval queue.

### 1️⃣5️⃣ Sandboxing, Security & Network Access
- 🟢 **`DOCUMENTED`**: Local execution is sandboxed with restricted filesystem and network rules. Out-of-sandbox actions require explicit user elevation.

### 1️⃣6️⃣ Uncertainty, Gaps & Ambiguity Handling
- 🟢 **`DOCUMENTED`**: When instructions conflict or files are missing, Codex stops and prompts the user via the JSON-RPC thread rather than hallucinating paths.

### 1️⃣7️⃣ Verification & Testing
- 🟢 **`DOCUMENTED`**: Codex executes automated test suites (e.g. `pytest`, `npm test`, `cargo test`) within the worktree to verify fixes before declaring completion.

### 1️⃣8️⃣ Completion & Review
- 🟢 **`DOCUMENTED`**: A task is complete when code passes verification and diffs are generated. The UI presents a dedicated side-panel review view for one-click commit, PR creation, or rejection.

### 1️⃣9️⃣ Memory, Context Compaction & Continuity
- 🟢 **`DOCUMENTED`**: Repository-level memory is anchored via `AGENTS.md` files. Session history is maintained per-thread with context window compaction during extended runs.

### 2️⃣0️⃣ Handoff & Integrations
- 🟢 **`DOCUMENTED`**: Integrates with IDEs (VS Code extension, JetBrains), terminal CLI (`codex`), desktop apps, and GitHub PR workflows.

### 2️⃣1️⃣ Project / Workspace Model
- 🟢 **`DOCUMENTED`**: Multi-repository workspace support. Each repository has its own root configuration, `AGENTS.md`, and independent worktree branches.

### 2️⃣2️⃣ Automation & Scheduled Runs
- 🟢 **`DOCUMENTED`**: Supports CI/CD automated triggers, PR review bots, and headless batch script execution via `codex exec`.

---

## ⚙️ Architectural Implication Analysis (Codex)

| Feature | Behavior | User Problem Solved | Runtime Implication | UI Implication |
| :--- | :--- | :--- | :--- | :--- |
| **Git Worktrees** | Multi-agent parallel checkout | Agents overwriting each other's uncommitted edits | Must manage git worktree lifecycles and branch cleanups | Multi-tab / multi-column worktree status indicators |
| **JSON-RPC App Server** | Bidirectional client/server protocol | Decoupling heavy agent runner from lightweight IDE/UI | Persistent daemon process with structured event streams | Reactive UI components updating on event notifications |
| **Permission Profiles** | Tiered sandbox (`read-only` to `workspace-write`) | Security risk of untrusted scripts or prompt injection | Sandbox execution boundary enforcing filesystem limits | Approval badge & interactive confirmation modal queue |
| **`AGENTS.md`** | Hierarchical standing project rules | Repetitive prompt explanations across sessions | Agent walks directory tree to load instructions | Visual project settings / rule inspector |
