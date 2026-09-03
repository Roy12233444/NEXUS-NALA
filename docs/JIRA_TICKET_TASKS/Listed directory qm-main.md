Listed directory qm-main
Listed directory src
Listed directory skills-seed
Listed directory plugins
Listed directory sessions
Listed directory memory
Listed directory tasks
Listed directory runs
Listed directory tools
Listed directory skills
Viewed session-store.ts:1-60
Viewed README.md:1-80
Viewed memory-service.ts:1-60
Listed directory cron
Listed directory connectors
Viewed turn-stream.ts:1-60
Viewed scheduler.ts:1-60

Now I have a complete picture. Here's the full analysis, buddy:

---

### 🔍 What `qm-main` Is

It's a **production-grade YC-backed multiplayer agent harness** — think of it as the battle-tested blueprint NALA should grow into.

---

### 🎯 What We Should Add to NALA (Priority Order)

**🥇 Priority 1 — Session Store (Do This First)**

- `qm-main` has a proper `session-store.ts` with a **Lease system** — sessions are locked per-turn to prevent race conditions
- NALA right now has flat `active_sessions{}` dict in RAM — no persistence, lost on restart
- **What to add:** A simple `session_store.py` that saves chat history + session metadata to a JSON file on disk

**🥈 Priority 2 — Memory System (`memory/MEMORY.md`)**

- `qm-main` has a `MemoryService` with `recall()`, `capture()`, `query()` methods
- It stores facts as bullet points in a `memory/MEMORY.md` file — simple, persistent, brilliant
- NALA has **zero memory** — each conversation starts fresh
- **What to add:** A simple `memory_service.py` that stores and retrieves facts from a markdown file

**🥉 Priority 3 — Turn Stream (Real-time Streaming)**

- `qm-main` has `TurnStream` — tracks live streaming state (`begin`, `publish`, `alive`, `end`)
- NALA already does streaming but has no proper stream lifecycle management
- **What to add:** Clean up NALA's streaming to follow this pattern

**4️⃣ Priority 4 — Cron Scheduler**

- `qm-main` has a full `Scheduler` with `tick()`, `runNow()`, `start()`, `stop()`
- NALA's sidebar shows "Cron Schedules 2 Jobs" but it's **fake/hardcoded**
- **What to add:** A real `cron_scheduler.py` that runs background tasks on schedule

**5️⃣ Priority 5 — Skills System**

- `qm-main`'s `skills-seed/` has: `browse`, `github-gitlab`, `memory`, `google-drive`, `morning-digest` etc.
- These are plug-and-play skill packs NALA can execute
- **What to add:** A `skill_loader.py` that loads and runs skill definitions

---

### 🚀 My Recommendation — Start With

**Session Store → Memory Service** (in that order)

These two alone will make NALA feel 10x smarter because it will **remember past conversations** and **not lose state on restart**. Want me to start with that buddy? 🔥

Listed directory web-ui
Listed directory src
Viewed session-list.ts:1-80
Viewed shell.ts:1-80
Viewed memory.ts:1-60
Viewed skills.ts:1-60

Here's the full UI analysis buddy:

---

### 🎨 What's in `qm-main`'s UI (`plugins/web-ui/src/`)

It has **54 UI files** built with **Lit framework** (Web Components). Here's what each major one does:

---

### 🏗️ Layout & Shell

| File | What It Is |
|---|---|
| `shell.ts` (29KB) | **Main app shell** — sidebar, navigation, pane layout |
| `split.ts` (29KB) | **Split pane view** — two conversations side by side |
| `shell.css` (142KB!) | **All styles** — massive production CSS |

---

### 💬 Chat & Sessions

| File | What It Is |
|---|---|
| `sessions.ts` (41KB) | **Session list** — real list from backend, pinned, archived, active |
| `session-list.ts` (6KB) | **Session grouping logic** — groups by project/personal/channel |
| `chat.ts` (72KB!) | **Full chat view** — the biggest file, handles all message rendering |
| `composer.ts` (49KB) | **Message input** — file attachments, model selector, skill mentions |
| `streaming-markdown.ts` | **Live markdown rendering** while AI types |

---

### 🧠 Sidebar Panels (What NALA's sidebar fakes but qm does for real)

| File | What It Is |
|---|---|
| `memory.ts` | **Memory panel** — view/edit/search/delete AI memories |
| `skills.ts` | **Skills panel** — list, create, edit, publish skills |
| `crons.ts` (27KB) | **Cron panel** — real schedule management UI |
| `files.ts` | **Files panel** — browse sandbox files |
| `connectors.ts` (34KB) | **OAuth connectors** — Google, GitHub, Slack |
| `deploys.ts` (35KB) | **Web app deploys** panel |
| `contexts.ts` (44KB) | **Workspace contexts** panel |

---

### ⚡ What NALA Can Borrow from the UI

| Priority | Feature | Why |
|---|---|---|
| **🥇 1** | `session-list.ts` grouping logic | Groups sessions by project — NALA's sidebar needs this |
| **🥇 1** | `streaming-markdown.ts` | NALA renders raw text — qm streams markdown live |
| **🥈 2** | `memory.ts` UI panel | Show/edit NALA's memory in sidebar |
| **🥉 3** | `crons.ts` UI panel | Make NALA's fake cron panel real |
| **4️⃣** | `composer.ts` features | File attachments, model picker |

---

### 💡 Key Insight

qm uses **Lit (Web Components)** — NALA uses **React + TypeScript**. We can't copy code directly but we can **copy the design patterns and features** into NALA's React components. The biggest win is the **session grouping + streaming markdown** buddy! 🚀
