# 🔬 NALA Architecture Research Notebook — NALA-UI-001-F
**Title:** Candidate NALA Workbench Architecture  
**Topic:** Derivation of the Runtime-Native UI Projection & Human Control Surface  
**Status:** 🟢 **DERIVATION COMPLETE (LOCKED FOR IMPLEMENTATION)**  

---

## 🧭 Core Architectural Philosophy
> **"Complex Runtime Underneath. Effortless Interaction Above."**

The NALA Workbench is not a decorative dashboard and not an ephemeral chatbot. It is a **real-time visual projection of NALA's authoritative `RuntimeState` and `NalaRunner` event stream**.

---

## 🖥️ The Workbench Layout Model

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  NALA WORKBENCH                                                   Ṛta: 0.98 (Nominal)  │
├──────────────┬──────────────────────────────────────────────────────────┬──────────────┤
│  WORKSPACE   │                     EXECUTION STAGE                      │  GOVERNANCE  │
│  (Collapsible│                                                          │  (On-Demand) │
│              │  🎯 GOAL: Build Multi-Vendor Benchmark Matrix           │              │
│  📁 Projects │  ──────────────────────────────────────────────────────  │  ⚠️ APPROVAL │
│  📜 Tasks    │  📋 PLAN:                                                │     QUEUE    │
│  💾 Memory   │  [✓] Step 1: Ingest primary PDF documents               │              │
│  🔄 Lineage  │  [▶] Step 2: Extract technical feature matrices (RUNNING)│  Delete file │
│     (LSN 42) │  [ ] Step 3: Compile comparative markdown report        │  test.tmp?   │
│              │  ──────────────────────────────────────────────────────  │  [Approve]   │
│              │  💬 LIVE EXECUTION & REASONING:                          │  [Reject]    │
│              │  ├─ Thinking: Parsing extraction tables from pypdf...    │              │
│              │  ├─ Tool: ripgrep search 'sub-agents' (200ms)            │  🛡️ SATYA    │
│              │  └─ Output: Found 14 matches in docs/                    │     LAYER    │
│              │  ──────────────────────────────────────────────────────  │  Truth: 99%  │
│              │  📄 ARTIFACT: benchmark_matrix.md (Preview)              │  Health: 100%│
│              │  ──────────────────────────────────────────────────────  │              │
│              │  [ ⌨️ Enter prompt, command, or mid-flight steer...    ] │              │
└──────────────┴──────────────────────────────────────────────────────────┴──────────────┘
```

---

## 🧩 The 4 Information Hierarchy Layers

To prevent visual clutter, the UI classifies information into 4 strict visibility tiers:

1. **Tier 1 (Essential — Always Visible):**
   - Active Goal title.
   - Current Step & live thought/narration stream.
   - Prompt input / steering bar with execution mode switch (`Chat` / `Autonomous`).
   - Active blocking Approval Request modal (when human action is required).

2. **Tier 2 (Primary — Prominently Positioned):**
   - Collapsible Plan checklist / DAG progress.
   - Generated Artifact preview cards with one-click full-view.
   - Ṛta Safety status indicator pill.

3. **Tier 3 (Secondary — On-Demand / Collapsible Drawer):**
   - Workspace file tree & project memory.
   - Checkpoint timeline (LSN history, rewind/resume controls).
   - Tool execution stdout/stderr telemetry logs.

4. **Tier 4 (Internal — System Log Only):**
   - Raw WebSocket ping/pong frames.
   - Low-level serialization buffers.
   - Ephemeral token latency calculations.

---

## 🔄 The UI ↔ Runtime Event & Command Contract

The Workbench communicates strictly through canonical contracts defined in `nala_server/contracts.py`:

```text
               CLIENT (UI)                          SERVER (NalaRunner)
                   │                                         │
                   │────── submit_prompt(goal, mode) ───────►│
                   │                                         │
                   │◄───── TASK_CREATED (task_id) ───────────│
                   │◄───── PLANNING_STARTED ─────────────────│
                   │◄───── PLANNING_COMPLETED (plan DAG) ────│
                   │                                         │
                   │◄───── STEP_STARTED (step_id, title) ────│
                   │◄───── TOOL_STARTED (tool_name, args) ───│
                   │◄───── TOOL_COMPLETED (output) ──────────│
                   │◄───── CHECKPOINT_SAVED (lsn, state) ────│
                   │◄───── STEP_COMPLETED (step_id) ─────────│
                   │                                         │
   [Sensitive Op]  │◄───── APPROVAL_REQUESTED (request_id) ──│ (Execution Paused)
   User Approves   │────── approve_action(request_id) ──────►│ (Execution Resumed)
                   │                                         │
                   │◄───── TASK_COMPLETED (artifacts) ───────│
```

---

## 🎯 Human Control Surface

The user retains complete, authoritative control at all times via 6 primary actions:
1. **Steer:** Inject mid-flight guidance directly into the active step without aborting the task.
2. **Pause / Resume:** Cooperatively pause the `NalaLoop` between step boundaries.
3. **Approve / Reject:** Authorize or deny sensitive write actions in the approval queue.
4. **Rewind (Time-Travel):** Revert task state to any verified LSN checkpoint and resume.
5. **Abort:** Cancel the task gracefully and clean up temporary sandbox directories.
6. **Fork:** Branch an existing task into a new thread to explore alternative approaches.
