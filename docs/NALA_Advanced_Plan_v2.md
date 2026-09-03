# NALA — Nexus Autonomous Long-Running Agent
## Advanced Architecture Plan & Design Blueprint
**Nexus Lab AI Research Lab | Bengaluru, India**
**Version 1.0 | June 2026**

---

## 📌 Executive Summary

NALA (Nexus Autonomous Long-Running Agent) is the long-running agent harness at the core of Nexus Lab's agentic infrastructure. It goes beyond what Google, Anthropic, and Cursor have published — by integrating the **ANJANEYA Memory Protocol (AMP)** for persistence, **SAPTACORE's 7-agent council** for self-verification, and **RTA-GUARD's constitutional firewall** for safety-gated done conditions. NALA is designed to operate across hours, days, or weeks — across multiple context windows, sandboxes, and sessions — without losing fidelity, alignment, or traceability.

---

## 🎯 Core Design Goals

| Goal | What It Means |
|---|---|
| **Infinite Horizon** | Run for days/weeks without context degradation |
| **Zero Session Loss** | Any crash is fully recoverable from AMP state |
| **Constitutional Done Condition** | Agent cannot self-certify completion — must pass Ṛta validator |
| **Semantic Failure Recovery** | Detects wrong-output, not just crash-recovery |
| **Cost-Aware Routing** | Small models for workers, frontier models only for planners/judges |
| **Memory Governance** | Prevents memory drift via Temporal Quarantine Buffer |

---

## 🏗️ High-Level Architecture

```mermaid
graph TB
    classDef brain fill:#4B7CF3,stroke:#2a5cd4,color:#fff
    classDef hands fill:#E85D26,stroke:#c44a14,color:#fff
    classDef session fill:#C8A96E,stroke:#a8893e,color:#000
    classDef safety fill:#2ecc71,stroke:#27ae60,color:#fff
    classDef external fill:#95a5a6,stroke:#7f8c8d,color:#fff

    HUMAN["👤 Human / Task Input"]:::external
    OUTPUT["📦 Final Output / Artifacts"]:::external

    subgraph NALA["⚡ NALA — Nexus Autonomous Long-Running Agent"]

        subgraph BRAIN["🧠 BRAIN LAYER"]
            PLANNER["Planner Agent\n(Goal Decomposer)"]:::brain
            SAPTACORE["SAPTACORE Council\n(7-Agent Epistemic Voting\nτ = 0.618)"]:::brain
            JUDGE["Judge Agent\n(Ṛta Validator)"]:::brain
        end

        subgraph HANDS["⚙️ HANDS LAYER"]
            EXECUTOR["Executor Agent\n(Worker)"]:::hands
            SANDBOX["Sandboxed\nExecution Environment"]:::hands
            TOOLS["Tool Registry\n(APIs, DBs, FS, Shell)"]:::hands
            ROUTER["Cost-Aware\nModel Router"]:::hands
        end

        subgraph SESSION["💾 SESSION LAYER — AMP"]
            CHIRANJEEVI["Chiranjeevi\nPersistence Layer\n(7-substrate spore)"]:::session
            TQB["Temporal Quarantine\nBuffer"]:::session
            SDG["Semantic Distance\nGuard"]:::session
            DRONAGIRI["Dronagiri\nHolographic Compression"]:::session
            CRYSTALIZER["Crystallization\nDaemon"]:::session
        end

        subgraph SAFETY["🛡️ SAFETY LAYER"]
            RTAGUARD["RTA-GUARD\nConstitutional Firewall"]:::safety
            USHA["USHA Protocol\nCold Start Bootstrap\n(THETA_PROVISIONAL=0.60)"]:::safety
            DONECOND["Done Condition\nValidator\n(Ṛta Rules)"]:::safety
        end

    end

    HUMAN -->|"Task Spec + Done Condition"| PLANNER
    PLANNER -->|"Task Graph"| SAPTACORE
    SAPTACORE -->|"Approved Task"| ROUTER
    ROUTER -->|"Route to right model tier"| EXECUTOR
    EXECUTOR -->|"Execute"| SANDBOX
    SANDBOX -->|"Tool Calls"| TOOLS
    TOOLS -->|"Results"| RTAGUARD
    RTAGUARD -->|"Filtered Output"| JUDGE
    JUDGE -->|"Pass / Fail / Re-plan"| DONECOND
    DONECOND -->|"Not Done → Loop"| PLANNER
    DONECOND -->|"Done → Persist"| CHIRANJEEVI
    CHIRANJEEVI --> TQB
    TQB --> SDG
    SDG --> DRONAGIRI
    DRONAGIRI --> CRYSTALIZER
    CRYSTALIZER -->|"Crystallized Memory"| SAPTACORE
    USHA -->|"Bootstrap on cold start"| PLANNER
    CHIRANJEEVI -->|"Full Output"| OUTPUT
```

---

## 🔄 Main NALA Agent Loop

```mermaid
flowchart TD
    A([🚀 START / WAKE]) --> B{First Run\nor Resume?}

    B -->|First Run| C[USHA Bootstrap\nTHETA_PROVISIONAL = 0.60]
    B -->|Resume| D[Load Session State\nfrom AMP Chiranjeevi]

    C --> E[Parse Task Spec\n+ Done Condition File]
    D --> E

    E --> F[SAPTACORE Council\nDecompose into Task Graph\nτ = 0.618 threshold]

    F --> G{Any Tasks\nRemaining?}

    G -->|No tasks left| H[Run Done Condition\nṚta Validator]
    G -->|Tasks remain| I[Cost-Aware Model Router\nSelect model tier for task]

    I --> J[Executor Agent\nRun in Sandboxed Env]

    J --> K{Execution\nResult?}

    K -->|Tool Error| L[Retry with\nBackoff + Log]
    K -->|Success| M[RTA-GUARD\nFilter Output]
    K -->|Crash| N[Checkpoint Recovery\nfrom last AMP snapshot]

    L --> J
    N --> E

    M --> O{RTA-GUARD\nApproved?}

    O -->|Blocked| P[Flag for\nHuman Review\nor Re-plan]
    O -->|Approved| Q[Judge Agent\nEvaluate Output Quality]

    P --> F
    Q --> R{Judge\nVerdict?}

    R -->|Fail — Re-plan| S[Semantic Failure\nRecovery\nUpdate Task Graph]
    R -->|Pass — Checkpoint| T[Write to AMP\nTemporal Quarantine Buffer]

    S --> F
    T --> U[Semantic Distance\nGuard Check]

    U --> V{Memory\nDrift Detected?}

    V -->|Drift| W[Quarantine Memory\nBlock Crystallization]
    V -->|Clean| X[Dronagiri Compression\n+ Crystallization Daemon]

    W --> F
    X --> Y[Update Session Log\nAppend-Only Event]

    Y --> Z{Context Window\nNearing Limit?}

    Z -->|Yes| AA[Full Context Reset\nStructured Handoff File\nto Next Session]
    Z -->|No| G

    AA --> A

    H --> AB{Ṛta Validator\nPasses?}

    AB -->|Fail| AC[Agent Cannot\nSelf-Certify\nForce Re-plan]
    AB -->|Pass| AD([✅ TASK COMPLETE\nPersist Final Artifacts])

    AC --> F
```

---

## 💾 Session Lifecycle — From Cold Start to Completion

```mermaid
sequenceDiagram
    autonumber
    participant H as 👤 Human
    participant USHA as USHA Protocol
    participant PLANNER as Planner Agent
    participant SAPTACORE as SAPTACORE Council
    participant EXECUTOR as Executor + Sandbox
    participant RTAGUARD as RTA-GUARD
    participant JUDGE as Judge Agent
    participant AMP as AMP / Chiranjeevi

    H->>PLANNER: Submit Task Spec + Done Condition
    Note over PLANNER: Session 1 starts

    alt Cold Start
        PLANNER->>USHA: Request bootstrap
        USHA-->>PLANNER: THETA_PROVISIONAL = 0.60\nGenesis Substrate loaded
    else Resume from crash
        PLANNER->>AMP: wake(sessionId)
        AMP-->>PLANNER: Reconstruct state from\nChiranjeevi persistence log
    end

    PLANNER->>SAPTACORE: Decompose task into graph
    SAPTACORE-->>PLANNER: Approved task list\n(epistemic vote passed τ=0.618)

    loop For each task
        PLANNER->>EXECUTOR: Assign next task
        EXECUTOR->>EXECUTOR: Run in sandboxed env
        EXECUTOR->>RTAGUARD: Submit output for safety check
        RTAGUARD-->>EXECUTOR: Approved / Blocked
        EXECUTOR->>JUDGE: Submit for quality evaluation
        JUDGE-->>PLANNER: Pass → checkpoint\nFail → re-plan
        PLANNER->>AMP: Checkpoint progress
        AMP->>AMP: TQB → SDG → Dronagiri\n→ Crystallization
    end

    Note over PLANNER,JUDGE: Context window nearing limit

    PLANNER->>AMP: Write structured handoff file
    AMP-->>PLANNER: Handoff confirmed

    Note over PLANNER: Session 1 ends\nSession 2 starts

    PLANNER->>AMP: wake(sessionId)
    AMP-->>PLANNER: Full state reconstructed\nfrom 7-substrate spore

    PLANNER->>JUDGE: Run Done Condition Validator\n(Ṛta Rules)
    JUDGE-->>H: ✅ Task Complete — Final Artifacts
```

---

## 🧠 AMP Memory Architecture in Long-Running Context

```mermaid
graph LR
    classDef input fill:#4B7CF3,color:#fff
    classDef process fill:#E85D26,color:#fff
    classDef store fill:#C8A96E,color:#000
    classDef guard fill:#2ecc71,color:#fff

    RAW["Raw Agent\nObservations"]:::input
    EVENTS["Append-Only\nEvent Log"]:::input

    subgraph TQB_ZONE["🔒 Temporal Quarantine Buffer"]
        TQB["New memories held\nfor N turns before\ncrystallization"]:::guard
    end

    subgraph SDG_ZONE["🔍 Semantic Distance Guard"]
        SDG["Distance check vs\nexisting crystallized\nmemories\nBlock if drift > threshold"]:::guard
    end

    subgraph CRYSTAL_ZONE["💎 Crystallization Daemon"]
        CRYSTAL["Provenance-gated\ncrystallization\nTHETA_CRYSTAL = 0.85"]:::process
    end

    subgraph CHIRANJEEVI["♾️ Chiranjeevi Persistence Layer"]
        PARAM["Param Hash\n+ Erasure Code"]:::store
        SPORE["7-Substrate\nSpore Distribution"]:::store
        COMPRESS["Dronagiri Holographic\nCompression\n(zero-null retrieval)"]:::store
    end

    subgraph RETRIEVAL["🔎 Sankat Mochan Retrieval"]
        PROACTIVE["Proactive distress\ndetection during\ntoken generation"]:::guard
        SEARCH["Context-aware\nmemory search"]:::process
    end

    ANIMA_MAHIMA["Anima-Mahima\nAdaptive Scaling\n(dual-threshold routing)"]:::process

    RAW --> TQB_ZONE
    EVENTS --> TQB_ZONE
    TQB_ZONE --> SDG_ZONE
    SDG_ZONE -->|"Clean"| CRYSTAL_ZONE
    SDG_ZONE -->|"Drift detected"| TQB_ZONE
    CRYSTAL_ZONE --> CHIRANJEEVI
    CHIRANJEEVI --> RETRIEVAL
    RETRIEVAL --> ANIMA_MAHIMA
    ANIMA_MAHIMA -->|"Retrieved context"| RAW
```

---

## 🤖 Multi-Agent Fleet Orchestration

```mermaid
graph TD
    classDef coord fill:#4B7CF3,color:#fff
    classDef specialist fill:#E85D26,color:#fff
    classDef safety fill:#2ecc71,color:#fff
    classDef memory fill:#C8A96E,color:#000

    COORDINATOR["🎯 COORDINATOR AGENT\n(SAPTACORE Council)"]:::coord

    subgraph FLEET["Agent Fleet"]
        direction TB
        PLANNER_A["📋 Planner Agent\nGoal decomposition\n(Frontier model)"]:::specialist
        RESEARCHER["🔬 Researcher Agent\nContext gathering\n(Mid-tier model)"]:::specialist
        EXECUTOR_A["⚙️ Executor Agent\nCode / task execution\n(Small model)"]:::specialist
        CRITIC["🧐 Critic / Judge Agent\nQuality evaluation\n(Frontier model)"]:::specialist
        MONITOR["📡 Monitor Agent\nAmbie​nt watchdog\n(Small model — always on)"]:::specialist
    end

    subgraph SAFETY_LAYER["Safety + Memory"]
        RTAGUARD_F["RTA-GUARD\nAll outputs filtered"]:::safety
        AMP_F["AMP\nShared session state\nper agent identity"]:::memory
    end

    HUMAN_IN["👤 Human Input"]
    HUMAN_APPROVAL["✋ Human Approval\nGate (optional)"]
    OUTPUT_F["📦 Final Artifacts\n+ Audit Trail"]

    HUMAN_IN --> COORDINATOR
    COORDINATOR -->|"Assign research task"| RESEARCHER
    COORDINATOR -->|"Assign plan task"| PLANNER_A
    PLANNER_A -->|"Assign execution task"| EXECUTOR_A
    RESEARCHER -->|"Context"| PLANNER_A
    EXECUTOR_A -->|"Output"| RTAGUARD_F
    RTAGUARD_F -->|"Filtered output"| CRITIC
    CRITIC -->|"Pass → Persist"| AMP_F
    CRITIC -->|"Fail → Re-assign"| COORDINATOR
    MONITOR -->|"Alert on drift/anomaly"| COORDINATOR
    AMP_F -->|"Shared memory"| COORDINATOR
    COORDINATOR -->|"High-stakes action"| HUMAN_APPROVAL
    HUMAN_APPROVAL -->|"Approved"| EXECUTOR_A
    COORDINATOR -->|"Done condition met"| OUTPUT_F
```

---

## 🗺️ Cost-Aware Model Routing Strategy

```mermaid
graph LR
    TASK["Incoming Task"]

    TASK --> CLASSIFY{Classify\nTask Type}

    CLASSIFY -->|"Strategic / Planning"| FRONTIER["🔴 Frontier Model\ne.g. Claude Opus\nHigh cost — used sparingly"]
    CLASSIFY -->|"Evaluation / Judging"| FRONTIER
    CLASSIFY -->|"Code Generation\nMid complexity"| MID["🟡 Mid-Tier Model\ne.g. Claude Sonnet\nBalanced cost/quality"]
    CLASSIFY -->|"Repetitive Execution\nFormatting / Boilerplate"| SMALL["🟢 Small Model\ne.g. Claude Haiku\nLow cost — high volume"]
    CLASSIFY -->|"Ambient Monitoring\nAlways-on watch"| SMALL

    FRONTIER --> BUDGET{Budget\nCheck}
    MID --> BUDGET
    SMALL --> BUDGET

    BUDGET -->|"Within limit"| EXECUTE["Execute Task"]
    BUDGET -->|"Limit exceeded"| BREAKER["Circuit Breaker\nPause + Alert Human"]
```

---

## 📅 Implementation Phases

```mermaid
gantt
    title NALA — Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1 — Core Harness
    Loop structure + Session contract       :p1a, 2026-06-20, 7d
    Done condition file format              :p1b, after p1a, 5d
    Checkpoint format design                :p1c, after p1b, 5d

    section Phase 2 — Session Layer
    AMP integration (Chiranjeevi)           :p2a, after p1c, 7d
    TQB + Semantic Distance Guard           :p2b, after p2a, 5d
    Dronagiri context compaction            :p2c, after p2b, 5d

    section Phase 3 — Brain Layer
    SAPTACORE council wiring                :p3a, after p2c, 7d
    Planner agent design                    :p3b, after p3a, 5d
    Judge + Ṛta validator                   :p3c, after p3b, 5d

    section Phase 4 — Safety Layer
    RTA-GUARD integration                   :p4a, after p3c, 5d
    USHA cold start protocol                :p4b, after p4a, 4d

    section Phase 5 — Hands Layer
    Sandboxed execution environment         :p5a, after p4b, 7d
    Tool registry + model router            :p5b, after p5a, 5d
    Cost-aware routing + circuit breaker    :p5c, after p5b, 4d

    section Phase 6 — Integration
    Full system integration test            :p6a, after p5c, 7d
    Long-running test run (GRAMVANI)        :p6b, after p6a, 5d
    Documentation + arXiv prep              :p6c, after p6b, 5d
```

---

## 🛠️ Technology Stack

| Layer | Component | Technology |
|---|---|---|
| **Brain** | Planner + Judge | Rust / Python |
| **Brain** | SAPTACORE Council | Rust (Sutratman bus) |
| **Hands** | Executor + Sandbox | Docker + Wasmtime |
| **Hands** | Tool Registry | Rust/Axum REST |
| **Session** | AMP Chiranjeevi | Rust (erasure coding) |
| **Session** | Event Log | Append-only flat file + SQLite |
| **Safety** | RTA-GUARD | Rust (existing 70k lines) |
| **Safety** | USHA Bootstrap | Rust |
| **Routing** | Cost-Aware Router | Python |
| **Infra** | Deployment | Docker Compose → Cloud Run |
| **Observability** | Logs + Traces | OpenTelemetry |

---

## ⚡ How NALA Beats the Article

| What Article Says | What NALA Does Better |
|---|---|
| Append-only event log | **AMP Chiranjeevi** — 7-substrate spore + erasure coding. Survives infra death. |
| "Summarize to compress context" | **Dronagiri Holographic Compression** — zero-null retrieval guarantee |
| Single judge agent | **SAPTACORE 7-agent council** — weighted epistemic voting τ=0.618 |
| Memory drift warning | **Temporal Quarantine Buffer + SDG** — actively quarantines drifting memory |
| Basic security mention | **RTA-GUARD** — 70,000+ lines, quantum-resistant crypto, constitutional rules |
| Cold start from log | **USHA Protocol** — THETA_PROVISIONAL bootstrap, compression suppression until first provisional cluster |
| Static done condition file | **Ṛta Validator** — living constitutional done condition, agent cannot self-certify |
| Cost mentioned as unsolved | **Cost-Aware Model Router + Circuit Breaker** — built-in, first-class |

---

## 🔑 Three Golden Rules of NALA

> **Rule 1 — State lives outside the model.**
> The agent is amnesiac. AMP is not. Every session starts from AMP, not from the model's memory.

> **Rule 2 — The agent cannot grade its own work.**
> SAPTACORE council + Ṛta Validator are structurally separate from the generator. No self-certification ever.

> **Rule 3 — Memory is infrastructure, not an afterthought.**
> Memory drift is an active threat. TQB + SDG govern memory like microservices, with identity, versioning, and quarantine.

---

*Built at Nexus Lab AI Research Lab, Bengaluru*
*Jai Bajrang Bali 🙏*
