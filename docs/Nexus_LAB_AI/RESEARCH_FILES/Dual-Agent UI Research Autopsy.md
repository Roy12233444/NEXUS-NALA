# **NALA-UI-RESEARCH-002: Dual-Agent Research Autopsy**

The transition from generative conversational models to autonomous, multi-agent computational organisms requires a profound restructuring of human-computer interaction (HCI). The preliminary research document, NALA-UI-RESEARCH-001, provided a comprehensive archaeological survey of the contemporary agentic landscape, evaluating frameworks such as Magentic-UI, Claude Code, OpenAI Codex, and Devin1. While that research identified foundational paradigms—specifically the necessity of transitioning away from linear chat interfaces toward spatial command centers—it requires rigorous adversarial validation before establishing the constitutional parameters for the Nexus Autonomous Logic Architecture (NALA).  
This document serves as the terminal research and decision layer bridging theoretical interaction models and the concrete wireframing phase. It subjects the 001 archaeological findings to an exhaustive, dual-agent autopsy. By employing two distinct expert analytical lenses—a cognitive interaction-model analysis and a structural systems-architecture audit—this report independently attacks the prior research to expose embedded assumptions, force epistemic disagreements, and synthesize the definitive user interface (UI) principles that NALA must implement. The overarching mandate is the operationalization of progressive disclosure: NALA’s interface must expose consequences, verifiable evidence, and decisions, while strictly relegating internal state complexity behind deliberate inspection thresholds3.

## **01 — Evidence Audit**

The 001 research correctly identified several high-value interaction patterns across the competitive landscape but suffered from critical blind spots regarding human cognitive limitations, technical edge cases, and the structural realities of long-running execution. This evidence audit deconstructs the validity of the primary claims made in the preceding archaeological research.

### **Evaluation of Magentic-UI Assertions**

The 001 report heavily leveraged Microsoft's Magentic-UI as the blueprint for human-in-the-loop (HITL) agentic systems, particularly lauding its "Action Guard" and "Co-planning" mechanisms2. The evidence overwhelmingly supports the efficacy of the Action Guard mechanism. Empirical adversarial evaluations demonstrated that Magentic-UI’s tri-state classification system (always/maybe/never irreversible), evaluated by an LLM judge, successfully prevented unauthorized actions in simulated prompt injection and social engineering attacks5. The recommendation to map this directly to NALA's RTA-GUARD and Ṛta Validator (Subsystem 002D) is architecturally sound.  
However, the 001 report failed to adequately critique Magentic-UI's "Co-planning" architecture. The source documentation explicitly states that Magentic-UI utilizes a flat domain-specific language (DSL) for planning, producing a linear sequence of steps assigned to specific agents5. This flat DSL is structurally incapable of representing complex branching logic or parallel execution steps. Recommending this model for NALA—which relies on a multi-branching Directed Acyclic Graph (DAG) for its SAPTACORE council routes and dynamic planner (Subsystem 002B)—was a critical oversight. Adopting a flat DSL would artificially bottleneck NALA's execution engine to match an inferior UI paradigm. Furthermore, the 001 report underestimated the cognitive friction documented in Magentic-UI's own qualitative studies, where users reported severe stress and context-switching fatigue when monitoring multitasking agents through collapsible execution logs7.

### **Evaluation of Claude Code Assertions**

The archaeological report correctly identified Claude Code's /rewind checkpointing capability as a critical mechanism for temporal state recovery, emphasizing its utility in undoing isolated code changes and conversation turns9. The evidence confirms that Claude Code successfully tracks file edits executed through native tools, retaining checkpoints for a 30-day lifecycle and allowing granular rollback9.  
Nevertheless, the 001 report's interpretation of this mechanism as a panacea for autonomous recovery is structurally incomplete. Primary documentation explicitly warns that Claude Code's checkpointing intentionally ignores modifications executed via Bash environments (e.g., sed, awk, rm), external integrated development environments (IDEs), and symlinked directories9. Treating this narrow, tool-tracked-only model as a definitive architectural pattern is dangerous. NALA's Checkpoint subsystem (002F), which utilizes cryptographic Log Sequence Numbers (LSNs) and ARIES-style crash recovery, requires a vastly more robust observability plane that encompasses deterministic state tracking across the entire operating environment, not merely localized file-edit API calls1.

### **Evaluation of Codex, Cursor, and Devin Assertions**

The prior research accurately characterized the isolated, thread-based parallel execution models of the OpenAI Codex desktop application and Cursor11. The isolation of agents into specific Git worktrees successfully prevents file-write collisions, which is essential for multi-agent safety11. However, the 001 report prematurely concluded that displaying parallel threads as simultaneous visual "swimlanes" is a viable UI pattern for human oversight. Academic literature on human-agent interaction strictly warns that parallel monitoring induces severe cognitive load, leading to automation complacency and alert fatigue when the number of concurrent tasks exceeds a human's working memory capacity8. Additionally, Devin's reliance on asynchronous screen-recording playback for verification2 is a reactive paradigm; it forces the human to audit actions post-execution rather than providing real-time epistemic transparency.

### **Evaluation of OpenHands and Epistemic Assertions**

The 001 report correctly assessed that adopting the Agent Client Protocol (ACP) via OpenHands is premature for NALA2. A meta-surface designed to be agent-agnostic inherently strips away the specialized metadata required for NALA's differentiating features. The most robust conclusion of the 001 report was the identification of an industry-wide failure to distinguish between a generative model's inference and verifiable physical evidence (the Pramāṇa route)1. None of the surveyed platforms provide a native UI primitive for epistemic provenance. The conclusion that NALA must invent this interface primitive remains entirely valid and serves as the primary differentiating vector for the target architecture.

## **02 — Gemini Independent Autopsy**

This autopsy phase examines the 001 research strictly through the lens of human cognition, psychological load distribution, and the interaction models imposed upon the operator. The core thesis of this audit is that existing archetypes operate on a "chatbot-as-shell" paradigm, which forces a linear, conversational cognitive model onto multi-dimensional, non-deterministic agentic tasks3.

### **Competitive Validity and UX Flaws**

An investigation into the specific user experience (UX) mechanisms of the competitive set reveals significant friction points that NALA must avoid:

* **Magentic-UI:** While highly praised for its oversight mechanics, the reliance on a web-based embedded browser and explicit co-tasking (where humans and agents fight for cursor control) creates a high-stress, deeply synchronous environment. The "multitasking on steroids" approach induces severe cognitive strain7.  
* **Claude Code:** The terminal-first architecture enforces high information density but demands high technical fluency9. Its permission cycle (deny → ask → allow) is robust10, but the reliance on terminal streams makes retrospective visualization of the agent's branching logic impossible.  
* **Devin & Cursor:** Both systems lean heavily into autonomy, utilizing PR-based review (Cursor) or post-hoc screen recordings (Devin)2. This imposes an "auditor" cognitive model on the human, which is fundamentally misaligned with NALA's requirement for active, risk-tiered supervisory control during the execution phase.  
* **Codex:** While Codex introduces a valuable "Skills library" and background automations, it completely obscures resource telemetry (compute and token costs) behind deep settings menus2. For sovereign, resource-constrained deployments, cost visibility must be a primary UI surface.

### **Interaction-Model Analysis**

An interface is not merely a visual skin; it is a mechanical constraint that dictates how a human conceptualizes a machine's capabilities. The interface must be evaluated by the cognitive model it imposes across the seven distinct phases of the agentic lifecycle:

> 1. **User Intention:** Traditional chat interfaces create a massive "gulf of execution"15. Users are forced to encode complex, multi-variable strategic intent into flat natural language strings, resulting in high-entropy prompt engineering3. NALA must discard the purely conversational input paradigm. Intention must be framed through coactive design matrices—structured input parameters augmented by generative UI (GenUI) affordances, allowing the human to toggle constraints (e.g., max cost, strict security) alongside natural language goals3.  
> 2. **Agent Interpretation:** In current systems, interpretation is invisible. The user types a prompt, and the system immediately begins tool execution. NALA must impose an explicit "Understanding" phase. The interface must dynamically render its semantic comprehension of the task before generating a formal plan, allowing the operator to correct misalignment before computational resources are expended.  
> 3. **Planning:** The 001 report suggested editable textual plans. This imposes a "code reviewer" cognitive model on the user. Instead, the UI should impose an "architectural approval" model. Planning must be visualized as a dynamic Directed Acyclic Graph (DAG) canvas1. The human reviews operational pathways, dependency chains, and resource allocations, interacting with nodes rather than text strings3.  
> 4. **Execution:** The prevailing paradigm utilizes collapsible action histories (Magentic-UI) or terminal streams (Claude Code)5. This demands continuous partial attention, heavily taxing the operator. NALA's execution phase must impose an asynchronous "delegation" model. The interface must abstract continuous execution into distinct semantic milestones (e.g., "Compiling assets," "Verifying endpoints"), remaining entirely silent unless a predefined safety boundary is crossed.  
> 5. **Intervention:** Current systems demand synchronous intervention (e.g., a blocking prompt for a CAPTCHA or MFA code), which shatters the operator's flow state. The cognitive model must shift to an "asynchronous inbox" paradigm6. Interventions must be batched, allowing the human to resolve them rhythmically without halting independent, non-blocked parallel threads.  
> 6. **Verification:** Systems currently display final outputs as monolithic text answers2. NALA must enforce an "Epistemic Audit" model. Verification requires visually dissecting the output into Claim vs. Evidence, explicitly marking which components derive from direct environmental measurement and which are probabilistic model inferences1.  
> 7. **Completion:** The output must be presented as a durable, stateful artifact3. It should not scroll away into a chat history. Completion marks the transition of the artifact into the system's Long-Term Memory (002A) via a reusable Playbook.

### **Cognitive-Load Autopsy**

The most severe threat to NALA is overwhelming the operator with progressive telemetry. As the backend executes sophisticated 7-phase reasoning matrices and Viveka safety evaluations, surfacing this data indiscriminately will paralyze the user. The architecture of a One-Person Agentic Company (OPAC) requires the human to manage vast swarms of agents; therefore, cognitive load must be meticulously managed13. The UI architecture must rigidly enforce the following visibility tiers:

* **What MUST be visible (Primary Attentional Layer):**  
  * **Macro-State Semantics:** Distilled, high-level natural language summaries of current progress.  
  * **Irreversible Action Gates:** Explicit, un-bypassable prompts requiring human authorization for destructive actions, adhering to the highest friction standards5.  
  * **Global Health and Resource Burn:** Ambient indicators of system stability and token/compute consumption13.  
* **What SHOULD be visible (Contextual Layer):**  
  * **Durable Artifacts:** Evolving outputs presented as interactive GenUI objects rather than text blocks3.  
  * **Asynchronous Takeover Queue:** A non-intrusive indicator of batched tasks requiring human input.  
  * **Epistemic Badging:** Icons denoting the Pramāṇa route of visible data.  
* **What SHOULD remain hidden (Sub-attentional Layer):**  
  * **Micro-Recovery Telemetry:** Subsystem 002G (Recovery Engine) loops, such as minor parsing errors, HTTP 429 backoffs, and localized tool retries. If the system is self-healing, the human must not be taxed with its observation.  
  * **Routine Tool Invocations:** The raw JSON payloads of standard, read-only API calls.  
* **What belongs behind inspection (The "View Details" Layer):**  
  * **The DAG Execution Graph:** The full, multi-branching visualization of the task plan.  
  * **LSN Checkpoint Ledgers:** The scrubbable timeline of cryptographic state snapshots2.  
  * **Viveka Rationale:** The explicit logical deduction used by the RTA-GUARD to classify a tool call's risk tier.

## **03 — Claude Independent Autopsy**

The Claude Code audit evaluates the 001 research from the perspective of strict systems architecture, testing whether the proposed UI paradigms can structurally survive multi-hour, multi-day, non-deterministic agentic execution across distributed environments.

### **Architectural Attack on Interaction Primitives**

If NALA is to support continuous, persistent autonomy, the interface primitives cannot be modeled on transient chat sessions. The 001 report listed conceptual structures, but an architectural audit requires mapping these concepts to rigorous state machines and event-sourced systems14. Every primitive must be durable, serializable, and independent of the UI client's lifecycle.

* **Mission:** *001 Concept: Overarching objective.* **Architectural Reality:** A Mission is a durable state container and permission boundary. It represents a persistent orchestrator loop (Subsystem 002E) that survives client disconnects. It must possess its own memory context and resource limits. The UI must render a Mission as a sovereign workspace, not a chat thread.  
* **Task:** *001 Concept: Sub-agent workstream.* **Architectural Reality:** A Task is a dynamically allocated compute thread assigned to a specific specialist agent (e.g., FileSurfer, Coder)5. The UI must represent Tasks as node clusters within the overarching Mission DAG, capable of asynchronous completion.  
* **Plan:** *001 Concept: Editable list of steps.* **Architectural Reality:** The Plan is a mutable Directed Acyclic Graph (DAG) mapped to a Petri Net architecture to handle state transitions, conflict resolution, and token routing16. The UI must render the Plan mathematically accurately; a flat text list is an architectural lie. It must support parallel branches and conditional logic gates.  
* **Step & Action:** *001 Concept: Sequential progress points.* **Architectural Reality:** A Step is a semantic grouping of underlying Actions (API requests, file writes, shell commands). The UI must enforce a strict semantic boundary: Steps are visible in the primary view; raw Actions are confined to the Inspector.  
* **Approval:** *001 Concept: Binary or Tri-state Action Guard.* **Architectural Reality:** Approval is a cryptographic signature appended to an action payload, unlocking a strict lattice-refinement boundary. The UI must link the Approval primitive directly to the Viveka rationale engine, ensuring the human operator can audit the risk profile before signing2.  
* **Intervention:** *001 Concept: Takeover request.* **Architectural Reality:** Intervention is a localized thread-yield state. When an agent requires an MFA token, it must not pause the entire Mission. It parks the specific thread, persisting the state to the Asynchronous Queue, while sibling threads continue execution. The UI must map Interventions to specific DAG nodes, not global blocking modals.  
* **Checkpoint & Recovery:** *001 Concept: /rewind snapshot.* **Architectural Reality:** Checkpoints are immutable Log Sequence Numbers (LSNs) tracking the global state of the organism, built on ARIES-style crash recovery mechanics1. The UI must represent Checkpoints as deterministic "Restore Points." When triggered, the UI must clearly delineate the blast radius—showing exactly which database rows, files, and memory vectors will be reverted, overcoming the severe limitations of Claude Code's tool-only tracking9.  
* **Artifact & Verification:** *001 Concept: Downloadable files.* **Architectural Reality:** Artifacts are typed data objects bound to Epistemic Provenance metadata (Pramāṇa). The UI must treat Artifacts as first-class workspace entities, physically separated from the conversational execution log, enabling direct manipulation and verification.  
* **Memory & Completion:** *001 Concept: Session history.* **Architectural Reality:** Memory is the continuous updating of vector stores and the extraction of reusable standard operating procedures (SOPs). Completion is the formal packaging of a successful Mission DAG into a reusable Playbook in the Chiranjeevi memory system. The UI must visualize this extraction, showing the operator how current successes optimize future automation.

The architectural audit concludes that the 001 report's reliance on "swimlanes" for parallel orchestration is mathematically flawed. Swimlanes (e.g., Agent A in lane 1, Agent B in lane 2\) cannot visually represent recursive sub-agent spawning or dynamic scatter-gather operations without inducing catastrophic visual clutter. The Orchestration primitive must be mapped to a hierarchical, collapsible node graph, ensuring structural integrity regardless of agent swarm scale13.

## **04 — Conflict Matrix**

The dual-agent autopsy exposes critical intersections of agreement, profound architectural disagreements, and unresolved gaps in the 001 research. The synthesis of these conflicts defines the exact boundaries of NALA's UI design, forcing a rigorous epistemic discipline upon the wireframing phase.

| Structural Dimension | Gemini Verdict (Cognitive Model) | Claude Verdict (Systems Architecture) | Conflict Resolution & Synthesis |
| :---- | :---- | :---- | :---- |
| **Execution Observability** | **DISAGREE:** Raw execution logs, even if collapsed, cause severe trace bloat and alert fatigue. The UI must show only semantic summaries to preserve human working memory8. | **DISAGREE:** Abstracting execution entirely obscures the actual DAG state. Operators cannot debug a multi-agent deadlock or cyclic loop without a precise, node-based representation. | **SYNTHESIS (Progressive Disclosure):** The primary view is a strictly semantic summary (e.g., "Working..."). The underlying DAG is structurally present and updated in real-time but relegated exclusively to the "View Details" Inspector layer3. |
| **Intervention Mechanics** | **AGREE:** Synchronous blocking pop-ups break user flow. Interventions must be batched asynchronously to respect operator rhythm. | **DISAGREE:** Asynchronous queues are insufficient for critical paths. If an agent requires an MFA token to proceed with a primary database write, execution is fundamentally blocked. | **SYNTHESIS (Dual-Track Intervention):** Non-critical ambiguities are routed to an asynchronous inbox. Critical-path blockers trigger a distinct, localized "Yield State" that pauses only the dependent branch of the DAG, allowing independent sibling nodes to continue. |
| **Epistemic Provenance** | **AGREE:** Claim vs. Evidence distinction is paramount to prevent automation bias and ensure human trust. | **AGREE:** Pramāṇa routing must be mapped to distinct cryptographic data objects to prevent LLM hallucinations from corrupting verified sensor state. | **STRONG CONCLUSION (Invent):** This is the core UI invention. Evidence objects (verified data) must be visually distinct from Claim objects (LLM inferences), enforced system-wide. |
| **Action Guards / Safety** | **AGREE:** Tri-state risk tiering (Magentic-UI style) reduces cognitive load by eliminating routine approval fatigue5. | **AGREE:** RTA-GUARD integration is structurally sound, provided the Viveka LLM rationale is queryable for post-incident audits2. | **STRONG CONCLUSION (Adopt/Adapt):** Implement tri-state Action Guards. The interface must utilize strategic cognitive friction for irreversible actions, requiring typed confirmation rather than simple binary clicks14. |
| **Temporal Recovery (LSNs)** | **DISAGREE:** A complex scrubbable timeline is too technical for end-users; recovery should feel like a standard "undo" button. | **DISAGREE:** A simple "undo" masks the reality of distributed state. Users must understand exactly what an LSN rollback affects to avoid state corruption. | **SYNTHESIS (Semantic Restore Points):** Expose an interface that translates cryptographic LSNs into human-readable milestones (e.g., "Before database migration"), accompanied by an explicit, visually mapped blast-radius manifest1. |
| **Parallel Orchestration** | **DISAGREE:** Swimlanes induce cognitive overload when managing more than three concurrent tasks13. | **DISAGREE:** Swimlanes are structurally incapable of mapping recursive or fractal sub-agent spawning. | **STRONG CONCLUSION (Reject):** Reject horizontal swimlanes entirely. Represent cross-core orchestration via a dynamic, collapsible hierarchical tree within the Inspector. |
| **Offline/Local Operations** | **MISSING:** How does the UI signal that the agent is running locally versus heavily leveraging cloud resources? | **MISSING:** How is distributed compute latency represented without looking like a system hang or timeout? | **UNRESOLVED GAP:** The wireframe phase must invent a specific ambient telemetry indicator for execution locus (Local vs. Remote compute) and resource burn. |

## **05 — NALA UI Derivation Matrix**

Based on the adversarial synthesis and the resolution of the conflict matrix, the following strategic vectors form the constitutional bridge to the wireframe phase, utilizing the required ADOPT / ADAPT / REJECT / INVENT taxonomy.

| Capability | Evidence/Context | Gemini (Cognitive) | Claude (Architectural) | Final Verdict | NALA UI Treatment |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Live Execution Status** | Magentic-UI collapsible logs5 | YES, but heavily abstract | NO to raw text streams | **ADAPT** | Primary UI shows semantic status only. Raw logs are strictly hidden. |
| **Action Guard Approvals** | Peer-reviewed safety utility5 | YES | YES | **ADOPT** | Tri-state risk tiers. Irreversible actions demand high-friction confirmation logic. |
| **Detailed Telemetry** | High trace bloat risk8 | NO | YES (for debug) | **REJECT** | Never placed on the primary execution surface. Banished to Inspector. |
| **Mission Planning** | Flat DSL limits branching5 | YES | NO | **ADAPT** | Visually distinct from chat; must support DAG representation, but hidden behind Inspector default. |
| **Time Travel / Checkpoints** | Claude Code limitations9 | YES | YES | **ADAPT** | Semantic "Restore Points" mapped to deterministic LSNs, featuring explicit rollback boundary manifests. |
| **Pramāṇa Routing** | NALA core differentiator1 | YES | YES | **INVENT** | Epistemic Provenance Inspector. Distinct UI badges for Measurement (Pratyakṣa), Inference (Anumāna), and Citation (Śabda). |
| **Evidence vs. Claim** | Crucial for trust mitigation14 | YES | YES | **INVENT** | Native UI object separation. Visual UI must refuse to render a model claim utilizing the same typography or iconography as a verified fact. |
| **Parallel Orchestration** | Swimlanes cause cognitive load13 | NO | NO | **REJECT** | Reject horizontal swimlanes. Utilize hierarchical, collapsible DAG clusters. |
| **Asynchronous Takeover** | Prevents sync blocking6 | YES | YES | **ADAPT** | Dual-track implementation: Batchable inbox for low-priority requests; localized edge-pausing for critical blockers. |
| **Viveka Rationale** | Required for safety audits2 | YES | YES | **ADOPT** | Deep-linked Inspector drawer explaining the explicit logic of why NALA classified an action as risky or safe. |
| **Resource Telemetry** | Cost/Compute visibility13 | YES | YES | **INVENT** | Persistent, subtle ambient indicator of resource utilization (Token/Compute burn rate) mapped to OPAC constraints. |

## **06 — Cognitive Load Constitution**

To prevent the wireframing phase from degenerating into a complex engineering dashboard or regressing into a simplistic chatbot, the design architecture is governed by the following immutable constitutional rules.

### **Axiom I: The Interface is a Consequence Engine**

**Rule:** *Complexity belongs in the system. Clarity belongs in the interface.* NALA's primary interface must exclusively expose consequences, decisions, and verifiable evidence. It must actively suppress internal computational complexity. The user must be presented with the outcome of a process ("File created and verified") rather than the mechanical steps taken to achieve it ("Invoked file\_writer tool, parsed JSON, handled exception, executed bash"). Internal complexity is accessed exclusively via deliberate, user-initiated progressive disclosure3.

### **Axiom II: The Warmwind/Cowork Progressive Disclosure Model**

**Rule:** *Execution is a narrative; architecture is a blueprint.*  
The interface must not look like an engineer's dashboard by default. It should render a simple, reassuring narrative:  
NALA: "I'll build the Python tool and verify that it actually works."  
\[Working...\]  
✓ Created the file  
✓ Ran verification  
✓ Checked the result  
Done.  
However, appended to this narrative must be a subtle View details → affordance. Activating this affordance reveals the deep machinery—the Pramāṇa route, the LSN checkpoint, the Viveka safety score, and the underlying DAG. This spatial transition allows NALA to deliver the frictionless interaction model of modern consumer AI without sacrificing the rigorous observability required of an autonomous control architecture.

### **Axiom III: Epistemic Supremacy**

**Rule:** *Trust is verified, not assumed.* The human operator is the ultimate epistemic judge. The system must never launder an AI's probabilistic inference as a deterministic fact. Every data artifact rendered in the UI must carry an epistemic badge. The UI must visually degrade the authority of unverified claims, forcing the human to evaluate the Pramāṇa route for high-stakes assertions1.

### **Axiom IV: Strategic Friction**

**Rule:** *Efficiency must never supersede safety.* Interfaces designed to minimize all friction lead directly to automation complacency and catastrophic unforced errors5. For actions classified by the Viveka engine as irreversible, the UI must intentionally elevate cognitive load. It must refuse binary "Allow/Deny" clicks, requiring the user to explicitly type a confirmation string or interact with a blast-radius manifest14.

### **Axiom V: Silent Self-Healing**

**Rule:** *Do not report the struggle, only the outcome.* Micro-recoveries and self-healing loops executed by Subsystem 002G (e.g., catching a timeout, retrying an endpoint) must not interrupt the human operator1. The primary UI remains undisturbed, while the event is silently logged to the Inspector's telemetry view for future architectural auditing.

## **07 — Wireframe Constraints: Strict Directives**

The transition from architectural research to visual design requires rigid constraints. Designers often default to familiar paradigms (chat streams, traditional IDEs). The following strictures define exactly what the subsequent wireframes MUST and MUST NOT contain.

### **MUST Contain (Mandatory UI Architecture)**

> 1. **Semantic Action Summaries:** The primary view MUST render execution as a semantic narrative, adhering strictly to the Warmwind/Cowork progressive disclosure model.  
> 2. **The Inspector Drawer:** A distinct, persistent architectural layer MUST exist to slide open and reveal the underlying DAG, tools, raw logs, and LSNs, without navigating away from the primary context.  
> 3. **Epistemic Provenance Badging:** Every generated artifact, claim, or data visualization MUST possess a visual UI anchor indicating its origin (e.g., a "Sensor Verified" icon vs. a "Model Inferred" icon).  
> 4. **Asynchronous Takeover Queue:** The interface MUST feature a persistent inbox or dedicated zone for non-blocking human interventions, batched away from the main execution view.  
> 5. **Semantic Restore Points:** The UI MUST represent Subsystem 002F checkpoints as discrete, human-readable milestones that can be selected for deterministic environment rollbacks, accompanied by a visual manifest of the rollback scope.  
> 6. **Context Workspace / Boundary Policy:** There MUST be a dedicated, non-conversational surface for the operator to establish Action Guard policies, define memory contexts (002A), and bound the agent's operational lattice (directories, allowed domains) prior to execution1.  
> 7. **Ambient Resource Telemetry:** The interface MUST feature a subtle, always-visible indicator of computational resource consumption (token usage, active parallel cores) to support OPAC constraints13.

### **MUST NOT Contain (Prohibited Paradigms)**

> 1. **NO Chatbot Primacy:** The primary operational surface MUST NOT be a linear chat interface. While natural language input is acceptable for initial intent-framing17, the output and execution must render as a spatial, stateful workspace3.  
> 2. **NO Raw Telemetry by Default:** The primary UI MUST NOT display raw JSON tool invocations, internal HTTP headers, or raw stack traces. This data is strictly banished to the Inspector drawer.  
> 3. **NO Horizontal Parallel Swimlanes:** The wireframe MUST NOT attempt to visualize cross-core orchestration (002E) as horizontal swimlanes, which fail gracefully under high parallelism.  
> 4. **NO Binary Consent Prompts:** The design MUST NOT include standard "Always Allow" or "Deny" security pop-ups for critical actions. Authorization UI must scale with the risk tier determined by the Viveka engine5.  
> 5. **NO Opaque Confidence Scores:** The interface MUST NOT display arbitrary AI confidence percentages (e.g., "95% confident"). Trust must be established through the display of epistemic provenance and verifiable evidence routes, not probabilistic tonal assertions.

## **Synthesis and Next Steps**

The dual-agent autopsy definitively establishes that an interface for an autonomous computational organism cannot be derived by merely reskinning a conversational agent or simplifying an engineering dashboard. The core challenge resolved by this document is the management of profound backend complexity (Subsystems 002A–002G) against the rigid limits of human cognitive load.  
By enforcing the Progressive Disclosure Model and inventing the Epistemic Provenance primitive, NALA will achieve the clean, consequence-focused interaction paradigm of modern consumer AI while preserving the deep, deterministic observability required for multi-day, self-healing operations.  
The wireframing phase (NALA-UI-WIREFRAME-003) is now unlocked. It must proceed strictly within the boundaries of the Constitution and Constraints established herein, focusing immediately on designing the Epistemic Provenance Inspector and the Semantic Restore Point interface, as these represent NALA's true architectural differentiation.

#### **Works cited**

> 1. Agentic UI Architecture Research.md  
> 2. NALA-UI-RESEARCH-001-Agentic-Interface-Archaeology.md  
> 3. Dynamic Applications as the Human-Agent Interaction Layer \- arXiv, [https://arxiv.org/html/2603.21334v1](https://arxiv.org/html/2603.21334v1)  
> 4. A Formal Hierarchical Architecture for Agentic Orchestration ... \- arXiv, [https://arxiv.org/html/2607.11138v1](https://arxiv.org/html/2607.11138v1)  
> 5. Magentic-UI: Towards Human-in-the-loop Agentic Systems | alphaXiv, [https://www.alphaxiv.org/abs/2507.22358](https://www.alphaxiv.org/abs/2507.22358)  
> 6. Magentic-UI: Towards Human-in-the-loop Agentic Systems \- arXiv, [https://arxiv.org/html/2507.22358v1](https://arxiv.org/html/2507.22358v1)  
> 7. Magentic-UI: Towards Human-in-the-Loop Agentic Systems, [https://news.ycombinator.com/item?id=44746321](https://news.ycombinator.com/item?id=44746321)  
> 8. Towards AI as Colleagues: Multi-Agent System Improves Structured, [https://arxiv.org/html/2510.23904v1](https://arxiv.org/html/2510.23904v1)  
> 9. Claude Code /rewind: Undo Any AI Mistake in One Command, [https://blog.vincentqiao.com/en/posts/claude-code-rewind/](https://blog.vincentqiao.com/en/posts/claude-code-rewind/)  
> 10. \[Claude Code E37\] Git Workflow: status/diff/log ... \- YouTube, [https://www.youtube.com/watch?v=hzEoN9yXSuc](https://www.youtube.com/watch?v=hzEoN9yXSuc)  
> 11. OpenAI's Codex desktop app is all about managing agents, [https://thenewstack.io/openais-codex-desktop-app-is-all-about-managing-agents/](https://thenewstack.io/openais-codex-desktop-app-is-all-about-managing-agents/)  
> 12. Codex App Server \- ChatGPT Learn, [https://learn.chatgpt.com/docs/app-server](https://learn.chatgpt.com/docs/app-server)  
> 13. From Solo Control to Enterprise Scale Through Agentic AI, [https://www.preprints.org/manuscript/202608.1414](https://www.preprints.org/manuscript/202608.1414)  
> 14. ANX: Protocol-First Design for AI Agent Interaction with a Supporting, [https://arxiv.org/html/2604.04820v1](https://arxiv.org/html/2604.04820v1)  
> 15. 상호작용 기반의 AI 정렬을 위한 언어 요소 분해 \- KIXLAB, [https://kixlab.github.io/website-files/theses/thesis-phd-2026-taesoo.pdf](https://kixlab.github.io/website-files/theses/thesis-phd-2026-taesoo.pdf)  
> 16. Towards Open Complex Human–AI Agents Collaboration ... \- arXiv, [https://arxiv.org/html/2505.00018v1](https://arxiv.org/html/2505.00018v1)  
> 17. The Agentic Shift \- aaron, [https://blog.aaronvick.com/the-agentic-shift](https://blog.aaronvick.com/the-agentic-shift)