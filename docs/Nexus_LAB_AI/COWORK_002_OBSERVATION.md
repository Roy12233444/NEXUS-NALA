# 🔬 NALA Architecture Research Notebook — COWORK #002 (Enriched)
**Topic:** Long-Running Execution & User Control  
**Source Document:** `docs/Nexus_LAB_AI/claude-co-work.pdf` (Pages 7–8, 13–18) + Official Anthropic Documentation Links  
**Status:** 🟢 **OBSERVATION & LINK ANALYSIS COMPLETE (LOCKED FOR NEXT STAGE)**  

---

## 🧭 Source Boundary & Epistemic Principles
* **Primary Source:** `claude-co-work.pdf` (Anthropic Official Product Guide).
* **Directly Corroborated Official Sources (Discovered via Document Links):**
  * `https://support.claude.com/en/articles/13364135-use-cowork-safely` (*Cowork Safety, Read vs. Write Tools, & Deletion Guards*)
  * `https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork` (*Tool Hierarchy, Computer Use & App-by-App Permissions*)
  * `https://code.claude.com/docs/en/sub-agents` (*Sub-Agents Architecture, Context Isolation & Scoped Tools*)
  * `https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork` (*Scheduled Cadences, Remote Cloud Execution & Question-Based Setup*)
  * `https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-cowork` (*Project Scoping, Project-Level Memory & Folder Bindings*)
  * `https://support.claude.com/en/articles/13837440-use-plugins-in-cowork` (*Plugin Toolkits, Skills, Subagents & MCP Declarations*)
* **Strict Discipline:** Documented behaviors from sources are strictly separated from engineering inferences.
* **Non-Documented Areas:** Any internal mechanism not explicitly stated in the source is designated as `UNKNOWN — NOT DOCUMENTED IN SOURCE`.
* **Zero Speculative Code:** No NALA implementation code or architectural assumptions are introduced.

---

## 1️⃣ OBSERVATION — Task is Running (Active Execution)

### Documented Behavior (PDF Page 8, Article 13364135, Article 14128542)
> *"When Claude is working on something in Claude Cowork, you can watch it work or step away. It walks through what it's doing at each step and surfaces its reasoning so you can follow along. If it's heading in the wrong direction, you can jump in mid-task and course-correct. For complex work, it may spin up multiple sub-agents running in parallel."* (PDF Page 8)

### Key Findings:
- **Individual Step Visibility:** Documented. Cowork *"walks through what it's doing at each step"*.
- **Reasoning Disclosure:** Documented. Cowork *"surfaces its reasoning so you can follow along"*.
- **Dual User Presence Modes:** Documented. The user can choose between active observation (*"watch it work"*) or asynchronous detachment (*"step away / close the window"*).
- **Execution Priority Hierarchy (Article 14128542):**
  1. *Connectors (MCP):* Fastest and most reliable path (Slack, Drive, Gmail APIs).
  2. *Browser (Chrome):* Navigates web applications via Claude in Chrome.
  3. *Screen Interaction (Computer Use):* Direct mouse clicks, typing, and desktop navigation (used only as fallback when no connector/browser path exists).

---

## 2️⃣ OBSERVATION — Progress & Transparency

### Documented Behavior (PDF Pages 8, 14, 15, Article 13854387)
- **Granularity of Progress:** Step-by-step narration accompanied by surfaced reasoning and tool actions.
- **Early Plan Visibility:** The guide explicitly recommends: *"If the folder is large, ask Claude Cowork to share its plan before diving in so you can correct course early."* (PDF Page 14).
- **Interactive Setup Dialogues:** For scheduled tasks, Claude asks multiple-choice clarification questions to establish schedule, target, and scope before locking the task (Article 13854387).
- **Sub-Agent Activity Stream:** When large jobs are broken down, Cowork indicates parallel sub-agent execution across distinct tracks (PDF Page 8, 11).
- **Exact Progress Percentages / Timelines:** `UNKNOWN — NOT DOCUMENTED IN SOURCE` (The UI streams step narration and thought blocks rather than a deterministic percentage progress bar).

---

## 3️⃣ OBSERVATION — Course Correction & Mid-Flight Steering

### Documented Behavior (PDF Pages 8, 14, 18)
> *"If it's heading in the wrong direction, you can jump in mid-task and course-correct."* (PDF Page 8)  
> *"Iterate in place rather than starting over. If the first draft is 80% right, tell Claude Cowork what to change. It remembers the conversation and edits faster than it regenerates from scratch."* (PDF Page 18)

### Documented Steering Capabilities:
- **Mid-Task Interruption:** The user can jump in mid-execution to steer or redirect Claude without discarding the session state.
- **Upfront Plan Shaping:** The user can review the proposed plan before execution to alter scope, constraints, or source prioritization.
- **In-Place Iteration:** Post-delivery refinement occurs in place against existing session memory rather than requiring a fresh restart.

---

## 4️⃣ OBSERVATION — User Absence & Asynchronous Execution

### Documented Behavior (PDF Pages 6, 8, 15, Article 13854387)
> *"Long-running work. Work on a task for as long as it takes. Keep the app open and come back to finished work."* (PDF Page 6)  
> *"Tasks can run for a while depending on complexity—monitor them if you want, or close the window and come back when Claude is done."* (PDF Page 8)  
> *"Scheduled tasks run remotely, so they run on their cadence even when your computer is asleep or the Claude Desktop app is closed."* (Article 13854387)

### Asynchronous Lifecycle Model:
```text
User initiates task / scheduled trigger
               │
               ▼
   Autonomous Execution Runs (Cloud / Desktop Agent)
  ┌────────────────────────────────────────┐
  │  Option A: User Watches Live           │
  │  Option B: User Closes Window / Leaves │
  │  Option C: Machine Asleep (Scheduled)  │
  └────────────────────────────────────────┘
               │
               ▼
   Finished Work Persisted (Files / Outputs on Disk or Account)
               │
               ▼
   User Returns & Reviews Finished Deliverables
```

---

## 5️⃣ OBSERVATION — Sub-Agent Parallelism

### Documented Behavior (PDF Pages 6, 8, 11, Article code.claude.com/docs/en/sub-agents)
> *"Sub-agents. Break large tasks into pieces and run them in parallel to streamline work."* (PDF Page 6)  
> *"Subagents: purpose-built assistants for specific kinds of work. Each runs in its own context window with a custom system prompt, specific tool access, and independent permissions."* (PDF Page 11 & Sub-Agents Doc)

### Technical Sub-Agent Properties (from Official Sub-Agents Documentation):
- **Isolated Context Windows:** Prevents primary orchestrator context pollution during heavy searches or large file reviews.
- **Targeted Tool Access:** Each subagent is restricted to specific tools required for its domain (e.g. read-only file search vs API mutations).
- **Custom System Prompts:** Specializes each worker for distinct sub-roles (e.g., contract clause reviewer, code reviewer, researcher).
- **Independent Permissions:** Subagents inherit or hold scoped execution permissions.

---

## 6️⃣ OBSERVATION — Permissions & Human Authority Boundaries

### Documented Behavior (PDF Pages 8, 15, Article 13364135, Article 14128542)
Anthropic explicitly classifies tool execution into two risk categories:
1. **Read Tools:** Reading inboxes, inspecting local files, capturing screen frames (carries prompt-injection risk from untrusted content).
2. **Write Tools:** Mutating environment, deleting files, sending messages, running commands, clicking screen UI (carries operational damage risk).

### Authority & Approval Matrix:

| Action / Operation | Autonomy Mode | Human Confirmation Policy | Source Reference |
| :--- | :--- | :--- | :--- |
| **Folder Access Grant** | Initial Setup | **Explicit initial user grant** (Claude sees 0 local files until granted). | PDF Page 8 |
| **Reading Local Files / Connected Apps** | Standard | Autonomous within granted boundaries. | PDF Page 8, Article 13364135 |
| **Drafting Documents & Spreadsheets** | Standard | Autonomous. | PDF Page 6, 14 |
| **Deleting Local Files** | Protected | **ALWAYS REQUIRES EXPLICIT APPROVAL** (even in auto mode). | PDF Page 8, Article 13364135 |
| **Sending Emails / External Messages** | Protected | **ALWAYS REQUIRES EXPLICIT APPROVAL** on each send. | PDF Page 15, Article 13364135 |
| **Financial / Purchasing Transactions** | Protected | **ALWAYS REQUIRES EXPLICIT CONFIRMATION**. | PDF Page 8, Article 13364135 |
| **Modifying System Files / Captchas** | Protected | **ALWAYS REQUIRES EXPLICIT CONFIRMATION**. | PDF Page 8, Article 13364135 |
| **Computer Use (Screen App Access)** | Protected | **App-by-App explicit user permission prompt**. | Article 14128542 |
| **"Act without asking" Mode Action Screening** | Auto-Approval | Background classifier reviews action; blocks unsafe operations and prompts user. | Article 13364135 |

---

## 7️⃣ OBSERVATION — Uncertainty, Gaps & Clarification

### Documented Behavior (PDF Pages 14, 15, 16)
> *"Claude Cowork will usually ask a clarifying question or two — about audience, length, or which sources to prioritize — before starting."* (PDF Page 14)  
> *"Claude Cowork will flag anywhere the kickoff notes were ambiguous rather than inventing details."* (PDF Page 15)  
> *"Claude Cowork will note where a proposal was silent on a criterion rather than guessing."* (PDF Page 16)

### Epistemic Policies:
1. **Upfront Clarification:** Resolves ambiguities in audience, scope, or prioritization before initiating deep work.
2. **Ambiguity Flagging over Hallucination:** Explicitly lists gaps and contradictions in source documents rather than fabricating details.
3. **Silence Transparency:** Distinguishes between "criterion evaluated as negative" vs "source file was completely silent on this criterion".

---

## 8️⃣ OBSERVATION — Completion & Final Deliverables

### Documented Behavior (PDF Pages 6, 14, 15, 16, Article 14116274)
- **Concrete Deliverable Files:** Work concludes with physical files written to local disk (e.g. `competitive-brief.md`, `weekly-update-2026-04-10.md`, formatted `.xlsx` spreadsheets with working formulas).
- **Inline Grounding:** Markdown and documents feature inline citations linking claims directly back to real local files and messages.
- **Interoperability & Refinement:** Artifacts open directly in Microsoft 365 desktop apps (Claude for Excel, Claude for PowerPoint, Claude for Word).

---

## 9️⃣ OBSERVATION — Blocked States & Inaccessible Resources

### Documented Behavior (PDF Page 14, Article 13364135)
> *"Claude Cowork will tell you if any source was inaccessible — for example, if Gmail isn't connected yet."* (PDF Page 14)

### Behavior on Missing Resources:
- Does not hallucinate mock data or fail silently.
- Transparently emits a status informing the user that a file or connector is inaccessible.
- Suggests connecting the required MCP connector or granting folder access.

---

## 🔟 OBSERVATION — Human Review, Memory & Tool Handoff

### Documented Behavior (PDF Page 18, Article 14116274)
> *"Review before you ship. Claude Cowork accelerates your work; it doesn't replace your judgment. Read what it produces before sending, publishing, or acting on it, especially anything with numbers, names, citations, or financial implications."* (PDF Page 18)  
> *"Know when to hand work off. For production code across a repo, hand off to Claude Code; Claude Cowork itself will offer to launch a Claude Code session when it detects a coding task."* (PDF Page 18)  
> *"Memory in projects: Claude remembers context from tasks you've run in a project and applies it to future tasks in the same project. Memory is scoped to the project."* (Article 14116274)

### Division of Responsibility:
- **Human Role:** Strategic judgment, verification of critical facts/finances, and final send/publish authorization.
- **Cowork Agent Role:** Heavy context synthesis, cross-tool action execution, scoped project memory accumulation, and intelligent handoff routing to specialized repo tools (Claude Code).

---

## 🔄 Behavioral Execution Lifecycle Map

Derived strictly from documented workflows across `claude-co-work.pdf` and official Anthropic support articles:

```text
                  ┌────────────────────────────────────────────┐
                  │           USER SPECIFIES OUTCOME           │
                  └─────────────────────┬──────────────────────┘
                                        │
                         [Clarification / Multi-Choice Q&A]
                                        │
                                        ▼
                  ┌────────────────────────────────────────────┐
                  │            PLANNING & SCOPING              │
                  │   - Share plan early (optional review)     │
                  │   - Bind folder & project memory           │
                  └─────────────────────┬──────────────────────┘
                                        │
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                         MULTI-STEP EXECUTION                           │
    │                                                                        │
    │  ├─ Tool Hierarchy: Connectors (MCP) ──► Browser ──► Computer Use     │
    │  ├─ Narration: Live step walkthrough + surfaced reasoning               │
    │  ├─ Sub-Agents: Parallel isolated contexts for sub-tasks               │
    │  ├─ User Mode: Watch Live OR Close Window/Step Away                    │
    │  ├─ User Action: Mid-task intervention & course-correction            │
    │  └─ Inaccessible Source: Explicit notification & connector suggestion  │
    └───────────────────┬────────────────────────────────┬───────────────────┘
                        │                                │
          [Write / Sensitive Operation]                  │ [Read / Safe Actions]
                        │                                │
                        ▼                                │
         ┌──────────────────────────────┐                │
         │    HUMAN APPROVAL GATEWAY    │                │
         │  - File Deletion             │                │
         │  - Send Email / Message      │                │
         │  - Financial / Transactions  │                │
         │  - App-by-App Screen Access  │                │
         └──────────────┬───────────────┘                │
                        │                                │
                    [Approved]                           │
                        │                                │
                        ▼                                ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                          PHYSICAL DELIVERABLE                          │
    │  - Tangible files on disk (.md, .xlsx formulas, .pptx)                 │
    │  - Grounded citations & explicit silence/ambiguity flags               │
    └───────────────────────────────────┬────────────────────────────────────┘
                                        │
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                      HUMAN REVIEW & POST-LIFECYCLE                     │
    │  - Human reviews before shipping                                       │
    │  - Iterate in place (session memory preserved)                         │
    │  - Scoped project memory update                                        │
    │  - Handoff to Claude Code (if production repo work detected)           │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Engineering Inferences (Clearly Labelled)

*(These are engineering deductions regarding the technical infrastructure required to support the documented behaviors above, not claims about Anthropic's proprietary code)*:

1. **Inference on Detached Execution Daemons:** The ability for scheduled and long-running tasks to continue executing when *"the Claude Desktop app is closed or computer is asleep"* requires a persistent remote execution runner and authoritative task ledger decoupled from desktop UI connections.
2. **Inference on Mid-Flight Event Injection:** Supporting mid-task course-correction requires the runtime worker to poll or await incoming client control events between tool-execution boundaries without killing the running task container.
3. **Inference on Epistemic Validation Gates:** Flagging ambiguity and source silence rather than guessing requires pre-synthesis verification logic (or negative-prompt guardrails) that checks source-fact grounding before output emission.
4. **Inference on Blocking State Machine:** The requirement for mandatory confirmation on deletions, email sends, and computer use requires an authoritative `APPROVAL_REQUESTED` state in the execution state machine that suspends progress until an explicit user response is received.

---

## 🛑 Research Status & Checklist

- [x] Long-running execution and detached presence documented (PDF Page 8, Article 13854387)
- [x] Progress & reasoning transparency analyzed (PDF Pages 8, 14)
- [x] Course-correction and in-place iteration documented (PDF Pages 8, 18)
- [x] Sub-agent architecture, context isolation, and tool restriction examined (PDF Page 11, Sub-Agents Doc)
- [x] Permissions model, Read vs Write tools, and Deletion guards audited (PDF Page 8, Article 13364135)
- [x] Computer use tool hierarchy & app-by-app authorization analyzed (Article 14128542)
- [x] Scheduled cadences and remote execution mechanics investigated (Article 13854387)
- [x] Project scoping and project-level memory verified (Article 14116274)
- [x] Uncertainty, source silence, and ambiguity handling documented (PDF Pages 14, 15, 16)
- [x] Physical deliverables and handoff boundaries mapped (PDF Pages 6, 18)
- [x] All document links fetched, inspected, and synthesized into the observation
- [x] Zero NALA code modified

```text
## RESEARCH STATUS

COWORK #002 (ENRICHED)
OBSERVATION COMPLETE 🟢

No NALA design decisions made.
No NALA code modified.

Next research dependency:
COWORK #003 — CODEX & CLAUDE CODE BENCHMARK AUDIT
```
