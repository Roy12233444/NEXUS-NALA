# NALA-UI-RESEARCH-002 — Artifact 03: Claude Independent Audit

**Role:** Systems architect, not UX reviewer.
**Object under audit:** `Agentic_UI_Architecture_Research.md` (001).
**Method:** Test whether 001's primitives and ADOPT/ADAPT/REJECT/INVENT verdicts survive contact with NALA's actual backend constraints — not whether they're well-written.
**Out of scope (per 002 charter):** no redesign, no wireframe, no code, no CSS, no citation-authority checking (that's Gemini's lane).

---

## 1. Primitive Survival Audit

001's own request (via the 002 brief) was to test the primitive set: **Mission, Task, Plan, Step, Action, Approval, Intervention, Checkpoint, Recovery, Artifact, Verification, Memory, Completion.** Checked against 001 §5 (Interaction Primitive Matrix), here's actual coverage:

| Primitive | 001 Status | Finding |
|---|---|---|
| Mission | Formally defined | Survives |
| Plan | Formally defined (DAG) | Survives, but collapses Task/Step into it — see below |
| Checkpoint | Formally defined (LSN) | Survives definition; contested on capability, see §2.1 |
| Intervention | Defined as "Takeover Request" | Survives, but conflated with Approval — see below |
| Memory | Named as subsystem 002A only in §7, absent from §5 | **Gap** — no primitive-level data model, only a UI-mapping label |
| Task / Step | Never named | **Missing** — DAG "nodes" are implied to be tasks/steps but never given a schema (id, status, parent plan, retry count) |
| Action | Only appears inside "Action Guard" | **Missing as its own object** — a tool invocation instance (what was called, with what params, what it returned) has no defined primitive |
| Approval | Only appears inside "Action Guard" / "Permission Boundary" | **Missing** — no record object for *who approved, what evidence they were shown, when*. This matters: Design Principle #3 demands "strategic cognitive friction" before approval, but there's nothing to prove that friction was actually engaged after the fact |
| Recovery | Named as subsystem 002G in §7 only | **Gap** — no primitive: what triggered it, what was tried, what the outcome was. Given NALA's actual crash-recovery work (ARIES phases, RunawayLoopGuard) already produces this data, the UI research doesn't yet have an object to bind it to |
| Artifact | Named only in Design Principle #9 ("first-class objects") | **Gap** — asserted as important, never given a schema |
| Verification | Never named as a distinct primitive | **Missing** — Pramāṇa (§7) covers *epistemic classification* of a claim, which is not the same thing as *verification* (e.g., a test ran and passed, a checksum matched, a human signed off). These get conflated in 001 and shouldn't be |
| Completion | Never defined | **Missing** — no stated condition for "Mission Complete," and no resolution of what happens if 002G recovery is still silently active after the UI shows "Done" |

**Verdict:** 8 of 13 target primitives are either absent or exist only as informal mentions inside subsystem-mapping prose, not as defined objects. §5's matrix is *thinner* than the interaction model the rest of 001 assumes. This is the single most important finding for the derivation matrix — it means several of 001's "ADOPT" verdicts (e.g., Action Guards, Co-Planning) are being adopted as *behaviors* without an underlying *data model*, which will bite during wireframing when someone asks "what does an Approval record actually contain."

---

## 2. Structural Stress-Tests on Major Claims

### 2.1 — LSN Time-Travel vs. side-effecting execution

001 §6A adopts "Visual State Checkpointing (Time Travel)" as essential, citing LangGraph Studio, and §11 Principle 6 states rewinding to an LSN "must accurately reflect the system state at that exact moment."

This is true for LangGraph because its side effects are largely internal to the graph. NALA's HANDS layer executes real tool calls — file writes, external API calls, sandboxed shell commands. Internal state (memory, plan position, checkpoint LSN) is trivially rewindable. **External world state is not.** If NALA writes a file, sends a request, or mutates an external system between LSN 40 and LSN 42, rewinding to LSN 40 restores NALA's *belief* about the world, not the world itself. 001 never distinguishes internal-state rewind from external-effect rewind, and treats "Time Travel" as a single uniform capability. It isn't. This is a REJECT-or-ADAPT-level issue, not a footnote — per NALA's own existing recovery work (ARIES-phase crash recovery, StateMatrixValidator), this distinction is presumably already handled at the recovery-engine level; the UI research needs to inherit that distinction rather than promise something the backend can't uniformly deliver.

**Recommended resolution before wireframe:** define two checkpoint semantics — *state rewind* (always safe) and *effect rewind* (only safe for compensable/idempotent tool actions) — and require the Inspector to visually distinguish which kind is available at a given LSN.

### 2.2 — Pramāṇa badging assumes a trustworthy classifier

001 §6D and §11 Principle 2 make epistemic grounding (Pratyakṣa / Anumāna / Upamāna / Śabda) load-bearing for NALA's entire trust model, explicitly rejecting "opaque confidence scores" in favor of this typed classification.

The architectural question 001 never asks: **who assigns the Pramāṇa type to a claim, and by what mechanism?** If the same generative model that produced the claim also self-labels its epistemic route, the badge is only as reliable as the model's self-report — which is exactly the failure mode (unverified, potentially hallucinated confidence) the badge is supposed to replace. For this to be the "cryptographically verified" differentiator 001 claims in §15, ClaimAttestation needs either (a) a deterministic, non-generative classifier, or (b) a hash-chain back to the actual tool/measurement output that a human or downstream check can independently verify. 001 uses the word "cryptographic" for LSN checkpoints but never establishes it for ClaimAttestation itself. Right now this is 001's single biggest unearned adjective.

**Verdict:** UNRESOLVED, not ADOPT-ready. This needs an answer before it becomes a UI primitive, or NALA ships a trust badge that can't back up its own claim of trustworthiness.

### 2.3 — Parallel Execution Swimlanes assume concurrency that may not exist yet

001 §7 (002E) and §10 describe "multiple agents executing tasks simultaneously" and swimlane visualization as near-term UI. Per project history, NALA's completed build milestones to date (context tracking, ARIES crash recovery, 1-hour soak test) do not include a documented concurrent multi-agent orchestration capability — the harness as built is describable as a single planner/executor loop with sandboxed tool execution, not a scatter-gather swarm.

This isn't a rejection of the swimlane concept — it's a flag that 001 is designing UI for a *target-state* capability (§13's own "Future 002H" framing hints at this) without labeling it as such in §7 and §10, where it reads as present-tense architecture. If swimlanes get built into the wireframe as a Phase-1 surface, and the backend can only ever show one active lane at a time, the UI will misrepresent system state on day one.

**Recommended resolution:** 002 should explicitly tag which backend subsystems (002A–G) are *built*, which are *in progress*, and which are *aspirational* before any surface gets promoted into wireframe scope. Swimlanes should be gated behind confirmed concurrent execution, not built ahead of it.

### 2.4 — Subsystem naming may have drifted from the actual harness

001 organizes everything around subsystems 002A–002G (Memory, Planner, Pramāṇa, Safety+Tool Registry, Orchestration, Checkpoints, Recovery Engine). NALA's actual documented architecture uses a different vocabulary: BRAIN (Planner + SAPTACORE Council + Ṛta Validator), HANDS (Executor + Sandbox + Tool Registry + Router), SESSION (AMP Chiranjeevi + TQB + SDG + Dronagiri + Crystallizer), SAFETY (RTA-GUARD + USHA Protocol + Circuit Breaker), plus concrete built modules like HandoffSpore, LockResolver, StateMatrixValidator, RunawayLoopGuard.

I can't fully resolve this from the research documents alone — it's possible 002A–G is a clean superset abstraction that maps onto BRAIN/HANDS/SESSION/SAFETY, or it's possible the UI research was written against an idealized architecture that has since diverged from what's actually implemented. Either way, this needs an explicit mapping table before wireframe, or the "NALA Backend → UI Mapping" in 001 §7 is mapping UI surfaces to labels that don't have a 1:1 correspondence to shippable modules.

**This is a GAP, not a FAILS — flag for verification, not rejection.**

### 2.5 — The chat-UI sunk cost isn't addressed

001 §6C rejects "Chatbot-as-Primary-Interface" outright and §16 recommends the wireframe phase "strictly ignore conversational UI paradigms." A working chat-based prototype (ChatSection.tsx + websocketService.ts + Socket.IO server) already exists as a real, running artifact. 001's recommendation amounts to a full interaction-paradigm discard, not an evolution of existing work, and the research never weighs that cost — it argues the architectural case for rejection cleanly, but "correct destination" and "free to get there" are different claims, and 001 only makes the first one.

**Not a flaw in the architectural conclusion** — the REJECT verdict on chat-as-primary is well-argued and I don't think it survives softening. But 002 (or the wireframe-constraints stage) should explicitly own the decision to discard the v0.1 chat prototype's UI paradigm rather than let it be an implicit casualty.

---

## 3. Verdict Table — Does the 001 Conclusion Survive Architectural Audit?

| 001 Conclusion | Original Verdict | Audit Result |
|---|---|---|
| Action Guards at tool boundary | ADOPT | **Survives** — sound, but needs an Approval primitive (§1) to be inspectable/auditable |
| Co-Planning DAG surface | ADOPT | **Survives** — but Task/Step need formal definition first |
| LSN Time-Travel / checkpoint scrubbing | ADOPT | **Survives with conditions** — must split state-rewind from effect-rewind (§2.1) |
| Lattice-refined permissions (reject binary allow/deny) | REJECT (of binary) | **Survives** |
| Chatbot-as-primary rejection | REJECT | **Survives**, but cost to existing prototype should be explicit (§2.5) |
| Pramāṇa epistemic badging | INVENT | **Unresolved** — trust mechanism undefined (§2.2) |
| Parallel execution swimlanes | ADOPT (near-term) | **Unresolved** — likely target-state, not current-state (§2.3) |
| 002A–G subsystem mapping | (structural framing) | **Gap** — needs verification against actual harness naming (§2.4) |
| Silent self-healing (002G) | (design principle 8) | **Survives** — consistent with existing ARIES/RunawayLoopGuard recovery work, but has no primitive to attach telemetry to (§1) |

---

## 4. What I'm handing to the conflict matrix

**High confidence (recommend ADOPT as-is):** Action Guards, Co-Planning DAG, lattice permissions, chatbot rejection, silent self-healing behavior.

**Needs resolution before wireframe, not more research:** the Task/Step/Action/Approval/Recovery/Artifact/Verification/Completion primitives need formal schemas — this is a definitional gap 002 can close directly without waiting on Gemini.

**Needs resolution that depends on backend truth, not UI research:** whether concurrent orchestration is currently real (§2.3), whether 002A–G maps cleanly onto BRAIN/HANDS/SESSION/SAFETY (§2.4), and whether ClaimAttestation has any non-generative verification path (§2.2). These three should go back to you, not forward to a wireframe — no amount of UI research resolves them.

**Where I expect disagreement with Gemini:** Gemini's brief is UX/cognitive-load focused, so I'd expect the strongest tension to land on the Pramāṇa badging question (§2.2) — Gemini may evaluate it purely as "does this reduce cognitive load," while my finding is that it's currently unearned trust regardless of how well it's presented. Worth deliberately checking whether Gemini's audit surfaces the same self-attestation problem or misses it.
