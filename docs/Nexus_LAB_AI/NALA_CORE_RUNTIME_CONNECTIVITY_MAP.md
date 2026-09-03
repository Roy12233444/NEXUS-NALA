# NALA Core Runtime Connectivity Quick-Reference Map
**Document ID**: `NALA-CORE-MAP-002`  
**Companion to**: `NALA-CORE-002 — Core Runtime Connectivity Baseline.md`  

---

## 🎯 High-Level Status Summary

```text
┌────────────────────────┬─────────────┬───────────┬──────────────┬──────────────┐
│ Subsystem              │ Implemented │ Tested    │ Live Runtime │ Observable   │
├────────────────────────┼─────────────┼───────────┼──────────────┼──────────────┤
│ 🧠 MemoryService       │ 🟢 REAL     │ 🔴 NO     │ 🔴 NO        │ 🟡 INIT ONLY │
│ 🧠 Planner.py          │ 🔴 0-BYTE   │ 🔴 NO     │ 🟡 MOCK      │ 🟢 YES (UI)  │
│ 🧠 SaptacoreCouncil    │ 🔴 0-BYTE   │ 🔴 NO     │ 🔴 NO        │ 🔴 NO        │
│ 🧠 TaskGraph           │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES (UI)  │
│ 🛡️ AdaptiveVivekaGate   │ 🟢 REAL     │ 🟢 YES    │ 🔴 NO        │ 🔴 NO        │
│ 🛡️ SatyaLayer          │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES       │
│ 🛡️ ṚtaGovernor & PID   │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES       │
│ 🦾 Process Sandbox     │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES       │
│ 🦾 Tool Registry       │ 🟢 REAL     │ 🟡 OLD    │ 🔴 BYPASSED  │ 🔴 NO        │
│ 🦾 Model Router        │ 🟢 REAL     │ 🔴 NO     │ 🔴 BYPASSED  │ 🔴 NO        │
│ ⚙️ NalaLoop Spine      │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES (UI)  │
│ ⚙️ CheckpointManager   │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES (WAL) │
│ ⚙️ ContextTracker      │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES (LOG) │
│ 🎯 Intent Classifier   │ 🟢 REAL     │ 🟢 YES    │ 🟢 YES       │ 🟢 YES (E2E) │
│ 🤝 Pramāṇa Router      │ 🟢 REAL     │ 🟢 YES    │ 🔴 BYPASSED  │ 🟡 CANNED    │
│ 🌐 AMP Client          │ 🟢 REAL     │ 🔴 NO     │ 🔴 NO        │ 🔴 NO        │
└────────────────────────┴─────────────┴───────────┴──────────────┴──────────────┘
```

---

## 🧭 Live Runtime Call Chain vs Dead-End Map

```text
[User Prompt via WebSocket]
       │
       ▼
1. core.intent.classifier.classify_intent ──────────────────► [🟢 LIVE]
       │
       ▼
2. nala_server.py: Session / TaskRequest ──────────────────► [🟢 LIVE]
       │
       ▼
3. NalaRunner ──► CompatibilityAdapter ─────────────────────► [🟢 LIVE]
       │
       ▼
4. core.harness.nala_loop.NalaLoop ─────────────────────────► [🟢 LIVE]
       ├── CheckpointManager.save_checkpoint (LSN) ────────► [🟢 LIVE]
       ├── ContextTracker.project_tokens ──────────────────► [🟢 LIVE]
       │
       ├── Planner (In-file fallback mock) ────────────────► [🟡 MOCK - planner.py is 0 B]
       │     └─► [DEAD END]: SaptacoreCouncil (0 B)
       │     └─► [DEAD END]: ṚtaValidator / Judge (0 B)
       │
       ├── Step: Initial Planning
       │     ├─► [DEAD END]: MemoryService.recall() ───────► [🔴 DISCONNECTED]
       │     └─► SatyaLayer.validate_output_truthfulness ──► [🟢 LIVE]
       │
       ├── Step: Execution Phase
       │     ├─► execute_tools_via_sandbox ────────────────► [🟢 LIVE in demo_files/]
       │     ├─► [DEAD END]: ToolRegistry.get_instance() ──► [🔴 BYPASSED]
       │     └─► [DEAD END]: AdaptiveVivekaGate ───────────► [🔴 DISCONNECTED]
       │
       └── Step: Reflection Synthesis
             ├─► Physical Disk Readback + SHA-256 Hash ────► [🟢 LIVE VERIFIED]
             ├─► [DEAD END]: MemoryService.capture() ──────► [🔴 DISCONNECTED]
             ├─► SatyaLayer.validate_output_truthfulness ──► [🟢 LIVE]
             └─► ṚtaGovernor & PID Evaluation ─────────────► [🟢 LIVE]
```

---

## 📋 Next Recommended Implementation Targets (002A–002K)

1. **`NALA-CORE-002A`**: **Memory Stabilization** — Wire `MemoryService` into `initial_planning` (recall) & `reflection_synthesis` (capture).
2. **`NALA-CORE-002B`**: **Planner Stabilization** — Implement dynamic goal decomposition in `core/brain/planner.py` to replace fallback mock.
3. **`NALA-CORE-002C`**: **Pramāṇa Epistemic Stabilization** — Connect `core/interaction/pramana_router.py` to generate dynamic cognitive pathways instead of canned telemetry.
4. **`NALA-CORE-002D`**: **Safety & Tool Registry Integration** — Wire `AdaptiveVivekaGate` and `ToolRegistry` into the execution pipeline.
