# 🚀 NALA Claude Co-Work Control Center Upgrade — Advanced Implementation Plan

## 📌 Executive Summary
This document defines the architectural upgrade plan to transform NALA's current 1-dimensional Chat UI into a full-fledged **Claude Co-Work / Cursor Style Autonomous Control Center**.

---

## 🚨 Current Limitations
1. **No Live Code & Diff Viewer**: When NALA edits files on the `E:` drive, users cannot see a side-by-side Monaco diff viewer (`+` green additions, `-` red deletions).
2. **No Embedded Live Terminal**: Commands executed inside `sandbox.py` (e.g. `pip install`, `pytest`, `npm test`) emit summaries rather than live streaming `stdout`/`stderr`.
3. **No Interactive Task Graph (DAG)**: Multi-step plans are listed as flat text items rather than an interactive node graph with status state indicators and single-node retry.
4. **No System & Kernel Telemetry Gauges**: Real-time memory RSS usage (against the 256MB Job Object cap), CPU %, and PEP 578 audit hook alerts are not visually displayed.

---

## 🏗️ Proposed Architecture: 4-Panel Co-Work Control Room Layout

### Layout Wireframe (Split-Screen Workspace):
```
+---------------------------------------------------------------------------------------------------+
|  NALA CONTROL ROOM  [⚡ Chat]  [⚡ Work (Co-Work Mode)]                                            |
+------------------------------------------+--------------------------------------------------------+
| PANEL 1: AGENT & TASK GRAPH (40%)        | PANEL 2: LIVE CODE & DIFF EDITOR (60%)                |
| - Chat & User Directives Input           | - Monaco Editor with Side-by-Side Git-Style Diff       |
| - Interactive Task DAG Graph             | - File Tree Explorer (`E:\Projects\TargetFolder`)      |
|   (Pending, Running, Passed, Failed)     |                                                        |
| - Viveka/Satya/Ṛta Health Gauges         +--------------------------------------------------------+
|                                          | PANEL 3: EMBEDDED SANDBOX TERMINAL (xterm.js)          |
|                                          | - Live stdout/stderr stream from `sandbox.py`          |
|                                          | - Terminal process status & kill button                |
+------------------------------------------+--------------------------------------------------------+
```

---

## 🛠️ Detailed Component Specifications

### 1. 📂 Panel 1: Live Workspace Explorer & Monaco Git-Style Diff Viewer
- **File Tree Component**: Displays the target workspace directory on the `E:` drive in real time.
- **Monaco Diff Viewer**: Uses `@monaco-editor/react` to display original file vs. proposed edits side-by-side with color-coded diff syntax highlighting (`+` additions, `-` deletions).
- **Approval Actions**: "Accept Change", "Reject Change", "Edit Manually".

### 2. 🖥️ Panel 2: Embedded Live Sandbox Terminal (`xterm.js`)
- **Interactive Terminal**: Integrates `xterm` and `xterm-addon-fit`.
- **Socket.IO Stream**: `nala_server.py` forwards real-time `stdout`/`stderr` from subprocesses executed inside Windows Kernel Job Objects directly to the UI terminal.

### 3. 🕸️ Panel 3: Interactive Task Graph (DAG Visualizer)
- **Node Graph Component**: Renders dynamic task execution nodes using React Flow / SVG DAG layouts.
- **Node States**:
  - `ACTIVE` (Glowing Gold)
  - `SUCCESS` (Emerald Green)
  - `FAILED` (Crimson Red with Retry trigger)
  - `WAITING_APPROVAL` (Amber Warning)

### 4. 📊 Panel 4: System & Kernel Telemetry Gauges
- **Resource Gauges**: Live RAM RSS meter capped at 256MB, CPU % meter.
- **PEP 578 Audit Log**: Real-time ticker displaying syscall intercepts and safety hook validations.

---

## 📅 Phased Execution Plan

| Phase | Feature | Target Deliverable |
| :--- | :--- | :--- |
| **Phase 1** | **Split-Screen Workspace Layout** | Refactor `WorkSection.tsx` to host 4-panel split layout. |
| **Phase 2** | **Monaco Diff Viewer & File Explorer** | Integrate Monaco editor with side-by-side diff view. |
| **Phase 3** | **Streaming xterm.js Sandbox Terminal** | Connect `nala_server.py` subprocess output to UI terminal. |
| **Phase 4** | **Task DAG & Kernel Telemetry Gauges** | Add visual node graph and memory/safety gauge meters. |

---
*Created for NALA Autonomous Project Backlog — `E:\NALA-Project\NALA\BACKLOG_Features\NEW_FEATURES\NALA_Claude_CoWork_Control_Center_Plan.md`*
