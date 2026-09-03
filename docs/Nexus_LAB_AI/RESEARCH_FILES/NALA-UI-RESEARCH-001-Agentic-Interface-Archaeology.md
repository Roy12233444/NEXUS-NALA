# NALA-UI-RESEARCH-001 — Agentic Interface Archaeology
**Research-only deliverable. No code, no NALA modification, no wireframe.**
Prepared as of August 28, 2026. All product facts below are grounded in cited sources; anything synthesized or recommended is explicitly marked as **Analysis**.

---

## 1. Executive Summary

No product studied is a "Control Center" in the sense NALA needs. Each optimizes for a different unit of work: **Codex** is a command center for parallel coding *threads*; **Claude Cowork** is a goal-in / deliverable-out workspace for non-coding knowledge work; **Claude Code** is a terminal-first, checkpoint-safe pairing tool built around explicit permission modes; **Magentic-UI** is a Microsoft Research prototype built specifically to *study* human-in-the-loop mechanisms, not a shipped product optimized for daily throughput. None of them expose anything resembling epistemic-method transparency (how a conclusion was reached) or a formal distinction between *evidence* and *claim* — which is exactly the territory NALA's Pramāṇa (002C) and evidence-provenance requirements occupy.

Two findings should anchor everything that follows:

1. **The single most validated mechanism across all competitive research is risk-tiered action approval** (Magentic-UI's Action Guard: always/maybe/never-irreversible, with an LLM judge for the ambiguous middle tier). This maps almost one-to-one onto RTA-GUARD + Ṛta Validator and should be adopted with high confidence.
2. **The single most consistent failure mode across all competitive research is cognitive overload from raw progressive disclosure.** Even Magentic-UI's own qualitative study — designed by the people building the mechanism — found users overwhelmed by collapsible logs and asking for higher-level summaries instead. NALA's backend is deeper (7 phases, dual safety layers, an epistemic council) than anything studied here, which means this failure mode is *more* likely for NALA, not less, unless synthesis layers are designed in from the start rather than retrofitted.

NALA's genuine white space is narrow but real: **epistemic-route transparency and evidence-vs-claim distinction**. Nothing studied — including the two products explicitly built around trust and oversight (Magentic-UI, Claude Code's plan/checkpoint system) — exposes *how* an agent knows something, only *what* it did and *whether* it asked permission. That gap is where a Control Center architecture, not a chatbot, actually earns its name.

---

## 2. Systems Studied

| # | System | Maker | What it actually is | Status as of Aug 2026 |
|---|---|---|---|---|
| 1 | Codex app | OpenAI | Desktop command center for parallel coding agents (threads), skills, and scheduled Automations | Shipped, macOS (Feb 2, 2026) + Windows (Mar 4, 2026) |
| 2 | Claude Cowork | Anthropic | Cloud-continued agentic workspace for non-coding knowledge work, built on the Claude Code architecture | Shipped, beta on web/mobile |
| 3 | Claude Code | Anthropic | Terminal/IDE/desktop agent for software engineering, with explicit permission modes and file checkpointing | Shipped, mature (v2.1.x) |
| 4 | Magentic-UI | Microsoft Research | Open-source **research prototype** for studying human-in-the-loop agent interaction (not a production product) | Research release, July 2025 paper |
| 5 | Devin | Cognition | Cloud-native autonomous software engineer with session-as-artifact model and desktop-testing playback | Shipped, Devin 2.2 |
| 6 | Cursor Cloud/Background Agents | Cursor / Anysphere | IDE-embedded parallel agent manager (up to 8 concurrent), branch-isolated, PR-delivered | Shipped, GA |
| 7 | OpenHands / Agent Canvas | OpenHands (formerly OpenDevin) | Open-source, **agent-agnostic** client using the Agent Client Protocol (ACP) to control OpenHands, Claude Code, or Codex interchangeably | Alpha (Agent Canvas, mid-2026) |

**Supplementary frameworks (not products, but load-bearing for Parts 6–7 below):**
- Sheridan & Verplank's ten-level scale of human supervisory control (1978) — the foundational academic model for "how much does the human vs. the machine decide."
- Shneiderman's (2022) two-dimensional critique of that model — automation and human control are independent axes, not opposite ends of one dial.
- Anthropic's own engineering writeup on its multi-agent Research system — directly relevant because it documents production-scale orchestrator/sub-agent observability, exactly NALA's 002E/002G territory, from the same company whose agentic architecture underlies Cowork and Claude Code.

---

## 3. Evidence Sources

**Primary (official product pages, docs, or the research paper itself):**
- OpenAI, "Introducing the Codex app," openai.com/index/introducing-the-codex-app (Feb 2, 2026; updated Mar 4, 2026)
- Anthropic, Claude Cowork overview and safety docs — claude.com/docs/cowork/overview; support.claude.com (articles 13345190, 13364135)
- Anthropic, Claude Code docs — code.claude.com/docs/en/permission-modes; code.claude.com/docs/en/checkpointing; platform.claude.com/docs (file-checkpointing)
- Anthropic, "How we built our multi-agent research system" and "How we built Claude Code auto mode" — anthropic.com/engineering
- Mozannar, Bansal, Tan, et al. (Microsoft Research), "Magentic-UI: Towards Human-in-the-loop Agentic Systems," arXiv:2507.22358 (full paper, including appendices and the 24-scenario adversarial evaluation)
- Cognition, "Devin 2.0," "Introducing Devin 2.2," "How Cognition Uses Devin to Build Devin," "Devin is now generally available" — cognition.com/blog; docs.devin.ai
- Cursor, "New Coding Model and Agent Interface" (2.0 changelog) — cursor.com/changelog/2-0
- OpenHands, "Agent Canvas Initiative" (GitHub issue #14374), "Controlling any Coding Agent with the OpenHands Agent Canvas and SDK" — github.com/OpenHands/OpenHands; openhands.dev/blog
- Sheridan & Verplank (1978), levels of human supervisory control (as reproduced/cited in later academic surveys, since the 1978 report itself is not web-hosted in full text)

**Secondary (used only to corroborate or fill gaps in primary sources, never as the sole basis for a claim):**
- IntuitionLabs, ALM Corp, Niobond, AICC, igmguru — Codex app feature summaries
- DataCamp, TechSy, AiOpsSchool — Claude Cowork tutorials and pricing context
- ClaudeFast, TheAiArchitects, ThePromptShelf, BuildThisNow, AIforAnything — Claude Code permission-mode and checkpoint mechanics (cross-checked against the two official doc pages above; treated as reliable where they matched primary docs verbatim)
- Medium (Nitinmatani), AImodels.fyi, Semantic Scholar mirrors — Devin and Magentic-UI secondary summaries
- Blink, AITechFy, Ameany, NodoAI — Cursor Background/Cloud Agent mechanics
- LocalAIMaster, AIagentsList — OpenHands architecture context
- Shneiderman (2022) two-dimensional automation/control framework, as surveyed in arXiv:2505.22477 ("Human-Centered Human-AI Collaboration")
- The AI Engineer, LangChain blog, ZenML, Constellation Research, ByteByteGo, Colourful Codes, LLM Multi Agent — secondary commentary on Anthropic's multi-agent engineering post, used only to corroborate points already present in the primary Anthropic post

**Note on marketing vs. observed behavior:** Several secondary sources describe Codex and Cursor features ("richer experience," "guided process") in promotional language not present in the primary sources. Those framings were excluded; only mechanically verifiable claims (what the interface does, what the docs say happens) were carried into this report.

---

## 4. Competitive UX Matrix

| Dimension | Codex app | Claude Cowork | Claude Code | Magentic-UI | Devin | Cursor Cloud Agents | OpenHands/Agent Canvas |
|---|---|---|---|---|---|---|---|
| Task creation unit | Thread (per project, per agent) | Session (per granted folder/goal) | Session (per repo/branch) | Session (per task) | Session (persistent, URL-addressable) | Agent run (per branch/worktree) | Agent-agnostic session over ACP |
| Planning visibility | Skills chosen implicitly; no MSR-style editable plan artifact evidenced | "Analyzes request and creates a plan," subtasks — plan object not shown as user-editable in docs fetched | Explicit Plan Mode; plan written to disk, editable, gated by Accept | Explicit editable plan DSL (agent, title, details); mandatory Accept before execution | Devin 2.0 proactively researches and proposes a plan before autonomous work | No pre-execution plan artifact evidenced; task description only | Delegates to whichever agent's own plan model is active |
| Execution visibility | Diff review per thread; worktree isolation | Sub-agent coordination described; internals not user-addressable | Real-time tool calls in terminal/IDE | Live browser view + collapsible per-step action banners | Session log + desktop screen-recording playback | Real-time progress indicators, file/decision logs | Depends on underlying agent |
| Approval/safety model | Sandboxed by default; elevated commands need approval; team-configurable rules | Folder-scoped permission grant; deletion requires approval | Six permission modes (manual/auto-accept/plan/auto/bypass/etc.), classifier-gated auto mode | Tri-state Action Guard (always/maybe/never irreversible) + LLM judge | Session-level pause/terminate; no documented per-action guard | Sandboxed shell by default (2.0); diff review before merge | Inherits underlying agent's model |
| Multi-agent / parallel | Yes — multiple threads, worktree-isolated | Yes — sub-agent workstreams, not individually addressable | Subagents via Task(AgentName); user controls which are allowed | Orchestrator + WebSurfer/Coder/FileSurfer/MCP agents | Not multi-agent in the Magentic-UI sense; single autonomous engineer | Up to 8 parallel, branch-isolated | Explicitly agent-agnostic by design |
| Long-running / background | Automations (scheduled, background) | Cloud-continued; survives laptop close | Sessions resumable via --resume/--continue | Multi-tasking sessions, switch between them | Persistent cloud sessions | Cloud-native by default | Depends on underlying agent |
| Recovery / failure handling | Not documented in sources fetched | Not documented beyond general reliability language | /rewind (checkpoints); explicit but tool-tracked-edits-only | Re-plan + wait-for-approval on detected risk (validated in 24 adversarial scenarios) | Screen-recording review after PR; self-review before handoff | PR-based review; no documented mid-run recovery UI | Depends on underlying agent |
| Memory / history | Session history + config persist per project | Sessions saved to account | Checkpoints persist 30 days; plans saved to plansDirectory | Saved-plans gallery (task→plan pairs), auto-retrieved by similarity | Session history; "Devin Wiki" and "Devin Search" over codebase | Branch history via git; no dedicated memory object | Depends on underlying agent |
| Notifications | Automation results land in a review queue | Not detailed in sources fetched | N/A (synchronous terminal) | Session status indicator (red dot / spinner / check) | Slack + desktop notifications | Email + desktop + Slack | Depends on underlying agent |
| Cost/resource visibility | Included in ChatGPT plan; credits purchasable, not inline | Usage tracked at org level (monitoring doc), not inline per-task | /usage estimates; Console is authoritative; not inline by default | Not a shipped product — no cost model | Plan-based; per-session cost not surfaced in sources fetched | Per-PR cost surfaced explicitly (~$4–6), most transparent of the set | Depends on underlying agent |
| User control vs. autonomy | High autonomy inside sandbox bounds; team-configurable elevation rules | High autonomy inside granted folder | Fully tunable, six discrete modes | Deliberately tuned for HITL; every mechanism exists to keep a human in the loop | High autonomy; human reviews after the fact more than during | High autonomy; human reviews via PR | N/A — a shell, not a policy |

**Analysis:** Cost/resource visibility is the weakest dimension across the board except Cursor, which is transparent mostly because its pricing model forces the issue (per-task cost). This is a genuine gap NALA can close by design rather than by accident — see Section 11, Principle 10.

---

## 5. Interaction Primitive Matrix

The brief for this research explicitly warns against assuming these primitives are equivalent across products. They are not. What each actually means:

- **"Thread" (Codex):** one agent's isolated, worktree-scoped conversation within a project. Multiple threads = multiple agents working in parallel on the same repo without file conflicts, not multiple *views* of one agent.
- **"Session" (Cowork):** a full agentic run — plan, sub-tasking, execution — against a folder the user has explicitly granted. The plan itself, per the documentation fetched, is described narratively ("Analyzes your request and creates a plan") but is not shown as a user-editable artifact the way Magentic-UI's or Claude Code's plans are. This is a real design difference, not a naming one.
- **"Plan" (Claude Code):** a literal, versioned artifact written to `plansDirectory` on disk, editable in a text editor (`Ctrl+G`), and gated by an explicit Accept step that also determines the execution permission mode. Distinct from "plan" in Magentic-UI, which lives only inside the app's UI state and vector-DB memory, not the filesystem.
- **"Plan" (Magentic-UI):** an explicit domain-specific language — a flat sequence of `(agent_name, title, details)` steps — editable directly in the UI or by natural-language feedback. The paper's own Discussion section flags that this flat DSL cannot represent branching or parallel steps, a known, self-reported limitation.
- **"Checkpoint" (Claude Code):** an automatic snapshot taken before every prompt that results in a file edit, scoped **only** to edits made through Claude's own Write/Edit/NotebookEdit tools. Edits made via Bash (`sed`, `mv`, `rm`), by other concurrent sessions, or through symlinks are explicitly **not** tracked — a documented blind spot, not an edge case.
- **"Checkpoint/Memory" (Magentic-UI):** not a state snapshot at all — it is a saved `(task, plan)` pair in a gallery, retrievable by similarity for future tasks. This is closer to what NALA would call a *playbook* than what NALA calls a checkpoint (002F).
- **"Action Guard" (Magentic-UI):** a per-action gate with three irreversibility tiers set by the developer (always/maybe/never irreversible); the "maybe" tier is resolved by a purpose-built LLM judge using a fixed rubric (real-world consequence, reversibility, data/privacy impact, effect on others).
- **"Session" (Devin):** a persistent, URL-addressable artifact that can be reviewed, shared, and resumed from Slack, CLI, web, or API — closer to a durable object than a conversation.
- **"Agent" (Cursor):** an isolated execution unit bound to a git worktree or remote machine; its natural output unit is a pull request, not a chat transcript.
- **"Agent" (OpenHands/Agent Canvas):** the primitive is deliberately underspecified — Agent Canvas treats "agent" as a pluggable, protocol-level entity (via ACP) that could be OpenHands' own agent, Claude Code, or Codex. It is architecturally the odd one out: a meta-surface for *any* agent rather than a specific agent's UI.

**Analysis — direct implication for NALA:** NALA's plan object needs branching/parallel support that Magentic-UI's own DSL lacks (to represent SAPTACORE's council routes), and NALA's checkpoint object needs to cover every mutation path that Claude Code's tool-tracked-only model misses (relevant because AMP/ARIES-style recovery already tracks state more broadly). Both are addressed in Section 6 and Section 7.

---

## 6. Keep / Reject / Adapt / Invent Matrix

| Pattern | Source | Classification | Reasoning |
|---|---|---|---|
| Editable pre-execution plan with mandatory Accept gate | Magentic-UI co-planning; Claude Code Plan Mode | **ADAPT** | The shared, editable plan representation and explicit accept gate are sound and well-evidenced. But a flat NL-only DSL is a *documented* limitation (no branching/parallel), and NALA's SAPTACORE council needs exactly that. Straight adoption would import a known weakness. |
| Collapsible per-step action history with progress bar | Magentic-UI | **ADOPT, with a synthesis layer** | The mechanism is sound, but Magentic-UI's own qualitative study found even this overwhelming for long histories; participants explicitly asked for higher-level visual/video summaries. Adopt the collapse, but pair every collapsed block with an AI-generated natural-language digest, not raw logs alone. |
| Tri-state irreversibility Action Guard + LLM judge | Magentic-UI | **ADOPT** | The single most rigorously validated mechanism in the competitive set (24-scenario adversarial red-team, zero successful attacks in default config). Maps almost directly onto RTA-GUARD/Ṛta Validator; NALA should mirror the always/maybe/never tiering and feed the "maybe" tier to Ṛta rather than inventing a new rubric. |
| Checkpoint/rewind restricted to tool-tracked edits | Claude Code | **ADAPT** | The UX (double-Esc, "Restore code / conversation / both," 30-day retention, 100-checkpoint cap) is a strong precedent for the *interaction*. The scope is not — Bash-mediated, symlinked, and cross-session edits are explicitly untracked. NALA's ARIES/LSN-based recovery is architecturally broader; the UI should not artificially narrow it to match this gap. |
| Multi-session sidebar with status-only indicators | Magentic-UI (red dot/spinner/check); Codex/Cursor/Devin session lists | **ADOPT the pattern, REJECT the ambiguity** | Magentic-UI's own participants found the red-dot design confusing. Adopt a persistent session list with state indicators, but use labeled text states, not color/shape alone — this becomes a design principle (Section 11, #3). |
| Desktop screen-recording playback as evidence | Devin | **ADAPT** | Valuable precedent for distinguishing an agent's narrated claim from what actually happened, but it's scoped to Devin's own browser-testing loop. NALA needs this generalized to any tool call or sensor output, not just visual UI testing — this feeds directly into the Evidence object (see Section 6, next row). |
| Agent-agnostic protocol client (ACP) | OpenHands/Agent Canvas | **REJECT for v1, revisit at 002H** | Architecturally elegant, but premature: NALA's differentiators (epistemic routing, Ṛta safety metadata, evidence provenance) are not generic-agent-shaped. Building an ACP-style pluggable shell now would force a lowest-common-denominator plan format and strip exactly the metadata that makes NALA's Control Center worth building. |
| Skills library as a first-class, inspectable, shareable object | Codex | **ADOPT** | Directly reusable as the UI representation for NALA's existing Agent Skills files and the Tool Registry (002D). |
| Automations with an async review queue | Codex | **ADOPT** | Strong precedent for a future Mission Queue (002H): schedule work, let it run unattended, land results in a review inbox rather than requiring live supervision. |
| Cost/resource meter as a buried settings page | Nearly every product studied except Cursor | **REJECT the pattern, INVENT the alternative** | Every competitor treats cost as an afterthought. Given NALA's sovereign/efficiency-constrained mission, cost and resource consumption should be always-on telemetry, not a settings page — this is architecturally aligned with the project's own premise, not just good UX. |
| Epistemic method / evidence classification as a first-class object | *(no direct precedent)* | **INVENT** | Nothing studied — not even Magentic-UI, which is explicitly built for oversight — exposes *how* an agent knows something (direct observation vs. inference vs. testimony) as a UI object. This is genuine white space and should be the centerpiece differentiator, not a bolt-on. |
| Physical evidence vs. model-claim distinction | Closest analogues: Devin's screen recordings, Magentic-UI's screenshot verification | **INVENT** | Neither analogue formally tags "this is sensor/tool-verified" vs. "this is the model's narrated account." NALA should introduce an explicit Evidence object type distinct from Action and from Claim. |

---

## 7. NALA Backend → UI Mapping

Following the requested chain — External Pattern → NALA Subsystem → UI Representation → User Value:

1. Magentic-UI's collapsible per-step action history + progress bar → **002E Cross-Core Orchestration** → Live causal execution timeline, swimlaned by core → User understands what NALA is doing across cores in real time.
2. Magentic-UI's editable co-planning DSL + Codex's skill-based delegation → **002B Dynamic Planner** → Editable Mission Plan with per-step agent/skill assignment and explicit branching support → User can align, correct, or veto NALA's approach before resources commit.
3. Magentic-UI's tri-state Action Guard → **002D Safety + Tool Registry (RTA-GUARD / Ṛta Validator)** → Pre-execution Action Guard with Ṛta-classified risk tiers → User is interrupted only for genuinely risky or irreversible actions, preserving low cognitive load.
4. Claude Code's `/rewind` checkpoint ledger (restore code / conversation / both) → **002F Durable Checkpoint & Runtime State (ARIES phases, LSN)** → LSN-indexed Checkpoint Ledger with selective restore → User can undo failed autonomous excursions with confidence, closing the exact blind spot (Bash-mediated edits) Claude Code itself has.
5. Devin's screen-recording playback + Magentic-UI's screenshot-based verification → **002C Pramāṇa + 002D Tool Registry (new: Evidence object)** → Evidence Inspector distinguishing sensor/tool-verified facts from model claims → User can tell what NALA actually observed versus what it inferred or was told.
6. OpenAI Codex's Automations + review queue → **Future 002H Long-Running Autonomy** → Mission Queue with an asynchronous review inbox → User delegates multi-day work without babysitting it, while still gating on completion review.
7. Anthropic's production tracing for multi-agent systems (decision-pattern and interaction-structure monitoring, without per-conversation content tracking) → **002G Recovery Engine & Self-Healing + 002A Memory** → System Health & Recovery Telemetry panel, aggregate and privacy-respecting → User (and NALA's own maintainer) can diagnose systemic failure modes, not just single-session errors.
8. Magentic-UI's saved-plans gallery + Codex's skills library → **002A Memory (Chiranjeevi / Crystallizer)** → Reusable Playbook Gallery of learned plans, re-attachable to new missions → The user's investment in correcting NALA once compounds into future missions instead of evaporating.
9. Magentic-UI's Action Guard judge rationale + Devin's self-review-before-handoff loop → **002D Viveka (discernment)** → Decision Rationale Panel, separate from the raw action log → User can audit *why* NALA judged something safe, unsafe, or correct — not merely *that* it did.

---

## 8. Cognitive Load Analysis

**Grounding finding:** Magentic-UI's own qualitative study — the most rigorous HITL usability evaluation in the competitive set — found that even its progressive-disclosure design (task → step → action, collapsible panels) overwhelmed several participants trying to review long histories. They asked for video-style or visual summaries instead of raw logs. This is direct evidence against a "show everything, just fold it" strategy. NALA's backend is substantially richer than Magentic-UI's, which raises rather than lowers this risk.

**Six-tier disclosure model** (mapping Part 5's requested items onto Part 6's visibility framework):

| Tier | What lives here |
|---|---|
| 1. Always visible | Mission goal, current step name, overall execution state (running / paused / awaiting-approval / recovering / complete), system health indicator, cost/resource meter |
| 2. Contextually visible | Safety decision awaiting approval, epistemic-route badge on the step currently executing, retry count when non-zero, human-approval prompt |
| 3. Inspector/drawer (opt-in) | Tool execution detail, evidence provenance, checkpoint/LSN detail, full plan DSL for direct editing |
| 4. Expandable detail | Per-step action list — collapsed by default, but summarized in natural language above the fold, never raw logs alone |
| 5. Historical view | Mission timeline replay, checkpoint ledger, playbook/memory gallery, past recovery events |
| 6. Developer/debug view | Raw SAPTACORE council transcripts, LockResolver/StateMatrixValidator internals, RunawayLoopGuard telemetry, soak-test heartbeat logs — behind an explicit mode switch, never default |

**Answering the four questions the brief poses directly:**
- *What must a user know immediately?* Current state, and a single unified signal for "does this need you right now" — labeled in text, because Magentic-UI's own users found a color-only/shape-only signal (the red dot) ambiguous.
- *What can remain hidden?* Low-level tool-call arguments, raw council deliberation transcripts, raw checkpoint/LSN binary data.
- *What should appear only when something changes?* Retry counters, re-planning events, epistemic-route escalations (e.g., a step moving from direct observation to inference).
- *What should appear only on failure?* Recovery state, RunawayLoopGuard trigger notices, degraded-mode banners.
- *What should be inspectable on demand?* Everything else — the drawer model, never a modal that blocks the live view.

---

## 9. Human-Agent Supervision Model

**Framework:** Sheridan & Verplank's ten-level scale treats autonomy as a single dial from fully manual to fully autonomous. Shneiderman's (2022) critique — that this one-dimensional model is outdated and potentially unsafe for trustworthy AI design — argues instead for two independent axes: how much the system decides, and how much control/oversight the human retains. **Analysis:** NALA should adopt Shneiderman's two-axis model explicitly, rather than modeling supervision as a single slider the way Claude Code's Shift-Tab permission-mode cycle effectively does. Magentic-UI's own qualitative data supports this: participants wanted *more* approval gates for high-risk actions (payments, emails, subscriptions) while explicitly wanting *fewer* for low-risk ones (adding to cart) — a single global autonomy dial cannot satisfy both preferences at once; risk-tiering can.

**What the human should always control:** mission-level goals and acceptance of a plan; approval of any Ṛta-flagged irreversible action; final override, pause, and cancel authority at any time.

**What NALA should control autonomously (within approved bounds):** step sequencing inside an accepted plan; tool selection within Tool Registry limits; self-healing and bounded retries governed by RunawayLoopGuard; choice of epistemic route for a given sub-question.

**Supervision primitives, judged against the research:**

| Primitive | Verdict | Basis |
|---|---|---|
| Observe | ADOPT | Combine Magentic-UI's live execution view with Cowork's "step away, return to finished work" pattern — both, not either. |
| Intervene | ADOPT, generalized | Claude Code's mid-task interrupt + Magentic-UI's co-tasking browser takeover, generalized beyond the browser to any tool NALA is using. |
| Redirect | ADOPT, with a fix | Magentic-UI's mid-execution plan editing is the right mechanism, but the paper documents cases where user edits were not successfully incorporated. NALA's Planner must guarantee a redirect is provably re-ingested, not silently absorbed. |
| Approve | ADOPT | Action Guard tri-state, mapped onto Ṛta risk tiers. |
| Pause/resume | ADOPT | Cowork's cloud-continuation model — a mission survives closing the laptop and can be resumed from any surface. |
| Cancel | ADOPT | Universal, always reachable, single-confirmation friction only. |
| Inspect | ADOPT | Devin's session-as-durable-artifact model, combined with the Evidence Inspector from Section 6. |
| Recover | **INVENT** | No competitor exposes "here is exactly what failed and how I'm retrying" as a first-class UI object — this is 002G's opportunity to lead, not follow. |
| Delegate | ADOPT | Codex Automations' scheduled/background delegation, gated by a review queue. |

---

## 10. NALA Information Architecture

*(Conceptual structure only — no wireframe, per the research brief.)*

**Primary navigation:** Missions (active/queued), Playbook/Memory gallery, System Health, Tool Registry & Settings. Reasoning: every competitor studied splits its top level this way in substance if not in name (Codex: threads-by-project; Cowork: sessions; Devin: sessions list; Magentic-UI: session sidebar).

**Secondary navigation, within a Mission:** Plan · Execution Timeline · Evidence · Checkpoints · Council/Epistemic Trace.

**Mission workspace:** the accepted plan plus an always-visible state strip (Section 8, Tier 1).

**Execution surface:** the live causal timeline, swimlaned by 002E core/agent, collapsed per step with an AI-generated digest above the fold (Section 6 verdict on Magentic-UI's pattern).

**Inspector:** a drawer, never a modal — opened on demand for tool calls, evidence, decision rationale (Viveka), and epistemic route. Modeled on Codex's non-blocking diff review and Magentic-UI's split-panel browser view, neither of which interrupts the live surface to show detail.

**History:** mission timeline replay and the checkpoint ledger, kept separate from the live view — because Magentic-UI's study found that reviewing "how the agent got there" was a distinct need from watching it happen, especially while multitasking across sessions.

**Artifact surface:** generated files/deliverables, versioned and downloadable — modeled on Cowork's "preview and download" pattern.

**Telemetry surface:** a persistent but minimized cost/resource/latency strip, expandable to a full graph — directly closing the cost-visibility gap found in Section 4's matrix.

**System status:** a global health/recovery indicator, distinct from any single mission's state, because 002G is a cross-cutting concern rather than something scoped to one mission.

**Intervention controls:** persistent and reachable from anywhere a mission is visible — never buried in a nested detail view. This directly addresses the documented Magentic-UI weakness where a mid-execution redirect sometimes failed to land: if intervention is a first-class, always-reachable control rather than a nested action, both the affordance and the guarantee of ingestion are easier to build and to verify.

---

## 11. NALA UI Design Principles

1. The human controls goals and irreversible actions; NALA controls sequencing and tool selection within approved bounds. *(Shneiderman's two-axis model.)*
2. Autonomy and interruptibility are independent controls, not opposite ends of one slider. *(Contrast with Claude Code's single permission-mode cycle.)*
3. State must be legible from a single glance, in text — never inferred from color or icon shape alone. *(Magentic-UI's own red-dot confusion.)*
4. Every collapsed action log needs a synthesized summary above it, not just a fold. *(MSR participants asked for visual/video digests.)*
5. Irreversibility, not task category, determines whether an action pauses for approval. *(Action Guard tri-state.)*
6. Approval requests should be batchable — several related decisions in one interruption beats one interruption per decision. *(MSR participants explicitly preferred bundled clarifying questions.)*
7. A redirect issued mid-execution must be provably ingested, not silently absorbed. *(Documented Magentic-UI plan-edit failures.)*
8. Checkpoints must cover every mutation path, not only the tool-mediated ones. *(Claude Code's own Bash-edit blind spot.)*
9. Evidence is not the same object as a claim; the interface must let the user tell them apart. *(Gap across every system studied; NALA's actual differentiator.)*
10. Cost and resource consumption are always-on telemetry, not a settings-page afterthought. *(Weak or absent across nearly every competitor.)*
11. Multi-mission oversight scales by summarization, not by requiring the human to open every session. *(Magentic-UI's own multitasking pain points.)*
12. Recovery from failure is narrated in the same interface as normal progress, never hidden in a separate log. *(No competitor does this well — genuine invention territory.)*
13. A saved plan or playbook is a first-class, editable, shareable object, not a hidden cache. *(Magentic-UI's saved-plans gallery; Codex's skills library.)*
14. Long-running and background missions must survive device or session loss without losing state or auditability. *(Cowork's cloud-continuation pattern.)*
15. The inspector is a drawer the user opens, never a modal that blocks the live view. *(Synthesized from Codex's diff review and Magentic-UI's split-panel design.)*
16. Developer/debug internals stay behind an explicit mode switch, never the default view. *(Cognitive-load discipline, Section 8.)*
17. Sensitive or irreversible autonomous actions get a visually distinct register from routine ones — never the same badge style. *(Magentic-UI risk-tier participant feedback.)*
18. Every autonomous decision NALA makes must be traceable to the epistemic route that produced it. *(No direct precedent — this is Pramāṇa's actual UI mandate.)*

---

## 12. Failure/Recovery UX Requirements

**What the research shows:**
- Magentic-UI's design response to detected risk (phishing pop-ups, prompt injection) is consistently to re-plan and wait for approval rather than fail silently or proceed — validated across 24 adversarial scenarios with zero successful attacks in the default configuration.
- Claude Code's checkpoint/rewind system is a real, well-designed manual recovery lever, but has documented gaps: Bash-mediated edits, symlinked/hard-linked files, a 100-checkpoint cap, and 30-day retention are all explicit, named limitations, not implementation accidents.
- Anthropic's own production multi-agent engineering post describes resuming agents from where they were when an error occurred, informing the agent of tool failures so it can adapt, and layering deterministic safeguards (retry logic, regular checkpoints) underneath that adaptive behavior — a pattern directly relevant to 002F/002G.

**Analysis — what NALA should do better:**
- Ambiguous state should never be silent. A generic spinner is insufficient; the interface should always show a labeled state distinguishing "working," "stuck and retrying (RunawayLoopGuard active)," "awaiting approval," and "recovered from a crash at checkpoint N."
- Partial completion needs explicit accounting — which plan steps succeeded, failed, or were skipped — not just a pass/fail final answer. Magentic-UI's own Discussion section flags this as an open problem: tasks without an inherent success signal are hard for both the agent and the user to evaluate from the final answer alone.
- On timeout or lost connection, missions should keep running and be resumable from any device, consistent with Cowork's cloud-continuation model and with what AMP's Chiranjeevi/HandoffSpore mechanisms already support at the architecture level — the UI's job is to make "resume where I left off" visibly trustworthy, directly answering the difficulty several Magentic-UI participants reported in reconstructing "what has it done" after stepping away.
- On tool failure, mirror Anthropic's own engineering finding: inform the agent so it can adapt, but surface the failure-and-adaptation as a visible event in the timeline, not hide it inside an invisible retry loop.
- Human-approval-required states must be impossible to miss across multiple concurrent missions — an aggregated "needs you" inbox, not per-mission indicators only, directly answering the cross-mission state-summary request Magentic-UI participants raised.

---

## 13. Future 002H+ Compatibility Analysis

| Future requirement | Does the architecture above survive it? | Basis |
|---|---|---|
| Long-running missions | Yes | Mission-as-persistent-object plus cloud-continuation (Cowork pattern). |
| Persistent state | Yes, and stronger than the market leader | The LSN-indexed checkpoint ledger (002F, ARIES-based) is already more complete than Claude Code's tool-tracked-only model. |
| Self-healing | Yes | Recovery telemetry is its own IA surface (Section 10), not mission-scoped, so it scales with 002G rather than being retrofitted into it. |
| Model independence | Yes, provisionally | The Plan, Action Guard, and Evidence objects are deliberately modeled as protocol-level constructs (echoing OpenHands/ACP's own insight) rather than as chrome tied to one model's behavior — but this should be re-checked once 002H concretizes multi-model routing. |
| Multiple agents / distributed execution | Yes, with a caveat | The swimlaned execution timeline (Magentic-UI's orchestrator view + Codex's per-thread parallelism) survives conceptually, but Magentic-UI's own multitasking study qualitatively flagged a human oversight ceiling — no competitor has solved "how many agents can one human meaningfully swimlane," and neither does this report. |
| Offline/local operation | **Open gap — not solved by any competitor studied** | Codex, Cowork, Devin, and Magentic-UI's own Docker/browser sandboxing all assume live connectivity. This is a genuine divergence between NALA's sovereign/local-first mission and every product in the competitive set; it needs original design work, not adaptation. |
| Tool ecosystems | Yes | Tool Registry + Skills-gallery pattern (Codex) scales without redesign. |
| Autonomous recovery | Yes | Covered under Section 12/002G above. |

---

## 14. Major Risks

- **Importing Magentic-UI's flat NL-only plan DSL wholesale** would bring in its own documented limitation (no branching/parallel steps) at precisely the moment NALA needs branching to represent SAPTACORE's council routes.
- **"Cockpit with 100 gauges" is a real risk, not a hypothetical one.** NALA's backend (7 phases, 68 files, dual safety layers, an epistemic council) is richer than anything studied here. The instinct to expose everything because it exists is the most likely single failure mode, and it is in direct tension with a build philosophy that rewards adding depth — that impulse is correct for the backend and actively dangerous if applied to UI surface area.
- **Ambiguous state signaling is a documented usability failure**, not a stylistic nitpick — Magentic-UI's own users found it confusing with far fewer state dimensions (three) than NALA needs to represent (checkpoint state, recovery state, epistemic route, safety tier, and mission progress, at minimum).
- **Building an ACP-style agent-agnostic shell prematurely** risks flattening NALA's actual differentiators — epistemic routing, Ṛta safety metadata, evidence provenance — into a generic agent viewer with none of them exposed.
- **No competitor studied solves offline/local-first operation.** This gap cannot be closed by imitating best practice, because none exists yet in the products examined; it requires original design work, and should not be assumed solved by extension of the patterns above.

---

## 15. Major Opportunities

- **Epistemic-route-as-UI-object and evidence-vs-claim distinction are genuinely unclaimed territory** among every system studied, including the two explicitly built around trust and oversight. This is a real first-mover position for a "trustable reasoning" Control Center, not a marketing claim.
- **NALA's ARIES/LSN-based checkpointing is architecturally more rigorous than the current market leader's (Claude Code's tool-tracked-only model).** The UI should make that rigor legible — a visible, provable claim ("every mutation path is checkpointed, not just editor-tool edits") rather than a hidden implementation detail.
- **RTA-GUARD and Ṛta Validator map almost directly onto Magentic-UI's single most-validated mechanism**, which already has a peer-reviewed adversarial evaluation behind it. This is low design risk and high alignment with the strongest prior art available.
- **SAPTACORE's council plus Viveka discernment give NALA a "show your reasoning" surface no competitor offers**, directly addressing the trust gap Magentic-UI's own qualitative study repeatedly surfaced — participants reviewing "code and all screenshots" out of necessity, or admitting they were trusting output they couldn't actually verify.

---

## 16. Recommended Next Step

Per the staged process this research is meant to feed (`/wireframe → /appscreen → /dashboard → /variations → /restyle`), the recommended next step is **not** to begin wireframing immediately. Two things should happen first:

1. **Terminology reconciliation.** This report used the document's own subsystem labels (002A Memory, 002B Planner, 002C Pramāṇa, 002D Safety/Tool Registry, 002D Viveka, 002E Orchestration, 002F Checkpoints, 002G Recovery). Project history elsewhere describes NALA's actual architecture in different terms — a four-layer BRAIN/HANDS/SESSION/SAFETY model with named components (AMP/Chiranjeevi, SAPTACORE Council, RTA-GUARD, Ṛta Validator, ARIES-based crash recovery). The mapping in Section 7 assumes these two naming schemes refer to the same underlying subsystems, which is a reasonable but unverified inference. Before wireframing, this mapping should be checked line-by-line against the current JIRA numbering so that the UI vocabulary and the backend vocabulary agree — a small reconciliation now is cheaper than a rename after screens exist. Worth flagging separately: this document's own framing of "NALA" as "Nexus Autonomous Logic Architecture" does not match the "Nexus Autonomous Long-Running Agent" expansion used elsewhere in the project — likely a drift in naming rather than a substantive conflict, but worth a single-line confirmation before it propagates further.
2. **A data-model sketch — not a wireframe — of the two genuinely novel objects this report identifies:** the Epistemic Route object (Pramāṇa) and the Evidence object (evidence-vs-claim). Neither has any direct competitive precedent, so unlike the Plan, Action Guard, and Checkpoint objects — which can adapt existing, validated patterns — these two need to be designed from NALA's own requirements first. Getting their fields right (what an epistemic route records, what qualifies as evidence vs. claim) before any visual design work will save a redesign cycle later, since these two objects are the report's stated centerpiece differentiator.

Only after those two steps should `/wireframe` begin, using Sections 7, 10, and 11 above as its direct input.
