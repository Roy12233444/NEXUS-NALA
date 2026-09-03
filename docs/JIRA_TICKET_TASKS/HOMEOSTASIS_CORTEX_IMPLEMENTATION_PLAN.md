# 🧠 Homeostasis Cortex & Resource Constraint Graph Implementation Plan

This document outlines the engineering specification and phased implementation roadmap for the **Homeostasis Cortex (HCX)** and **Resource Constraint Graph (RCG)** in NALA. The goal is to evolve NALA's passive resource tracking into an active, self-regulating feedback control system that ensures stable, long-running agent operation under strict hardware, token, and API cost constraints.

---

## 🏗️ Architectural Overview

The Homeostasis Cortex manages the computational "physiology" of NALA. It monitors runtime variables, propagates constraints along a dependency graph, and adaptively adjusts model choices, compaction triggers, and scheduling queues to maintain system health.

```text
                  User Goal
                      │
                      ▼
                Goal Cortex
                      │
                      ▼
           Deliberation Cortex (Planner / Judge)
                      │
                      ▼
           Homeostasis Cortex (HCX)
       ├── Resource Constraint Graph (RCG)
       │     ├── CPU / Memory RSS Trackers
       │     └── Token / API Cost Trackers
       ├── Token Budget Controller (Trigger Compactions)
       ├── Compute Budget Manager (Model Router Downshifts)
       └── Adaptive Scheduler (Halt / Queue / Resynchronize)
                      │
                      ▼
        Autonomous Runtime Kernel (Executor)
```

---

## 🚀 Phased Implementation Roadmap

### 📦 Milestone 1: Live Resource Registry & Sensors
Build the core telemetry collection and monitoring nodes. This phase establishes the system sensors that feed metrics into the Homeostasis Cortex.

#### 1. Implement `agents/monitor_agent.py` [NEW]
* Inherit from the base agent class.
* Continuously sample local hardware metrics:
  * **Memory RSS:** Current process memory footprint (via `psutil` or platform-specific `/proc` falls).
  * **CPU Utilization:** Dynamic load percentage.
  * **File Descriptors:** Open handles to files/sockets.
  * **Thread Count:** Active concurrent workers.
* Periodically push metrics (default every 5 seconds) to `NalaServerState` in `nala_server.py`.

#### 2. Establish `runtime/resource_graph.py` [NEW]
* Define `ResourceNode` classes tracking `capacity`, `current_usage`, `priority`, and `cost_per_unit`.
* Implement a thread-safe registry to store these nodes: `CPU`, `RAM`, `TokenWindow`, `APIBudget`, and `NetworkIO`.

---

### 🕸️ Milestone 2: Resource Constraint Graph (RCG) & Dependency Propagation
Establish the relationship edges between resources and calculate constraint violations.

#### 1. Define `ConstraintEdge` and Hysteresis [NEW]
* Model resource relationships as directed graph edges. For example:
  * `Prompt Size` ──[Increases]──▶ `Token Window Pressure` ──[Increases]──▶ `Latency`
  * `Model Complexity` ──[Increases]──▶ `RAM Footprint` ──[Decreases]──▶ `Available Memory`
* Implement constraint checks using a multi-objective cost calculation:
  $$Cost = w_1 \cdot \text{ComputeCost} + w_2 \cdot \text{Latency} + w_3 \cdot \text{FailureProbability}$$

#### 2. Implement `core/safety/homeostasis_controller.py` [NEW]
* Act as the central coordinator for the HCX.
* Continuously evaluate the RCG constraints.
* Calculate an **Integrity Score** indicating overall system health.
* Interface with the `RtaFeedbackLoop` to log score adjustments and emit bound warnings.

---

### 🔄 Milestone 3: Adaptive Scheduling & Feedback Effectors
Connect the Homeostasis Cortex to active controllers that can modify agent behavior dynamically.

#### 1. Token Budget Effector (Context Compression)
* Register a constraint callback: If the `TokenWindow` node exceeds **85% capacity**, trigger the `DronagiriCompactor` (`core/harness/context_tracker.py`) to run a holographic memory compaction.
* If memory compaction does not bring token usage below **75%**, trigger a prompt truncation.

#### 2. Compute Budget Effector (Model Downshifting)
* Register a cost constraint callback: If the `APIBudget` node drops below a safety threshold or local model execution latencies exceed the SLA, trigger the `ModelRouter` (`core/hands/model_router.py`) to swap the running inference engine:
  * **Default:** Frontier model (e.g. Qwen 2.5 Coder 7B / GPT-4o)
  * **Downshift:** Lightweight local model (e.g. Qwen 2.5 Coder 1.5B)

#### 3. Execution Scheduler (Cooperative Pause / Sacred Pause)
* Integrate with `rta_governor.py`: If the RTA score falls below **0.4**, emit a `ModeRequest(SHIFT_PRATYAKSHA)` to increase interactive human steering.
* If the RTA score reaches overconfidence bounds (**>0.95**), emit `ModeRequest(SACRED_PAUSE)` to put the task runner into a 60-second cooldown (ATHAPRAPTI mode).

---

### 📊 Milestone 4: Benchmarking & Dashboard Integration
Expose the homeostasis variables to the React UI and benchmark performance under stress.

#### 1. Socket.IO Telemetry Streaming
* Update the event loop in `nala_server.py` to stream real-time events from the Homeostasis Controller:
  * `resource-update`: Sends current CPU/RAM/IO stats.
  * `safety-metrics-update`: Sends updated Viveka strictness and Satya latency.
  * `rta-score-update`: Streams the live Ṛta-score delta.
* Connect these events in `src/services/websocketService.ts` to dispatch directly into the Redux store.

#### 2. UI Panel Activation
* Hook up the React dashboard panels under `src/components/features/dashboard/`:
  * **SafetyGauges:** Renders dynamic validation strictness indicators.
  * **SystemMetrics:** Visualizes Operation Mode, stability status, and transcendent coherence levels.
  * **ToolActivityPanel:** Displays sparkline load charts for each tool.
  * **TranscendentPanel:** Renders the historical Ṛta-score wave graph.

---

## 📈 Verification & Performance Metrics

To ensure the Homeostasis Cortex functions effectively, execution metrics will be compared against a static baseline (fixed resource allocations) under high workloads:

| Metric | Target | Verification Method |
|---|---|---|
| **Budget Adherence** | **>99%** | Budget compliance audits over 100 consecutive tasks. |
| **Scheduler Latency** | **<20 ms** | Measuring scheduler overhead before dispatching steps. |
| **Out-of-Memory (OOM) Recovery** | **>95%** | Deliberately injecting RAM/Token exhaustion and verifying compactions/swaps recover execution. |
| **Runtime Overhead** | **<3%** | Verifying CPU load added by the watchdog monitoring agent. |
