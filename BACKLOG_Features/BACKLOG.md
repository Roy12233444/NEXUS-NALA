# FUTURE ENHANCEMENTS & BACKLOG

This backlog outlines future technical enhancements to be built on top of the NALA Core Run-Loop (`nala_loop.py`). These features will extend the reliability, scalability, and multi-agent coordination capabilities of the NALA framework.

---

## 1. Custom Step-Retry Policies

### Goal
Implement granular control over how the execution engine handles temporary step failures (e.g., rate limits, transient network dropouts, temporary service downtime) instead of failing immediately.

### Technical Design
* **Polymorphic Retry Strategies:** Introduce standard strategies like `FixedIntervalRetry`, `LinearBackoffRetry`, and `ExponentialBackoffRetry`.
* **Step-Type Registry:** Bind specific retry policies to step types (e.g., `web_search` gets a linear backoff, while `llm_call` gets an exponential backoff with jitter).
* **Retry Hooks:** Introduce `on_step_retry` lifecycle hooks to log retry attempts in the telemetry system.
* **Idempotency Safeguards:** Ensure steps that are retried clean up any partial state before running again.

---

## 2. Adaptive Wait Delays

### Goal
Dynamically adjust wait delays between execution steps to optimize API usage, avoid rate limits (HTTP 429), and manage throughput during high congestion.

### Technical Design
* **Dynamic Congestion Window:** Use an additive-increase/multiplicative-decrease (AIMD) algorithm or rate limit headers (`X-RateLimit-Reset`, `Retry-After`) to adjust execution pacing.
* **Token Bucket Rate Limiter:** Maintain an in-memory token bucket per remote service (e.g., OpenAI, Anthropic, web search provider) to throttle outgoing requests.
* **Cooperative Sleep:** Ensure sleep/wait intervals check the loop's `stop_event` so the agent remains responsive to pause/stop signals even during long delays.

---

## 3. Multi-Agent Messaging & Handoffs

### Goal
Support coordination and delegation between multiple NALA loops or specialized sub-agents working on a shared task graph.

### Technical Design
* **Agent-to-Agent Handoff Steps:** Introduce a special `HandoffStep` that pauses execution of the parent loop and routes a sub-task to another agent loop.
* **Structured Inbox/Outbox:** Add thread-safe message queues to `SessionState` to allow loops to exchange telemetry, results, or coordination signals.
* **Distributed Locking:** Upgrade the file-based `filelock` system to support cross-process coordination across distributed nodes.
* **Consensus Checkpoints:** Ensure all collaborating agent sessions persist sync points to avoid state divergence during system crashes.

---
**Jai Bajrang Bali 🙏**
