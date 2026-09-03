Yes buddy. 🧠⚔️ Since you now have the **Anthropic public Cowork guide**, we can make `NALA-UI-000` much more concrete.

The PDF itself is actually excellent for our research because it describes Cowork not as “better chat,” but as **a system that takes an outcome, plans, executes across files/tools, and produces tangible work**. It explicitly covers local files, sub-agents, long-running work, scheduled tasks, projects, plugins, skills, permissions, and progress/steering.

## 1. First: don't design NALA yet

Your notebook should have this pipeline:

```text
OBSERVATION
     ↓
COMMON PATTERN
     ↓
NALA SHOULD ADOPT
     ↓
NALA SHOULD REJECT
     ↓
NALA SHOULD INVENT
```

But **do it in that order**.

Do not jump from:

> “Cowork has Skills”

to:

> “NALA needs Skills.”

Instead:

> “Cowork has Skills → what problem are Skills solving? → is that problem relevant to NALA? → how does NALA's architecture solve it differently?”

That's the research mindset.

---

# 📕 2. For the Cowork PDF, start here

You don't need to read all 24 pages equally.

Use these pages as your primary observation material:

### 🔥 Pages 4–6 — Mental model + product architecture

The PDF says traditional AI is:

```text
question → answer
```

while Cowork is:

```text
outcome
 ↓
plan
 ↓
execute
 ↓
deliverable
```

It also explicitly identifies:

* local files
* sub-agents
* real deliverables
* long-running work
* scheduled tasks
* projects

as key capabilities.

### Write this in your notebook

**OBSERVATION — COWORK #001**

> Cowork treats AI as a worker operating on an outcome rather than merely a conversational answer generator.

Then underneath:

```text
What does this enable?
What user problem does it solve?
What runtime primitive is required?
What UI primitive is required?
```

---

# 📕 3. Pages 8–9 — THIS IS VERY IMPORTANT FOR NALA

Study the section:

> **“What to expect during a task”**

The PDF says the user can:

```text
watch work
   ↓
see what is happening
   ↓
course-correct
   ↓
let it continue
   ↓
return later
```

It also says complex work can use multiple sub-agents in parallel.

And the current Cowork product page emphasizes the same concept: users can see steps, files opened, tools used, and choices made, while redirecting the task during execution. ([Claude][1])

### Your notebook

```text
OBSERVATION — COWORK #002

LONG-RUNNING WORK

User gives:
    ↓
Goal

System:
    ↓
Plans
    ↓
Executes
    ↓
Shows progress
    ↓
Allows steering
    ↓
Continues
    ↓
Returns result
```

Then ask:

> **Which of these already exists in NALA's RuntimeState / TaskEvent / checkpoint architecture?**

That's where your research becomes **NALA-specific**.

---

# 📕 4. Pages 10–12 — Skills / Plugins

This is where your earlier instinct about **Skills** becomes interesting.

The PDF describes a plugin as a package that can contain:

```text
Skills
Sub-agents
Connectors
```

and says Skills are reusable step-by-step playbooks loaded when a task matches.

Codex independently uses a similar concept: Skills bundle instructions, resources, and scripts so agents can execute repeatable workflows consistently. ([OpenAI][2])

### Don't write

> NALA needs Skills.

Write:

```text
OBSERVATION

Skills solve:
    repeated procedural knowledge

Why useful:
    consistency
    specialization
    less re-explaining
    reusable workflows

NALA QUESTION:

Can NALA represent procedural capability
as a first-class runtime object?
```

That last question is much more valuable.

---

# 📕 5. Pages 13–16 — Real Workflows

This is probably the **best part of the PDF for your research**.

Don't focus on the specific business examples.

Look at the **shape of the workflows**.

For example:

```text
messy inputs
     ↓
gather context
     ↓
analyze
     ↓
produce structured output
     ↓
save artifact
     ↓
human reviews
```

Another:

```text
multiple sources
     ↓
cross-reference
     ↓
synthesize
     ↓
produce deliverable
```

And another:

```text
ambiguous input
     ↓
ask clarification
     ↓
execute
     ↓
flag uncertainty
     ↓
deliver
```

The guide repeatedly emphasizes grounding outputs in actual files and explicitly flagging ambiguity rather than inventing details.

### This is VERY relevant to NALA

Write:

> **A long-running agent UI must represent not only conversation, but the lifecycle of work.**

---

# 📕 6. Page 18–19 — Agent behavior

This section gives us another important observation.

The guide says:

> **Start with a real task, not a demo.**

And recommends using Skills for recurring workflows.

That's directly aligned with what we're doing with NALA.

So your notebook should ask:

```text
Does NALA UI encourage:

Toy conversation?

OR

Real work?
```

That's an architectural question, not a visual-design question.

---

# 🌐 Now: which Codex website should you observe?

Use **official OpenAI sources**, not random YouTube screenshots.

### Start here

[OpenAI Codex](https://openai.com/codex/?utm_source=chatgpt.com)

This gives you the current high-level product model: Codex as a command center for agentic coding, multi-agent workflows, Skills, and background work. ([OpenAI][3])

Then study:

[Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/?utm_source=chatgpt.com)

This is particularly useful for your notebook because it discusses:

* multiple agents
* projects
* threads
* worktrees
* reviewing changes
* Skills
* automations
* background work

([OpenAI][2])

### For Codex, your observation should concentrate on

```text
PROJECT
  ↓
TASK / THREAD
  ↓
AGENT
  ↓
WORK
  ↓
DIFF / ARTIFACT
  ↓
REVIEW
  ↓
CONTINUE
```

Don't obsess over colors or layout.

---

# 🌐 Which Cowork website?

Use these two:

[Claude Cowork official product page](https://claude.com/product/cowork?utm_source=chatgpt.com)

and:

[Claude Cowork product guide](https://claude.com/blog/the-claude-cowork-product-guide?utm_source=chatgpt.com)

The official product page currently emphasizes **tasks, files/tools, visible work, steering, long-running execution, parallel work, Skills, connectors and sub-agents**. ([Claude][1])

You already have the deeper guide as your PDF, so **use the PDF as your primary source** for Cowork observations.

---

# 🧪 And Claude Code?

Yes — study it separately.

Use:

[Claude Code Foundations — Anthropic](https://www.anthropic.com/webinars/claude-code-foundations?utm_source=chatgpt.com)

Why?

Because Cowork shows **knowledge-work agent design**, while Claude Code shows **agentic engineering-work design**.

Anthropic describes Claude Code around the agent loop:

```text
read
 ↓
plan
 ↓
act
 ↓
observe
```

with project instructions, Skills, plugins and sub-agents. ([Anthropic][4])

That gives NALA another reference axis.

---

# 🧠 Your notebook should eventually contain this matrix

Don't fill it from assumptions. Fill it as you observe.

| Capability               | Cowork | Codex | Claude Code | NALA |
| ------------------------ | ------ | ----- | ----------- | ---- |
| Goal-oriented work       |        |       |             |      |
| Long-running execution   |        |       |             |      |
| Projects                 |        |       |             |      |
| Files                    |        |       |             |      |
| Artifacts                |        |       |             |      |
| Live progress            |        |       |             |      |
| Steering                 |        |       |             |      |
| Multiple agents          |        |       |             |      |
| Skills                   |        |       |             |      |
| Plugins                  |        |       |             |      |
| Tools                    |        |       |             |      |
| Approvals                |        |       |             |      |
| Checkpoints              |        |       |             |      |
| Recovery                 |        |       |             |      |
| Scheduling               |        |       |             |      |
| Execution history        |        |       |             |      |
| Runtime state            |        |       |             |      |
| Provenance               |        |       |             |      |
| Local/offline capability |        |       |             |      |

**Don't fill the NALA column yet.**

That's crucial.

---

# 🔥 Then perform the five-stage analysis

After you've filled the observations:

## ① OBSERVATION

Facts only.

Example:

> Cowork shows progress during execution and allows mid-task steering.

---

## ② COMMON PATTERN

Now compare products.

For example:

```text
Cowork ──┐
         ├──► Long-running work must remain observable
Codex ───┤
         │
Claude ──┘
```

That's a **pattern**, not a feature.

---

## ③ NALA SHOULD ADOPT

Ask:

> Does this solve a fundamental problem NALA has?

If yes:

```text
ADOPT
```

But identify **why**, not merely what.

---

## ④ NALA SHOULD REJECT

This is equally important.

Ask:

> Does this pattern conflict with NALA's architectural principles?

For example, if a design assumes permanent cloud execution, that's something we should investigate critically because NALA's architecture has a local-first/sovereignty direction.

Don't automatically reject it either.

**Record the architectural reason.**

---

## ⑤ NALA SHOULD INVENT

This is where I expect the most interesting discoveries.

Ask:

> **What can NALA expose because we have RuntimeState + TaskEvent + checkpoint/recovery architecture?**

For example, investigate whether NALA could expose concepts like:

```text
Execution lineage
Checkpoint health
Recovery position
State ownership
Task continuity
Runtime provenance
Execution graph
Capability state
Agent lifecycle
```

Don't decide these now.

**Discover them.**

---

# ⚔️ The key research principle

Buddy, I want you to remember this sentence while doing `UI-000`:

> **We are not studying interfaces. We are studying how intelligence becomes a visible working environment.**

That's the real research.

Codex is showing us one branch:

```text
software engineering
+
agents
+
parallel work
+
skills
+
background execution
```

([OpenAI][2])

Cowork shows another:

```text
knowledge work
+
files
+
tools
+
sub-agents
+
long-running execution
+
deliverables
+
projects
```

Claude Code gives us another:

```text
repo
+
agent loop
+
tools
+
skills
+
sub-agents
+
verification
```

([Anthropic][4])

And **NALA should eventually synthesize these around its own primitive: persistent, observable, recoverable runtime execution.**

That's why I want your notebook first.

**Don't design NALA yet. Observe the ecosystem. Then we derive NALA.** 🧠🔬⚙️

[1]: https://claude.com/product/cowork?utm_source=chatgpt.com "Claude Cowork | Claude by Anthropic"
[2]: https://openai.com/index/introducing-the-codex-app/?utm_source=chatgpt.com "Introducing the Codex app | OpenAI"
[3]: https://openai.com/codex/?utm_source=chatgpt.com "Codex in ChatGPT | AI Coding Agents for Software Engineering | OpenAI"
[4]: https://www.anthropic.com/webinars/claude-code-foundations?utm_source=chatgpt.com "Claude Code: Foundations | Webinars \ Anthropic"
