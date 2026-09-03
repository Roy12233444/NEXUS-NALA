# NALA Control Center — UI Forensic Audit

**Document Version:** `1.0.0-AUTHORITATIVE`  
**Classification:** Pre-Design Architectural Audit (No Implementation / Inspection Only)  
**Date:** August 28, 2026  
**Auditor:** Principal Frontend Architect & UI Systems Forensic Engineer  

---

## 1. Executive Finding

The NALA Control Center frontend is currently in an **asymmetric transition state**:
1. **The Backend Organism is Highly Advanced (002A–002G Complete)**: The Python runtime possess dynamic memory indexing, deterministic task-graph decomposition, Pramāṇa epistemic routing, adaptive Viveka safety gates, durable ARIES checkpoints, physical SHA-256 corroboration, and bounded self-healing recovery.
2. **The Surviving Mounted UI is a Single-Screen Conversational Shell**: The user currently interacts exclusively through a clean, single-screen chat interface (`CoworkLayout.tsx` $\to$ `ChatSection.tsx`). The previously designed complex multi-panel dashboard (`DashboardContainer`, `TaskGraph`, `SafetyGauges`, `ToolActivityPanel`, `TranscendentPanel`, `MemoryPanel`, `RightSidebar`, `LeftColumn`, `CenterColumn`) was completely unmounted from the layout tree.
3. **The Redux Store is Fully Wired to WebSocket Events, but Orphaned from Rendering**: `websocketService.ts` actively ingests over 25 distinct runtime events and dispatches them into 6 Redux slices (`connection`, `mode`, `ritaScore`, `safety`, `tools`, `transcendent`), but **no currently mounted component reads from or subscribes to the Redux store**.
4. **Current Observability is Local to the Chat Bubble**: The mounted `ChatSection.tsx` maintains its own isolated React `useState` and projects:
   - Execution Plan (001E / 002B)
   - Live Step Progress Timeline (001D / 002E)
   - Runtime Verification Badge (`SHA-256 & Disk Readback`) (001F / 002F)
   - Physical Artifact Cards with SHA-256 Checksums (001F / 002F)

---

## 2. Current Frontend Stack

| Layer | Technology | Version | Notes / Strictness |
| :--- | :--- | :--- | :--- |
| **Framework** | React + React-DOM | `18.2.0` | Client-Side SPA model; fast SWC compiler |
| **Bundler & Dev Server** | Vite | `4.3.0` (Vite 4.5.14 runtime) | Configured on port `3000`, strict host binding |
| **Language** | TypeScript | `5.0.2` | `strict: true`, `target: ES2020`, path alias `@/*` |
| **State Management** | Redux Toolkit | `^1.9.5` (React-Redux `^8.1.1`) | 6 slices configured in `src/store/` |
| **Real-Time Transport** | Socket.IO Client | `^4.7.2` | Connects to `http://localhost:3001` with retry backoff |
| **Styling Paradigm** | Vanilla CSS + CSS Variables | N/A | Plain CSS with Dark/Light design tokens; **Zero Tailwind** |
| **Typography & Math** | KaTeX | `^0.16.8` | Mathematical rendering support for equations |
| **Icons** | Custom Lucide SVG Pack | Internal (`src/components/ui/LucideIcons.tsx`) | 30+ bespoke feather/lucide icons |

---

## 3. Surviving UI Architecture

```text
src/
├── App.tsx                              [MOUNTED ROOT: Switches between 'website' & 'app']
├── index.tsx                            [ROOT DOM MOUNT]
│
├── components/
│   ├── layout/
│   │   ├── CoworkLayout.tsx             [MOUNTED: Clean shell hosting Header & ChatSection]
│   │   ├── CoworkLayout.css             [MOUNTED: Styling for minimal top bar]
│   │   ├── MainLayout.tsx               [ORPHANED / UNMOUNTED: Previous 3-column shell]
│   │   ├── Sidebar.tsx                  [ORPHANED / UNMOUNTED: Previous left nav sidebar]
│   │   ├── Header.tsx                   [ORPHANED / UNMOUNTED: Previous complex header]
│   │   └── Footer.tsx                   [ORPHANED / UNMOUNTED: Previous app footer]
│   │
│   ├── features/
│   │   ├── chat/
│   │   │   ├── ChatSection.tsx          [MOUNTED: Core live message stream & composer]
│   │   │   ├── ChatSection.css          [MOUNTED: Message bubbles, plan, timeline styles]
│   │   │   ├── ChatContainer.tsx        [ORPHANED / UNMOUNTED]
│   │   │   ├── NalaExecutionPipeline.tsx [ORPHANED / UNMOUNTED]
│   │   │   ├── AgentPlanningBlock.tsx   [ORPHANED / UNMOUNTED]
│   │   │   ├── AIThinkingBlock.tsx      [ORPHANED / UNMOUNTED]
│   │   │   ├── MessageBubble.tsx        [ORPHANED / UNMOUNTED]
│   │   │   ├── MessageInput.tsx         [ORPHANED / UNMOUNTED]
│   │   │   └── AIActionsBar.tsx         [ORPHANED / UNMOUNTED]
│   │   ├── center/
│   │   │   └── CenterColumn.tsx         [ORPHANED / UNMOUNTED]
│   │   ├── left/
│   │   │   └── LeftColumn.tsx           [ORPHANED / UNMOUNTED]
│   │   ├── right/
│   │   │   ├── RightColumn.tsx          [ORPHANED / UNMOUNTED]
│   │   │   └── RightSidebar.tsx         [ORPHANED / UNMOUNTED]
│   │   ├── memory/
│   │   │   └── MemoryPanel.tsx          [ORPHANED / UNMOUNTED]
│   │   └── dashboard/
│   │       ├── DashboardContainer.tsx   [ORPHANED / UNMOUNTED]
│   │       ├── TaskGraph.tsx            [ORPHANED / UNMOUNTED]
│   │       ├── SafetyGauges.tsx         [ORPHANED / UNMOUNTED]
│   │       ├── SystemMetrics.tsx        [ORPHANED / UNMOUNTED]
│   │       ├── ToolActivityPanel.tsx    [ORPHANED / UNMOUNTED]
│   │       ├── TranscendentPanel.tsx    [ORPHANED / UNMOUNTED]
│   │       └── RunLogs.tsx              [ORPHANED / UNMOUNTED]
│   │
│   ├── ui/
│   │   ├── MarkdownRenderer.tsx         [MOUNTED: Used in ChatSection]
│   │   ├── LucideIcons.tsx              [MOUNTED: Used in ChatSection & CoworkLayout]
│   │   ├── ChainOfThoughtMaster.tsx     [ORPHANED / UNMOUNTED]
│   │   ├── ToolExecutionTrace.tsx       [ORPHANED / UNMOUNTED]
│   │   ├── ExecutionCell.tsx            [ORPHANED / UNMOUNTED]
│   │   ├── Reasoning.tsx                [ORPHANED / UNMOUNTED]
│   │   ├── ModeSelector.tsx             [ORPHANED / UNMOUNTED]
│   │   ├── DotMatrix.tsx                [ORPHANED / UNMOUNTED]
│   │   ├── Citation.tsx                 [ORPHANED / UNMOUNTED]
│   │   └── ContextButton.tsx            [ORPHANED / UNMOUNTED]
│   │
│   └── website/                         [MOUNTED: 9 Website Landing Page Sections]
│
├── services/
│   ├── websocketService.ts              [ACTIVE: Ingests 25+ events, dispatches to Redux]
│   └── chatService.ts                   [ORPHANED / 1 BYTE EMPTY]
│
├── store/
│   ├── index.ts                         [ACTIVE STORE: 6 Redux slices, but unconsumed by UI]
│   └── slices/
│       ├── connectionSlice.ts           [INGESTS: AMP, Fleet, Safety, KB status]
│       ├── modeSlice.ts                 [INGESTS: Autonomous/Assist/Supervised mode]
│       ├── ritaScoreSlice.ts            [INGESTS: Coherence score]
│       ├── safetySlice.ts               [INGESTS: Viveka, Satya truthfulness]
│       ├── toolsSlice.ts                [INGESTS: Tool predictions, warming, metrics]
│       └── transcendentSlice.ts         [INGESTS: Pramāṇa active, awareness, coherence]
│
└── hooks/
    ├── useScrollReveal.ts               [MOUNTED: Website animations]
    ├── useLenisScroll.ts                [MOUNTED: Website smooth scroll]
    ├── useAppState.ts                   [ORPHANED: Unused hook]
    ├── useChat.ts                       [ORPHANED / 1 BYTE EMPTY]
    └── useWebSocket.ts                  [ORPHANED / 1 BYTE EMPTY]
```

---

## 4. Component Inventory

| Component | File Path | Exists | Mounted | Visible | Purpose | Backend Connected |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **`App`** | `src/App.tsx` | YES | YES | YES | Viewport switcher (`website` vs `app`) | NO |
| **`CoworkLayout`** | `src/components/layout/CoworkLayout.tsx` | YES | YES | YES | Control Center top bar & shell | PARTIAL (Static status badge) |
| **`ChatSection`** | `src/components/features/chat/ChatSection.tsx` | YES | YES | YES | Message stream, timeline, plan, artifacts | **YES** (Direct socket listeners) |
| **`MarkdownRenderer`** | `src/components/ui/MarkdownRenderer.tsx` | YES | YES | YES | Renders formatted markdown in chat | NO (Pure renderer) |
| **`LucideIcons`** | `src/components/ui/LucideIcons.tsx` | YES | YES | YES | Vector iconography pack | NO (SVG Library) |
| **`Website/*` (9 files)**| `src/components/website/*` | YES | YES | YES | Public presentation landing page | NO |
| `DashboardContainer` | `src/components/features/dashboard/DashboardContainer.tsx` | YES | **NO** | **NO** | Master dashboard grid | YES (Redux connected) |
| `TaskGraph` | `src/components/features/dashboard/TaskGraph.tsx` | YES | **NO** | **NO** | Visual dependency node graph | YES (Redux/Socket connected) |
| `SafetyGauges` | `src/components/features/dashboard/SafetyGauges.tsx` | YES | **NO** | **NO** | Viveka & Satya radar/gauges | YES (Redux connected) |
| `SystemMetrics` | `src/components/features/dashboard/SystemMetrics.tsx` | YES | **NO** | **NO** | CPU/Memory/Network telemetry | YES (Redux connected) |
| `ToolActivityPanel`| `src/components/features/dashboard/ToolActivityPanel.tsx` | YES | **NO** | **NO** | Tool usage & latency monitor | YES (Redux connected) |
| `TranscendentPanel`| `src/components/features/dashboard/TranscendentPanel.tsx` | YES | **NO** | **NO** | Pramāṇa epistemic radar | YES (Redux connected) |
| `RunLogs` | `src/components/features/dashboard/RunLogs.tsx` | YES | **NO** | **NO** | Real-time console log stream | YES (Redux connected) |
| `MemoryPanel` | `src/components/features/memory/MemoryPanel.tsx` | YES | **NO** | **NO** | Memory browser & fact inspector | YES (Redux/Socket connected) |
| `LeftColumn` | `src/components/features/left/LeftColumn.tsx` | YES | **NO** | **NO** | Session list & navigation drawer | YES (Redux connected) |
| `RightColumn` | `src/components/features/right/RightColumn.tsx` | YES | **NO** | **NO** | Telemetry inspector column | YES (Redux connected) |
| `RightSidebar` | `src/components/features/right/RightSidebar.tsx` | YES | **NO** | **NO** | Multi-tab inspector | YES (Redux connected) |
| `NalaExecutionPipeline` | `src/components/features/chat/NalaExecutionPipeline.tsx` | YES | **NO** | **NO** | Step-by-step pipeline visualizer | YES (Socket connected) |
| `ToolExecutionTrace` | `src/components/ui/ToolExecutionTrace.tsx` | YES | **NO** | **NO** | Tool invocation JSON tracer | NO |
| `ChainOfThoughtMaster` | `src/components/ui/ChainOfThoughtMaster.tsx` | YES | **NO** | **NO** | Internal reasoning visualizer | NO |

---

## 5. Current Screen Composition

When a user opens [`http://localhost:3000`](http://localhost:3000):
1. **Initial Screen**: Renders the complete **NALA Public Landing Page** (`viewMode === 'website'`) with Navigation, Hero, Marquee, Problem, Architecture, Rigor, Roadmap, and Research sections.
2. **Transition**: Clicking `"Launch Agent Control Room"` or `"Launch App"` sets `viewMode = 'app'`, mounting `CoworkLayout.tsx`.
3. **Control Center Viewport**:
   - **Header**: Minimalist bar with `"Back"` button, `"NALA Control Center"` brand dot, and static indicator: `🧬 Self-Healing Engine Active (002G)`.
   - **Main Area**: `ChatSection.tsx` occupying 100% of the viewport width and height.
   - **Empty State**: When no messages exist, displays `"✨ How can I help you today? Ask anything or enter a directive for NALA."`
   - **Bottom Composer**: Pill-shaped textarea with auto-resizing height and purple send button.
   - **Message Bubble Projection**: Agent bubbles render Markdown text, and if a task was triggered:
     1. Structured Plan block (`EXECUTION PLAN` with step numbers)
     2. Live Progress Timeline (`EXECUTION PROGRESS` with pulsing/check markers)
     3. Verification Card (`RESULT VERIFIED` / `SHA-256 & Disk Readback`)
     4. Artifact Card (File name, byte size, SHA-256 prefix)

---

## 6. WebSocket / Real-Time Event Architecture

```text
                                  ┌────────────────────────┐
                                  │   NALA Python Server   │
                                  │  (nala_server.py:3001) │
                                  └───────────┬────────────┘
                                              │
                                   [Socket.IO Transport]
                                              │
                                  ┌───────────▼────────────┐
                                  │  websocketService.ts   │
                                  └─────┬────────────┬─────┘
                                        │            │
             ┌──────────────────────────┘            └──────────────────────────┐
             │ (Dispatches to Redux)                                            │ (Direct Event Subscriptions)
             ▼                                                                  ▼
┌───────────────────────────────┐                              ┌───────────────────────────────┐
│          Redux Store          │                              │        ChatSection.tsx        │
│ ┌───────────────────────────┐ │                              │ ┌───────────────────────────┐ │
│ │ safetySlice               │ │                              │ │ session_created           │ │
│ │ toolsSlice                │ │                              │ │ ai_response / chunk       │ │
│ │ transcendentSlice         │ │                              │ │ step_event                │ │
│ │ connectionSlice           │ │                              │ │ session_complete          │ │
│ │ ritaScoreSlice            │ │                              │ │ session_error             │ │
│ │ modeSlice                 │ │                              │ └─────────────┬─────────────┘ │
│ └───────────────────────────┘ │                              └───────────────┼───────────────┘
└───────────────┬───────────────┘                                              │
                │                                                              ▼
                ▼                                               ┌───────────────────────────────┐
   ⚠️ [ORPHANED / UNCONSUMED]                                   │    Visible Chat Message UI    │
  (No mounted components read                                   │ - Plan Steps (002B)           │
   or render this state)                                        │ - Live Timeline (002E)        │
                                                                │ - Verification Card (002F)    │
                                                                │ - Physical Artifact (002F)    │
                                                                └───────────────────────────────┘
```

### Registered Backend Events vs Consumption Status:

| Event Name | Backend Producer | Frontend Ingested in `websocketService` | Connected to Redux | Rendered in Active UI |
| :--- | :--- | :---: | :---: | :---: |
| `session_created` | `nala_server.py` | YES | NO | **YES** (`ChatSection.tsx`) |
| `ai_response_chunk` | `nala_server.py` (Ollama stream) | YES | NO | **YES** (`ChatSection.tsx`) |
| `ai_response` | `nala_server.py` | YES | NO | **YES** (`ChatSection.tsx`) |
| `step_event` | `nala_runner.py` / `orchestrator` | YES | NO | **YES** (`ChatSection.tsx`) |
| `session_complete` | `nala_server.py` | YES | NO | **YES** (`ChatSection.tsx`) |
| `session_error` | `nala_server.py` | YES | NO | **YES** (`ChatSection.tsx`) |
| `pramana-active` | `server_state.update_pramana_state`| YES | YES (`transcendentSlice`)| **NO** (Orphaned) |
| `pramana-reasoning-clear`| `server_state` | YES | YES (`transcendentSlice`)| **NO** (Orphaned) |
| `transcendent-*` (4 events)| `server_state` | YES | YES (`transcendentSlice`)| **NO** (Orphaned) |
| `safety-metrics-update` | `server_state.update_safety_metrics`| YES | YES (`safetySlice`) | **NO** (Orphaned) |
| `viveka-*` (4 events) | `server_state` | YES | YES (`safetySlice`) | **NO** (Orphaned) |
| `satya-*` (3 events) | `server_state` | YES | YES (`safetySlice`) | **NO** (Orphaned) |
| `tool-predictions` | `server_state` | YES | YES (`toolsSlice`) | **NO** (Orphaned) |
| `tool-warmed / cooled` | `server_state` | YES | YES (`toolsSlice`) | **NO** (Orphaned) |
| `tool-ready` | `server_state` | YES | YES (`toolsSlice`) | **NO** (Orphaned) |
| `tool-usage-update` | `server_state` | YES | YES (`toolsSlice`) | **NO** (Orphaned) |
| `rita-score-update` | `server_state.update_rita_score` | YES | YES (`ritaScoreSlice`) | **NO** (Orphaned) |
| `operation-mode` | `server_state` | YES | YES (`modeSlice`) | **NO** (Orphaned) |
| `recovery-*` (7 events) | `RecoveryEngine` / `resume_session`| YES | YES (`connectionSlice`)| **NO** (Console only) |

---

## 7. Backend → UI Capability Matrix

| Capability (Subsystem) | Backend Exists | Runtime Wired | Event/API Exists | Frontend Receives | UI Exposes | Gap Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **002A: Dynamic Memory Recall** | YES | YES | PARTIAL | NO | PARTIAL | Context is injected into agent thinking, but facts/memory browser is not visible to user. |
| **002A: Memory Capture** | YES | YES | YES | YES | PARTIAL | Textual confirmation in chat only; no dedicated memory repository view. |
| **002B: Dynamic Decomposition**| YES | YES | YES | YES | **YES** | Execution plan steps are rendered inside the agent chat card. |
| **002B: TaskGraph Topology** | YES | YES | YES | NO | **NO** | Dependency DAG nodes and parallel edges are not visualized. |
| **002C: Pramāṇa Epistemic Route**| YES | YES | YES | YES | **NO** | Active Pramāṇa (Pratyakṣa, Anumāna, etc.) is held in Redux but unrendered. |
| **002C: Epistemic Confidence** | YES | YES | YES | YES | **NO** | Confidence score is received but not displayed. |
| **002D: Tool Registry** | YES | YES | YES | YES | **NO** | Available tools, predictions, and warming states are received in Redux but unrendered. |
| **002D: Adaptive Viveka Gate** | YES | YES | YES | YES | PARTIAL | Safety decisions block actions; metrics exist in Redux but no visible safety gauge. |
| **002D: Sandboxed Execution** | YES | YES | YES | YES | PARTIAL | Step timeline marks completion, but sandbox telemetry/logs are hidden. |
| **002E: Cross-Core Execution** | YES | YES | YES | YES | **YES** | Real-time step progress (`executing` $\to$ `completed`) streams cleanly in chat. |
| **002F: Durable Checkpoints** | YES | YES | YES | YES | PARTIAL | Checkpoint LSNs are tracked on disk; UI only sees the final verification result. |
| **002F: SHA-256 Corroboration** | YES | YES | YES | YES | **YES** | Physical verification badge and artifact SHA-256 hashes are displayed clearly. |
| **002G: Self-Healing Engine** | YES | YES | YES | YES | PARTIAL | Header displays `🧬 Self-Healing Engine Active`; deep recovery cards were unmounted. |
| **002G: ARIES Crash Recovery** | YES | YES | YES | YES | **NO** | Resumption happens autonomously in backend; recovery rationale is not exposed on screen. |

---

## 8. Runtime Observability Matrix

| Runtime Phase | Observability Status | Where / How It Appears |
| :--- | :---: | :--- |
| **Goal Received** | **VISIBLE** | User message bubble appears in chat stream. |
| **Intent Classification** | **BACKEND ONLY** | Logged on server (`TaskRequest.intent`); not rendered in chat. |
| **Memory Recall** | **BACKEND ONLY** | Recalled context is passed to planner in background; no recall pill in UI. |
| **Generated Plan** | **VISIBLE** | `EXECUTION PLAN` box appears inside agent message bubble. |
| **TaskGraph Step Execution** | **VISIBLE** | `EXECUTION PROGRESS` timeline with live status icons (`✓`, executing spinner). |
| **Selected Pramāṇa** | **BACKEND ONLY** | Emitted as `pramana-active`, stored in Redux `transcendentSlice`, unrendered. |
| **Selected Tool** | **PARTIALLY VISIBLE** | Step description mentions action; tool registry metadata is unrendered. |
| **Viveka Decision** | **BACKEND ONLY** | Emitted as `viveka-transition-outcome`, stored in Redux `safetySlice`, unrendered. |
| **Sandbox Execution** | **PARTIALLY VISIBLE** | Resulting file is visible, but sandbox environment isolation is unrendered. |
| **Artifact Creation** | **VISIBLE** | `📄 filename.ext (X bytes)` card with SHA-256 prefix. |
| **Verification & SHA-256** | **VISIBLE** | `✓ RESULT VERIFIED` badge with `SHA-256 & Disk Readback` label. |
| **Checkpoint Creation & LSN** | **BACKEND ONLY** | Persisted to disk (`data/checkpoints/`); LSN numbers not displayed in UI. |
| **Recovery / ARIES Resume** | **BACKEND ONLY** | Telemetry emitted; handled smoothly in background without dedicated UI card. |
| **Runaway Loop Safe Halt** | **PARTIALLY VISIBLE** | Error text displayed if task halts; no dedicated safe-halt telemetry badge. |
| **Memory Fact Commitment** | **PARTIALLY VISIBLE** | Formatted Markdown confirmation message in chat. |
| **Final Synthesized Result** | **VISIBLE** | Full Markdown response rendered by `MarkdownRenderer`. |

---

## 9. State Architecture Analysis

### Current State Representation:
1. **Chat Local State (`ChatSection.tsx`)**:
   ```typescript
   interface Message {
     id: string;
     sender: 'user' | 'agent';
     author: string;
     time: string;
     text: string;
     status?: 'typing' | 'thinking' | 'complete';
     taskId?: string;
     sessionId?: string;
     plan?: PlanStep[];
     runtimeSteps?: RuntimeStepState[];
     verification?: VerificationResult;
     artifact?: ArtifactInfo;
   }
   ```
2. **Redux Store (`src/store/index.ts`)**:
   - `connection`: Socket connection and core component health.
   - `mode`: Active operational mode (`autonomous`, `assist`, `supervised`).
   - `ritaScore`: Coherence score and factor history.
   - `safety`: Viveka strictness, calibration, Satya consistency, overall health.
   - `tools`: Tool predictions, warming statuses, usage latencies.
   - `transcendent`: Active Pramāṇa, confidence, awareness, coherence, insight depth.

---

## 10. UI Survivability Audit

### 1. Long Execution (100+ Steps)
* **Status**: **SURVIVES WITH BOUNDED MEMORY**
* **Reasoning**: `ChatSection.tsx` maps steps by `stepId` in an array. While 100+ steps will render as a long scrollable list, it does not crash React. However, there is no step virtualization or collapsible grouping for long missions.

### 2. Failure & Crash Resumption
* **Status**: **SURVIVES CLEANLY**
* **Reasoning**: The backend `RecoveryEngine` resumes from disk checkpoints and emits updated `step_event` records with the same `taskId`. `ChatSection.tsx` merges updates into the existing message card without duplicate bubble spawning.

### 3. Browser Disconnection & Reconnect
* **Status**: **PARTIALLY SURVIVES**
* **Reasoning**: `websocketService.ts` automatically attempts 10 reconnection cycles with exponential backoff and flushes outbound queues. However, upon reconnect, `ChatSection.tsx` does not currently trigger a `fetch_session_history` REST call to hydrate steps that finished while the browser was closed.

### 4. Multiple Concurrent Tasks
* **Status**: **SINGLE-TASK BOUNDED**
* **Reasoning**: `ChatSection.tsx` receives events globally on the socket. If multiple tasks execute simultaneously in the backend, events for different `taskId`s can interleave in the active message bubble. Multi-task separation requires task tab / workspace scoping.

---

## 11. Visual System Audit

* **Color Tokens**:
  - Background: `#0B0F19` (Deep Obsidian Dark Mode)
  - Card Surfaces: `#1E293B` / `#0F172A` (Slate Navy)
  - Accent Primary: `#6366F1` (Indigo Purple)
  - Accent Neon: `#00F0FF` (Cyan Glow), `#00FF9D` (Emerald Spring), `#A855F7` (Purple Pulse)
  - Border Colors: `#334155` / `rgba(255, 255, 255, 0.08)`
* **Typography**:
  - Primary Font: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  - Monospace Font: `"JetBrains Mono", "Fira Code", monospace` (used for hashes and IDs)
* **Elevation & Borders**:
  - Border Radius: `8px` (cards), `24px` (composer pill)
  - Shadows: `0 4px 20px rgba(0, 0, 0, 0.25)`

---

## 12. Architecture Fitness Score

| Evaluated Dimension | Score (0–5) | Architectural Rationale |
| :--- | :---: | :--- |
| **Component Architecture** | **3.0 / 5** | Clean separation of UI components, but excessive orphaned files remaining in folders. |
| **State Architecture** | **2.5 / 5** | Fragmented between Redux (unconsumed) and local `useState` in `ChatSection`. |
| **Runtime Event Handling** | **4.0 / 5** | Comprehensive socket event coverage in `websocketService.ts` and `ChatSection.tsx`. |
| **WebSocket Integration** | **4.5 / 5** | Solid Socket.IO connection with queuing, reconnection backoff, and heartbeat. |
| **Type Safety** | **4.0 / 5** | Strong TypeScript types across plan, steps, verification, and artifacts; some empty `.d.ts` files. |
| **Error Handling** | **3.5 / 5** | Graceful fallback on socket errors, model timeouts, and connection drops. |
| **Loading States** | **4.0 / 5** | Sleek pulsing dot indicator and thinking spinner during generation. |
| **Real-time Rendering** | **4.5 / 5** | Step-by-step progress, streaming chunks, and timeline update in real time. |
| **Long-Running Execution UI** | **2.5 / 5** | Lacks pagination, mission collapsible groups, or session archives. |
| **Recovery Visualization** | **1.5 / 5** | Backend recovery is 100% complete, but visual recovery telemetry was unmounted. |
| **Observability** | **2.5 / 5** | High observability for chat/plan/artifacts; zero observability for Pramāṇa/Viveka/Tools. |
| **Extensibility** | **4.0 / 5** | Modular structure allows clean re-attachment of sidebars, panels, and drawer tabs. |
| **Maintainability** | **3.5 / 5** | Easy to maintain once dead/orphaned files are audited and cleaned up. |
| **OVERALL COMPOSITE** | **3.35 / 5** | **Solid technical foundation; requires unified state and purposeful layout.** |

---

## 13. Dead / Orphaned UI Inventory

The following files exist in `src/` but are **completely unmounted and never imported by any active screen**:

1. **Dashboard Feature Set**:
   - `src/components/features/dashboard/DashboardContainer.tsx`
   - `src/components/features/dashboard/TaskGraph.tsx`
   - `src/components/features/dashboard/SafetyGauges.tsx`
   - `src/components/features/dashboard/SystemMetrics.tsx`
   - `src/components/features/dashboard/ToolActivityPanel.tsx`
   - `src/components/features/dashboard/TranscendentPanel.tsx`
   - `src/components/features/dashboard/RunLogs.tsx`
2. **Column Layout Feature Set**:
   - `src/components/features/left/LeftColumn.tsx`
   - `src/components/features/center/CenterColumn.tsx`
   - `src/components/features/right/RightColumn.tsx`
   - `src/components/features/right/RightSidebar.tsx`
   - `src/components/features/memory/MemoryPanel.tsx`
3. **Legacy Chat Subcomponents**:
   - `src/components/features/chat/ChatContainer.tsx`
   - `src/components/features/chat/NalaExecutionPipeline.tsx`
   - `src/components/features/chat/AgentPlanningBlock.tsx`
   - `src/components/features/chat/AIThinkingBlock.tsx`
   - `src/components/features/chat/MessageBubble.tsx`
   - `src/components/features/chat/MessageInput.tsx`
   - `src/components/features/chat/AIActionsBar.tsx`
4. **Unused UI Primitives**:
   - `src/components/ui/ToolExecutionTrace.tsx`
   - `src/components/ui/ChainOfThoughtMaster.tsx`
   - `src/components/ui/ExecutionCell.tsx`
   - `src/components/ui/Reasoning.tsx`
   - `src/components/ui/ModeSelector.tsx`
   - `src/components/ui/DotMatrix.tsx`
   - `src/components/ui/Citation.tsx`
   - `src/components/ui/ContextButton.tsx`
5. **Empty Placeholder Files**:
   - `src/services/chatService.ts` (1 byte)
   - `src/hooks/useChat.ts` (1 byte)
   - `src/hooks/useWebSocket.ts` (1 byte)
   - `src/types/index.d.ts` (1 byte)

---

## 14. Missing UI Capabilities

To evolve into a true Autonomous Control Center, the UI currently lacks:
1. **A Collapsible Inspector Panel**: A clean, dockable right-side tray to view active Pramāṇa, Viveka safety status, and tool telemetry on demand without cluttering the chat.
2. **Session / Mission History Drawer**: A left-hand drawer to switch between active and historical missions.
3. **Memory Inspector**: A clean modal or tab to view what NALA has committed to `MEMORY.md`.
4. **State Rehydration on Reconnect**: An initialization hook that fetches the current session state from the backend when the browser refreshes.

---

## 15. Technical Risks

1. **State Divergence Risk**: `ChatSection.tsx` manages its own message array while `websocketService.ts` updates Redux. If components are re-introduced that read Redux, Redux state and chat state could desynchronize unless unified.
2. **Orphaned Asset Bloat**: Over 25 unused component files exist in the repository. While they do not break the build (tree-shaking removes them from `dist/`), they create architectural confusion.
3. **Multi-Session Collisions**: `ChatSection.tsx` does not filter incoming socket events by `sessionId`, meaning if multiple browser tabs or background tasks emit events, they could cross-contaminate.

---

## 16. Recommended UI Architecture Direction (Analysis Only)

The ideal professional NALA Control Center should follow a **Hybrid Co-Work Workspace Architecture**:
* **Center**: Clean, dominant conversation and execution stream (what exists today in `ChatSection.tsx`).
* **Collapsible Right Inspector**: A sleek, non-intrusive collapsible drawer that opens when a user wants deep observability (Pramāṇa confidence, Viveka decision log, Checkpoint LSN, and Tool usage).
* **Collapsible Left Drawer**: A lightweight mission history list to load past checkpoints and tasks.
* **Unified State**: Bridge Redux and Chat state so that selecting a step in chat automatically highlights its epistemic route and safety verdict in the Inspector.

---

## 17. Recommended UI Work Breakdown (Planning Only)

When entering the UI redesign phase with the user:

```text
Stage 1: /wireframe
  └── Establish visual wireframes for a 3-zone collapsible Control Center (Nav, Stream, Inspector).

Stage 2: /appscreen
  └── Finalize the core workspace layout, panel docking, and header indicators.

Stage 3: /dashboard
  └── Design compact, high-density telemetry cards for Pramāṇa, Viveka, Checkpoints, and Tools.

Stage 4: /variations
  └── Explore theme variations, color contrast, and typography hierarchy.

Stage 5: /restyle
  └── Apply polished CSS tokens, micro-animations, and unified responsive behavior.
```

---

## 18. Evidence & Verification

- **Production Build Status**: Verified via `npm run build` — `152 modules transformed`, `dist/` bundle compiled with 0 errors.
- **Backend Core Test Status**: Verified via `pytest` — **113 / 113 core tests passing** (002A–002G).
- **Socket Connectivity**: Verified via `websocketService.ts` running on port `3001` with bi-directional streaming.

---

## 19. Conclusion

NALA has a world-class autonomous reasoning and self-healing backend. The current frontend is a rock-solid, functional chat foundation that already cleanly projects plans, live timelines, and verified SHA-256 artifacts.

By preserving this clean chat foundation and methodically connecting the rich backend telemetry through purposeful, collapsible inspector panels under the user's guidance, NALA will become an industry-leading, professional Autonomous AI Control Center.
