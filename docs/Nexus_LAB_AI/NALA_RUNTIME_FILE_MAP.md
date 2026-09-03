# NALA RUNTIME FILE MAP
**Audit Date**: August 2026  
**Status**: ARCHITECTURAL FORENSICS VERIFIED

---

## 1. Physical Component & Execution Graph

```
React Web UI (port 3000)
    │
    │ WebSocket / Socket.IO (port 3001)
    ▼
nala_server.py (Monolithic root server)
    ├── @sio.event 'submit_prompt'
    │     ├── chat path ──► handle_chat_message()
    │     └── task path ──► [DIVERGENCE POINT]
    │                         ├── [INTENDED]: NalaRunner (nala_server/nala_runner.py) ──► RuntimeState (nala_server/state.py)
    │                         └── [ACTUAL LEGACY]: process_nala_session() ──► Inline NalaLoop ──► NameError (unbound runtime_state)
```

---

## 2. Inventory of Server & Execution Files

| File Path | Role in System | Architecture Version | Status / Finding |
|---|---|---|---|
| `nala_server.py` (root) | Socket.IO Server & Transport (1,971 lines) | **Legacy Monolith** | **Active runtime entrypoint**. Contains old `ServerState` and bypasses `NalaRunner`. |
| `nala_server/nala_runner.py` | Orchestration Engine (2,080 lines) | **New Architecture** | Fully verified in unit tests, but **never invoked by `nala_server.py`**. |
| `nala_server/state.py` | Authoritative RuntimeState (2,250 lines) | **New Architecture** | Verified in unit tests. Referenced in `nala_server.py` but **never imported**, causing runtime crash. |
| `nala_server/contracts.py` | Canonical TaskEvent & TaskRequest (600 lines) | **New Architecture** | Canonical schema definitions. |
| `nala_server/compatibility_adapter.py` | Event Translator (750 lines) | **New Architecture** | Verified translator. Referenced in `stream_events_to_client` but never initialized at module level. |
| `nala_server/main.py` | Intended Modern Server Entrypoint | Empty (0 B) | Not implemented. |
| `nala_server/handlers.py` | Intended Modular Handlers | Empty (0 B) | Not implemented. |
| `src/services/websocketService.ts` | Frontend Socket.IO Client | Hybrid | Emits `submit_prompt` to port 3001. Listens for `step_update`, `session_created`, `session_complete`. |
| `src/components/features/chat/ChatSection.tsx` | Main Workbench View | Hybrid | Dispatches `submit_prompt` on user action. |
| `core/harness/nala_loop.py` | Core Execution Loop | Shared Core | Executed directly by `nala_server.py` bypassing `NalaRunner`. |
| `core/safety/rta_feedback_loop.py` | Ṛta Coherence Daemon | Transcendent Layer | Running background thread (bounded 1,000-entry rollover verified). |

---

## 3. Dependency & Execution Discrepancy Matrix

```
Intended Path:
ChatSection.tsx ──► websocketService.ts ──► nala_server.py ──► NalaRunner ──► RuntimeState ──► NalaLoop ──► TaskEvent ──► CompatibilityAdapter ──► Socket.IO ──► UI

Actual Path in Production:
ChatSection.tsx ──► websocketService.ts ──► nala_server.py ──► process_nala_session() ──► raw NalaLoop in Thread
                                                                        │
                                                                        └──► stream_events_to_client()
                                                                                  │
                                                                                  └──► NameError: 'runtime_state' is not defined (CRASHES STREAM)
```
