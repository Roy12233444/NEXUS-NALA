# NALA — Survival Layer & Mathematical Foundations
## Comprehensive Deep-Dive & Mathematical Specifications
**Nexus Lab AI Research Lab | Bengaluru, India**
**Version 1.0 | June 2026**

---

## 📌 Introduction

This document provides an extended, production-grade technical specification of NALA’s **Survival Layer** and its core **Mathematical Foundations & Governing Equations**. 

The fundamental architectural thesis of NALA is that **survival takes precedence over intelligence**. An agent that suffers from amnesia or state corruption after a crash is functionally useless for long-running, multi-day, or multi-week operations. By establishing a robust system spine, NALA ensures full recovery and continuity under arbitrary environment interruptions.

---

## 💾 Part 1: The NALA Survival Layer

The Survival Layer is a sequence of five operations that coordinate state serialization, persistence, crash recovery, and context management.

```
┌────────────────────────────────────────────────────────┐
│                   NALA Run Loop                         │
│                                                        │
│  ┌──────────────────┐      ┌────────────────────────┐  │
│  │ 1. Session       │ ───► │ 2. Reliable Checkpoint │  │
│  │    Contract      │      │    (Write to Disk)     │  │
│  └──────────────────┘      └───────────┬────────────┘  │
│           ▲                            │               │
│           │ (Recovery/Reload)          ▼               │
│  ┌────────┴─────────┐      ┌────────────────────────┐  │
│  │ 3. Crash         │ ◄─── │ 4. Context Tracker     │  │
│  │    Recovery      │      │    (Trigger Handoff)   │  │
│  └──────────────────┘      └────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 1. The Session Contract (`core/harness/session_contract.py`)
The Session Contract acts as the single source of truth for the active state. It is a strictly validated schema (typically implemented using Pydantic or Protocol Buffers) that models the runtime state of the agent.

*   **Task Specification:** Holds the immutable prompt, objective, user-provided resources, and the living `done_condition`.
*   **State Matrix:** Tracks variables like active subagents, token counters, elapsed time, current execution step, and tool usage frequencies.
*   **Task Graph:** A directed acyclic graph (DAG) representing the plan decomposed by the Planner. Each node represents a task with states: `PENDING`, `RUNNING`, `SUCCESS`, or `FAILED`.
*   **Checkpoint Registry:** Metadata references containing historical snapshot coordinates, log offsets, and container state identifiers.

---

### 2. Reliable Checkpoints (`core/harness/checkpoint.py`)
Checkpointing represents the mechanism of committing the active Session Contract state to a persistent storage substrate.

*   **Transactional Durability:** Checkpoints are written using an append-only transaction log. In production, this uses an SQLite database with WAL (Write-Ahead Logging) enabled, preventing data corruption during midway power interruptions.
*   **Log Sequence Numbers (LSN):** Every snapshot is assigned a monotonically increasing integer LSN. This allows recovery engines to track event order and perform rollbacks to a known-good sequence state if corruption occurs.
*   **State Diffs:** Rather than saving the entire multi-megabyte context on every step, NALA serializes incremental diffs of the filesystem and memory vectors, referencing the parent LSN.

---

### 3. Crash Recovery (`core/session/recovery.py`)
Crash Recovery acts as the bootstrap protocol when the NALA daemon is restarted (either manually or after a server crash).

*   **Reconstructive Sequence:**
    1.  The recovery manager queries the persistent SQLite database for the highest valid LSN.
    2.  It replays all append-only logs up to that LSN to reconstruct the memory state of the Session Contract.
    3.  It invokes the sandboxed container manager to roll back the container's OverlayFS layer to the matched LSN checkpoint.
    4.  It re-binds existing system tools and resumes execution at the next pending node in the Task Graph.

---

### 4. Context Handoffs (`core/session/handoff.py`)
When an LLM operates over long periods, the chat history grows continuously, eventually approaching the model's context window limit (e.g., 200,000 tokens). This leads to increased latency, memory pollution, and hallucinated reasoning.

*   **Relay Mechanism:** Instead of failing or running out of memory, NALA executes a context flush:
    1.  The system summarizes completed achievements, open variables, current plan nodes, and next action priorities into a structured **Handoff File** (less than 2,000 tokens).
    2.  The active execution session is cleanly closed.
    3.  A new session is initialized. The model is fed the **Handoff File** as its new system prompt, wiping out thousands of lines of terminal clutter and intermediate reasoning logs.
    4.  The agent continues working with a completely clean context window.

---

### 5. The Long-Running Loop (`core/harness/nala_loop.py`)
The main orchestrator of NALA is a robust execution engine wrapped in error boundaries and recovery checks:

```python
def nala_survival_loop(session_id: str):
    # 1. Boot system: Resume or perform Cold Start
    session_contract = recovery.restore_or_init(session_id)
    
    while not session_contract.is_done():
        try:
            # 2. Retrieve next pending action
            next_task = session_contract.task_graph.get_next_node()
            
            # 3. Route & execute task inside sandboxed container
            result = executor.run(next_task, sandbox)
            
            # 4. Update state matrix
            session_contract.update_state(next_task.id, result)
            
            # 5. Commit state to disk
            checkpoint.save(session_contract)
            
            # 6. Check context window limits
            if context_manager.is_nearing_limit():
                session_contract = handoff.trigger_rotation(session_contract)
                
        except TemporaryToolError as e:
            logger.warning(f"Retrying transient error: {e}")
            time.sleep(exponential_backoff(retry_count))
            
        except FatalExecutionError as e:
            logger.critical(f"Fatal crash detected. Initiating recovery: {e}")
            session_contract = recovery.reconstruct_state(session_id)
```

---

## 🧮 Part 2: The Core Mathematical Foundations

NALA is governed by three mathematical thresholds to prevent decision bias, protect memory purity, and safely manage cold bootstrap sequences.

### Equation 1: Saptacore Epistemic Consensus ($\tau = 0.618$)
Instead of relying on a single judge model or a simple majority, NALA evaluates high-risk actions (e.g., executing system commands, committing file edits, or validating the final done condition) using a weighted 7-agent council.

We define a **Consensus Score ($\mathcal{C}$)** for any action $A$:

$$\mathcal{C} = \sum_{i=1}^{7} w_i \cdot V_i$$

Where:
*   $V_i \in \{0, 1\}$ represents the vote of Agent $i$ ($0$ for rejection, $1$ for approval).
*   $w_i \in [0, 1]$ represents the epistemic weight (reliability modifier) of Agent $i$, normalized such that:
    $$\sum_{i=1}^{7} w_i = 1.0$$

The action is approved if and only if the Consensus Score meets or exceeds the **Golden Ratio threshold ($\tau$)**:

$$\text{Approved}(A) \iff \mathcal{C} \ge 0.618$$

*   **Significance:** By setting the threshold to $0.618$, NALA demands a qualified consensus. Even if 4 out of 7 agents approve ($57\%$), the action is rejected unless the voting weight shifts to the highly-weighted planner and critic agents. This prevents consensus-hacking by weaker model tiers.

---

### Equation 2: Memory Crystallization Threshold ($\theta_{\text{crystal}} = 0.85$)
To prevent **semantic drift** (where the agent slowly fills its memory with irrelevant details and loses focus on the core task), observations are held in a **Temporal Quarantine Buffer (TQB)**.

We calculate the **Combined Relevance Score ($\mathcal{S}_{\text{combined}}$)** of a quarantined memory candidate $M_c$:

$$\mathcal{S}_{\text{combined}} = \alpha \cdot \mathcal{S}_{\text{semantic}}(M_c, \mathcal{M}_{stable}) + (1 - \alpha) \cdot \mathcal{S}_{\text{task-graph}}(M_c, \mathcal{G}_{active})$$

Where:
*   $\mathcal{S}_{\text{semantic}}$ is the cosine similarity between the embedding vector of $M_c$ and the centroids of currently crystallized memory clusters ($\mathcal{M}_{stable}$).
*   $\mathcal{S}_{\text{task-graph}}$ is the lexical overlap score between keywords in $M_c$ and the active nodes in the task graph ($\mathcal{G}_{active}$).
*   $\alpha$ is the scaling factor, set dynamically to $0.7$ (favoring semantic topical similarity).

A memory is permanently crystallized into the long-term storage ledger if and only if:

$$\text{Crystallize}(M_c) \iff \mathcal{S}_{\text{combined}} \ge 0.85$$

*   **Significance:** Setting the threshold high ($0.85$) ensures that only memories directly matching both the semantic theme and the immediate active tasks are committed to the permanent lookup directory, keeping the lookup index clean.

---

### Equation 3: USHA Cold-Start Margin ($\theta_{\text{provisional}} = 0.60$)
On a cold start, the stable memory ledger $\mathcal{M}_{stable}$ is empty, causing $\mathcal{S}_{\text{semantic}}$ calculation to fail or return division-by-zero errors. To bootstrap the system safely, the USHA protocol activates a provisional validation bypass.

We define the **Provisional Confidence Score ($\mathcal{P}$)** for early observations:

$$\mathcal{P} = \beta \cdot \text{Accuracy}_{\text{local}} + (1 - \beta) \cdot \text{Entropy}_{\text{obs}}$$

Where:
*   $\text{Accuracy}_{\text{local}}$ represents local task success verification.
*   $\text{Entropy}_{\text{obs}}$ measures the information density of the observation.
*   $\beta$ is a decay coefficient that decreases as the number of stable memory clusters increases.

The agent is permitted to write early observations to a provisional buffer if:

$$\text{ProvisionalWrite}(M_c) \iff \mathcal{P} \ge 0.60$$

*   **Significance:** Lowering the threshold to $0.60$ on cold-start prevents the bootstrap sequence from stalling due to empty memory directories, while still establishing a basic safety threshold to filter out garbage log files.

---

*Built at Nexus Lab AI Research Lab, Bengaluru*
*Jai Bajrang Bali 🙏*
