Good instinct buddy. Here's what would make this genuinely more powerful — not just bigger:

---

## 🔥 5 Additions Worth Making

**1. Live Heartbeat File — Monitor From Your Phone**
Right now the test runs blind for 60 minutes with just a log file. I'll write a `soak_status.json` updated every 30s — elapsed time, current phase, current generation, RSS, context status, compactions so far. Combined with your Tailscale setup from earlier, you can `cat` this from your phone mid-run and actually know what's happening without SSH-ing in and tailing raw logs.

**2. Multi-Failure Chaos Injection — Not Just SIGKILL**
Currently the plan only tests ONE crash type. I'll add **checkpoint corruption injection** — deliberately flip a byte in a real checkpoint file mid-run to force the SHA-256 rollback chain to actually fire for real (not just in JIRA-005's unit tests). This tests the ACTUAL failure mode most likely in a 1-month run: disk corruption, not just process death.

**3. Configurable Duration for Fast Iteration**
A `SOAK_DURATION_S` env var override. So you can run a **5-minute smoke test** first to catch obvious bugs, then commit to the full 60-minute run only once the quick version passes. Nobody should have to wait an hour to discover a typo.

**4. Regression History Tracking — Catches Slow Decay**
Since your real goal is 1-month continuous operation, a single pass/fail isn't enough. I'll save each run's final metrics (peak RSS, compaction count, total cost) to `soak_history.jsonl`, and compare THIS run against the median of your last 5 runs. If RSS is *technically* under the 10% threshold but has been creeping up run after run — that's the early warning sign of a slow leak that a one-shot test would miss entirely.

**5. Auto-Bundled Failure Report**
If it fails at 2am while you're asleep, instead of you digging through 4 different log files in the morning, everything zips into one `soak_failure_bundle_<timestamp>.zip` — failure report, last 3 checkpoints, log tail, leak reports. Ready to hand straight to me for diagnosis.

---

## What I'd Skip (Not Worth It)

Webhook/Telegram notifications and multi-session parallel stress testing — both genuinely useful but belong to SANKET Protocol and PRERAK Engine in your BACKLOG, not bolted onto JIRA-007 as an afterthought. Keeping scope discipline here.

---

Want all 5, or should I trim it down? Your call buddy 🔥
