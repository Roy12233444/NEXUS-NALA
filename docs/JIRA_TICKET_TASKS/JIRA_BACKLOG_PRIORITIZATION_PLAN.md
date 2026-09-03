# NALA Backlog Features — Technical Implementation & Prioritization Plan

**Nexus Lab AI Research Lab | Bengaluru, India**  
**Version:** 1.0.0  
**Context:** Following the successful completion of **Epic NALA-001 (Phase 1)**

---

## 1. Executive Summary & Strategy 🎯

With the NALA Core Run-Loop, checkpointing, compaction, and crash recovery (JIRA-001 through JIRA-007) fully implemented and verified on Windows, NALA has a bulletproof survival loop. 

Our next objective is to transition from **Core Survival** to **Practical Efficiency and Live Monitoring (Phase 2)**. 

To achieve this, we prioritize two critical **P0 Quick Wins**:
1. **`VIVEK Router`** — A dynamic LLM routing model to reduce development/testing costs by up to 70%.
2. **`SANKET Protocol`** — An event-driven webhook notification framework to alert you of milestones, warnings, or recoveries directly on your phone/channels.

---

## 2. Priority Matrix 📊

Based on effort-to-impact ratios, we organize the backlog into the following phases:

| Priority | Feature | Effort | What It Does | Strategic Value | Build Phase |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | **`VIVEK Router`** 🔀 | **Low** (3 files) | 4-tier model routing engine. Routes easy steps to cheap models and hard tasks to smart models. | **70% Cost Saving:** Drastically lowers token expenditure during long runs. | Phase 2 (Next) |
| **P0** | **`SANKET Protocol`** 🔔 | **Low** (5 files) | Ṛta-gated notification system (converts status alerts to webhooks). | **Oversight:** Alerts the developer on Slack/Discord/Phone when NALA recovers, needs help, or succeeds. | Phase 2 (Next) |
| **P1** | **`LAKSHYA Protocol`** 🎯 | **Medium** (3 files) | Grader/Outcomes loop. Grades step outputs against a rubric before advancing. | **Quality:** Guarantees task success before moving forward. | Phase 3 |
| **P1** | **`PRATIDWANDI Review`** ⚔️ | **Medium** (4 files) | Adversarial peer review (Consensus verification). | **Consensus:** Two subagents review code commits; consensus required to merge. | Phase 3 |

---

## 3. Detailed JIRA Ticket Breakdowns (P0 Quick Wins) 🛠️

Below are the structured tickets, implementation targets, and technical designs for the prioritized Phase 2 features.

---

### 🎫 JIRA-008: VIVEK Router (4-Tier Dynamic LLM Router)

#### Goal
Reduce LLM API expenditures by up to 70% during long-running tasks by dynamically selecting the cheapest model capable of executing the current task step, with a hard cost circuit-breaker.

#### Technical Design & File Structure
We will introduce three new files under NALA's `core/hands/` directory:
* `core/hands/vivek_router.py` — The core routing registry.
* `core/hands/complexity_classifier.py` — Classifies steps (e.g. static search vs. complex code generation).
* `core/hands/budget_guard.py` — Acts as a cost circuit-breaker to halt execution if cost exceeds thresholds.

```
nala/
└── core/
    └── hands/
        ├── vivek_router.py
        ├── complexity_classifier.py
        └── budget_guard.py
```

#### Proposed Routing Tiers
1. **Tier 1 (Static/Local):** Regex / local string manipulations (zero API cost).
2. **Tier 2 (Basic API - e.g. Gemini Flash):** For lightweight checks, logging formats, and simple summaries.
3. **Tier 3 (Standard API - e.g. GPT-4o-mini):** For routine code reading, standard search parsing, and validation.
4. **Tier 4 (Advanced API - e.g. Claude 3.7 Sonnet / o1):** Reserved exclusively for complex code edits, reasoning, and major planning steps.

#### Acceptance Criteria (AC)
1. **AC-1:** Dynamic classifier correctly maps incoming tasks to one of the 4 tiers based on metadata and rules.
2. **AC-2:** Budget Guard throws a `BudgetExceededError` and transitions the loop to `FAILED` if the session's total cost exceeds a configurable USD limit (e.g. $5.00).
3. **AC-3:** Telemetry in `StateMatrix` correctly attributes prompt/completion token usage and cost per model.

---

### 🎫 JIRA-009: SANKET Protocol (Ṛta-Gated Event Webhooks)

#### Goal
Provide real-time progress and exception monitoring without requiring the developer to tail console logs, by pushing structured notifications to external endpoints.

#### Technical Design & File Structure
We will introduce a new directory `sanket/` under NALA root:
* `sanket/sanket_protocol.py` — The main webhook dispatcher.
* `sanket/channel_router.py` — Routes alerts to Discord, Slack, or Email.
* `sanket/suppression_engine.py` — Implements quiet hours and alerts batching.

```
nala/
└── sanket/
    ├── sanket_protocol.py
    ├── channel_router.py
    └── suppression_engine.py
```

#### Monitored Event Types
* **`CRITICAL`:** Crash recovery loops, failure aborts, budget exhaustion.
* **`WARNING`:** Context tracker warnings (compaction triggers), step retries, low budget warnings.
* **`INFO`:** Generation completions, handoff spore creations, and successful test run reports.

#### Acceptance Criteria (AC)
1. **AC-1:** Dispatches a JSON webhook payload to configured URLs within 5.0 seconds of any monitored event.
2. **AC-2:** Suppression engine correctly groups duplicate warnings (e.g. repeated step retries) to avoid spamming the developer.
3. **AC-3:** Safe failover ensures that webhook dispatch errors (e.g. connection timeout to Slack) never crash NALA's main execution loop.

---
**Jai Bajrang Bali 🙏**
