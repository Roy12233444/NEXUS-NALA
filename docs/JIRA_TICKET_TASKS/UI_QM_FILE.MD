Listed directory src
Listed directory components
Listed directory features
Listed directory chat
Listed directory left
Listed directory right
Viewed App.tsx:1-62

Here are the key UI sections we should port from the `qm-main` web-ui into NALA, buddy:

---

### 1. The Memory Panel (`memory.ts` Pattern)

* **What it does in `qm-main`:** Shows a list of facts the agent has extracted and saved over time. The user can search, edit, add, or delete these memories directly in a clean UI panel.
* **Why NALA needs it:** Right now, NALA's memory is invisible to you. Adding this panel lets you see exactly what NALA remembers and correct any facts in real-time.

---

### 2. The Skills Registry Panel (`skills.ts` Pattern)

* **What it does in `qm-main`:** Displays all active tools/skills the agent has (e.g., browse, github, linear). The user can click on any skill to read its code, edit it, or write a new custom skill.
* **Why NALA needs it:** Currently, NALA's "Skills" section in the sidebar is just a static label. A real skills panel will let you see NALA's actual capabilities and eventually create your own custom workflows.

---

### 3. The Cron Schedules Panel (`crons.ts` Pattern)

* **What it does in `qm-main`:** Allows the user to schedule background tasks (like checking emails, monitoring a website, or generating daily digests), view logs of past runs, and run them manually.
* **Why NALA needs it:** NALA has a hardcoded "Cron Schedules - 2 Jobs" label in the sidebar. Porting this UI will make NALA capable of executing scheduled background tasks that you can monitor.

---

### 4. The Sandbox Files Panel (`files.ts` Pattern)

* **What it does in `qm-main`:** A mini file-explorer that shows the outputs, logs, and code files generated inside the agent's execution sandbox.
* **Why NALA needs it:** When NALA runs a script or saves a file, you currently have to look at your VS Code/explorer to see it. This file panel will let you see and download NALA's outputs directly from the UI.

---

### 5. Split Pane Layout (`split.ts` Pattern)

* **What it does in `qm-main`:** Lets the user split the screen to chat with NALA in one pane while viewing code, files, or logs in the other pane.
* **Why NALA needs it:** It gives NALA a professional, IDE-like multitasking experience instead of a single chat layout.

---

### 🚀 Recommendation for Next UI Step

We should start with the **Memory Panel** first. It connects beautifully with our plan to add the `Memory Service` to the backend, giving NALA a complete, visible brain!

What do you think, buddy? Which one do you want to target first when you have your limits back? 📈
