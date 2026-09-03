# 🔬 NALA-ARCH-FORENSICS-001: ARCHITECTURE FORENSIC AUDIT REPORT
**Author**: Kill-Critic Forensic Architecture Auditor  
**Date**: August 24, 2026  
**Status**: 🔴 **RED — CRITICAL ARCHITECTURAL BYPASS IDENTIFIED**

---

## 1. Executive Verdict

### **Verdict: 🔴 RED**

When a human user opens the real NALA UI and submits a task, **NALA DOES NOT execute through the new NALA server architecture (`NalaRunner` + `RuntimeState`)**. 

Instead, it executes through the **legacy monolithic `nala_server.py` path**, which:
1. Completely **bypasses `NalaRunner`**.
2. Manually spawns an ad-hoc `threading.Thread` around `NalaLoop`.
3. Crashes immediately inside `stream_events_to_client()` due to an unimported/uninitialized `runtime_state` variable (`NameError: name 'runtime_state' is not defined`), causing the Socket.IO event stream to abort on the very first tick.
4. Leaves the UI in an un-updated state where live steps are never delivered to the client.

---

## 2. Intended vs. Actual Execution Architecture

### Intended Architecture
```text
React UI (ChatSection.tsx)
    │
    ▼ emit('submit_prompt')
websocketService.ts (port 3001)
    │
    ▼
nala_server.py (Thin transport bridge)
    │
    ▼ TaskRequest
RuntimeState (nala_server/state.py)
    │
    ▼ start_session()
NalaRunner (nala_server/nala_runner.py)
    │
    ▼ execute()
NalaLoop (core/harness/nala_loop.py)
    │
    ▼ TaskEvent stream
RuntimeState.consume_event()
    │
    ▼
CompatibilityAdapter (nala_server/compatibility_adapter.py)
    │
    ▼ emit('step_update', 'session_complete')
React UI (Live Execution Workbench)
```

### Actual Runtime Path (Discovered in Code Forensics)
```text
React UI (ChatSection.tsx)
    │
    ▼ emit('submit_prompt')
nala_server.py (Legacy monolith, line 848)
    │
    ▼
submit_prompt() (line 904)
    │
    ▼
server_state.create_session() (Legacy in-memory dictionary)
    │
    ▼
asyncio.create_task(process_nala_session(session_id, sid)) (line 917)
    │
    ▼ [BYPASS: NalaRunner is NEVER invoked!]
process_nala_session() (lines 1044-1440)
    ├── Spawns ad-hoc threading.Thread(target=run_loop)
    └── Calls stream_events_to_client(session_id, client_sid) (line 1499)
            │
            ▼ line 1522
            canonical_ev = runtime_state.consume_event(timeout=0.01)
            💥 NameError: name 'runtime_state' is not defined
            │
            ▼ line 1572
            except Exception as e: logger.error(...) -> break
            💥 Stream loop exits immediately!
            💥 UI receives ZERO step_update or completion events!
```

---

## 3. Code-Level Forensic Evidence

### Evidence Item A: `NalaRunner` is Never Instantiated or Invoked in `nala_server.py`
- **File**: [`nala_server.py`](file:///E:/NALA-Project/NALA/nala_server.py)
- **Line 1–1971**: Exact occurrences of `class NalaRunner` or `from nala_server.nala_runner import NalaRunner` = **0**.
- **Finding**: While `nala_server/nala_runner.py` was thoroughly tested in isolated unit tests (`tests/unit/test_nala_runner_integration.py`), `nala_server.py` was never refactored to delegate execution to `NalaRunner`.

### Evidence Item B: Unimported `runtime_state` and `compat_adapter` Crash Event Streaming
- **File**: [`nala_server.py`](file:///E:/NALA-Project/NALA/nala_server.py#L1515-L1575)
- **Code Region**:
  ```python
  1521: while True:
  1522:     canonical_ev = runtime_state.consume_event(timeout=0.01)
  1523:     if canonical_ev is None:
  1524:         break
  1525:     if canonical_ev.session_id == session_id:
  1526:         adapted = compat_adapter.to_socket_event(canonical_ev)
  ```
- **Finding**: Neither `runtime_state` nor `compat_adapter` are defined in the global module scope of `nala_server.py`. When line 1522 runs, Python throws `NameError: name 'runtime_state' is not defined`. Line 1572 catches the error and executes `break`, terminating the streaming generator before any events reach the client.

### Evidence Item C: Dual State Split (Legacy `ServerState` vs. `RuntimeState`)
- **File**: [`nala_server.py`](file:///E:/NALA-Project/NALA/nala_server.py#L140-L200)
- **Code Region**:
  `server_state = ServerState()` maintains `self.active_sessions = {}` and `self.event_queue = Queue()`.
- **Finding**: `nala_server.py` mutates `server_state` rather than `RuntimeState`. As a result, state authority is fractured between the old dictionary and the new state engine.

---

## 4. Why Antigravity Terminal Succeeded While the UI Failed

1. **Terminal Unit Tests (`pytest`)**:
   - Directly imported `RuntimeState` and `NalaRunner` from `nala_server.state` and `nala_server.nala_runner`.
   - Executed synthetic sessions directly through `NalaRunner.start()`.
   - Verified that `NalaRunner` works in isolation.

2. **Real NALA UI Running in Browser**:
   - Sends WebSocket frame `submit_prompt` to `http://localhost:3001`.
   - `nala_server.py` receives the frame and enters `submit_prompt` -> `process_nala_session`.
   - Hits the missing import in `stream_events_to_client` and terminates the stream.
   - The UI never receives live progress signals because `NalaRunner` was never wired into `nala_server.py`.

---

## 5. Primary Bottleneck & Root Cause

### **Primary Root Cause**:
**`nala_server.py` was never wired to use `NalaRunner` and `RuntimeState`.** It still runs the old monolithic execution handler (`process_nala_session`) which has broken references to unimported `runtime_state` variables.

### **Secondary Contributing Causes**:
1. **Broken Event Streaming**: `stream_events_to_client()` in `nala_server.py` aborts immediately due to `NameError`.
2. **Scaffold Folder Disconnect**: `nala_server/main.py` and `nala_server/handlers.py` are empty 0-byte placeholders, while the live server is the 1,971-line legacy `nala_server.py` in the root folder.
3. **State Split**: State mutation occurs in `ServerState` instead of canonical `RuntimeState`.

---

## 6. Exact Answers to Core Questions

### Question 1:
> *"When I open the real NALA UI and submit a task, am I actually executing the NEW NALA server architecture we designed, or am I still executing some part of the OLD NALA architecture?"*

**Direct Forensic Answer**:
You are executing the **OLD NALA architecture**. `NalaRunner` is completely bypassed, and `nala_server.py` runs a legacy monolithic loop that crashes its own Socket.IO event streamer.

### Question 2:
> *"What is the single most important bottleneck we should fix BEFORE performing NALA-UI-001?"*

**Direct Forensic Answer**:
**Refactor `nala_server.py:submit_prompt` to instantiate and delegate task execution to `NalaRunner` using `RuntimeState` and `CompatibilityAdapter`**, replacing the legacy `process_nala_session` function with the verified `NalaRunner` async pipeline.

---

## 7. Recommended Minimum Fix & Next Steps

1. **DO NOT touch the UI yet**.
2. **Thin `nala_server.py`**:
   - Import `RuntimeState` from `nala_server.state`.
   - Import `NalaRunner` from `nala_server.nala_runner`.
   - Import `CompatibilityAdapter` from `nala_server.compatibility_adapter`.
   - In `@sio.event submit_prompt`:
     - Create `TaskRequest`.
     - Dispatch to `NalaRunner.start(task_req)`.
     - Stream canonical `TaskEvent`s via `CompatibilityAdapter.to_socket_event()` to Socket.IO.
3. **Verify with a real browser submission** before beginning NALA-UI-001.

---
**Audit Complete — No further code edits performed per Forensic Audit protocol.**
