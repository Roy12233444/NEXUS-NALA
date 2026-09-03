New features to add so you can actually interact with NALA

Once Phases 1–3 land, these features make NALA usable as a daily assistant — ordered by value.

Tier A — Core interaction (build next)

1. Explicit mode toggle in UI
   • Chat | Auto | Agent/Work
   • Auto = classifier; Work = always TASK; Chat = never sandbox.
   • Gives you control when Auto is wrong.

2. “Run this?” confirm for borderline messages
   • e.g. code in a question → answer in chat + button Execute in sandbox.
   • Fixes mixed intent without over-eager execution.

3. Streaming replies
   • Token-by-token in the bubble. Biggest perceived quality jump after intent split.

4. Session continuity (true multi-turn chat)
   • Keep last N turns for chat context.
   • Today every submit_prompt is basically a new session — that kills conversation.

5. Stable final answer
   • One field: the model’s reply.
   • Pipeline status as a small badge/footer, not the main message.

6. Stop / cancel
   • Kill running TASK (loop + sandbox) from UI. Critical for long agent runs.

Tier B — Power-user coding interaction

1. Attach file / folder context (you already have attachment UI hooks)
   • “Explain this file”, “refactor selection”, with files in the prompt.

2. Diff / apply patch flow
   • Propose changes → show diff → Apply or Discard.
   • Safer than silent writes.

3. Terminal as opt-in tool, not always-on theater
   • Show ExecutionCell only when shell/file tools ran.
   • Button: Open terminal for this task.

4. Checkpoints only on TASK + resume
    • “Resume last agent run” from session list.
    • Chat should not litter sessions/.

5. Model / speed picker
    • Fast (1.5b) / Balanced (3b) / Deep (7b) for the user, not only auto.

6. Tool permission levels
    • Read-only / workspace write / full sandbox — so you trust longer runs.

Tier C — “Feels like a real product”

1. Slash commands
    • /chat, /task, /model, /clear, /resume, /explain, /run
    • Fast, predictable interaction without fighting the classifier.

2. Pinned system status
    • Ollama up/down, which model loaded, sandbox ready — one glance.

3. Conversation list + rename
    • Multiple threads (debug, feature X, random chat).

4. Developer drawer (hidden)
    • Raw step events, telemetry, LSN — for you; never in the main Thinking fold.

5. Feedback on wrong mode
    • “This should have been a task” / “This was just chat” → improves heuristics.

Tier D — Later / backlog-aligned (after NALA feels good)

• Multi-agent visible roles (planner/executor/judge) as clean labels
• Soak / long-run monitor UI
• Spore handoff / session handoff for long jobs
• Rich CoT export for tasks only

Those match your deeper backlog, but only after chat works.

───

Suggested product roadmap (simple)

Now     Fix monopath: intent → chat vs task
Next    Fast stream chat + no fake fallbacks + no thinking on hi
Then    Clean task thoughts + terminal only when real work
Then    Mode toggle, multi-turn memory, stop, slash commands
Then    Diff/apply, resume sessions, model picker, permissions
Later   Fancy agent civilization / advanced plans from backlog

───

My concrete recommendation for you as the user of NALA

If the goal is “I want to talk to NALA and also make it do real work”:

1. Must fix: chat vs task routing + light chat path + UI not always Thinking/terminal.
2. Must fix: faster small model + streaming + honest errors.
3. Must fix: final message = real answer, not pipeline boilerplate.
4. Best next features for interaction: mode toggle, multi-turn memory, stop button, slash commands, “Run in sandbox?”.
5. Ignore for interaction quality: ONNX intent, diagnostic port 3002, thought A/B, most of the industrial Phase 5 in the md file.

───

One-sentence strategy

Make NALA bimodal and honest first; then add controls (mode, run, stop, memory, slash) so you drive it — don’t pile features on a system that treats “hi” like a deployment.

When you want to implement, we can start with Phase 1 only (intent + handle_chat_message + UI gate) and keep the rest of the doc as a later checklist.
