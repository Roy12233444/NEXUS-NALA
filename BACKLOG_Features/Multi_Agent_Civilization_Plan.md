# Multi-Agent Civilization & Social Structures Plan

This backlog document outlines the architectural plan for evolving NALA from a single-agent sequential executor to a multi-agent cooperative society. The designs are inspired by the *Project Sid* research paper (*Many-agent simulations toward AI civilization*) and adapt its core concepts (PIANO architecture, theory of mind, social sentiment, role specialization, governance, and meme diffusion) to the NALA core harness.

---

## 1. Concurrent Multi-Timescale Modules (Real-time Async Loop)

### Goal
Decouple planning, sensing, and execution in NALA. Instead of sequential execution (`step_01 -> wait -> step_02`), run parallel threads operating at different timescales to enable real-time adaptability.

### Technical Design
* **Asynchronous Subsystems:** Introduce `asyncio`-driven concurrent loops inside `NalaLoop`:
  * **Sensory Module (Interval: ~0.5s):** Polls filesystem, process telemetry, and active communication channels to update `SessionState.metadata`.
  * **Cognitive Controller (Interval: ~1.5s):** Filters state via a **Cognitive Bottleneck** and updates the agent's active `HighLevelIntent`.
  * **Execution Module (Dynamic Trigger):** Dispatches pending tasks and monitors tool execution status.
* **Cognitive Bottleneck Registry:** Restrict input context size for LLM re-planning by constructing a dynamic summary of critical errors, remaining tasks, and active alerts.
* **Grounding Feedback Loop:** If an executor fails, update state immediately. The Cognitive Controller intercepts this and dynamically re-plans the task graph before the next execution ticks.

---

## 2. Social Sentiment & Theory of Mind

### Goal
Allow NALA agents to interact with other agents and human users with an awareness of relationships, trust, and historical cooperation.

### Technical Design
* **Theory of Mind Database:** Maintain a relational graph in `SessionState` tracking:
  * `social_sentiments`: Dict mapping `agent_id/user_id -> affinity_score (0.0 to 10.0)`.
  * `cooperation_history`: Transaction log of shared task execution and success/failure ratios.
* **Dynamic Prompts Conditioning:** Inject relationship summaries into the Cognitive Controller's planning prompts. Agents will prioritize tasks from high-trust peers and apply stricter validations/checks to low-trust entities.
* **Sentiment Mutators:** Create utility hooks that increase affinity when tasks are completed successfully and decrease affinity on uncooperative events (e.g., timeouts, late deliveries).

---

## 3. Role Specialization & Agent Economy

### Goal
Organize multi-agent NALA fleets into specialized task workers who trade tasks and resource tokens on a local computational marketplace.

### Technical Design
* **Agent Archetypes:** Define class structures for specialized sub-agents:
  * `CoderAgent`: Specializes in writing python files and tests.
  * `ResearchAgent`: Specializes in web search and literature retrieval.
  * `QualityJudgeAgent`: Specializes in linting, debugging, and code reviews.
* **Decentralized Task Bidding:** 
  * A planning agent publishes unresolved task steps to a shared registry as "Contracts".
  * Specialized agents compute bids (token cost + estimated completion time) based on their current load.
  * The planning agent selects the best bid and delegates the task.
* **Shared Ledger (Computational Credits):** Implement an in-memory or SQLite-backed transaction ledger to track token consumption. Agents charge for task completion, ensuring optimal utilization of LLM resources.

---

## 4. Governance, Laws & Democracy

### Goal
Implement democratic decision-making and law enforcement within NALA multi-agent fleets to resolve conflicts, prioritize tasks, and establish consensus.

### Technical Design
* **Consensus Engine:** Provide voting mechanisms (majority, weighted, or quadratic voting) for task graphs:
  * When a major plan change or rollback occurs, agents vote on whether to adopt it based on validation results.
* **Constitutional Constraints (Laws):** Maintain a registry of invariant laws (e.g., "Do not delete files in `/core` without code review approval", "Never exceed $5 USD cost per step").
* **Judicial Review Loop:** Spawns a `JudgeAgent` to audit execution traces. If a law is broken, the offending agent is flagged, its trust score is penalized, and recovery actions are triggered.

---

## 5. Cultural Transmission & Knowledge Sharing (Meme Diffusion)

### Goal
Allow agents to share successful prompts, execution patterns, and tool-use scripts dynamically to improve collective performance over time.

### Technical Design
* **Community Memory (Vector DB):** Set up a shared semantic memory store accessible by all active NALA loops.
* **Diffusion Mechanism:** When an agent successfully completes a complex step (judged as high-quality), it generates a "meme card" (a structured summary of the prompt, parameters, and successful tool output) and flushes it to the shared memory.
* **Context Ingestion:** Prior to starting a task, the planner searches the shared community memory for similar task descriptions to extract proven prompt strategies.

---

**Jai Bajrang Bali 🙏**
