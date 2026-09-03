# NALA — Advanced Project Structure
## Nexus Autonomous Long-Running Agent
**Nexus Lab AI Research Lab | Bengaluru, India**
**Version 1.0 | June 2026**

---

## 📁 Full Project Tree

```
nala/
│
├── README.md                          # Project overview + quickstart
├── BACKLOG.md                         # Future ideas — nothing touches main plan
├── pyproject.toml                     # Python project config + dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
│
├── docs/                              # All documentation
│   ├── NALA_Advanced_Plan.md          # Master architecture plan
│   ├── architecture.md                # Component deep-dives
│   └── api_reference.md               # Internal API contracts
│
├── config/                            # All configuration files
│   ├── __init__.py
│   ├── settings.py                    # Global settings + env loader
│   ├── done_condition.json            # Done condition spec template
│   └── model_routing.yaml             # Cost-aware model tier config
│
├── core/                              # Heart of NALA
│   │
│   ├── harness/                       # Phase 1 — Core Loop
│   │   ├── __init__.py
│   │   ├── nala_loop.py               # Main agent loop — the spine of everything
│   │   ├── session_contract.py        # Session data structure + schema
│   │   ├── checkpoint.py              # Checkpoint read / write logic
│   │   ├── task_graph.py              # Task decomposition + dependency graph
│   │   └── context_manager.py         # Context window tracking + reset trigger
│   │
│   ├── session/                       # Phase 2 — Session Layer (AMP)
│   │   ├── __init__.py
│   │   ├── amp_client.py              # Interface to AMP / Chiranjeevi
│   │   ├── event_log.py               # Append-only event log writer
│   │   ├── handoff.py                 # Session handoff file for context reset
│   │   └── recovery.py                # Crash recovery + state reconstruction
│   │
│   ├── brain/                         # Phase 3 — Brain Layer
│   │   ├── __init__.py
│   │   ├── planner.py                 # Goal decomposer — breaks task into graph
│   │   ├── saptacore_council.py       # 7-agent epistemic voting (τ = 0.618)
│   │   ├── judge.py                   # Output quality evaluator
│   │   └── rta_validator.py           # Ṛta-based done condition check
│   │
│   ├── hands/                         # Phase 5 — Hands Layer
│   │   ├── __init__.py
│   │   ├── executor.py                # Worker agent — runs inside sandbox
│   │   ├── sandbox.py                 # Sandboxed execution environment
│   │   ├── tool_registry.py           # Registry of all available tools
│   │   └── model_router.py            # Cost-aware model tier routing
│   │
│   └── safety/                        # Phase 4 — Safety Layer
│       ├── __init__.py
│       ├── rta_guard.py               # RTA-GUARD constitutional firewall
│       ├── usha.py                    # USHA cold start bootstrap protocol
│       └── circuit_breaker.py         # Cost limiter + rate breaker
│
├── memory/                            # AMP Memory Architecture
│   ├── __init__.py
│   ├── chiranjeevi.py                 # 7-substrate spore persistence layer
│   ├── tqb.py                         # Temporal Quarantine Buffer
│   ├── sdg.py                         # Semantic Distance Guard
│   ├── dronagiri.py                   # Holographic compression engine
│   ├── crystallizer.py                # Crystallization daemon (THETA=0.85)
│   └── anima_mahima.py                # Dual-threshold adaptive scaling router
│
├── agents/                            # Individual Agent Definitions
│   ├── __init__.py
│   ├── base_agent.py                  # Base class — all agents inherit this
│   ├── planner_agent.py               # Planner (Frontier model)
│   ├── executor_agent.py              # Executor / Worker (Small model)
│   ├── judge_agent.py                 # Judge / Critic (Frontier model)
│   ├── researcher_agent.py            # Researcher — context gathering (Mid model)
│   └── monitor_agent.py               # Ambient watchdog — always on (Small model)
│
├── tools/                             # Tool Registry Implementations
│   ├── __init__.py
│   ├── base_tool.py                   # Base tool class
│   ├── file_tool.py                   # File read / write / search
│   ├── shell_tool.py                  # Shell command execution
│   ├── api_tool.py                    # External API calls
│   ├── db_tool.py                     # Database read / write
│   └── search_tool.py                 # Web / knowledge search
│
├── fleet/                             # Multi-Agent Fleet Orchestration
│   ├── __init__.py
│   ├── coordinator.py                 # Fleet coordinator — top-level orchestrator
│   ├── fleet_registry.py              # Agent identity + role registry
│   └── fleet_monitor.py               # Ambient fleet watchdog + drift detector
│
├── observability/                     # Logging, Tracing, Metrics
│   ├── __init__.py
│   ├── tracer.py                      # OpenTelemetry distributed tracing
│   ├── logger.py                      # Structured event logger
│   └── metrics.py                     # Cost + performance + token metrics
│
├── tests/                             # All Tests
│   ├── unit/                          # Unit tests per module
│   │   ├── test_session_contract.py
│   │   ├── test_checkpoint.py
│   │   ├── test_task_graph.py
│   │   ├── test_tqb.py
│   │   ├── test_sdg.py
│   │   ├── test_rta_validator.py
│   │   └── test_model_router.py
│   │
│   ├── integration/                   # Integration tests across layers
│   │   ├── test_harness_loop.py
│   │   ├── test_amp_integration.py
│   │   ├── test_saptacore_voting.py
│   │   └── test_safety_pipeline.py
│   │
│   └── long_running/                  # Full end-to-end long run tests
│       ├── test_24hr_run.py
│       ├── test_crash_recovery.py
│       └── test_context_reset.py
│
├── scripts/                           # Utility Shell Scripts
│   ├── run_nala.sh                    # Start a fresh NALA run
│   ├── resume_session.sh              # Resume from last checkpoint
│   ├── check_budget.sh                # Check current API cost spend
│   └── inspect_session.sh            # Human-readable session log dump
│
└── data/                              # Runtime Data (gitignored)
    ├── sessions/                      # Live session state files
    ├── checkpoints/                   # Periodic checkpoint snapshots
    ├── logs/                          # Append-only event logs
    └── outputs/                       # Final task artifacts
```

---

## 📦 Total File Count

| Layer | Files |
|---|---|
| Core Harness | 5 |
| Session Layer | 4 |
| Brain Layer | 4 |
| Hands Layer | 4 |
| Safety Layer | 3 |
| Memory (AMP) | 6 |
| Agents | 6 |
| Tools | 6 |
| Fleet | 3 |
| Observability | 3 |
| Config | 4 |
| Tests | 13 |
| Scripts | 4 |
| Docs | 3 |
| **TOTAL** | **68 files** |

---

## 🔢 Build Order — File by File

Build in this exact sequence. Never skip ahead.

### 🔵 Phase 1 — Core Harness (Foundation)
```
1.  config/settings.py
2.  config/done_condition.json
3.  config/model_routing.yaml
4.  core/harness/session_contract.py
5.  core/harness/checkpoint.py
6.  core/harness/task_graph.py
7.  core/harness/context_manager.py
8.  core/harness/nala_loop.py          ← First working loop
```

### 🟡 Phase 2 — Session Layer
```
9.  core/session/event_log.py
10. core/session/handoff.py
11. core/session/recovery.py
12. memory/chiranjeevi.py
13. memory/tqb.py
14. memory/sdg.py
15. memory/dronagiri.py
16. memory/crystallizer.py
17. memory/anima_mahima.py
18. core/session/amp_client.py         ← AMP fully wired
```

### 🟠 Phase 3 — Brain Layer
```
19. agents/base_agent.py
20. agents/planner_agent.py
21. core/brain/planner.py
22. agents/judge_agent.py
23. core/brain/judge.py
24. core/brain/rta_validator.py
25. core/brain/saptacore_council.py    ← Council fully wired
```

### 🔴 Phase 4 — Safety Layer
```
26. core/safety/usha.py
27. core/safety/rta_guard.py
28. core/safety/circuit_breaker.py    ← Safety fully wired
```

### 🟣 Phase 5 — Hands Layer
```
29. tools/base_tool.py
30. tools/file_tool.py
31. tools/shell_tool.py
32. tools/api_tool.py
33. tools/db_tool.py
34. tools/search_tool.py
35. agents/executor_agent.py
36. core/hands/sandbox.py
37. core/hands/tool_registry.py
38. core/hands/model_router.py
39. core/hands/executor.py            ← Hands fully wired
```

### ⚪ Phase 6 — Fleet + Observability
```
40. agents/researcher_agent.py
41. agents/monitor_agent.py
42. fleet/fleet_registry.py
43. fleet/fleet_monitor.py
44. fleet/coordinator.py
45. observability/logger.py
46. observability/tracer.py
47. observability/metrics.py          ← Fleet fully wired
```

### ✅ Phase 7 — Tests + Scripts
```
48–60. tests/unit/*
61–64. tests/integration/*
65–67. tests/long_running/*
68.    scripts/*                      ← NALA complete
```

---

## 🔑 Key File Descriptions

### `core/harness/nala_loop.py`
The absolute spine of NALA. The main while-loop that wakes a session, picks the next task, routes it, executes it, checkpoints it, checks the done condition, and either loops or exits. Everything else serves this file.

### `core/harness/session_contract.py`
The data schema every single component reads and writes. Defines what a Session, Task, Checkpoint, and Result look like. Get this right before writing anything else.

### `config/done_condition.json`
The structured spec that defines what task completion looks like. The Ṛta Validator checks every output against this. The agent cannot self-certify — this file is the ground truth.

### `core/brain/saptacore_council.py`
The 7-agent epistemic voting engine. Replaces the single judge pattern. No task is approved unless it passes weighted consensus at threshold τ = 0.618.

### `memory/tqb.py`
Temporal Quarantine Buffer. New memories are held here before crystallization. Blocks memory drift at the source.

### `core/safety/usha.py`
USHA Protocol cold start bootstrap. Sets THETA_PROVISIONAL = 0.60 and suppresses crystallization until the first provisional cluster forms. NALA's safe boot sequence.

### `fleet/coordinator.py`
Top-level multi-agent orchestrator. Delegates to Planner, Researcher, Executor, Judge, and Monitor agents. Handles human approval gates for high-stakes actions.

---

## 📌 Rules During Build

> 1. Build files in the exact order above — no skipping
> 2. Every file gets a unit test before moving to the next phase
> 3. New ideas go into `BACKLOG.md` — never into the current build
> 4. Each phase must run end-to-end before starting the next
> 5. `data/` folder is always gitignored — no session state in repo

---

*Built at Nexus Lab AI Research Lab, Bengaluru*
*Jai Bajrang Bali 🙏*
