# NALA Future Enhancements & Roadmap

This document outlines the detailed goals, technical designs, and implementation steps for future NALA orchestration improvements.

---

## 1. Custom Step-Retry Policies

### Goal

Implement granular control over how the execution engine handles temporary step failures (e.g., rate limits, transient network dropouts, temporary service downtime) instead of marking them failed immediately.

### What We Build

A polymorphic retry module containing strategies such as:

* **`FixedIntervalRetry`:** Retries step execution after a static delay interval.
* **`LinearBackoffRetry`:** Retries with a delay that increments linearly with each attempt.
* **`ExponentialBackoffRetry`:** Retries using exponential delay curves, augmented with random jitter to prevent thundering herd congestion on remote APIs.

### How It Works

* **Central Registry:** Policies are registered in a centralized registry mapped by step tool type or step ID (e.g., search tools use `LinearBackoff`, heavy LLM calls use `ExponentialBackoff`).
* **Hook Integration:** Integrates `on_step_retry` lifecycle hooks to log attempts, notify tracking dashboards, and register the metrics in the `StateMatrix` telemetry.
* **Idempotency Guard:** Cleans up any variables or partial outputs from the step's temporary run before initiating a retry execution, preventing duplicate or corrupted state logs.

---

## 2. Adaptive Wait Delays & Rate Limiting

### Goal

Implement proactive congestion control when communicating with external LLM providers and search endpoints to avoid rate limit breaches (HTTP 429).

### What We Build

A traffic-congestion coordinator and token-bucket rate limiter that acts as an outbound gateway scheduler for step execution.

### How It Works

* **Token Bucket Limiter:** Maintains request capability and token counters per remote host/endpoint. Stalls steps cooperatively if the endpoint's token bucket is currently empty.
* **AIMD Congestion Window:** Implements an Additive-Increase/Multiplicative-Decrease (AIMD) algorithm. On success, delay between steps shrinks. On detection of congestion or rate limit headers (like `X-RateLimit-Reset` or `Retry-After`), the delay doubles.
* **Cooperative Sleep:** Ensures all pacing delay intervals poll the loop's thread-safe `stop_event` so NALA can pause or stop immediately during sleep.

---

## 3. Multi-Agent Messaging & Delegation

### Goal

Transition NALA from a single-agent orchestrator loop into a collaborative multi-agent ecosystem.

### What We Build

Thread-safe inbox/outbox message structures and delegation step interfaces allowing multiple NALA processes to coordinate.

### How It Works

* **Message Queues:** Adds `inbox` and `outbox` queues to the root `SessionState` contract to allow asynchronous communication, telemetry sharing, and output exchange between loops.
* **Handoff Step Executor:** Introduces a specialized `HandoffStep` that cooperatively pauses the parent loop and routes a sub-task graph to a child agent loop.
* **Consensus Checkpoints:** Collaborating agents write checkpoints synchronously before resolving dependencies, ensuring that node crashes don't cause state divergence.
* **Distributed Locks:** Upgrades the file-based `filelock` system to support distributed process environments (e.g. database-backed locks or Redis-based locks).

---
**Jai Bajrang Bali 🙏**

graph TD
    A[Start: 1-Hour Soak Test] --> B[Execute Task Step]
    B --> C[Generate Large Output Payload]
    C --> D[ContextTracker Evaluates Token Level]

    D -- Token Limit Exceeded? No --> B
    D -- Token Limit Exceeded? Yes --> E[DronagiriCompactor Stage 1: Regex Pruning]
    
    E -- Compaction Cleared Space? Yes --> B
    E -- Compaction Cleared Space? No --> F[DronagiriCompactor Stage 2: LLM Crystallization]
    
    F -- Space Cleared? Yes --> B
    F -- Space Cleared? No --> G[Trigger CONTEXT_EXHAUSTED Handoff]
    
    G --> H[Write Pre-Handoff Checkpoint LSN=N]
    H --> I[Write handoff.spore.json to S2 Directory]
    I --> J[Simulate Process Kill / Restart]
    
    J --> K[LockResolver Unlinks Stale Lockfiles]
    K --> L[recover_session reads Spore & Checkpoint]
    L --> M[Monotonic Correction on StateMatrix]
    M --> N[S2 Loops Begins Execution at Next Step]
    N --> B
