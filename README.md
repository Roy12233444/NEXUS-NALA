# 🧬 NALA — Nexus Autonomous Logic Architecture

**The Foundational Systems Layer for Long-Running, Self-Healing, and Sovereign Autonomous AI Organisms**

---

[![Tests](https://img.shields.io/badge/Tests-113%2F113%20Passing-brightgreen.svg)](./NALA/tests/)
[![Architecture](https://img.shields.io/badge/Architecture-4--Layer%20Sovereign%20Stack-blue.svg)](./NALA/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Nexus%20LAB%20AI-blueviolet.svg)](./NALA/)
[![Status](https://img.shields.io/badge/Status-Production%20%26%20Evaluation%20Ready-emerald.svg)](./NALA/)

> **Company:** Nexus LAB AI  
> **Founder & Principal Systems Architect:** Sourav Ray  
> **Direct Codebase Access:** [📁 Browse NALA Core Architecture & Codebase (`NALA/`)](./NALA/)  
> **Full Technical Specification:** [📖 NALA Official Product & Systems Documentation](./NALA/NALA_OFFICIAL_PRODUCT_DOCUMENTATION.md)  

---

## ⚡ Direct Repository Navigation

All core runtime implementations, cognitive engines, safety monitors, and test suites are maintained inside the canonical application directory:

```
NALA-Project/
├── 📁 NALA/                               # Primary Engine & Application Core
│   ├── 📁 core/                          # 4-Layer Autonomous Systems Core
│   │   ├── 📁 brain/                     # Planner, MemoryService, ModelRouter
│   │   ├── 📁 hands/                     # ToolRegistry, Execution Sandbox
│   │   ├── 📁 harness/                   # ARIES RecoveryEngine, Session Contract
│   │   ├── 📁 interaction/               # Epistemic Pramāṇa Router
│   │   └── 📁 safety/                    # Adaptive Viveka Gate, RTA Feedback Loop
│   ├── 📁 docs/                          # Architectural Specs & Research Corpus
│   │   └── 📁 Nexus_LAB_AI/              # NALA-UI & NALA-THEORY-001 Research
│   ├── 📁 nala_server/                   # SRV-001 WebSocket / HTTP Runtime Server
│   ├── 📁 src/                           # React + TypeScript Workstation Frontend
│   ├── 📁 tests/                         # 113 Unit, Integration & Soak Test Suites
│   │   ├── 📁 unit/                      # Core module tests (44 passed)
│   │   ├── 📁 integration/               # Cross-core orchestration (6 passed)
│   │   └── 📁 long_running/              # 24hr soak & crash recovery (63 passed)
│   └── 📄 NALA_OFFICIAL_PRODUCT_DOCUMENTATION.md  # Comprehensive 350-line Spec
├── 📄 README.md                          # Repository Landing Page & Overview
└── 📄 .gitignore                         # Comprehensive Git Hygiene Rules
```

👉 **[Click here to enter the NALA engine directory (`NALA/`)](./NALA/)**

---

## 1. Executive Summary & Core Value Proposition

The vast majority of modern "AI agent" frameworks are superficial prompt wrappers built over third-party APIs. When deployed in complex, multi-hour enterprise workflows, they inevitably suffer from **silent execution drift, context window exhaustion, inability to recover from process crashes, security sandbox escapes, and complete hallucination of success without physical evidence**.

**NALA (Nexus Autonomous Logic Architecture)** is an original, first-principles AI systems engine built from the ground up to solve these structural failure modes. NALA provides the deterministic operating infrastructure beneath autonomous agents—combining:

1. **Durable Transactional Persistence**: ARIES-style database recovery, monotonic Log Sequence Numbers (LSNs), and Write-Ahead Logging (WAL) that guarantee zero-corruption crash recovery.
2. **Mathematical Epistemic Verification (Pramāṇa)**: Strict separation between probabilistic LLM assertions and physical, cryptographic SHA-256 disk readback evidence.
3. **Deterministic Safety Gating (Adaptive Viveka)**: Kernel-level process isolation, non-bypassable reference monitors, and destructive command interception.
4. **Graph-Theoretic Dynamic Planning**: Directed Acyclic Graph (DAG) goal decomposition with pre-flight cycle detection ($O(|V| + |E|)$).
5. **Crash-Resilient Working Memory**: Flat-file semantic storage with $O(1)$ set deduplication, atomic POSIX file replacement, and SHA-256 Optimistic Concurrency Control (OCC).

> **Core Philosophy**: *"Complexity belongs in the system. Clarity belongs in the interface. Roots before fruits."*

---

## 2. The Structural Industry Gap

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CURRENT STATE vs NALA ARCHITECTURE                     │
├────────────────────────────┬────────────────────────────────────────────────┤
│ Conventional Agent Tools   │ NALA Autonomous Systems Engine                 │
├────────────────────────────┼────────────────────────────────────────────────┤
│ Volatile in-memory state   │ Monotonic on-disk LSN Checkpoints & WAL        │
│ Halts or dies on crash     │ Automated ARIES-style crash recovery engine    │
│ Trust based on model tone  │ Cryptographic SHA-256 byte readback evidence   │
│ Naive vector DB overhead   │ High-speed atomic flat-file memory + OCC       │
│ Superficial string prompts │ Capability-based Viveka security gateway       │
│ Linear, rigid chat logs    │ Dynamic DAG planning & step timeline streams   │
│ Foreign cloud dependence   │ 100% sovereign, local & on-premise executable  │
└────────────────────────────┴────────────────────────────────────────────────┘
```

---

## 3. The 4-Layer Systems Architecture

NALA is architected across four cleanly separated, decoupled operational domains:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. BRAIN (Cognitive & Deliberative Core)                                    │
│    - Dynamic Planner (TaskGraph, DAG decomposition, Tarjan's DFS cycles)   │
│    - MemoryService (Flat-file markdown, O(1) deduplication, OCC revision)  │
│    - Saptacore Council & Ṛta Validator (Epistemic consensus & validation)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. HANDS (Deterministic Tool Execution & Isolation)                         │
│    - ToolRegistry (Capability-based dispatch, idempotent execution)         │
│    - Epistemic Readback (Disk state SHA-256 vs LLM assertion verification)  │
│    - OS Process Isolation & Working Directory Enforcement                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. HARNESS (Durability, Checkpointing & Recovery Engine)                    │
│    - SessionContract (Strict JSON-schema session state authority)           │
│    - Checkpoint Engine (Monotonic LSN progression, zero-loss sync)          │
│    - Recovery Engine (ARIES-style Analysis, Redo, Undo phases)              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. INTERACTION & SAFETY (Epistemic & Ethical Boundary)                     │
│    - Pramāṇa Epistemic Router (Pratyakṣa, Anumāna, Upamāna, Śabda)          │
│    - Adaptive Viveka Gate (Risk-tiered security, high-risk human gates)     │
│    - RTA Feedback Loop (Rolling safety scores, sliding window rollover)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Empirical Verification & Test Suite Proofs

The NALA architecture is verified by **113 automated test suites**:

| Test Category | Suite Count | Target Subsystems Tested | Pass Rate |
| :--- | :---: | :--- | :---: |
| **Core Unit Tests** | `44` | Planner DAG, Memory OCC, Viveka Gate, Pramāṇa Router, Recovery Engine | **100% (44/44)** |
| **Integration Tests** | `6` | Cross-Core Orchestration, SRV-001 Live Bridge, SocketIO Telemetry | **100% (6/6)** |
| **24-Hour Soak & Crash** | `63` | Chaos Injection, Sudden SIGKILL Termination, Memory Rollover | **100% (63/63)** |
| **Total Test Suite** | **113** | **End-to-End Autonomous Systems Verification** | **100% (113/113)** |

### Running the Test Suites

```bash
# Navigate to the core engine directory
cd NALA

# Run full unit & integration verification
pytest tests/unit tests/integration -v

# Run crash recovery & soak verification
pytest tests/long_running/test_crash_recovery.py -v
```

---

## 5. Quick Start & Evaluation

### Prerequisites

- **Python:** 3.11 or higher
- **Node.js:** v18.0 or higher
- **Package Manager:** npm or pnpm

### 1. Launch the NALA Core Server

```bash
cd NALA
python -m venv .venv
# On Windows: .venv\Scripts\activate | On Unix: source .venv/bin/activate
pip install -r requirements.txt
python nala_server.py
```

*Server initializes on `http://localhost:3001` (WebSocket + HTTP).*

### 2. Launch the Autonomous Workstation Interface

```bash
cd NALA
npm install
npm run dev
```

*Frontend connects automatically to the local NALA runtime on `http://localhost:5173`.*

---

## 6. Official Documentation & Deep Dives

For the complete technical specification, API/WebSocket protocol contracts, mathematical formulations, and systems research, refer to:

- 📄 **[NALA Official Product & Systems Documentation](./NALA/NALA_OFFICIAL_PRODUCT_DOCUMENTATION.md)**
- 🔬 **[Nexus LAB AI Research Corpus](./NALA/docs/Nexus_LAB_AI/)**
  - `NALA-UI-RESEARCH-001`: Agentic Interface Archaeology
  - `NALA-UI-RESEARCH-002`: Dual-Agent Research Autopsy
  - `NALA-UI-RESEARCH-003`: Runtime Truth & UI Primitive Verification
  - `NALA-UI-RESEARCH-004`: Runtime-Derived UI Constraints & Information Architecture
  - `NALA-THEORY-001`: Comprehensive 10-Part AI/ML & Systems Engineering Curriculum

---

*© 2026 Nexus LAB AI. Proprietary & Confidential. Built with pride by Sourav Ray.*
