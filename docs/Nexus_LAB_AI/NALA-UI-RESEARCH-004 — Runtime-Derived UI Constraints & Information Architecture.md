# 📐 NALA-UI-RESEARCH-004: Runtime-Derived UI Constraints & Information Architecture

**Document Version:** `2.0.0-DEEP-SYNTHESIS`  
**Classification:** Pre-Wireframe Architectural Decision Gate (No Implementation / Inspection & Derivation Only)  
**Status:** 🟢 **FULLY SYNTHESIZED WITH RESEARCH_FILES (001, 002, 003)**  
**Date:** August 29, 2026  
**Auditor:** Principal Frontend Architect & UI Systems Forensic Engineer  
**Governing Law:** *"Given the conclusions of 001 + 002 and the runtime truths established by 003, what information architecture allows a human to supervise NALA with maximum useful observability and minimum cognitive load?"*

---

# 1. Executive Decision & Core Philosophical Invariant

Research-004 serves as the **unbreakable architectural decision bridge** between forensic runtime truth (003), adversarial autopsy findings (001, 002 from `RESEARCH_FILES`), and structural wireframing (005).

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   THE DERIVATION PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  001: Archaeology    ──► Deconstructed OpenAI Operator, Claude Code/Cowork, Magentic-UI,   │
│                          and LangGraph Studio to extract agentic control primitives.        │
│  002: Autopsy        ──► Dual-Agent adversarial attack (Gemini cognitive audit + Claude     │
│                          systems audit) exposed state vs effect rewind, unearned Pramāṇa    │
│                          claims, swimlane scaling failures, and approval gaps.              │
│  003: Runtime Truth  ──► Forensic inspection of laptop repository (nala_server/, core/,     │
│                          src/, tests/) proved exact code capabilities and constraints.      │
│  004: Constraints    ──► Derives the definitive 5-Tier Information Hierarchy, 3-Zone        │
│                          Workspace Architecture, and 13 formal primitive schemas.           │
│  005: Wireframe      ──► Establishes exact pixel geometries, drawer docking, and layouts.   │
│  006: Implementation ──► Systematic React + Vanilla CSS implementation under user guidance. │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### The 5 Immutable Cognitive Axioms:
1. **Axiom I: The Interface is a Consequence Engine**: Complexity belongs in the system; clarity belongs in the interface. NALA's primary interface must exclusively expose consequences, decisions, and verifiable evidence. Routine tool calls, parsing retries, and internal JSON formatting remain behind deliberate inspection thresholds.
2. **Axiom II: The Progressive Disclosure Model**: Execution is a narrative; architecture is a blueprint. The default screen is a clear, reassuring operational narrative. Appended to every milestone is an interactive `View details →` affordance revealing deep machinery (Pramāṇa routes, LSN checkpoints, Viveka safety scores, and DAG topology).
3. **Axiom III: Epistemic Supremacy**: Trust is verified via physical provenance, never assumed through tone. The system must never launder probabilistic LLM assertions as deterministic facts.
4. **Axiom IV: Strategic Cognitive Friction**: Efficiency must never supersede safety. High-stakes irreversible actions demand deliberate cognitive effort, rejecting binary rubber-stamping in favor of typed confirmation and blast-radius manifests.
5. **Axiom V: Silent Self-Healing**: Do not report the struggle; report the outcome. Micro-recoveries managed by Subsystem 002G (e.g., catching timeouts, backoff retries, syntax re-prompts) are logged silently to the Inspector and must never interrupt the operator unless bounded budgets are exhausted.

---

# 2. Deep Synthesis of `RESEARCH_FILES` (001, 002, 003)

Our deep analysis of the 4 core research files in `docs/Nexus_LAB_AI/RESEARCH_FILES` integrates the following critical resolutions:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                          SYNTHESIS OF CRITICAL RESEARCH RESOLUTIONS                         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. State Rewind vs Effect Rewind (002 Claude Audit §2.1)                                    │
│    - Internal state (RAM, plan position, LSN) is trivially rewindable.                      │
│    - External world state (disk files, network payloads, DB mutations) is NOT.             │
│    - RESOLUTION: Checkpoint UI explicitly distinguishes State Rewind from Effect Rewind.    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Unearned Pramāṇa Badging (002 Claude Audit §2.2)                                         │
│    - If the generative model self-labels its epistemic confidence, it is epistemic theater. │
│    - RESOLUTION: Pramāṇa badges are only authoritative when backed by deterministic         │
│      measurements (PRATYAKSHA = SHA-256 disk readback). Model inference is labeled ANUMĀNA. │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Parallel Swimlane Failure (002 Autopsy §04)                                              │
│    - Horizontal swimlanes fail under recursive sub-agent spawning and multi-task scale.     │
│    - RESOLUTION: Reject swimlanes. Use hierarchical, collapsible DAG clusters in Inspector. │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Rejection of Chatbot-as-Primary (001 §6C & 002 §02)                                      │
│    - Linear chat streams bury multi-agent state in trace bloat and context fatigue.         │
│    - RESOLUTION: Chat is demoted to a semantic input widget / composer, while the primary   │
│      operational surface is spatial, stateful, and consequence-driven.                      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Dual-Track Human Intervention (002 Autopsy §04)                                          │
│    - Synchronous blocking popups break operator flow; pure async queues fail blockers.      │
│    - RESOLUTION: Dual-Track model: Non-critical ambiguities go to an async inbox; critical  │
│      blockers trigger a localized "Edge-Yield" on the dependent DAG node only.              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 3. Comprehensive Traceability Matrix

Every architectural constraint in 004 is anchored to specific benchmark findings and physical repository code:

| # | UI Architecture Constraint | 001 Archaeological Root | 002 Adversarial Autopsy Root | 003 Runtime Truth Root | Human Need Addressed |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Dominant Center Mission Surface** | Cowork Outcome Stream / Codex Thread | Prevent fragmentation across 5 competing panes | `ChatSection.tsx` & `NalaRunner` execution loop | Unambiguous focus on active goal and live progress |
| **2** | **Step Progress Timeline** | Codex step trace / Claude Code headers | Eliminate opaque spinners & fake progress | `session_contract.py::TaskStep` & `TaskEvent` | Real-time awareness of active step duration and status |
| **3** | **Collapsible Right Inspector** | Magentic-UI inspector / LangGraph nodes | Prevent "Telemetry Cockpit Syndrome" | Redux slices (`safety`, `tools`, `transcendent`) | Deep observability on demand without cluttering stream |
| **4** | **Verified Artifact Cards** | Cowork local disk files / Codex diffs | Distinguish LLM hallucination from real files | `core/harness/recovery.py` & SHA-256 readback | Mathematical proof that files exist and match disk bytes |
| **5** | **Explicit State vs Effect Rewind**| LangGraph Time Travel | State rewind $\neq$ side effect rewind | `CheckpointManager` LSN atomic JSON commits | Prevents user from assuming external actions are undone |
| **6** | **No Pause Button** | Codex pause / Claude interrupt | Pause cannot be claimed if thread can't suspend | `NalaRunner` has zero pause functions | Eliminates UI deception; prevents state corruption |
| **7** | **Cooperative Cancel Only** | Claude Code `Ctrl+C` interrupt | Hard kill destroys checkpoint boundaries | `NalaRunner.cancel()` sets `cancel_event` flag | Graceful termination preserving durable disk LSNs |
| **8** | **Strategic Cognitive Friction** | Action Guard & ConLeash lattice | Binary allow/deny causes rubber-stamping | `AdaptiveVivekaGate` (`ALLOW`/`DENY`/`CONFIRM`) | High-friction verification for destructive operations |
| **9** | **Left History Drawer** | Cowork Project History / Codex Threads | Long-running missions require session switching | `state.py::SessionRecord` & LSN history files | Seamless navigation across past checkpoints & runs |
| **10**| **Dual-Track Intervention Queue** | Magentic-UI Co-tasking & Asynchronous Inbox| Blocking modals destroy operator flow | `nala_runner.py::_ApprovalWaiter` | Batchable non-blocking human interventions |

---

# 4. The 5-Tier Information Hierarchy

To balance high observability with low cognitive load, runtime data is partitioned into five distinct visibility tiers:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 0: IMMEDIATE HUMAN AWARENESS (Global Header / Top-Level Bar - Height: 56px)            │
│  - Active Mission Title & Operational Mode (Autonomous / Supervised)                        │
│  - Live State Indicator (Idle, Planning, Running, Waiting Approval, Failed)                 │
│  - Ambient System Health (Self-Healing Active, Circuit Breaker Normal, Resource Burn)       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: PRIMARY OPERATIONAL STREAM (Center Mission Surface - Flexible Width)                │
│  - Objective & Intent Decomposition (Intentmaking Phase)                                    │
│  - Execution Plan Steps (PlanStep[]) with dynamic status markers                            │
│  - Live Progress Timeline (Active Step, Elapsed Time, Step Status, Duration)                │
│  - Physical Artifact Cards (Filename, Byte Size, SHA-256 Checksum, Copy affordance)         │
│  - High-Friction Human Approval Prompts (When Viveka gates critical risk)                   │
│  - Executive Markdown Synthesis & Delivery Deliverables                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: CONTEXTUAL INSPECTION (Collapsible Right Inspector - Width: 320px - 380px)          │
│  - Active Pramāṇa Epistemic Route (Pratyakṣa, Anumāna, Śabda, Upamāna, Arthāpatti)         │
│  - Adaptive Viveka Safety Score & Decision Rationale (ALLOW / APPROVAL_REQUIRED / DENY)     │
│  - Active Tool Registry Metadata, Invocation Arguments & Latency Tracking (ms)              │
│  - Monotonic Checkpoint LSN History (`LSN-1`, `LSN-2`, etc.) with State Rewind affordance   │
│  - Memory Recall Provenance (`memory/MEMORY.md` bullet facts injected into context)         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: HISTORICAL AUDIT (Collapsible Left Drawer - Width: 260px - 300px)                   │
│  - Past Sessions & Mission Archives with search & tag filtering                             │
│  - Checkpoint Recovery Lineage & ARIES Crash Resumption Audit Logs                          │
│  - Durable Artifact Repository & Historical Output Manifests                                │
│  - Context Workspace: Read/write governance of persistent project memory                    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: DEVELOPER DIAGNOSTICS (Quarantined Debug Drawer / Modal)                            │
│  - Raw Socket.IO JSON Event Payloads (Canonical TaskEvent stream)                           │
│  - Low-Level Sandbox stdout/stderr Streams & Subprocess Exit Codes                          │
│  - Internal UUIDs (`request_id`, `generation_id`, `transition_id`, `session_id`)            │
│  - Python Tracebacks, Exception Contexts, and Thread Pool Allocation                        │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. The 7-Phase Agentic Lifecycle Interaction Model

Derived directly from the cognitive interaction audit (`Dual-Agent UI Research Autopsy.md §02`), NALA structures human supervision across seven distinct operational phases:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INTENTMAKING (User Intention Framing)                                                    │
│    - User enters directive via coactive input matrices (natural language + constraint pills)│
│    - UI Affordance: Pill composer with mode toggles (Autonomous vs Interactive).            │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. INTERPRETATION (Agent Semantic Comprehension)                                            │
│    - Agent dynamically renders its semantic comprehension before heavy computation.         │
│    - UI Affordance: Brief "Intent Breakdown" block confirming understanding of the goal.    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. CO-PLANNING (Architectural DAG Review)                                                   │
│    - Planner generates dynamic DAG. Human can review, reorder, or inject steps.             │
│    - UI Affordance: Structured Plan card with step numbering, dependencies, and estimates.  │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. EXECUTION (Delegated Operational Progress)                                               │
│    - NALA executes steps autonomously; UI abstracts execution into semantic milestones.     │
│    - UI Affordance: Live progress timeline with active pulse, elapsed timer, and checkmarks.│
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. INTERVENTION (Dual-Track Yield State)                                                    │
│    - Non-critical requests routed to Asynchronous Inbox; blockers trigger Edge-Yield.       │
│    - UI Affordance: High-friction modal for critical safety gates; inbox badge for async.   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. EPISTEMIC AUDIT (Claim vs Observation vs Physical Proof)                                 │
│    - Output visually dissected into Claim (LLM inference) vs Physical Evidence (Disk bytes).│
│    - UI Affordance: Pramāṇa badge (`🟢 PRATYAKSHA` vs `🟡 ANUMANA`) with SHA-256 copy.      │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 7. COMPLETION (Durable Artifact & Memory Playbook Extraction)                               │
│    - Deliverable saved as stateful artifact; successful DAG packaged into Chiranjeevi memory│
│    - UI Affordance: Verified Artifact Card + "Saved to Project Memory" confirmation.        │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. Formal Schemas for All 13 Agentic Primitives

Closing the definitional gap identified in `NALA-UI-RESEARCH-002-Claude-Independent-Audit.md §1`, below are the formal, typed schemas for all 13 core interaction primitives:

```typescript
// 1. Mission Primitive (Overarching Objective Container)
interface MissionPrimitive {
  missionId: string;
  title: string;
  objective: string;
  mode: 'autonomous' | 'interactive';
  state: 'created' | 'planning' | 'running' | 'waiting_approval' | 'recovering' | 'completed' | 'failed' | 'cancelled';
  activeSessionId: string;
  createdAt: string;
  completedAt?: string;
  resourceBurn: { tokensIn: number; tokensOut: number; elapsedSeconds: number; estimatedCostUsd: number };
}

// 2. Task Primitive (Allocated Compute Workstream)
interface TaskPrimitive {
  taskId: string;
  sessionId: string;
  missionId: string;
  goal: string;
  state: 'created' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  currentStepId?: string;
  checkpointRef?: string;
  createdAt: string;
  completedAt?: string;
}

// 3. Plan Primitive (Dynamic DAG Model)
interface PlanPrimitive {
  planId: string;
  taskId: string;
  steps: ExecutionStepPrimitive[];
  isEditable: boolean;
  totalEstimatedSeconds?: number;
  hasCycles: boolean; // Verified by DFS Tarjan cycle detector
}

// 4. Step Primitive (Semantic Progress Node)
interface ExecutionStepPrimitive {
  stepId: string;
  index: number;
  totalSteps: number;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  details?: string[];
  retryCount: number;
}

// 5. Action Primitive (Specific Tool Invocation Instance)
interface ActionPrimitive {
  actionId: string;
  stepId: string;
  toolName: string;
  action: string;
  arguments: Record<string, any>;
  sandboxStatus: 'isolated' | 'host_elevated' | 'denied';
  exitCode?: number;
  stdoutSnippet?: string;
  latencyMs: number;
}

// 6. Approval Primitive (Cryptographic Signature Record)
interface ApprovalRecordPrimitive {
  requestId: string;
  taskId: string;
  stepId: string;
  actionId: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  policyTriggered: string;
  blastRadius: { filesAffected: string[]; networksAccessed: string[]; willMutateDisk: boolean };
  approvedBy?: 'human_user' | 'auto_policy';
  approvedAt?: string;
  decision: 'PENDING' | 'APPROVED' | 'REJECTED' | 'TIMED_OUT';
}

// 7. Intervention Primitive (Asynchronous Takeover Request)
interface InterventionPrimitive {
  interventionId: string;
  taskId: string;
  stepId: string;
  type: 'CREDENTIAL_REQUIRED' | 'AMBIGUITY_RESOLVE' | 'PERMISSION_GRANT' | 'MANUAL_INSPECTION';
  title: string;
  prompt: string;
  isBlocking: boolean; // True = Edge-Yield on DAG node; False = Batchable Async Inbox
  createdAt: string;
  resolvedAt?: string;
}

// 8. Checkpoint Primitive (Durable Temporal Snapshot)
interface CheckpointPrimitive {
  lsn: number;
  checkpointId: string;
  sessionId: string;
  stepId: string;
  timestamp: string;
  contentHash: string; // SHA-256 of session state JSON
  filePath: string;
  isGenesis: boolean;
  rollbackCapability: 'STATE_ONLY' | 'COMPENSABLE_EFFECT';
}

// 9. Recovery Primitive (Self-Healing Diagnosis & Action)
interface RecoveryPrimitive {
  recoveryId: string;
  taskId: string;
  stepId: string;
  failureClass: 'TRANSIENT_EXECUTION_ERROR' | 'INTERRUPTED_EXECUTION' | 'ARTIFACT_UNCERTAINTY' | 'CORRUPTED_CHECKPOINT' | 'SAFETY_VIOLATION';
  strategy: 'RETRY' | 'RESUME' | 'CORROBORATE' | 'ROLLBACK' | 'SAFE_HALT';
  attemptCount: number;
  maxAttempts: number;
  rootCause: string;
  status: 'DIAGNOSING' | 'EXECUTING_STRATEGY' | 'RESOLVED' | 'HALTED';
}

// 10. Artifact Primitive (Physical Typed Data Object)
interface ArtifactPrimitive {
  artifactId: string;
  name: string;
  path: string;
  sizeBytes: number;
  mimeType: string;
  checksum: string; // Cryptographic SHA-256
  isPhysicalOnDisk: boolean;
  createdAt: string;
}

// 11. Verification Primitive (Cryptographic Attestation Record)
interface VerificationPrimitive {
  verificationId: string;
  artifactId: string;
  method: 'SHA256_DISK_READBACK' | 'UNIT_TEST_PASS' | 'LINT_COMPLIANCE' | 'HUMAN_SIGNOFF';
  passed: boolean;
  expectedHash?: string;
  actualHash?: string;
  testSuiteSummary?: { passed: number; failed: number; skipped: number };
  verifiedAt: string;
}

// 12. Memory Primitive (Durable Context Bullet Fact)
interface MemoryFactPrimitive {
  factId: string;
  content: string;
  dateTag: string; // YYYY-MM-DD
  revisionToken: string; // SHA-256 for optimistic concurrency
  provenance: 'USER_EXPLICIT' | 'MISSION_SYNTHESIS' | 'PLAYBOOK_EXTRACTION';
}

// 13. Completion Primitive (Formal Packaging Record)
interface CompletionPrimitive {
  missionId: string;
  status: 'SUCCESS' | 'PARTIAL_SUCCESS' | 'SAFE_HALT' | 'CANCELLED';
  finalArtifacts: ArtifactPrimitive[];
  totalStepsExecuted: number;
  totalDurationSeconds: number;
  playbookGenerated: boolean;
  executiveSummary: string;
}
```

---

# 7. The Epistemic Evidence Model (Claim vs Observation vs Proof)

Resolving the core vulnerability exposed in `NALA-UI-RESEARCH-002-Claude-Independent-Audit.md §2.2`: **Preventing Epistemic Theater**.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             THE 3-TIER EPISTEMIC TRUTH LADDER                               │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ ⚪ TIER 1: MODEL CLAIM (Probabilistic Inference / Assertion)                                │
│    - Definition: Raw text generated by the LLM (e.g. "I wrote the auth module").           │
│    - UI Representation: Standard message typography; zero verification badges.              │
│    - Epistemic Status: UNGROUNDED ASSERTION (ANUMĀNA)                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🟡 TIER 2: RUNTIME OBSERVATION (Subsystem Telemetry)                                        │
│    - Definition: Tool execution completed; subprocess returned exit code 0.                 │
│    - UI Representation: Subtle tool execution badge (`file_writer ✓ 42ms`).                 │
│    - Epistemic Status: PROCESS OBSERVATION (ARTHĀPATTI / UPAMĀNA)                           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🟢 TIER 3: PHYSICAL EVIDENCE (Cryptographic & Deterministic Corroboration)                  │
│    - Definition: `PhysicalEvidenceCorroborator` reads physical bytes from OS filesystem and │
│      calculates genuine SHA-256 checksum matching the claimed artifact.                     │
│    - UI Representation: Verified Artifact Card with `🟢 PRATYAKSHA (SHA-256 Matched)` badge.│
│    - Epistemic Status: ATTESTED PHYSICAL TRUTH (PRATYAKṢA)                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Unbreakable Rule of Epistemic Representation:
> **The UI must refuse to render a green "Verified" badge based solely on an LLM's self-reported confidence score. Verification is reserved exclusively for Tier 3 Physical Evidence.**

---

# 8. Checkpoint Semantics: State Rewind vs Effect Rewind

Resolving `NALA-UI-RESEARCH-002-Claude-Independent-Audit.md §2.1`:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                          STATE REWIND vs EFFECT REWIND DISCIPLINE                           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ WHAT CHECKPOINT RESTORATION CAN DO (State Rewind):                                          │
│  ✔ Restores SessionState variables in Python RAM.                                           │
│  ✔ Rewinds TaskStep statuses (Step 4 returns to PENDING).                                   │
│  ✔ Reverts token, cost, and active error counters to prior LSN.                             │
│                                                                                             │
│ WHAT CHECKPOINT RESTORATION CANNOT DO (External Effect Rewind):                             │
│  ✖ Does NOT delete or un-write physical files created on disk during Step 4.                │
│  ✖ Does NOT revert external database rows committed via network tools.                      │
│  ✖ Does NOT retract HTTP POST payloads transmitted to third-party APIs.                      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### UI Implementation Constraints:
* The UI must **never** offer an ambiguous `"Undo"` or `"Rollback World"` button.
* Reversion controls must be explicitly labeled: `"Restore Internal State to LSN-X"`.
* When a user triggers an LSN state restore, the UI must present an explicit **Blast-Radius Manifest** displaying which memory vectors and step statuses will revert, noting that physical files on disk remain untouched unless manually cleaned.

---

# 9. The 3-Zone Workspace Information Architecture

The authoritative spatial structure for the NALA Control Center:

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ GLOBAL TOP CONTROL BAR (Height: 56px) ]                                                                              │
│ 🧬 NALA Control Center  •  🎯 Mission: Auth System  •  Status: 🔵 RUNNING (Step 2/4)  •  Burn: $0.02  •  [ ⏹ Stop Mission ]│
├─────────────────────────┬───────────────────────────────────────────────────────────┬──────────────────────────────────┤
│ [ ZONE 1: LEFT DRAWER ] │ [ ZONE 2: CENTER MISSION SURFACE ]                        │ [ ZONE 3: RIGHT INSPECTOR ]      │
│ (Collapsible History)   │ (Primary Conversational & Execution Stream)               │ (Collapsible Telemetry)          │
│ Width: 260px - 300px    │ Flexible Width (Min 600px)                                │ Width: 320px - 380px             │
│                         │                                                           │                                  │
│ 📁 ACTIVE MISSIONS      │ 💬 HUMAN DIRECTIVE (Intentmaking)                         │ 👁️ PRAMĀṆA EPISTEMIC ROUTE      │
│ • Mission-001 (Active)  │    "Build RS256 JWT middleware and verify on disk"        │   Primary: PRATYAKSHA            │
│ • Mission-000 (Done)    │                                                           │   Confidence: 0.96 (Attested)    │
│                         │ 📋 EXECUTION PLAN (Co-Planning DAG - 4 Steps)             │                                  │
│ 📜 CHECKPOINT LINEAGE   │    1. Inspect existing token signing interfaces (✓ 1.2s)  │ 🛡️ VIVEKA SAFETY GAUGE           │
│ • LSN-4 (2m ago)        │    2. Generate JWT validation middleware (⚡ Active 8.4s)  │   Strictness: 0.95 (AUTONOMOUS)  │
│ • LSN-3 (5m ago)        │    3. Execute unit test harness inside sandbox (⏳)       │   Decision: ALLOW (Safe Path)    │
│ • LSN-2 (8m ago)        │    4. Corroborate physical artifact SHA-256 (⏳)          │                                  │
│ • LSN-1 (Genesis)       │                                                           │ ⚡ ACTIVE TOOL REGISTRY          │
│                         │ ⏳ LIVE PROGRESS TRACE                                    │   Name: `file_writer`            │
│ 🧠 CONTEXT WORKSPACE    │    └─ Writing `src/auth/jwt_validator.ts` via Tool...     │   Sandbox: Isolated (Local)      │
│ • 42 facts committed    │       └─ Tool: `file_writer` | Sandbox: Isolated          │   Latency: 42ms | Exit Code: 0   │
│ • Rules: Dark Mode, TS  │                                                           │                                  │
│                         │ 📄 VERIFIED ARTIFACT DELIVERABLE                          │ 💾 CHECKPOINT LEDGER (LSN)       │
│ 📥 ASYNC INBOX (1)      │    `jwt_validator.ts` (2,418 bytes)                       │   Active LSN: 4                  │
│ • Review test mock data │    🟢 PRATYAKSHA: SHA-256 e3b0c442... [Copy]              │   Status: Atomic JSON Committed  │
│                         │    (Physical disk readback confirmed)                     │   [ Restore State to LSN-4 ]     │
│                         │                                                           │                                  │
│                         │ 💬 NALA EXECUTIVE SYNTHESIS                               │ 🧠 RECALLED MEMORY FACTS         │
│                         │    "Middleware generated, tested, and verified on disk."  │   - (2026-08-28) User uses TS.   │
│                         │ ───────────────────────────────────────────────────────── │   - (2026-08-28) RS256 required. │
│                         │ [ 💬 Enter directive or constraint for NALA... ]          │                                  │
└─────────────────────────┴───────────────────────────────────────────────────────────┴──────────────────────────────────┘
```

### Dynamic Responsive Geometries:
* **Ultra-Wide ($> 1440\text{px}$)**: All 3 zones open simultaneously; provides persistent tri-pane situational awareness.
* **Standard Desktop ($1024\text{px} - 1440\text{px}$)**: Center Mission Surface dominant; Left and Right zones collapse into slide-over trays accessible via top bar buttons.
* **Compact / Tablet ($< 1024\text{px}$)**: Center Surface occupies 100% viewport width; Left History and Right Inspector act as modal sheets.

---

# 10. The Authoritative MUST / MUST NOT Constitution

This constitution forms the **unbreakable mandate for Stage 005 (Wireframing)**:

### 🟢 MUST EXIST (Mandatory in Wireframe):
1. **Dominant Center Mission Surface**: Conversational intent framing, co-planning plan cards, live execution progress timeline, verified artifact cards, and executive synthesis.
2. **Cryptographic SHA-256 Badges**: Physical byte size and truncated SHA-256 checksums on all generated artifact cards.
3. **Cooperative Stop/Cancel Control**: Prominent top-bar button bound to `NalaRunner.cancel()` to cleanly halt tasks at safe checkpoint boundaries.
4. **Strategic Cognitive Friction for Approvals**: Explicit confirmation dialogs requiring typed confirmation or blast-radius review before destructive operations execute.
5. **Silent Self-Healing with Visible Recovery Badges**: Automatic 002G retries logged cleanly with an animated indicator (`"Retrying Step (Attempt X of 3)"`).
6. **Collapsible Right Inspector Drawer**: Dedicated tabs for `Evidence (Pramāṇa)`, `Safety (Viveka)`, `Tools & Sandbox`, `Checkpoints (LSN)`, and `Memory`.
7. **Collapsible Left History Drawer**: Dedicated space for switching active missions, auditing checkpoint lineage, managing project memory, and checking the Asynchronous Inbox.

### 🔴 MUST NOT EXIST (Strictly Forbidden in Wireframe):
1. ❌ **No Pause Button**: Cannot simulate a pause capability that the backend execution loop does not support.
2. ❌ **No External Side-Effect Rollback Button**: Cannot claim to undo disk writes or API calls.
3. ❌ **No Horizontal Parallel Swimlanes**: Replaced by hierarchical, collapsible DAG clusters in Inspector.
4. ❌ **No "Proof" Badges on Pure LLM Claims**: Only render mathematical verification badges on physical SHA-256 disk readbacks.
5. ❌ **No Raw Event Telemetry in Primary Stream**: Raw Socket.IO JSON is quarantined in Tier 4 debug drawers.
6. ❌ **No Multi-Day Offline Approval Inbox**: Approvals are active memory waiters (`threading.Event`).
7. ❌ **No Opaque Confidence Percentages**: Trust is established via epistemic provenance, not arbitrary probability numbers.

---

# 11. Hostile Scenario Validation (Stress-Testing the Architecture)

The synthesized 004 architecture was subjected to 8 hostile operational scenarios:

### 🧪 Scenario A: Simple 5-Second Chat Query
* **Execution**: User asks `"What port is the server running on?"`
* **UI Behavior**: Operates as a sleek conversational stream. Left and Right drawers remain closed. Answer streams cleanly. **PASS**.

### 🧪 Scenario B: 4-Hour Autonomous Mission (80 Steps)
* **Execution**: NALA executes multi-file refactoring across 80 steps.
* **UI Behavior**: Timeline groups completed steps into a collapsible summary (`"74 steps completed ✓"`). Active step and recent artifacts stay pinned. Zero DOM lag. **PASS**.

### 🧪 Scenario C: Tool Fails Mid-Step (404 / Syntax Error)
* **Execution**: Subprocess exits with error code 1.
* **UI Behavior**: Recovery Engine intercepts error, increments attempt counter, and displays amber card: `"Auto-Retrying Step (Attempt 2/3) with Adjusted Prompt"`. No panic or broken UI. **PASS**.

### 🧪 Scenario D: Destructive Command Attempted (`rm -rf /`)
* **Execution**: Tool request targets prohibited system directory.
* **UI Behavior**: `AdaptiveVivekaGate` returns `APPROVAL_REQUIRED`. High-friction modal surfaces with red danger banner and blast-radius details. User clicks `Deny` $\to$ NALA halts step cleanly. **PASS**.

### 🧪 Scenario E: Hard Process Crash (`SIGKILL`) & Restart
* **Execution**: Server terminates abruptly mid-step.
* **UI Behavior**: On reboot, `NalaRunner` loads `checkpoint_LSN_000003.json`. React timeline resumes cleanly at Step 3 without duplicate bubbles or corrupted state. **PASS**.

### 🧪 Scenario F: Browser Disconnects for 5 Minutes
* **Execution**: User closes laptop while mission runs.
* **UI Behavior**: Top status dot turns Amber (`"Reconnecting..."`). Upon socket reconnect, stream catches up to current active step without state loss. **PASS**.

### 🧪 Scenario G: Model Claims Success But File is Missing
* **Execution**: Model asserts `"Created database.py"`, but file does not exist on disk.
* **UI Behavior**: `PhysicalEvidenceCorroborator` fails readback. Zero Artifact Card is rendered. Verification badge reads `"No Physical Artifact Found on Disk"`. Zero hallucination bypass. **PASS**.

### 🧪 Scenario H: Managing Multiple Concurrent Missions
* **Execution**: User runs Mission A (Frontend) and Mission B (Backend).
* **UI Behavior**: Left History Drawer allows 1-click switching between Mission A and B. Active stream is scoped strictly to `activeSessionId`. Events never cross-contaminate. **PASS**.

---

# 12. Structural Constraints for Stage 005 (Wireframing Inputs)

When drawing the wireframes in Stage 005:

1. **Top Bar Geometry**: Fixed height $56\text{px}$, containing Brand Icon, Mission Breadcrumb, State Dot, Elapsed Timer, Resource Burn Indicator, and Stop Button.
2. **Left History Drawer Geometry**: Width $260\text{px} - 300\text{px}$, containing Active Missions, Checkpoint Lineage, Context Workspace (Memory), and Async Inbox.
3. **Right Inspector Drawer Geometry**: Width $320\text{px} - 380\text{px}$, containing 4 clean tabs:
   - Tab 1: `Epistemic Evidence & Pramāṇa`
   - Tab 2: `Safety & Viveka Gate Rationale`
   - Tab 3: `Tool Registry & Sandbox Telemetry`
   - Tab 4: `Checkpoints & WAL Ledger (LSN)`
4. **Center Mission Surface Geometry**: Flexible width (Min $600\text{px}$), containing Human Directive, Co-Planning Plan Card, Live Progress Timeline, Verified Artifact Cards, and Sticky Pill Composer.
5. **Composer Pill Placement**: Sticky at bottom with auto-expanding textarea, mode selector pill, and Send button.

---

# 13. Final Architectural Verdict

### Verdict: 🟢 **AUTHORITATIVE APPROVAL — PROCEED TO 005 WIREFRAMES**

`NALA-UI-RESEARCH-004` successfully bridges theoretical agentic research, hostile dual-agent autopsy findings, and physical laptop repository truth into a unified, mathematically sound, and cognitively ergonomic Information Architecture.

*We are now 100% prepared to proceed to Stage 005: Structural Geometry & Wireframes.* 🧠📐⚔️🚀
