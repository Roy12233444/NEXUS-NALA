"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_subprocess_entrypoint.py
Ticket  : JIRA-007 — 1-Hour Soak Test (Executor Subprocess Entrypoint)
Sections: JIRA_007_1HOUR_SOAK_TEST_PLAN_V2.MD §3.2 (Exit Code Contract),
          §4.1 (tracemalloc Heap Profiling), §8 (Implementation Task List),
          §9 (Verification Plan)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
The ONLY place in the entire soak suite that translates a NalaLoop
``LoopStatus`` (or a recovery-phase exception) into a process exit code
(§3.2). Launched fresh by ``SoakSupervisor._spawn_session()`` as
``python -m tests.long_running._soak_subprocess_entrypoint ...`` for every
generation — "initial" (fresh TaskGraph), "handoff" (graceful spore
recovery, new session_id already resolved by the supervisor), or
"crash_recovery" (hard SIGKILL, same session_id, checkpoint-LSN recovery).

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. TWO-PHASE COMPACTOR BINDING (chicken-and-egg resolution).
   ``DronagiriCompactor.checkpoint_fn`` must be ``Callable[[str], Path]`` —
   in production this is always ``NalaLoop._save_checkpoint``, which wraps
   ``CheckpointManager.write_checkpoint()`` with retry logic AND already
   holds bound references to the correct ``session``/``cm`` pair. But
   ``_save_checkpoint`` does not exist until a ``NalaLoop`` instance exists,
   and ``NalaLoop.__init__`` itself accepts ``compactor`` as a constructor
   argument — an unbreakable circular dependency if attempted in one step,
   in BOTH the "initial" path (we control construction directly) and, more
   subtly, the recovery path (``recover_session()`` builds and returns the
   ``NalaLoop`` internally, so the caller never gets a chance to construct a
   compactor bound to it beforehand). This entrypoint resolves it
   identically in both paths: construct the loop (or call
   ``recover_session()``) with ``compactor=None``, THEN construct the
   ``DronagiriCompactor`` using the now-existing ``loop._save_checkpoint``
   bound method, THEN assign ``loop.compactor = compactor`` post-hoc via
   ``_bind_context_engine()``. This reuses NalaLoop's production retry logic
   instead of duplicating checkpoint-retry semantics inside test code.

2. TRACEMALLOC BASELINE IS CAPTURED AFTER STEP 10, NOT AT PROCESS START.
   A snapshot taken at t=0 would forever show "growth" against every
   subsequent snapshot purely from one-time interpreter/import/module-init
   allocations (NalaLoop, Pydantic core, tiktoken tables, etc.), producing a
   permanent false-positive leak signal. Waiting for the 10th successful
   step lets that warm-up allocation settle before establishing the
   comparison floor.

3. LEAK CHECKS ARE GATED ON WALL-CLOCK TIME, NOT STEP COUNT.
   ``on_step_success`` fires once per step regardless of how long that step
   took (2-4s baseline pacing in Phases 1/2/4, but real recovery/backoff
   overhead can extend individual steps). Gating on
   ``time.monotonic() - last_check_ts >= LEAK_CHECK_INTERVAL_S`` guarantees a
   genuinely time-uniform ~60s profiling cadence across all four workload
   phases, rather than a step-count cadence that would drift wildly.

4. ``sys.stdout.flush()`` / ``sys.stderr.flush()`` BEFORE EVERY ``sys.exit()``.
   The supervisor redirects this process's stdout/stderr directly to a log
   file opened in line-buffered mode. Line buffering flushes on ``\\n``, but
   the FINAL log line written immediately before a ``sys.exit(N)`` is not
   guaranteed to have completed its flush before the interpreter tears down
   file descriptors during shutdown — an explicit flush removes any
   ambiguity and guarantees the supervisor's post-mortem log tail
   (``_dump_failure_diagnostics``) never misses the final line, which is
   usually the single most diagnostically important one.

5. ``heap_leaks.jsonl`` PATH IS DERIVED FROM ``cm.base_dir``, NEVER FROM
   ``session.metadata``. The leak-report path only needs ``base_dir`` (known
   at process start from ``--checkpoint-dir``) and ``session.session_id``
   (known inside every hook callback) — both already available without
   threading extra state through ``SessionState.metadata``, which is
   reserved for genuine caller-supplied session context, not internal
   test-harness bookkeeping.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.harness.checkpoint import CheckpointManager
from core.harness.context_tracker import ContextTracker, DronagiriCompactor
from core.harness.nala_loop import LoopHooks, LoopStatus, NalaLoop, StepResult
from core.harness.recovery import SessionRecoveryError, recover_session
from core.harness.session_contract import SessionState, TaskStep

from tests.long_running._soak_workload import (
    SOAK_TRACKER_CONFIG,
    build_soak_task_graph,
    mock_step_executor,
)

_logger = logging.getLogger("nala.soak.entrypoint")

# ── Module constants ─────────────────────────────────────────────────────────

SOAK_OBJECTIVE:          str   = "NALA JIRA-007 Sovereign 1-Hour Soak Test"
LEAK_CHECK_INTERVAL_S:   float = 60.0   # §4.1 — check every 60 wall-clock seconds
LEAK_CHECK_WARMUP_STEPS: int   = 10     # §4.1 — baseline captured after step 10


# ==============================================================================
# SECTION 1 — tracemalloc Heap Profiling (§4.1)
# ==============================================================================

def start_heap_profiling() -> None:
    """
    Enable tracemalloc at the very start of the entrypoint, before any NALA
    module is imported/constructed, so the eventual baseline snapshot (taken
    after step 10) diffs against everything the interpreter has allocated up
    to that point — not just what was allocated after some arbitrary later
    point in the script.

    25 stack frames is enough to pinpoint the allocating call site inside
    ``DronagiriCompactor`` / ``ContextTracker`` / ``TaskGraph`` internals
    without the excessive tracing overhead full-depth capture would add
    across 1,200 steps.
    """
    tracemalloc.start(25)


def take_baseline_snapshot() -> "tracemalloc.Snapshot":
    """
    Capture the comparison baseline. Must be called exactly once, after
    ``LEAK_CHECK_WARMUP_STEPS`` successful steps have completed — see module
    docstring, design decision #2.
    """
    return tracemalloc.take_snapshot()


def check_for_leaks(
    baseline:         "tracemalloc.Snapshot",
    leak_report_path: Path,
    step_index:       int,
) -> None:
    """
    Diff the current Python heap against ``baseline`` and append one JSON
    line to ``leak_report_path`` describing the top 5 growing allocation
    sites plus the current/peak traced memory in MB.

    This is the PYTHON-HEAP layer of the soak suite's dual-layer memory
    profiling design — it catches leaks in pure-Python objects (e.g. an
    ever-growing list retained somewhere in ``DronagiriCompactor``'s state)
    that the supervisor's OS-level psutil RSS sampling cannot attribute to a
    specific call site.

    Parameters
    ----------
    baseline          : Snapshot returned by ``take_baseline_snapshot()``.
    leak_report_path  : Path to ``heap_leaks.jsonl`` for this generation.
                        Parent directory is created if it does not exist.
    step_index        : Success count at which this check fired, for
                        correlating leak growth against the workload phase
                        (§7 of the plan).
    """
    current = tracemalloc.take_snapshot()
    top_stats = current.compare_to(baseline, "lineno")
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()

    row: Dict[str, Any] = {
        "ts":          time.time(),
        "step_index":  step_index,
        "current_mb":  round(current_bytes / (1024 * 1024), 3),
        "peak_mb":     round(peak_bytes / (1024 * 1024), 3),
        "top_5_diffs": [str(stat) for stat in top_stats[:5]],
    }

    leak_report_path.parent.mkdir(parents=True, exist_ok=True)
    with leak_report_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")

    _logger.info(
        "[HeapProfile] step=%d | current=%.2fMB | peak=%.2fMB | top_diff=%s",
        step_index, row["current_mb"], row["peak_mb"],
        row["top_5_diffs"][0] if row["top_5_diffs"] else "none",
    )


# ==============================================================================
# SECTION 2 — Mock LLM Summarizer for DronagiriCompactor Stage 2
# ==============================================================================

def _mock_soak_summarizer_fn(system_prompt: str, user_prompt: str) -> str:
    """
    Stand-in for a real LLM call inside the soak test. ``DronagiriCompactor``'s
    Stage 2 (``_stage2_llm_summarize``) invokes this exactly as it would a
    real Claude/GPT call, via ``summarizer_fn(system_prompt, user_prompt)``.

    Parses the embedded "Input TaskStep JSON array:" payload directly out of
    ``user_prompt`` (built by ``DronagiriCompactor._build_user_prompt()``)
    and deterministically produces one ``crystallized_steps`` entry per
    ``step_id`` found — exercising the FULL Stage 2 code path (JSON parse,
    step_id matching against ``summarizable``, with ``n_preserve_tail``
    exclusion already applied upstream by the compactor) without requiring
    a real API key or network access during the soak run.

    Parameters
    ----------
    system_prompt : Unused by this mock — accepted only to match the real
                    ``Callable[[str, str], str]`` contract exactly.
    user_prompt   : Contains the embedded TaskStep JSON array to crystallize.

    Returns
    -------
    str
        A JSON string conforming to ``{"crystallized_steps": [...]}``.
    """
    marker = "Input TaskStep JSON array:\n"
    start  = user_prompt.find(marker)
    if start == -1:
        _logger.warning("[MockSummarizer] Marker not found in user_prompt.")
        return json.dumps({"crystallized_steps": []})

    payload_start = start + len(marker)
    end_marker    = "\n</immediate_request>"
    end           = user_prompt.find(end_marker, payload_start)
    raw_json      = user_prompt[payload_start: end if end != -1 else None]

    try:
        steps: List[Dict[str, Any]] = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        _logger.warning("[MockSummarizer] Failed to parse embedded TaskStep array: %s", exc)
        return json.dumps({"crystallized_steps": []})

    crystallized = [
        {
            "step_id":     s.get("step_id", "unknown"),
            "status":      "SUCCESS",
            "summary":     f"Soak-mock crystallization of {s.get('step_id', 'unknown')}.",
            "key_outputs": {},
            "errors":      None,
        }
        for s in steps
        if isinstance(s, dict)
    ]
    return json.dumps({"crystallized_steps": crystallized})


# ==============================================================================
# SECTION 3 — CLI Parsing
# ==============================================================================

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse the arguments passed by the supervisor: --session-id, --checkpoint-dir,
    --spawn-reason, and the advanced run-start-ts / generation-index flags.
    """
    parser = argparse.ArgumentParser(
        prog="_soak_subprocess_entrypoint",
        description="NALA JIRA-007 soak test — Executor subprocess entrypoint.",
    )
    parser.add_argument(
        "--session-id", required=True, type=str,
        help="UUID of the session this generation will run or recover.",
    )
    parser.add_argument(
        "--checkpoint-dir", required=True, type=str,
        help="Root checkpoint directory (CheckpointManager.base_dir).",
    )
    parser.add_argument(
        "--spawn-reason", required=True, type=str,
        choices=["initial", "handoff", "crash_recovery"],
        help="Why this generation is being spawned — determines the bootstrap path.",
    )
    parser.add_argument(
        "--run-start-ts", required=False, type=float, default=0.0,
        help="Epoch timestamp of when the entire soak test run started.",
    )
    parser.add_argument(
        "--generation-index", required=False, type=int, default=1,
        help="1-based index of the current generation.",
    )
    return parser.parse_args(argv)


# ==============================================================================
# SECTION 4 — Lifecycle Hooks (leak-check wiring)
# ==============================================================================

def _build_hooks(
    cm: CheckpointManager,
    run_start_ts: float = 0.0,
    generation_index: int = 1,
    spawn_reason: str = "initial",
) -> LoopHooks:
    """
    Build the ``LoopHooks`` used across BOTH bootstrap paths.
    Includes wall-clock gated heap leak checks (every 60s) AND live heartbeat
    status writes (every 30s) to cm.base_dir / "soak_status.json".
    """
    _state: Dict[str, Any] = {
        "baseline":      None,
        "last_check_ts": 0.0,
        "success_count": 0,
        "last_heartbeat_ts": 0.0,
    }

    def _on_loop_start(session: SessionState) -> None:
        _logger.info(
            "[LoopStart] session_id=%s | objective=%s | total_steps=%d | "
            "pending=%d | already_success=%d",
            session.session_id, session.objective[:60],
            len(session.task_graph.steps),
            session.task_graph.pending_count(),
            session.task_graph.success_count(),
        )

    def _on_step_success(step: TaskStep, result: StepResult, session: SessionState) -> None:
        _state["success_count"] += 1

        # ── Heartbeat Check (Addition 1) ─────────────────────────────────────
        now_mono = time.monotonic()
        if now_mono - _state["last_heartbeat_ts"] >= 30.0 or _state["last_heartbeat_ts"] == 0.0:
            try:
                from tests.long_running._soak_heartbeat import build_snapshot, write_heartbeat
                from core.harness.context_tracker import ContextTracker
                from tests.long_running._soak_workload import SOAK_TRACKER_CONFIG

                tracker = ContextTracker(SOAK_TRACKER_CONFIG)
                status_val = tracker.monitor_context(session).value
                comp_count = session.metadata.get("compactions_this_gen", 0)

                snapshot = build_snapshot(
                    run_start_ts=run_start_ts,
                    session_id=session.session_id,
                    generation_index=generation_index,
                    spawn_reason=spawn_reason,
                    current_step_id=step.step_id,
                    steps_completed=session.task_graph.success_count(),
                    steps_total=len(session.task_graph.steps),
                    context_status=status_val,
                    compactions_this_gen=comp_count,
                    total_cost_usd=session.state_matrix.estimated_cost,
                )
                write_heartbeat(cm.base_dir / "soak_status.json", snapshot)
            except Exception as exc:
                _logger.warning("[_on_step_success] Failed to write live heartbeat: %s", exc)
            _state["last_heartbeat_ts"] = now_mono

        # ── Leak Check ────────────────────────────────────────────────────────
        if _state["baseline"] is None:
            if _state["success_count"] >= LEAK_CHECK_WARMUP_STEPS:
                _state["baseline"] = take_baseline_snapshot()
                _state["last_check_ts"] = time.monotonic()
                _logger.info(
                    "[HeapProfile] Baseline captured after %d successful steps "
                    "(warm-up complete).",
                    _state["success_count"],
                )
            return  # still warming up — no leak check possible yet

        if now_mono - _state["last_check_ts"] >= LEAK_CHECK_INTERVAL_S:
            leak_report_path = cm.base_dir / session.session_id / "heap_leaks.jsonl"
            check_for_leaks(
                baseline=_state["baseline"],
                leak_report_path=leak_report_path,
                step_index=_state["success_count"],
            )
            _state["last_check_ts"] = now_mono

    def _on_step_failure(step: TaskStep, error_message: str, session: SessionState) -> None:
        _logger.warning(
            "[StepFailure] step_id=%s | retries=%d | error=%s",
            step.step_id, step.retries, error_message,
        )

    def _on_context_warning(session: SessionState) -> None:
        _logger.info(
            "[ContextWarning] session_id=%s | LSN=%d — approaching compaction threshold.",
            session.session_id, session.checkpoint_meta.lsn,
        )

    def _on_loop_end(status: LoopStatus, session: SessionState) -> None:
        _logger.info(
            "[LoopEnd] session_id=%s | status=%s | LSN=%d | success=%d/%d | "
            "error_count=%d",
            session.session_id, status.value, session.checkpoint_meta.lsn,
            session.task_graph.success_count(), len(session.task_graph.steps),
            session.state_matrix.error_count,
        )

    return LoopHooks(
        on_loop_start=_on_loop_start,
        on_step_success=_on_step_success,
        on_step_failure=_on_step_failure,
        on_context_warning=_on_context_warning,
        on_loop_end=_on_loop_end,
    )


# ==============================================================================
# SECTION 5 — Two-Phase Context Engine Binding (§ module docstring #1)
# ==============================================================================

def _bind_context_engine(loop: NalaLoop) -> NalaLoop:
    """
    Construct a fresh ``ContextTracker(SOAK_TRACKER_CONFIG)`` and a
    ``DronagiriCompactor`` bound to ``loop._save_checkpoint`` — which now
    exists, since ``loop`` is already fully constructed by the time this is
    called — then assign both directly onto the loop instance.

    This is called identically from BOTH bootstrap paths (fresh construction
    and ``recover_session()`` recovery), fully resolving the chicken-and-egg
    problem documented in the module docstring's design decision #1.

    Parameters
    ----------
    loop : NalaLoop
        An already-constructed loop with ``compactor=None`` /
        ``context_tracker=None`` (either just built, or just returned by
        ``recover_session()``).

    Returns
    -------
    NalaLoop
        The same loop instance, now with ``context_tracker`` and
        ``compactor`` bound (mutated in place and returned for convenient
        chaining at the call site).
    """
    tracker = ContextTracker(SOAK_TRACKER_CONFIG)
    compactor = DronagiriCompactor(
        tracker=tracker,
        summarizer_fn=_mock_soak_summarizer_fn,
        checkpoint_fn=loop._save_checkpoint,
    )
    loop.context_tracker = tracker

    # ── Wrap compactor.compact to track per-generation compaction count ───────
    # ``DronagiriCompactor`` does not maintain its own call counter, and editing
    # core harness code would break the cross-cutting concern boundary.  Instead
    # we replace the bound method on this specific instance with a thin closure
    # that increments ``session.metadata["compactions_this_gen"]`` after every
    # successful compact() call, making the count available to the heartbeat
    # writer in ``_on_step_success`` without any shared mutable state.
    _orig_compact = compactor.compact  # type: ignore[attr-defined]

    def _counted_compact(*args: object, **kwargs: object) -> object:
        result = _orig_compact(*args, **kwargs)
        loop.session.metadata["compactions_this_gen"] = (
            loop.session.metadata.get("compactions_this_gen", 0) + 1
        )
        return result

    try:
        compactor.compact = _counted_compact  # type: ignore[method-assign]
    except AttributeError:
        _logger.warning(
            "[ContextEngine] Cannot monkey-patch compactor.compact — compaction "
            "count will not be tracked in heartbeat snapshots.",
        )

    loop.compactor = compactor

    _logger.info(
        "[ContextEngine] Bound. max_context_tokens=%d | warning=%d | "
        "compaction=%d | safety_ceiling=%d",
        tracker.config.max_context_tokens,
        tracker.config.warning_threshold_tokens,
        tracker.config.compaction_threshold_tokens,
        tracker.config.safety_ceiling_tokens,
    )
    return loop



# ==============================================================================
# SECTION 6 — Bootstrap Paths
# ==============================================================================

def _bootstrap_initial(
    session_id:       str,
    cm:               CheckpointManager,
    run_start_ts:     float = 0.0,
    generation_index: int   = 1,
) -> NalaLoop:
    """
    Build the very first generation of the soak run: a fresh
    ``SessionState`` with a fresh 1,200-step ``TaskGraph``
    (``build_soak_task_graph``), structurally validated and genesis-
    checkpointed to disk before the loop takes a single step.

    Parameters
    ----------
    session_id        : UUID supplied via ``--session-id`` for this very first
                        generation of the whole soak run.
    cm                : CheckpointManager rooted at ``--checkpoint-dir``.
    run_start_ts      : Wall-clock epoch timestamp when the entire soak run
                        started — forwarded to the heartbeat builder so it can
                        compute accurate elapsed time.
    generation_index  : 1-based index of this generation (always 1 for initial).

    Returns
    -------
    NalaLoop
        Fully constructed, with ``mock_step_executor`` as the default
        handler and a bound ``ContextTracker`` + ``DronagiriCompactor``.
    """
    session = SessionState(
        session_id=session_id,
        objective=SOAK_OBJECTIVE,
        task_graph=build_soak_task_graph(n_steps=1200),
    )
    session.validate_task_graph()

    # write_checkpoint() internally calls session.prepare_checkpoint(), which
    # increments checkpoint_meta.lsn (0 → 1) and computes the SHA-256 hash —
    # no separate manual "increment" call is needed or correct here; calling
    # one would double-increment the LSN before this very first write.
    genesis_path = cm.write_checkpoint(session)
    _logger.info(
        "[Bootstrap:initial] Genesis checkpoint written. session_id=%s | "
        "LSN=%d | path=%s | total_steps=%d",
        session_id, session.checkpoint_meta.lsn, genesis_path,
        len(session.task_graph.steps),
    )

    loop = NalaLoop(
        session,
        cm,
        max_retries_per_step=3,
        checkpoint_on_success_only=False,
        hooks=_build_hooks(
            cm,
            run_start_ts=run_start_ts,
            generation_index=generation_index,
            spawn_reason="initial",
        ),
        context_tracker=None,
        compactor=None,
    )
    loop.set_default_handler(mock_step_executor)
    loop.session.metadata.setdefault("compactions_this_gen", 0)
    return _bind_context_engine(loop)


def _bootstrap_recovery(
    session_id:       str,
    cm:               CheckpointManager,
    spawn_reason:     str,
    run_start_ts:     float = 0.0,
    generation_index: int   = 1,
) -> NalaLoop:
    """
    Restore a session via ``recover_session()`` — used for BOTH:

    - ``"handoff"``       : graceful ``CONTEXT_EXHAUSTED`` spore handoff.
    - ``"crash_recovery"``: hard SIGKILL; same ``session_id`` is reused.

    Parameters
    ----------
    session_id        : UUID to recover.
    cm                : CheckpointManager rooted at ``--checkpoint-dir``.
    spawn_reason      : ``"handoff"`` or ``"crash_recovery"``.
    run_start_ts      : Epoch timestamp of the soak run start (for heartbeat).
    generation_index  : 1-based index of this generation (for heartbeat).

    Returns
    -------
    NalaLoop
        Fully recovered and context-engine-bound, ready for ``.run()``.

    Raises
    ------
    SessionRecoveryError
        (Or a subclass.) Propagated to the caller; ``main()`` maps it to exit 3.
    """
    loop = recover_session(
        session_id=session_id,
        checkpoint_manager=cm,
        handlers={},
        default_handler=mock_step_executor,
        context_tracker=None,
        compactor=None,
        max_retries_per_step=3,
        hooks=_build_hooks(
            cm,
            run_start_ts=run_start_ts,
            generation_index=generation_index,
            spawn_reason=spawn_reason,
        ),
    )
    _logger.info(
        "[Bootstrap:%s] Recovery complete. session_id=%s | LSN=%d | "
        "pending=%d | success=%d | error_count=%d",
        spawn_reason, loop.session.session_id, loop.session.checkpoint_meta.lsn,
        loop.session.task_graph.pending_count(),
        loop.session.task_graph.success_count(),
        loop.session.state_matrix.error_count,
    )
    loop.session.metadata.setdefault("compactions_this_gen", 0)
    return _bind_context_engine(loop)


# ==============================================================================
# SECTION 7 — Exit Code Contract Mapping (§3.2)
# ==============================================================================

def _map_status_to_exit_code(status: LoopStatus) -> int:
    """
    Translate a terminal ``LoopStatus`` into the JIRA-007 §3.2 exit code
    contract. This is the ONLY function in the soak suite that performs this
    mapping — ``NalaLoop.run()`` itself deliberately knows nothing about
    process exit codes, since it is also called as a library function.

    Since this suite NEVER calls ``loop.stop()``, the only code path that
    can produce ``LoopStatus.PAUSED`` here is ``NalaLoop.run()`` internally
    catching ``ContextExhaustedSignal`` after ``HandoffSpore.write_spore()``
    has already been durably written to disk — so ``PAUSED`` is unambiguous
    in this context and maps directly to exit code 10.

    Mapping
    -------
    COMPLETED -> 0   |  PAUSED -> 10  |  BLOCKED -> 2  |  (else) -> 1
    """
    if status == LoopStatus.COMPLETED:
        return 0
    if status == LoopStatus.PAUSED:
        return 10
    if status == LoopStatus.BLOCKED:
        return 2
    # LoopStatus.FAILED, or any other value that should structurally never
    # occur as a terminal return from run() — fail safe to exit code 1
    # rather than raising here, so the supervisor still gets a classifiable
    # exit code instead of a hung/zombie process.
    return 1


# ==============================================================================
# SECTION 8 — main()
# ==============================================================================

def main(argv: Optional[List[str]] = None) -> None:
    """
    Entrypoint. Parses CLI args, starts heap profiling, bootstraps the
    correct path (fresh vs recovery), runs the loop to a terminal
    ``LoopStatus``, and exits with the exact code the supervisor expects.

    Every exit path — success, bootstrap failure, or run-time failure —
    flushes stdout/stderr immediately before calling ``sys.exit()`` (module
    docstring, design decision #4).
    """
    # tracemalloc MUST start before any further NALA imports/construction
    # happen at runtime, so the eventual baseline snapshot reflects true
    # warm-up allocation — see module docstring, design decision #2.
    start_heap_profiling()

    args                    = _parse_args(argv)
    session_id:     str     = args.session_id
    checkpoint_dir: Path    = Path(args.checkpoint_dir)
    spawn_reason:   str     = args.spawn_reason
    run_start_ts:   float   = args.run_start_ts
    generation_index: int   = args.generation_index

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    _logger.info(
        "[Entrypoint] Starting. session_id=%s | spawn_reason=%s | "
        "checkpoint_dir=%s | pid=%d | gen_idx=%d",
        session_id, spawn_reason, checkpoint_dir, os.getpid(), generation_index,
    )

    cm = CheckpointManager(base_dir=checkpoint_dir)

    # ── Bootstrap phase ──────────────────────────────────────────────────────
    try:
        if spawn_reason == "initial":
            loop = _bootstrap_initial(
                session_id, cm,
                run_start_ts=run_start_ts,
                generation_index=generation_index,
            )
        else:
            loop = _bootstrap_recovery(
                session_id, cm, spawn_reason,
                run_start_ts=run_start_ts,
                generation_index=generation_index,
            )
    except SessionRecoveryError as exc:
        # Catches SessionRecoveryError AND its subclasses
        # (SessionRecoveryLockError, RunawayLoopError) — all three map to
        # exit code 3, but type(exc).__name__ preserves which one fired for
        # the supervisor's failure-report log tail.
        _logger.critical(
            "[Entrypoint] Recovery FAILED (%s): %s", type(exc).__name__, exc,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(3)
    except Exception as exc:  # noqa: BLE001 — last-resort bootstrap guard
        _logger.critical(
            "[Entrypoint] Unhandled exception during bootstrap: %s", exc,
            exc_info=True,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)

    # ── Run phase ────────────────────────────────────────────────────────────
    try:
        status: LoopStatus = loop.run()
    except Exception as exc:  # noqa: BLE001 — NalaLoop.run() already has its
                               # own last-resort guard internally, but this
                               # protects against anything escaping that too.
        _logger.critical(
            "[Entrypoint] Unhandled exception escaped loop.run(): %s", exc,
            exc_info=True,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)

    exit_code = _map_status_to_exit_code(status)
    _logger.info(
        "[Entrypoint] Exiting cleanly. session_id=%s | final_status=%s | "
        "exit_code=%d", loop.session.session_id, status.value, exit_code,
    )
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
