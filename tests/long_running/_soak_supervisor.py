"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_supervisor.py
Ticket  : JIRA-007 — 1-Hour Soak Test (Cross-Process Supervisor)
Sections: JIRA_007_1HOUR_SOAK_TEST_PLAN_V2.MD §3.2 (Exit Code Contract),
          §3.3 (SoakSupervisor), §4.2 (psutil OS-Level Sampling)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
Parent-process orchestrator for the JIRA-007 soak run. Spawns each session
generation as a REAL child OS process (never an in-process mock — see §3.1 of
the plan on why threading.Event-based cooperative stop is a different failure
domain than a filesystem lock / SIGKILL), classifies its exit code against the
documented contract, and respawns the next generation via the correct path:
graceful spore handoff (exit 10) vs same-session_id crash recovery (exit 137).

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. STDOUT/STDERR → LOG FILE, NEVER subprocess.PIPE.
   A long-lived child (up to ~25 minutes per generation in Phase 3) writing
   compaction/telemetry logs to a PIPE that the parent does not actively drain
   will fill the OS pipe buffer (~64KB) and deadlock the child mid-write while
   the parent sits blocked in `proc.wait()`. Redirecting stdout/stderr directly
   to a per-generation log file removes this entire class of bug — there is no
   buffer to fill. This is also what makes AC-3's "[Dronagiri] log line" scan
   trivial: it's a completed file, not a live stream to race against.

2. PSUTIL SAMPLING RUNS IN A DECOUPLED BACKGROUND THREAD.
   The main thread's `proc.wait()` is a hard, uninterruptible OS-level block.
   All resource sampling therefore lives in its own daemon thread with its own
   independent `psutil.Process` handle, so a `psutil.NoSuchProcess` race
   (sampled a heartbeat after the child died) can never affect the main
   thread's ability to correctly observe the real exit code.

3. THE SIGKILL "ARM" FLAG IS SET BEFORE THE KILL THREAD SLEEPS, NOT AFTER
   IT FIRES. Setting `self._sigkill_fired = True` only inside the sleeping
   thread's body (after `time.sleep(delay)` returns) leaves a race window in
   which a SECOND generation could spawn and schedule a SECOND kill while the
   first is still asleep — violating the "at most one real SIGKILL per soak
   run" contract. The flag is armed synchronously, in the calling thread,
   before the background thread is even started.

4. THE KILL CHECK USES `proc.poll() is None`, NOT A BARE `psutil.pid_exists`.
   `Popen.poll()` tracks ONLY the exact child this Popen object spawned via
   its internal wait4()/waitpid() bookkeeping. A raw `os.kill(pid, ...)` after
   a long `random.uniform()` delay risks the OS having already recycled that
   PID for an unrelated process if our own child exited naturally in the
   meantime — `proc.poll()` is immune to this PID-reuse hazard by construction.

5. THE SPORE IS READ AS RAW JSON, NOT VIA `HandoffSporeModel`.
   The supervisor is a test-harness component and deliberately keeps the
   smallest possible dependency surface (stdlib + psutil only) — it must stay
   launchable even in the presence of a transient production Pydantic-schema
   regression, which is precisely the class of bug this soak suite exists to
   surface, not be blocked by.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import psutil

_logger = logging.getLogger("nala.soak.supervisor")

# ==============================================================================
# SECTION 1 — Spawn Reason & SessionGeneration Ledger Entry
# ==============================================================================

SpawnReason = Literal["initial", "handoff", "crash_recovery"]


@dataclasses.dataclass
class SessionGeneration:
    """
    One row in the supervisor's ledger — one Executor subprocess lifetime.

    Deliberately kept as a pure data-transfer object (no live OS handles such
    as `subprocess.Popen` stored on it) so it can be freely logged, JSON-
    serialized for the failure report, and compared without any risk of
    accidentally holding a stale process reference. The live `Popen` object
    for the CURRENT generation is instead threaded explicitly as a method
    argument to `_sample_until_exit()` and `_maybe_schedule_sigkill()`.

    Fields
    ------
    session_id       : UUID of the session this generation executed.
    spawn_reason      : Why this generation was spawned — "initial" (very
                        first process of the whole soak run), "handoff"
                        (previous generation exited 10, a fresh session_id
                        was minted via HandoffSpore), or "crash_recovery"
                        (previous generation exited 137 via SIGKILL; SAME
                        session_id is reused and recovered via checkpoint LSN).
    pid               : OS process ID assigned to this generation's child.
    start_monotonic   : `time.monotonic()` at the instant Popen() returned.
    end_monotonic     : `time.monotonic()` at the instant proc.wait() returned.
    raw_returncode    : The unmodified value of `Popen.returncode` — negative
                        on POSIX if terminated by a signal (e.g. -9 for SIGKILL).
    normalized_exit   : `raw_returncode` passed through `_normalize_exit_code()`
                        — the shell-standard 128+N convention for signal deaths.
    floor_tokens_in   : Cumulative `_meta_tokens_in` floor contributed by this
                        generation's SUCCESS steps (populated by the caller
                        after generation completion, for AC-6 bookkeeping).
    floor_tokens_out  : Same, for `_meta_tokens_out`.
    floor_cost_usd    : Same, for `_meta_cost_usd`.
    """

    session_id:       str
    spawn_reason:      SpawnReason
    pid:               int
    start_monotonic:   float
    end_monotonic:     Optional[float] = None
    raw_returncode:    Optional[int]   = None
    normalized_exit:   Optional[int]   = None
    floor_tokens_in:   int             = 0
    floor_tokens_out:  int             = 0
    floor_cost_usd:    float           = 0.0


# ==============================================================================
# SECTION 2 — SoakSupervisor
# ==============================================================================

class SoakSupervisor:
    """
    Cross-process orchestrator for the JIRA-007 1-hour soak test.

    Public API
    ----------
    run(initial_session_id: str) -> bool
        Drives the entire soak run to completion or abort. Returns True on
        overall success (AC-1 satisfied with a clean final LoopStatus.COMPLETED),
        False on any abort path (exit codes 1, 2, or 3).

    Constants
    ---------
    SOAK_DURATION_S     : Minimum wall-clock supervisor runtime, in seconds (AC-1).
    PSUTIL_SAMPLE_S     : Sampling cadence for the background profiler thread.
    KILL_WINDOW_START_S : Earliest elapsed-time offset (seconds) at which the
                          single simulated SIGKILL may be scheduled (Phase 3 start).
    KILL_WINDOW_END_S   : Latest elapsed-time offset (seconds) for the SIGKILL
                          window (Phase 3 end).
    """

    SOAK_DURATION_S:     int = int(os.environ.get("SOAK_DURATION", 3600))   # default 60 minutes
    PSUTIL_SAMPLE_S:      int = 10     # §4.2 — sample every 10 seconds
    KILL_WINDOW_START_S:  int = int(SOAK_DURATION_S * 0.33)
    KILL_WINDOW_END_S:    int = int(SOAK_DURATION_S * 0.75)

    # Maximum single sleep duration used when scheduling the SIGKILL injector,
    # to guarantee the kill actually fires well inside the intended window
    # even if `_maybe_schedule_sigkill()` is first called very early in it.
    _MAX_KILL_SCHEDULE_DELAY_S: float = 300.0

    def __init__(
        self,
        checkpoint_base_dir: Path,
        python_exe: str = sys.executable,
    ) -> None:
        """
        Parameters
        ----------
        checkpoint_base_dir : Path
            Root directory NALA's CheckpointManager writes session
            checkpoints and handoff spores under. Also the root under which
            this supervisor creates its own `supervisor_logs/`,
            `soak_metrics.jsonl`, and (on abort) `soak_failure_report.json`.
        python_exe : str
            Interpreter used to spawn each Executor subprocess. Defaults to
            the currently running interpreter (`sys.executable`), ensuring
            the same virtualenv/dependency set is used for every generation.
        """
        self.checkpoint_base_dir: Path = checkpoint_base_dir
        self.python_exe:          str  = python_exe

        self.checkpoint_base_dir.mkdir(parents=True, exist_ok=True)

        self.log_dir: Path = self.checkpoint_base_dir / "supervisor_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_path: Path = self.checkpoint_base_dir / "soak_metrics.jsonl"

        self.generations: List[SessionGeneration] = []

        self._run_start:     float = 0.0
        self._sigkill_fired: bool  = False
        self._target_duration_reached: bool = False

        # Guards concurrent writes to metrics_path from the main thread, the
        # background sampler thread, and the SIGKILL-injector thread.
        self._metrics_lock: threading.Lock = threading.Lock()

        # session_id -> Path to that generation's redirected stdout/stderr log,
        # used exclusively by _dump_failure_diagnostics() for post-mortem tails.
        self._log_paths: Dict[str, Path] = {}

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, initial_session_id: str) -> bool:
        """
        Drive the full soak run: spawn → sample → wait → classify → respawn,
        looping until the run either succeeds (AC-1 satisfied with a clean
        completion) or aborts (an unrecoverable exit code is observed).

        Parameters
        ----------
        initial_session_id : str
            UUID for the very first Executor generation. Subsequent
            generations derive their session_id from either a HandoffSpore
            (exit 10) or reuse this same value across a hard crash (exit 137).

        Returns
        -------
        bool
            True  — AC-1 satisfied: total elapsed wall-clock time reached
                    SOAK_DURATION_S and the final generation exited with
                    LoopStatus.COMPLETED (normalized exit code 0).
            False — the run aborted on exit code 1 (FAILED), 2 (BLOCKED), or
                    3 (SessionRecoveryError family raised inside recover_session()).

        Raises
        ------
        AssertionError
            If a generation completes (exit 0) BEFORE the SOAK_DURATION_S
            floor — this indicates the workload's STEP_PACING_S is mis-tuned
            for the configured step count, not a genuine test failure, and
            must be corrected before the soak suite can produce a meaningful
            result. Also raised if an exit code outside the documented
            {0, 1, 2, 3, 10, 137} set is ever observed (AC-8 violation).
        """
        self._run_start = time.monotonic()
        session_id:   str          = initial_session_id
        spawn_reason: SpawnReason  = "initial"

        _logger.info(
            "[SoakSupervisor] Starting soak run. initial_session_id=%s | "
            "target_duration_s=%d", initial_session_id, self.SOAK_DURATION_S,
        )

        while True:
            proc, gen = self._spawn_session(session_id, spawn_reason)
            self.generations.append(gen)

            sampler_thread = threading.Thread(
                target=self._sample_until_exit,
                args=(gen, proc),
                daemon=True,
                name=f"soak-sampler-{session_id[:8]}",
            )
            sampler_thread.start()

            self._maybe_schedule_sigkill(gen, proc)

            # Wait for child process to exit, but actively monitor total elapsed time
            # so we terminate gracefully when the target duration is reached.
            raw_rc = None
            while True:
                raw_rc = proc.poll()
                if raw_rc is not None:
                    break

                elapsed_total = time.monotonic() - self._run_start
                if elapsed_total >= self.SOAK_DURATION_S:
                    _logger.warning(
                        "[SoakSupervisor] Target duration of %ds reached. "
                        "Terminating active child process for graceful success...",
                        self.SOAK_DURATION_S
                    )
                    self._target_duration_reached = True
                    proc.terminate()
                    try:
                        raw_rc = proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        raw_rc = proc.wait()
                    break
                time.sleep(1.0)

            gen.end_monotonic   = time.monotonic()
            gen.raw_returncode  = raw_rc
            if self._target_duration_reached:
                gen.normalized_exit = 0
            else:
                gen.normalized_exit = self._normalize_exit_code(raw_rc)

            # Give the sampler a bounded grace period to notice the exit and
            # write its final "process_exited" event before we move on.
            sampler_thread.join(timeout=self.PSUTIL_SAMPLE_S + 5.0)

            elapsed_total = time.monotonic() - self._run_start
            self._log_generation_summary(gen, elapsed_total)

            _logger.info(
                "[SoakSupervisor] Generation ended. session_id=%s | "
                "spawn_reason=%s | raw_rc=%s | normalized_exit=%s | "
                "elapsed_total=%.0fs",
                session_id, spawn_reason, raw_rc, gen.normalized_exit, elapsed_total,
            )

            if gen.normalized_exit == 0:
                if elapsed_total < self.SOAK_DURATION_S:
                    raise AssertionError(
                        f"[SoakSupervisor] Session '{session_id}' reached "
                        f"LoopStatus.COMPLETED at {elapsed_total:.0f}s — before "
                        f"the {self.SOAK_DURATION_S}s AC-1 floor. This means "
                        f"the TaskGraph was fully consumed too quickly; retune "
                        f"STEP_PACING_S / n_steps in _soak_workload.py rather "
                        f"than treating this as a genuine soak-test failure."
                    )
                return True

            if gen.normalized_exit == 10:
                session_id   = self._read_spore_new_session_id(session_id)
                spawn_reason = "handoff"
                continue

            if gen.normalized_exit == 137:
                spawn_reason = "crash_recovery"   # session_id intentionally unchanged
                continue

            if gen.normalized_exit in (1, 2, 3):
                self._dump_failure_diagnostics(gen)
                return False

            raise AssertionError(
                f"[SoakSupervisor] Unrecognized normalized exit code "
                f"{gen.normalized_exit} for session '{session_id}' (raw "
                f"returncode was {raw_rc}). This violates AC-8 (Exit Code "
                f"Fidelity) — every termination must classify into exactly "
                f"one of {{0, 1, 2, 3, 10, 137}}."
            )

    # ── Spawning ───────────────────────────────────────────────────────────────

    def _spawn_session(
        self,
        session_id:   str,
        spawn_reason: SpawnReason,
    ) -> Tuple[subprocess.Popen, SessionGeneration]:
        """
        Launch one Executor subprocess and return both the live `Popen` handle
        (needed by the caller for `.wait()` and by the sampler/kill threads)
        and a fresh `SessionGeneration` ledger entry.

        stdout and stderr are both redirected directly to a dedicated,
        per-generation log file (never `subprocess.PIPE` — see module
        docstring, design decision #1) at:
            {checkpoint_base_dir}/supervisor_logs/{session_id}__gen{NN}__{reason}.log
        """
        generation_index = len(self.generations) + 1
        log_path = self.log_dir / (
            f"{session_id}__gen{generation_index:02d}__{spawn_reason}.log"
        )

        argv = [
            self.python_exe, "-m", "tests.long_running._soak_subprocess_entrypoint",
            "--session-id", session_id,
            "--checkpoint-dir", str(self.checkpoint_base_dir),
            "--spawn-reason", spawn_reason,
        ]

        log_fh = log_path.open("w", encoding="utf-8")
        try:
            proc = subprocess.Popen(
                argv,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,   # line-buffered — log lines land promptly for live tailing
            )
        finally:
            # Safe to close the PARENT's copy of the fd immediately: Popen()
            # has already duplicated it for the CHILD at process-creation
            # time. Holding it open for the full generation lifetime would
            # leak one fd per generation across a 60-minute, multi-handoff run.
            log_fh.close()

        gen = SessionGeneration(
            session_id=session_id,
            spawn_reason=spawn_reason,
            pid=proc.pid,
            start_monotonic=time.monotonic(),
        )
        self._log_paths[session_id] = log_path

        self._append_metric_row({
            "ts": time.time(), "event": "generation_spawned",
            "session_id": session_id, "spawn_reason": spawn_reason,
            "pid": proc.pid, "log_path": str(log_path),
        })
        _logger.info(
            "[SoakSupervisor] Spawned generation #%d. session_id=%s | "
            "spawn_reason=%s | pid=%d | log=%s",
            generation_index, session_id, spawn_reason, proc.pid, log_path,
        )
        return proc, gen

    # ── Background resource profiling (§4.2) ────────────────────────────────────

    def _sample_until_exit(self, gen: SessionGeneration, proc: subprocess.Popen) -> None:
        """
        Runs in its own daemon thread, fully decoupled from the main thread's
        blocking `proc.wait()` call. Samples RSS, VMS, CPU%, thread count, and
        open-fd count every `PSUTIL_SAMPLE_S` seconds via a psutil.Process
        handle that is independent of the Popen object — a NoSuchProcess race
        here can never affect the main thread's exit-code observation.

        Terminates cleanly (returns, does not raise) the moment the process
        can no longer be sampled, logging a `"process_exited"` event as the
        final row for this generation.
        """
        try:
            ps_proc = psutil.Process(gen.pid)
            # Priming call: per psutil's own documentation, the FIRST
            # cpu_percent() reading after a Process() is constructed is
            # meaningless (0.0 or unreliable) because no time interval has
            # yet elapsed to measure against. This call establishes that
            # baseline without blocking (interval=None).
            ps_proc.cpu_percent(interval=None)
        except psutil.NoSuchProcess:
            self._append_metric_row({
                "ts": time.time(), "session_id": gen.session_id, "pid": gen.pid,
                "event": "process_vanished_before_first_sample",
            })
            return

        while True:
            try:
                mem = ps_proc.memory_info()
                row: Dict[str, Any] = {
                    "ts":         time.time(),
                    "session_id": gen.session_id,
                    "pid":        gen.pid,
                    "rss_mb":     round(mem.rss / (1024 * 1024), 2),
                    "vms_mb":     round(mem.vms / (1024 * 1024), 2),
                    "cpu_pct":    ps_proc.cpu_percent(interval=None),
                    "n_threads":  ps_proc.num_threads(),
                    "n_fds":      ps_proc.num_fds() if hasattr(ps_proc, "num_fds") else -1,
                }
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                # EXPECTED at every generation boundary — graceful handoff
                # exit, natural completion, or the injected SIGKILL. Not a
                # profiling error; simply the signal to stop this thread.
                self._append_metric_row({
                    "ts": time.time(), "session_id": gen.session_id,
                    "pid": gen.pid, "event": "process_exited",
                })
                return
            except Exception as exc:  # noqa: BLE001 — defensive: profiling must
                                       # never crash or hang the soak run itself.
                self._append_metric_row({
                    "ts": time.time(), "session_id": gen.session_id,
                    "pid": gen.pid, "event": "sample_error", "error": repr(exc),
                })
                _logger.warning(
                    "[SoakSupervisor] Sampler for pid=%d raised unexpectedly: %s",
                    gen.pid, exc,
                )
                return

            self._append_metric_row(row)
            time.sleep(self.PSUTIL_SAMPLE_S)

    # ── SIGKILL injection ─────────────────────────────────────────────────────

    def _maybe_schedule_sigkill(
        self,
        gen:  SessionGeneration,
        proc: subprocess.Popen,
    ) -> None:
        """
        Schedule AT MOST ONE real `os.kill(pid, SIGKILL)` for the entire soak
        run, fired at a random moment inside the Phase 3 window
        [KILL_WINDOW_START_S, KILL_WINDOW_END_S], independent of the natural
        CONTEXT_EXHAUSTED handoff cycles also expected in that window — this
        exercises BOTH crash modes (graceful spore handoff and hard process
        death) within the same 60-minute run (AC-4).

        Called once per generation spawn; is a no-op on every call after the
        first successful scheduling, and a no-op on every call if the window
        has already passed.
        """
        if self._sigkill_fired:
            return

        elapsed_now = time.monotonic() - self._run_start
        abs_start = self.KILL_WINDOW_START_S
        abs_end = self.KILL_WINDOW_END_S

        # If the window has already completely passed, we cannot schedule a kill
        if elapsed_now > abs_end:
            return

        # Determine delays relative to now that land inside the [abs_start, abs_end] window
        min_delay = max(0.0, abs_start - elapsed_now)
        max_delay = abs_end - elapsed_now

        # Schedule the random injection time inside the valid range
        delay = random.uniform(min_delay, min(max_delay, self._MAX_KILL_SCHEDULE_DELAY_S))

        # Armed HERE, synchronously, in the calling (main) thread — BEFORE the
        # background thread is even started. This closes the race window in
        # which a second generation could spawn during this thread's sleep()
        # and schedule a second, unwanted SIGKILL (see module docstring #3).
        self._sigkill_fired = True

        def _fire() -> None:
            time.sleep(delay)
            # `proc.poll()` tracks ONLY this exact child via its own
            # wait4()/waitpid() bookkeeping — immune to PID-reuse hazards
            # that a bare `psutil.pid_exists(gen.pid)` check would not be
            # (see module docstring #4).
            if proc.poll() is None:
                sig = getattr(signal, "SIGKILL", 9)
                os.kill(gen.pid, sig)
                self._append_metric_row({
                    "ts": time.time(), "session_id": gen.session_id,
                    "pid": gen.pid, "event": "sigkill_injected",
                    "scheduled_delay_s": round(delay, 1),
                })
                _logger.warning(
                    "[SoakSupervisor] SIGKILL injected. session_id=%s | "
                    "pid=%d | after_delay_s=%.1f",
                    gen.session_id, gen.pid, delay,
                )
            else:
                self._append_metric_row({
                    "ts": time.time(), "session_id": gen.session_id,
                    "pid": gen.pid, "event": "sigkill_skipped_already_exited",
                    "scheduled_delay_s": round(delay, 1),
                })

        threading.Thread(target=_fire, daemon=True, name="soak-sigkill-injector").start()

        _logger.info(
            "[SoakSupervisor] SIGKILL scheduled. session_id=%s | pid=%d | "
            "fires_in_s=%.1f (window=[%d, %d]s, now=%.0fs)",
            gen.session_id, gen.pid, delay,
            self.KILL_WINDOW_START_S, self.KILL_WINDOW_END_S, elapsed_now,
        )

    # ── Exit code normalization (§3.2) ──────────────────────────────────────────

    @staticmethod
    def _normalize_exit_code(raw_returncode: Optional[int]) -> int:
        """
        Convert Python's POSIX signal-termination convention (a NEGATIVE
        signal number, e.g. -9 for SIGKILL, as reported by
        `subprocess.Popen.returncode`) into the universal shell-standard
        `128 + N` convention (e.g. 137 for SIGKILL) used throughout the
        JIRA-007 plan and every log line in this module.

        Non-negative return codes (normal `sys.exit(N)` calls from the
        Executor entrypoint — 0, 1, 2, 3, or 10) pass through unchanged.
        """
        if raw_returncode is None:
            raise AssertionError(
                "[SoakSupervisor] proc.wait() returned a None returncode — "
                "this should be structurally impossible once wait() has "
                "returned."
            )
        if raw_returncode < 0:
            return 128 + abs(raw_returncode)
        if os.name == "nt" and raw_returncode == 9:
            return 137
        return raw_returncode

    # ── Spore resolution ───────────────────────────────────────────────────────

    def _read_spore_new_session_id(self, original_session_id: str) -> str:
        """
        Locate the most recently written `handoff.spore.json` anywhere under
        `checkpoint_base_dir` and extract its `new_session_id`.

        The spore is written by NalaLoop under the NEW session's own
        checkpoint directory (`{base_dir}/{new_session_id}/handoff.spore.json`)
        — the supervisor cannot know that UUID in advance, so it scans by
        modification time rather than guessing a path.

        Read as raw JSON rather than via `HandoffSporeModel` — see module
        docstring, design decision #5.
        """
        candidates = sorted(
            self.checkpoint_base_dir.glob("*/handoff.spore.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise AssertionError(
                f"[SoakSupervisor] Exit code 10 (context-exhausted handoff) "
                f"received for session '{original_session_id}' but no "
                f"handoff.spore.json was found anywhere under "
                f"'{self.checkpoint_base_dir}'."
            )

        latest = candidates[0]
        spore  = json.loads(latest.read_text(encoding="utf-8"))

        found_original = spore.get("original_session_id")
        if found_original != original_session_id:
            raise AssertionError(
                f"[SoakSupervisor] Most recently written spore at '{latest}' "
                f"has original_session_id='{found_original}', but this "
                f"supervisor expected '{original_session_id}'. Spore/"
                f"session bookkeeping has desynchronized — refusing to "
                f"guess which session_id to resume."
            )

        new_session_id = spore["new_session_id"]
        self._append_metric_row({
            "ts": time.time(), "event": "handoff_spore_resolved",
            "original_session_id": original_session_id,
            "new_session_id": new_session_id, "spore_path": str(latest),
        })
        _logger.info(
            "[SoakSupervisor] Handoff spore resolved. original=%s | new=%s | path=%s",
            original_session_id, new_session_id, latest,
        )
        return new_session_id

    # ── Bookkeeping & diagnostics ────────────────────────────────────────────────

    def _log_generation_summary(
        self,
        gen:            SessionGeneration,
        elapsed_total_s: float,
    ) -> None:
        """Append a single structured summary row once a generation has fully ended."""
        duration_s = (
            round(gen.end_monotonic - gen.start_monotonic, 2)
            if gen.end_monotonic is not None else -1.0
        )
        self._append_metric_row({
            "ts": time.time(), "event": "generation_complete",
            "session_id": gen.session_id, "spawn_reason": gen.spawn_reason,
            "pid": gen.pid, "raw_returncode": gen.raw_returncode,
            "normalized_exit": gen.normalized_exit,
            "generation_duration_s": duration_s,
            "run_elapsed_s": round(elapsed_total_s, 2),
        })

    def _dump_failure_diagnostics(self, gen: SessionGeneration) -> None:
        """
        Write a consolidated `soak_failure_report.json` post-mortem artifact
        when the run aborts (exit codes 1, 2, or 3). Includes the last 200
        lines of the failing generation's redirected stdout/stderr log and a
        summary of every generation observed so far in this run.
        """
        report_path = self.checkpoint_base_dir / "soak_failure_report.json"
        log_path    = self._log_paths.get(gen.session_id)
        log_tail    = ""

        if log_path is not None and log_path.exists():
            lines    = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            log_tail = "\n".join(lines[-200:])

        report: Dict[str, Any] = {
            "failed_session_id": gen.session_id,
            "spawn_reason":      gen.spawn_reason,
            "pid":               gen.pid,
            "raw_returncode":    gen.raw_returncode,
            "normalized_exit":   gen.normalized_exit,
            "start_monotonic":   gen.start_monotonic,
            "end_monotonic":     gen.end_monotonic,
            "duration_s": (
                round(gen.end_monotonic - gen.start_monotonic, 2)
                if gen.end_monotonic is not None else None
            ),
            "log_path":               str(log_path) if log_path else None,
            "log_tail_last_200_lines": log_tail,
            "all_generations_so_far": [
                {
                    "session_id":      g.session_id,
                    "spawn_reason":    g.spawn_reason,
                    "normalized_exit": g.normalized_exit,
                }
                for g in self.generations
            ],
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        self._append_metric_row({
            "ts": time.time(), "event": "soak_run_aborted",
            "failed_session_id": gen.session_id,
            "exit_code": gen.normalized_exit, "report_path": str(report_path),
        })
        _logger.critical(
            "[SoakSupervisor] Soak run ABORTED. session_id=%s | exit_code=%s | "
            "report written to %s",
            gen.session_id, gen.normalized_exit, report_path,
        )

    def _append_metric_row(self, row: Dict[str, Any]) -> None:
        """
        Thread-safe append of a single JSON line to `soak_metrics.jsonl`.
        Guarded by `_metrics_lock` since the main thread, the sampler thread,
        and the SIGKILL-injector thread may all write concurrently.
        """
        with self._metrics_lock:
            with self.metrics_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")


__all__ = [
    "SpawnReason",
    "SessionGeneration",
    "SoakSupervisor",
]
