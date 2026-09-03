# 🧠 NALA-SRV-001 — Execution Entrypoint Migration Report

**Date:** 2026-08-24  
**Status:** 🟢 **PASSED & VERIFIED (LOCKED)**  
**Objective:** Migrate the real execution entrypoint from legacy server brain to the new NALA runtime without destroying existing architecture.

---

## 1. Executive Summary

During the forensic architecture audit (**NALA-ARCH-FORENSICS-001**), we proved that the newly engineered NALA runtime (`RuntimeState`, `NalaRunner`, `CompatibilityAdapter`) was isolated from the actual user entrypoint (`nala_server.py`). The UI continued to run the legacy `process_nala_session` loop, bypassing the state machine, concurrency controls, and canonical event queues.

Under **NALA-SRV-001**, the bridge has been completely unified:
1. **Authoritative RuntimeState**: Root `nala_server.py` now registers every incoming task directly into `RuntimeState` via canonical `TaskRequest`.
2. **NalaRunner Delegation**: Real execution is delegated to `NalaRunner.start(task_id)`, managing `NalaLoop`, `CheckpointManager`, `ContextTracker`, and safety gates in an isolated runner worker thread.
3. **CompatibilityAdapter Bridging**: The canonical event stream (`TaskEvent`) is consumed from `RuntimeState` and seamlessly translated into Socket.IO payloads (`step_update`, `session_complete`, etc.) via `CompatibilityAdapter`.
4. **Approval Hook Delegation**: User approval decisions submitted via `submit_approval` are routed directly to `nala_runner.submit_approval()`.

---

## 2. Architecture Comparison

### 🔴 Before NALA-SRV-001 (Legacy Monolith Bypass)
```text
NALA UI
   │
   ▼
Socket.IO (nala_server.py)
   │
   ▼
submit_prompt() ───► process_nala_session() [LEGACY THREAD]
                         │
                         ├─► Manually loops custom_step_handler
                         ├─► Threw NameError on runtime_state.consume_event()
                         └─► Bypassed NalaRunner & State Machine
```

### 🟢 After NALA-SRV-001 (Canonical Runtime Native)
```text
NALA UI
   │
   ▼
Socket.IO (nala_server.py)
   │
   ▼
submit_prompt()
   │
   ├─► 1. runtime_state.create_task(TaskRequest) ───► Authoritative Task State (CREATED)
   │
   ├─► 2. nala_runner.start(task_id) ───────────────► Background Worker Execution
   │       │                                            ├─► NalaLoop State Machine
   │       │                                            ├─► CheckpointManager (LSN & SHA-256)
   │       │                                            ├─► Adaptive Viveka & Satya Layers
   │       │                                            └─► Physical Filesystem Tool Execution
   │       ▼
   └─► 3. stream_events_to_client(session_id) ──────► Consumes RuntimeState event queue
           │                                            └─► Translated via CompatibilityAdapter
           ▼
     sio.emit('step_update', 'session_complete')
           │
           ▼
      NALA UI Frontend
```

---

## 3. Verification & Proof

### Test Suite Summary (68 / 68 PASSED)
- `tests/unit/test_runtime_state_authority.py` (10 tests) — **PASSED**
- `tests/unit/test_session_contract.py` (27 tests) — **PASSED**
- `tests/unit/test_checkpoint.py` (13 tests) — **PASSED**
- `tests/unit/test_nala_runner_integration.py` (5 tests) — **PASSED**
- `tests/unit/test_compatibility_adapter.py` (10 tests) — **PASSED**
- `tests/unit/test_feedback_ledger_rollover.py` (1 test) — **PASSED**
- `tests/integration/test_srv001_live_bridge.py` (1 test) — **PASSED**
- `tests/integration/test_srv001_socketio_e2e.py` (1 test) — **PASSED**

### Physical Execution Proof
- Real task execution through `submit_prompt` produced physical verified files with valid contents and SHA-256 integrity hashes on the physical filesystem.
- Frontend production bundle built cleanly with `npm run build` (0 errors).

---

## 4. Operational Signoff
- **Backend Entrypoint:** `nala_server.py` is unified with `nala_server/state.py` and `nala_server/nala_runner.py`.
- **Legacy Bypass:** Eliminated.
- **Server / Runtime Separation:** Locked.
