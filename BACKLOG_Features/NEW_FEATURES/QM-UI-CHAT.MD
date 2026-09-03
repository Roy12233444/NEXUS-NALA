Listed directory src

Ah! Look at the files in the directory!
We can map the main UI views/panels to the sidebar browse navigation items we created:

1. **Chats Panel (`sessions.ts`, `session-list.ts`)**: Manages the session list, including pinned and archived chats, and groups them by project scope.
2. **Projects/Contexts Panel (`contexts.ts`)**: Groups contexts and rooms (teams/personal scopes).
3. **Files Explorer Panel (`files.ts`, `file-list.ts`)**: The sandbox file manager and explorer.
4. **Crons Panel (`crons.ts`, `cron-format.ts`)**: Manages background scheduled tasks and jobs.
5. **Keychain Panel (`keychain-state.ts`, `connectors.ts`)**: Handles credentials, API keys, and OAuth connectors (Gmail, GitHub, Google, Dropbox, Linear, etc.).
6. **Deploys/Apps Panel (`deploys.ts`, `deploy-view.ts`)**: Displays and controls deployed web apps and sandbox containers.
7. **Memory Notebook Panel (`memory.ts`)**: The memory panel that lets you search, edit, add, or delete agent memories (which we just adapted to NALA!).
8. **Skills Registry Panel (`skills.ts`, `skill-registry.ts`)**: Manages NALA's installed system tools and skills.

---

And let's look at the **Split Pane & Chat Layout** components:

1. **Split Pane Coordinator (`split.ts`, `split-layout.ts`)**: Handles the split screen system. It allows dividing the screen into multiple concurrent panes side-by-side or stacked, resizing them, full-screening a pane, and closing panes.
2. **The Chat Shell (`chat.ts`, `composer.ts`)**:
   - **Message stream**: Displays markdown content, generated code, LaTeX math formulas (`lazy-katex.ts`), and media/images.
   - **Interactive Tool Execution Trace**: Collapsible tree structure showing tool executions in real-time (e.g. `7 tool calls >` containing sub-logs).
   - **Dynamic Composer**: The text area for "Ask anything" or "Steer the running task...", which supports drag-and-drop file upload, file attachments, model selectors, and cancel/stop controls.
   - **Active Task Progress indicator**: Renders progress messages showing what the agent is currently doing (e.g., `Reading file for 2s n.txt`).

This is a beautiful, detailed mapping that will give the user exactly the information they want! Let's write the response.Based on the files in the `web-ui` source directory and the screenshot you shared, here is an in-depth analysis of the main UI sections and components in **qm-main**, buddy:

---

### 1. 🗂️ The Split Pane Coordinator (`split.ts`, `split-layout.ts`)

As shown in your screenshot, the workspace is a **multitasking grid** that uses a library called `dockview` under the hood:
- **Side-by-Side (Split) View**: Lets you open multiple session panes concurrently (e.g., running code on the left while monitoring YC batch stats on the right).
- **Pane Control Bar (Top Right of each pane)**:
  - `+` : Creates a new blank split pane.
  - **Expand/Contract Arrows** : Swaps a pane between fullscreen mode and grid mode.
  - `X` : Closes the active pane.

---

### 2. 💬 The Chat Shell / Composer (`chat.ts`, `composer.ts`)

This is the interactive workspace panel shown inside each split pane:
- **Message Stream**:
  - Renders markdown formatting, tables, inline images (like the Möbius strip image on the left), and mathematical equations (`lazy-katex.ts`).
  - **Tool Traces (`7 tool calls >`)**: A collapsible timeline element (`timeline.ts`) that expands to show exactly what tools the agent called, what parameters it passed, and the terminal/API output.
- **Steerable Composer (Bottom Input Bar)**:
  - Displays `"Ask anything"` when idle, and changes to `"Steer the running task..."` when the agent is executing an autonomous loop.
  - Includes attachments (`IconPaperclip`), model parameters/configs, and a Stop/Cancel button (`IconSquare` / `IconSend`).
- **Active Status Indicator (`Reading file for 2s n.txt`)**:
  - A real-time running log at the bottom showing the user exactly what file or process the agent is currently reading or running.

---

### 3. 📂 Panel Views (Corresponding to the Sidebar Navigation)

Each of the 8 sidebar items opens a corresponding panel view in the main pane:

1. **Chats Panel (`sessions.ts`, `session-list.ts`)**: Renders the grouped sessions explorer.
2. **Projects Panel (`contexts.ts`)**: Allows creating and switching between team rooms, personal spaces, and collaborative workspace contexts.
3. **Files Panel (`files.ts`, `file-list.ts`)**: A sandbox file explorer that lets you upload, download, search, and delete files inside your secure coding environment.
4. **Crons Panel (`crons.ts`, `cron-format.ts`)**: Displays background tasks that run on a schedule (like cron jobs).
5. **Keychain Panel (`connectors.ts`)**: Handles integrations and credentials (like linking Gmail, GitHub, Slack, etc.).
6. **Apps Panel (`deploys.ts`, `deploy-view.ts`)**: Manages sandboxed web apps deployed by the agent.
7. **Memory Panel (`memory.ts`)**: The visual index of facts the agent has extracted and remembered (which we just built!).
8. **Skills Panel (`skills.ts`, `skill-registry.ts`)**: A registry showing all the active capabilities, custom tools, and scripts the agent knows how to use.
