# 🥞 NALA Split Pane & Steerable Chat Shell Implementation Plan

This document outlines a phased plan to port the advanced multitasking grid and interactive chat layout features from the YC `qm-main` design into NALA.

---

## 🏗️ Phase 1: Split Pane Coordinator (`split.ts` & `split-layout.ts` Pattern)

Implement a flexible React-based split-pane layout manager that handles side-by-side workspace panes.

### Key Deliverables:
1. **Multi-Pane Context / State**:
   - Establish a pane layout state (`panes` array) tracking active views, session IDs, and sizes.
   - Support splitting a session into side-by-side active views (columns) or stacked views (rows).
2. **Pane Wrapper Component (`WorkspacePane.tsx`)**:
   - Render a custom title bar for each active workspace pane containing:
     - Scoped Title/Header (e.g., `Current YC Batch Size`).
     - **Add/Split Button (`+`)**: Splits the view to open another active pane.
     - **Expand/Contract Toggle**: Maximizes the current pane to occupy full space, collapsing others.
     - **Close Button (`X`)**: Closes the current pane and re-distributes space among remaining active panes.
3. **Resizing Rails**:
   - Vertical handles between panes to allow dragging to resize pane widths on the fly.

---

## 💬 Phase 2: Steerable Composer & Task Progress Indicator (`composer.ts` Pattern)

Upgrade NALA's input box into a dynamic steering console that reacts to background task executions.

### Key Deliverables:
1. **Steerable Composer (`SteerableComposer.tsx`)**:
   - Dual-state input field:
     - **Idle Mode**: Displays `"Ask anything"`.
     - **Executing Mode**: Displays `"Steer the running task..."` when NALA is running an autonomous loop.
   - Add control indicators:
     - **File Attachment Clip** (`IconPaperclip`) for drag-and-drop file ingestion.
     - **Cancel / Stop Button** (`IconSquare`) next to the input to halt or pause active autonomous agent steps.
2. **Active Status Log Bar**:
   - Place a real-time progress text row directly above the input bar (e.g. `Reading file for 2s n.txt >`).
   - Connect this label to NALA's server status updates.

---

## 📈 Phase 3: Interactive Tool Execution Timeline (`timeline.ts` & `chat.ts` Pattern)

Replace flat markdown tool reports with an interactive, collapsible timeline that documents NALA's tool usage in real-time.

### Key Deliverables:
1. **Collapsible Timeline Component (`ToolExecutionTrace.tsx`)**:
   - Render tool calls inside the message stream as collapsed summary rows (e.g., `7 tool calls >`).
   - Clicking expands the row into a nested tree showing:
     - Tool name (e.g., `read_file`).
     - Input parameters (in code-block format).
     - Execution status (success/error) and duration.
     - Output result console.

---

## 🧪 Phase 4: LaTeX Math & Advanced Renderers (`lazy-katex.ts` Pattern)

Incorporate support for formula parsing and advanced markdown elements in the message stream.

### Key Deliverables:
1. **Math Formula Parser**:
   - Integrate KaTeX parser wrapper (`lazy-katex.ts`) to render math equations styled correctly in inline and block modes.
2. **Premium Layouts & Inline Artifacts**:
   - Render inline tables, system-generated image assets, code-change diff blocks, and script logs natively.
