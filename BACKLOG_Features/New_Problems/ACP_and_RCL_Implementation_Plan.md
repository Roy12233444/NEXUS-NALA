# 🛡️ Implementation Plan: Adaptive Contract Protocol (ACP) & Runtime Constitution Layer (RCL)

**Target Component:** NALA Autonomous Agent Runtime  
**Ticket Ref:** NLA-ACP-013  
**Status:** Advanced Implementation Specification  
**Created:** July 22, 2026  
**Target Path:** `E:\NALA-Project\NALA\BACKLOG_Features\New_Problems\ACP_and_RCL_Implementation_Plan.md`

---

## 📐 Executive Overview

Current agent runtimes rely on **Static Governance**—permissions, tool allowlists, resource quotas, and safety rules are set once before task launch. If an agent experiences repeated failures, prompt drift, or anomalous behavior during execution, standard runtimes cannot adapt permissions without aborting the task.

The **Adaptive Contract Protocol (ACP)** introduces **Dynamic Runtime Renegotiation**. The execution contract $C_t = (P_t, R_t, B_t)$ dynamically evolves during execution based on runtime telemetry $O_t$:

$$C_{t+1} = f(C_t, O_t)$$

This plan defines the end-to-end engineering specification to implement ACP and synthesize it with NALA's existing sandboxing, persistence, and Satya/Viveka safety layers into an integrated **Runtime Constitution Layer (RCL)**.

---

## 🏛️ High-Level System Architecture

```text
                                  ┌───────────────────────────────┐
                                  │          User Goal            │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │        Planning Engine        │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │  Initial Execution Contract   │
                                  │       C_0 = (P_0, R_0, B_0)   │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RUNTIME CONSTITUTION LAYER (RCL)                                │
│                                                                                                   │
│  ┌────────────────────────┐    ┌────────────────────────┐    ┌─────────────────────────────────┐  │
│  │   Behavior Monitor     │    │    Resource Monitor    │    │         Policy Monitor          │  │
│  │ (behavior_monitor.py)  │    │  (sandbox_windows.py)  │    │ (context_aware_satya_layer.py)  │  │
│  └───────────┬────────────┘    └───────────┬────────────┘    └────────────────┬────────────────┘  │
│              │                             │                                  │                   │
│              └─────────────────────────────┼──────────────────────────────────┘                   │
│                                            ▼                                                      │
│                                ┌───────────────────────┐                                          │
│                                │    Risk Estimator     │                                          │
│                                │  (risk_estimator.py)  │                                          │
│                                └───────────┬───────────┘                                          │
│                                            ▼                                                      │
│                                ┌───────────────────────┐                                          │
│                                │   Contract Engine     │ ──► [ Execution Ledger / Replay ]        │
│                                │  (contract_engine.py) │ ──► [ Session Checkpoints LSN ]          │
│                                └───────────┬───────────┘                                          │
│                                            ▼                                                      │
│                                ┌───────────────────────┐                                          │
│                                │  Permission Manager   │                                          │
│                                │(permission_manager.py)│                                          │
│                                └───────────┬───────────┘                                          │
└────────────────────────────────────────────┼──────────────────────────────────────────────────────┘
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │    Execution Runtime    │
                                │   (PEP 578 / Sandbox)   │
                                └─────────────────────────┘
```

---

## 🧩 Phase 1: Core Schemas & Data Models (`schemas/execution_contract.py`)

Create a unified Pydantic v2 data model specifying the execution contract, behavioral snapshots, and transition events.

### 1. File Location
`schemas/execution_contract.py`

### 2. Core Schemas Specification

```python
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ContractStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    EVALUATING = "EVALUATING"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"

class PermissionSet(BaseModel):
    allowed_tools: List[str] = Field(default_factory=list)
    blocked_tools: List[str] = Field(default_factory=list)
    file_read_allowlist: List[str] = Field(default_factory=list)
    file_write_allowlist: List[str] = Field(default_factory=list)
    network_domain_allowlist: List[str] = Field(default_factory=list)
    allow_subprocess_spawn: bool = False

class ResourceBudget(BaseModel):
    max_memory_mb: int = 16384
    max_cpu_percent: float = 80.0
    max_step_retries: int = 3
    max_execution_time_sec: int = 3600
    token_budget: int = 100000

class BehavioralConstraints(BaseModel):
    max_planning_depth: int = 10
    strictness_level: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    require_step_approval: bool = False
    enforce_deterministic_seed: bool = True

class BehaviorSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    planner_depth: int
    tool_calls_count: int
    retry_count: int
    memory_growth_mb: float
    latency_ms: float
    policy_violations: int = 0
    anomalous_tool_requests: List[str] = Field(default_factory=list)

class ExecutionContract(BaseModel):
    contract_id: str
    goal_id: str
    version: int = 1
    permissions: PermissionSet
    resource_budget: ResourceBudget
    constraints: BehavioralConstraints
    risk_score: float = 0.0  # Range: 0.0 (Safe) to 1.0 (Critical Risk)
    confidence: float = 1.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    status: ContractStatus = ContractStatus.ACTIVE

class ContractChangeEvent(BaseModel):
    event_id: str
    contract_id: str
    previous_version: int
    new_version: int
    trigger_reason: str
    risk_score_before: float
    risk_score_after: float
    permissions_added: List[str] = Field(default_factory=list)
    permissions_revoked: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## ⚙️ Phase 2: Runtime Modules Implementation (`runtime/`)

Implement the modular governance engine responsible for monitoring, risk scoring, evaluation, and permission enforcement.

### 1. File Structure
```text
runtime/
├── __init__.py
├── behavior_monitor.py      # Telemetry & anomaly tracking
├── risk_estimator.py        # Real-time risk & confidence calculation
├── policy_evaluator.py      # Policy validation & contract rule evaluation
├── permission_manager.py    # Sandbox & tool governor synchronization
└── contract_engine.py       # Main ACP Orchestrator (C_{t+1} = f(C_t, O_t))
```

### 2. Module Specifications

#### A. `runtime/behavior_monitor.py`
- **Role:** Collects real-time execution signals from `sandbox_hooks.py`, `context_tracker.py`, and `nala_loop.py`.
- **Key Functions:**
  - `record_tool_call(tool_name: str, args: dict)`
  - `record_retry(step_id: str, error: Exception)`
  - `capture_snapshot() -> BehaviorSnapshot`
  - `detect_anomalies(window_size: int = 5) -> List[str]`

#### B. `runtime/risk_estimator.py`
- **Role:** Evaluates snapshots to generate a continuous risk score $R \in [0.0, 1.0]$.
- **Formula:**
  $$\text{RiskScore} = w_1 \cdot \text{ViolationRate} + w_2 \cdot \text{RetryRatio} + w_3 \cdot \text{PlanningDepthRatio} + w_4 \cdot \text{MemorySpike}$$
- **Threshold Ranges:**
  - `0.0 – 0.3`: Low Risk (Normal execution; gradual permission expansion allowed).
  - `0.3 – 0.6`: Moderate Risk (Warning state; increase monitoring frequency).
  - `0.6 – 0.8`: High Risk (Restricted mode; revoke sensitive tools, restrict file writes).
  - `0.8 – 1.0`: Critical Risk (Pause execution; require manual human approval).

#### C. `runtime/policy_evaluator.py`
- **Role:** Validates proposed contract updates against pre-defined safety rules, constitutional guidelines (Satya/Viveka), and corporate policies.
- **Key Functions:**
  - `evaluate_policy(contract: ExecutionContract, snapshot: BehaviorSnapshot) -> Tuple[bool, str]`
  - `assert_policy_consistency(proposed_contract: ExecutionContract) -> bool`

#### D. `runtime/permission_manager.py`
- **Role:** Interacts directly with `core/hands/sandbox.py`, `sandbox_hooks.py`, and `hysteresis_tool_governor.py` to enforce active permissions.
- **Key Functions:**
  - `apply_permissions(permissions: PermissionSet)`
  - `revoke_tool(tool_name: str)`
  - `grant_tool(tool_name: str)`
  - `lockdown_sandbox()`

#### E. `runtime/contract_engine.py` (ACP Main Orchestrator)
- **Role:** Executes the state evolution loop $C_{t+1} = f(C_t, O_t)$.
- **Key Functions:**
  - `initialize_contract(goal_id: str, initial_policy: dict) -> ExecutionContract`
  - `evaluate_step(snapshot: BehaviorSnapshot) -> ExecutionContract`
  - `renegotiate_contract(reason: str) -> ContractChangeEvent`

---

## 🔄 Phase 3: Deterministic Replay & Checkpoint Integration

Integrate ACP contract changes into NALA's crash-resilient persistence framework (`core/harness/session_contract.py` & `checkpoint.py`).

### 1. Ledger Recording
- Every `ContractChangeEvent` is appended to the execution ledger with a unique sequence number (LSN).
- Guarantees **>99% deterministic replay fidelity**: Replaying an execution trace recreates the exact contract version history ($C_0 \rightarrow C_1 \rightarrow \dots \rightarrow C_n$).

### 2. Checkpoint Restoration Integration
- Extend `SessionState` in `core/harness/session_contract.py`:
  ```python
  class SessionState(BaseModel):
      # Existing fields...
      active_contract: ExecutionContract
      contract_history: List[ContractChangeEvent] = Field(default_factory=list)
  ```
- Update `checkpoint.py` so that during crash recovery or context overflow handoff, the exact active contract state and permission bounds are fully restored.

---

## 🏛️ Phase 4: Runtime Constitution Layer (RCL) Integration

Synthesize all security and governance modules into a single unified Runtime Constitution Layer:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RUNTIME CONSTITUTION LAYER (RCL)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Sandbox Hardening (PEP 578 Hooks, Windows Job Objects, Linux Seccomp)    │
│ 2. Satya & Viveka Layers (Contextual Verification & Policy Gate)            │
│ 3. Ṛta Governor (Epistemic Score Calculation)                               │
│ 4. Hysteresis Tool Governor (Historical Tool Success Tracking)              │
│ 5. Adaptive Contract Protocol (Dynamic Permission Evolution Engine)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Integration Points in NALA Engine (`core/harness/nala_loop.py`):
1. **Pre-Step Check:** `RCL.before_step_execution()` queries `ContractEngine` to verify if the planned tool call is authorized under $C_t$.
2. **Post-Step Check:** `RCL.after_step_execution()` passes execution telemetry to `BehaviorMonitor`, computes new risk score, and triggers `ContractEngine.evaluate_step()`.
3. **Dynamic Reconfiguration:** If risk score exceeds thresholds, `PermissionManager` updates sandbox rules on-the-fly.

---

## 🧪 Phase 5: Benchmark Suite & Simulator (`benchmarks/` & `tests/`)

Build a comprehensive simulation harness to rigorously benchmark ACP against static permission models.

### 1. Files to Create
- `benchmarks/contract_benchmark.py`
- `tests/test_contract_engine.py`

### 2. 3-Phase Simulation Design (`contract_benchmark.py`)

```text
[Phase 1: Normal Execution] ──► [Phase 2: Suspicious Behavior] ──► [Phase 3: Recovery & Restrict]
- Standard tool calls           - Excessive retries               - Contract restricts permissions
- Low risk score (0.1)          - Anomalous tool request          - Risk score drops back to safe
- Full tool access              - Risk score escalates to 0.75    - Execution continues safely
```

### 3. Quantitative Target Metrics & Acceptance Criteria

| Metric | Target | Verification Method |
| :--- | :--- | :--- |
| 🔒 **Unauthorized Actions Blocked** | **100%** | Test script attempts unauthorized tool/file calls during restricted phase. |
| 🎯 **False-Positive Restrictions** | **< 2%** | Measure unnecessary restrictions during standard 1,000-step baseline runs. |
| ⚡ **Contract Update Latency** | **< 100 ms** | Benchmark time taken to evaluate $C_{t+1} = f(C_t, O_t)$. |
| 🔄 **Replay Fidelity** | **> 99%** | Compare original execution contract history against replayed contract history. |
| ⏱️ **Runtime Overhead** | **< 5%** | Measure latency added to total loop execution time. |

---

## 📁 File Creation Index

| File Path | Component | Description |
| :--- | :--- | :--- |
| `schemas/execution_contract.py` | Phase 1 | Pydantic v2 schemas for contracts, snapshots, and change events. |
| `runtime/__init__.py` | Phase 2 | Package init for runtime governance modules. |
| `runtime/behavior_monitor.py` | Phase 2 | Real-time behavior and telemetry snapshot collector. |
| `runtime/risk_estimator.py` | Phase 2 | Risk score and confidence calculation module. |
| `runtime/policy_evaluator.py` | Phase 2 | Constitutional policy and consistency evaluator. |
| `runtime/permission_manager.py` | Phase 2 | Interface to sandbox audit hooks and job objects. |
| `runtime/contract_engine.py` | Phase 2 | Primary ACP engine orchestrating contract state updates. |
| `benchmarks/contract_benchmark.py` | Phase 5 | 3-phase simulation benchmark script. |
| `tests/test_contract_engine.py` | Phase 5 | Comprehensive Pytest unit and integration test suite. |

---

## 🗓️ Step-by-Step Implementation Roadmap

1. **Step 1:** Create `schemas/execution_contract.py` and validate serialization/deserialization.
2. **Step 2:** Build `runtime/behavior_monitor.py` and `runtime/risk_estimator.py`.
3. **Step 3:** Implement `runtime/policy_evaluator.py`, `runtime/permission_manager.py`, and `runtime/contract_engine.py`.
4. **Step 4:** Integrate contract state models into `core/harness/session_contract.py` and `checkpoint.py`.
5. **Step 5:** Wire ACP engine into `core/harness/nala_loop.py` to form the Runtime Constitution Layer (RCL).
6. **Step 6:** Build `benchmarks/contract_benchmark.py` and `tests/test_contract_engine.py`. Run tests to verify target metrics.
