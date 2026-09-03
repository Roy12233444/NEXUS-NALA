# Transcendent Dual-Mode Framework Implementation Plan

## Overview
This document outlines the step‑by‑step implementation plan for the five layers of the **Transcendent Dual‑Mode Framework** described in `BACKLOG_Features/transcendent_dual_mode_framework.md`.  
The goal is to implement the Ṛta‑Score driven mode‑transition system (PRATYAKSHA ↔ PAROKSHA ↔ ATHAPRAPTI) by building each layer in dependency order.

---

## Current Status (as of 2026‑07‑10)

| Layer | Component(s) | Status |
|-------|--------------|--------|
| **Layer 3** – Adaptive Safety Gateway | `adaptive_viveka_gate.py` | ✅ Implemented (provides **Viveka‑Clarity**) |
| **Layer 4** – Truthfulness Validation | `context_aware_satya_layer.py` | ✅ Implemented (provides **Satya‑Truthfulness**) |
| **Layer 4** – Ṛta‑Feedback Control Loop | `rta_feedback_loop.py`, `rta_governor.py` | ⏳ **Next to implement** |
| **Layer 1** – Pramāṇa Interface Layer | `pramana_router.py`, `interaction_contract.py` | ⏳ Planned |
| **Layer 2** – Āgama‑Compliant Tool Orchestration | `agama_tool_selector.py`, `dharma_tool_governor.py` | ⏳ Planned |
| **Layer 3** – Saṃskāra‑Memory Integration | `samskara_encoder.py`, `samskara_decoder.py` | ⏳ Planned |
| **Layer 5** – Moksha‑Monitoring Observatory | `moksha_monitor.py`, `darshan_viewer.py` | ⏳ Planned |

*Note*: Layers are referred to by their numbers in the framework document, **not** by the order of implementation.

---

## Implementation Order

1. **Layer 4 – Ṛta‑Feedback Control Loop**  
   - **Why first?** This layer consumes the outputs of the already‑implemented Layer 3 (Viveka) and Layer 4 (Satya) to produce the Ṛta‑Score, which is the central metric for all mode‑transition decisions.  
   - **Files to create:**  
     - `core/safety/rta_feedback_loop.py` – computes Ṛta‑Score using:  
       * Viveka‑Clarity (from `adaptive_viveka_gate.py`)  
       * Satya‑Truthfulness (from `context_aware_satya_layer.py`)  
       * Placeholder estimators for **Dustara‑Complexity** (cognitive load) and **Ānanda‑Burden** (interaction latency/entropy)  
       * Outputs to:  
         - `pramana_router.py` (future) – for mode decisions  
         - `model_router.py` (future) – for model‑complexity adjustment  
         - `feedback_ledger.jsonl` – persistent log for alignment tracking  
     - `core/safety/rta_governor.py` – enforces Ṛta‑Bounds:  
       * Lower bound > 0.4 → gentle mode shift toward PRATYAKSHA if score too low  
       * Upper bound > 0.95 → triggers a sacred pause (60 s ATHAPRAPTI cooldown) to prevent overconfidence  
       * Emits corrective commands (mode shift requests, pause signals) to the fleet coordinator / model router.

2. **Layer 1 – Pramāṇa Interface Layer**  
   - Depends on the Ṛta‑Score from Layer 4 to select interaction modality.  
   - **Files to create:**  
     - `core/interaction/pramana_router.py` – selects the appropriate model (Gaṇeśa, Sarasvatī, Śiva) based on current Ṛta‑Score and mode.  
     - `core/interaction/interaction_contract.py` – extends the session contract with `pramana_state`, `Ṛta_metrics`, and `pramana_history`.

3. **Layer 2 – Āgama‑Compliant Tool Orchestration**  
   - Uses the current pramāṇa state (from Layer 1) to gate tool access.  
   - **Files to create:**  
     - `core/hands/agama_tool_selector.py` – wraps `tool_registry.py` and classifies tools as Śruti, Smṛti, or Anubhava.  
     - `core/hands/dharma_tool_governor.py` – enforces tool‑access rules based on pramāṇa state, Ṛta‑Score thresholds, and optional SAPTACORE council votes.

4. **Layer 3 – Saṃskāra‑Memory Integration**  
   - Encodes interaction patterns as saṃskāras (mental impressions) and makes them available for recall in PRATYAKSHA mode.  
   - **Files to create:**  
     - `memory/samskara_encoder.py` – compresses interaction patterns into AMP memory with śruti‑weighted hashing and karmic decay.  
     - `memory/samskara_decoder.py` – retrieves relevant saṃskāras using Anima‑Mahima scaling (single‑vector vs. graph expansion).

5. **Layer 5 – Moksha‑Monitoring Observatory**  
   - Provides observability and long‑term alignment tracking (moksha index, bandha events, sadhana ratio).  
   - **Files to create:**  
     - `observability/moksha_monitor.py` – computes moksha_index, tracks bandha_events, sadhana_ratio, and emits `moksha_report.json`.  
     - `observability/darshan_viewer.py` – real‑time visualization of Ṛta‑Score waveform, pramāṇa state transitions, and saṃskāra activation heatmap.

---

## Detailed Tasks for **Layer 4 – Ṛta‑Feedback Control Loop**

### 4.1 `rta_feedback_loop.py`
- **Inputs:**  
  - `VivekaClarity` value (0‑1) – expose via a getter from `AdaptiveVivekaGate` (e.g., `get_viveka_clarity()` or read from its metrics).  
  - `SatyaTruthfulness` value (0‑1) – expose via a getter from `ContextAwareSatyaLayer` (e.g., `get_truthfulness_score()`).  
  - `DustaraComplexity` – provisional metric: could be a moving average of recent token‑count / reasoning steps, or a placeholder static value (e.g., 0.3).  
  - `AnandaBurden` – provisional metric: could be average inter‑request latency or interaction entropy; placeholder (e.g., 0.2).  
- **Formula:**  
  ```python
  rta_score = (viveka_clarity * satya_truthfulness) / (dustara_complexity + ananda_burden + 1e-8)
  ```
- **Outputs:**  
  - Publish `rta_score` on a thread‑safe shared state (e.g., a singleton `RtaState` or via an event bus).  
  - Append a JSON line to `feedback_ledger.jsonl`: `{timestamp, viveka, satya, dustara, ananda, rta_score}`.  
  - Provide a simple API for subscribers: `get_current_rta()`, `subscribe(callback)`.

### 4.2 `rta_governor.py`
- **Subscribe** to `rta_feedback_loop` updates.  
- **Logic:**  
  - If `rta_score < 0.4` → request a **gentle shift** towards PRATYAKSHA (increase interactive responsiveness, decrease autonomous depth).  
  - If `rta_score > 0.95` → trigger a **sacred pause**:  
    - Command the fleet coordinator to enter ATHAPRAPTI mode for a fixed duration (e.g., 60 seconds).  
    - During the pause, suspend non‑essential tooling and log the event.  
  - Otherwise, maintain current mode.  
- **Output:** Emit commands to the fleet coordinator (e.g., via a shared `ModeRequest` queue) and optionally to the model router for temporary complexity adjustment.  
- **Logging:** Record each bound violation with timestamp and corrective action taken.

### 4.3 Integration Points
- Update `fleet/coordinator.py` to accept mode‑request messages from `rta_governor.py` (if not already present).  
- Ensure both `AdaptiveVivekaGate` and `ContextAwareSatyaLayer` expose simple getter methods for their current scores (add if missing).  
- Add unit tests for both new files under `tests/unit/` (e.g., `test_rta_feedback_loop.py`, `test_rta_governor.py`).

---

## Acceptance Criteria for Layer 4
- ✅ `rta_feedback_loop.py` computes a `float` Ṛta‑Score in \[0, ∞) using the formula above.  
- ✅ The score is published and persisted to `feedback_ledger.jsonl` at least once per second (or per evaluation cycle).  
- ✅ `rta_governor.py` correctly triggers a gentle mode shift when score < 0.4 and a sacred pause when score > 0.95.  
- ✅ Unit tests achieve ≥ 80 % line coverage for both new modules.  
- ✅ Manual sanity check: running a simple simulation with varying Viveka/Satya inputs produces expected Ṛta‑Score and governor actions.

---

## Next Immediate Action
Create the two files for **Layer 4**:
1. `core/safety/rta_feedback_loop.py`
2. `core/safety/rta_governor.py`

After these are implemented, tested, and integrated, proceed to **Layer 1** (`pramana_router.py` & `interaction_contract.py`).

--- 

*This plan is intended to be followed sequentially; each layer should be verified before moving to the next to ensure the Ṛta‑Score pipeline remains functional.*