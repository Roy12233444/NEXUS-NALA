"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_workload.py
Ticket  : JIRA-007 — 1-Hour Soak Test (Workload Generation Module)
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
This module is the sole source of synthetic workload for the JIRA-007 1-hour
soak test. It provides:

  1. CONSTANTS            — Phase boundaries, pacing, failure rate, and
                            the deliberately small TrackerConfig that forces
                            multiple compaction cycles within the 60-minute
                            window (see SS5.4 of JIRA_007_1HOUR_SOAK_TEST_PLAN_V2.MD).

  2. PAYLOAD GENERATORS  — Three distinct payload profiles, each engineered to
                            exercise a specific branch of the Dronagiri Stage 1
                            regex pipeline or to force escalation to Stage 2 LLM
                            crystallization:
                            a) generate_high_entropy_base64()  -> _RE_BASE64_BLOB path
                            b) generate_system_log_snippet()   -> _RE_TRACEBACK / _RE_ANSI path
                            c) generate_manifest_payload()     -> Stage-2 force (SHA-256 resistant)

  3. TASK GRAPH BUILDER  — build_soak_task_graph(n_steps=1200): linear chain with
                            3-way fan-out/join groups every 100 steps, verified
                            cycle-free via DFS (AC-2).

  4. MOCK EXECUTOR       — mock_step_executor(): phase-aware payload dispatch,
                            random paced sleep, transient failure injection,
                            and DUAL-WRITE telemetry (AC-6 contract, SS5.3).

DUAL-WRITE TELEMETRY CONTRACT (CRITICAL -- DO NOT REMOVE)
---------------------------------------------------------
Every StepResult returned by mock_step_executor() writes token/cost telemetry
in TWO independent locations:

  (a) StepResult.prompt_tokens / .completion_tokens / .cost_usd
      -> consumed by NalaLoop._update_telemetry() -> StateMatrix.add_llm_call()
        during normal per-step execution.

  (b) output["_meta_tokens_in"] / ["_meta_tokens_out"] / ["_meta_cost_usd"]
      -> consumed ONLY by StateMatrixValidator.validate_reconstructed() during
        crash recovery, to compute the monotonic floor from SUCCESS step results.

Omitting (b) would make AC-6 telemetry-continuity invariant trivially true
even when a real regression exists -- a silent false-negative that ARIES would
not surface. Both paths MUST always be populated.

================================================================================
Jai Bajrang Bali
================================================================================
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from core.harness.context_tracker import TrackerConfig
from core.harness.nala_loop import StepResult
from core.harness.session_contract import (
    SessionState,
    TaskGraph,
    TaskStep,
    utcnow,
)

_logger = logging.getLogger("nala.soak.workload")


# ==============================================================================
# SECTION 1 -- Soak Constants
# ==============================================================================

PHASE_BOUNDARIES: List[int] = [0, 200, 400, 900, 1200]

FAILURE_INJECTION_RATE: float = 0.05

STEP_PACING_S: Tuple[float, float] = (2.0, 4.0)

SOAK_TRACKER_CONFIG: TrackerConfig = TrackerConfig(
    max_context_tokens=100_000,
    warning_percent=0.70,
    compaction_percent=0.85,
    safety_buffer_fraction=0.05,
    n_preserve_tail=3,
    per_message_overhead=20,
)


# ==============================================================================
# SECTION 2 -- Payload Generators
# ==============================================================================

def generate_high_entropy_base64(size_bytes: int, line_width: int = 76) -> str:
    """
    Generate a line-wrapped base64 string from size_bytes of OS-sourced
    cryptographically random bytes.

    Stage 1 path: _RE_BASE64_BLOB matches any run of 3+ consecutive lines
    each containing >= 60 base64-alphabet characters. With line_width=76
    (RFC 2045 MIME default), this payload is reliably caught and redacted
    to [BINARY_CONTENT_REDACTED] by Stage 1.

    Parameters
    ----------
    size_bytes : int
        Number of random bytes to encode.
    line_width : int
        Character width at which to wrap. Default 76 (RFC 2045 / PEM).

    Returns
    -------
    str
        A newline-wrapped base64 ASCII string.
    """
    if size_bytes <= 0:
        raise ValueError(f"size_bytes must be > 0, got {size_bytes!r}")
    if line_width <= 0:
        raise ValueError(f"line_width must be > 0, got {line_width!r}")

    raw: bytes = os.urandom(size_bytes)
    b64: str = base64.b64encode(raw).decode("ascii")
    return "\n".join(b64[i : i + line_width] for i in range(0, len(b64), line_width))


def generate_system_log_snippet(target_bytes: int = 100 * 1024) -> str:
    """
    Synthesize a realistic ~target_bytes multi-line system/tool-execution
    log, mixing plain INFO/WARN/ERROR timestamp lines, ANSI colour tags,
    embedded Python tracebacks (~1% of lines), and periodic blank-line clusters.

    Stage 1 patterns exercised: P1 (traceback), P2 (ANSI), P3 (tool header),
    P5 (separator), P6 (excess blank lines).

    Parameters
    ----------
    target_bytes : int
        Approximate byte length of the generated log string. Default 100 KB.

    Returns
    -------
    str
        A newline-joined synthetic log string.
    """
    if target_bytes <= 0:
        raise ValueError(f"target_bytes must be > 0, got {target_bytes!r}")

    _LEVELS: List[Tuple[str, str]] = [
        ("\x1b[32mINFO\x1b[0m",  "step completed successfully"),
        ("\x1b[33mWARN\x1b[0m",  "retrying connection -- attempt 2/3"),
        ("\x1b[31mERROR\x1b[0m", "transient socket timeout -- will retry"),
    ]

    _TRACEBACK_BLOCK: str = (
        "Traceback (most recent call last):\n"
        "  File 'tool_runner.py', line 88, in execute\n"
        "    result = subprocess.run(cmd, timeout=30)\n"
        "subprocess.TimeoutExpired: Command timed out after 30 seconds"
    )

    lines: List[str] = ["--- Tool Output ---"]

    while sum(len(line) + 1 for line in lines) < target_bytes:
        tag, msg = random.choice(_LEVELS)
        month_day = f"{random.randint(10, 29):02d}"
        hh = f"{random.randint(0, 23):02d}"
        mm_s = f"{random.randint(0, 59):02d}"
        ss = f"{random.randint(0, 59):02d}"
        lines.append(f"2026-06-{month_day}T{hh}:{mm_s}:{ss}Z [{tag}] {msg}")

        if random.random() < 0.01:
            lines.append(_TRACEBACK_BLOCK)

        if random.random() < 0.02:
            lines.append("\n\n\n")

    lines.append("=" * 30)
    return "\n".join(lines)


def generate_manifest_payload(n_entries: int = 220) -> Dict[str, Any]:
    """
    Synthesize a realistic n_entries-item file-manifest step result.

    Each SHA-256 digest is EXACTLY 64 lowercase hex characters -- individually
    below the _RE_BASE64_BLOB repetition minimum, and bounded by JSON punctuation
    outside the [A-Za-z0-9+/] character class. This makes the payload
    Stage-1-resistant by design, reliably forcing Stage 2 LLM crystallization
    (AC-3 requirement for at least 1 Stage-2 compaction).

    Parameters
    ----------
    n_entries : int
        Number of synthetic file entries to generate. Default 220.

    Returns
    -------
    Dict[str, Any]
        A dict with a single "manifest" key containing a list of file-entry dicts.
    """
    if n_entries <= 0:
        raise ValueError(f"n_entries must be > 0, got {n_entries!r}")

    entries: List[Dict[str, Any]] = [
        {
            "path":       f"/repo/src/module_{i:04d}.py",
            "size_bytes": random.randint(512, 65_536),
            "sha256":     hashlib.sha256(os.urandom(16)).hexdigest(),
            "mtime":      f"2026-06-{random.randint(10, 29):02d}T00:00:00Z",
        }
        for i in range(n_entries)
    ]
    return {"manifest": entries}


# ==============================================================================
# SECTION 3 -- Task Graph Builder
# ==============================================================================

def build_soak_task_graph(n_steps: int = 1_200) -> TaskGraph:
    """
    Build the JIRA-007 soak task graph: a linear dependency chain of n_steps
    steps, with a 3-way parallel fan-out/join group inserted every 100 steps.

    Structure per 100-step window:
      - soak_step_{i:04d}_branch_0  depends on prev_id
      - soak_step_{i:04d}_branch_1  depends on prev_id
      - soak_step_{i:04d}_branch_2  depends on prev_id
      - soak_step_{i:04d}_join      depends on all three branches

    All other steps are plain linear nodes. No backward edges exist;
    the graph is a strict DAG verified by has_circular_dependency() (DFS).

    AC-2: len(graph.steps) >= 1000 is asserted before return.

    Parameters
    ----------
    n_steps : int
        Total number of logical step slots. Actual step count is higher
        because each fan-out cluster contributes 4 steps (3 branches + 1 join).

    Returns
    -------
    TaskGraph
        A validated, cycle-free TaskGraph instance.

    Raises
    ------
    AssertionError
        If AC-2 is violated or a circular dependency is detected.
    """
    steps: List[TaskStep] = []
    prev_id: Optional[str] = None

    for i in range(1, n_steps + 1):
        step_id_base = f"soak_step_{i:04d}"
        linear_deps: List[str] = [prev_id] if prev_id else []

        if i % 100 == 0:
            branch_ids: List[str] = [
                f"{step_id_base}_branch_{b}" for b in range(3)
            ]
            for bid in branch_ids:
                steps.append(
                    TaskStep(
                        step_id=bid,
                        description=f"Soak fan-out branch: {bid}",
                        dependencies=linear_deps,
                    )
                )

            join_id = f"{step_id_base}_join"
            steps.append(
                TaskStep(
                    step_id=join_id,
                    description=f"Soak fan-out join: {join_id}",
                    dependencies=branch_ids,
                )
            )
            prev_id = join_id

        else:
            steps.append(
                TaskStep(
                    step_id=step_id_base,
                    description=f"Soak step {i} of {n_steps}",
                    dependencies=linear_deps,
                )
            )
            prev_id = step_id_base

    assert len(steps) >= 1_000, (
        f"[AC-2 VIOLATION] build_soak_task_graph generated only {len(steps)} steps "
        f"(n_steps={n_steps}). TaskGraph must have >= 1,000 steps."
    )

    graph = TaskGraph(steps=steps)

    assert not graph.has_circular_dependency(), (
        "[build_soak_task_graph] FATAL: circular dependency detected in soak graph. "
        "This is a construction bug -- review fan-out/join dependency wiring."
    )

    _logger.info(
        "[SoakWorkload] TaskGraph built: %d total steps (%d fan-out clusters).",
        len(steps),
        n_steps // 100,
    )
    return graph


# ==============================================================================
# SECTION 4 -- Phase Resolution Helper
# ==============================================================================

def _resolve_phase(step_id: str) -> int:
    """
    Extract the numeric step index from a soak step_id and map it to a
    phase number (1-4) based on PHASE_BOUNDARIES.

    Supports plain linear IDs ("soak_step_0042") and fan-out branch/join IDs
    ("soak_step_0100_branch_0", "soak_step_0100_join"). For branch/join steps,
    the cluster base index is used.

    Returns phase 1 as a safe default if parsing fails.

    Parameters
    ----------
    step_id : str
        The TaskStep.step_id string to parse.

    Returns
    -------
    int
        Phase number in the range [1, 4].
    """
    try:
        base = (
            step_id
            .replace("_join", "")
            .replace("_branch_0", "")
            .replace("_branch_1", "")
            .replace("_branch_2", "")
        )
        parts = base.split("_")
        idx = int(parts[2])
    except (IndexError, ValueError):
        _logger.debug(
            "[SoakWorkload] Could not parse step index from step_id=%r -- defaulting to Phase 1.",
            step_id,
        )
        return 1

    for phase, (lo, hi) in enumerate(
        zip(PHASE_BOUNDARIES, PHASE_BOUNDARIES[1:]), start=1
    ):
        if lo < idx <= hi:
            return phase

    return 4


# ==============================================================================
# SECTION 5 -- Mock Step Executor
# ==============================================================================

def mock_step_executor(step: TaskStep, session: SessionState) -> StepResult:
    """
    Phase-aware mock executor for JIRA-007 soak test steps.

    Execution Contract
    ------------------
    1. Pacing: sleeps for a uniform-random duration in STEP_PACING_S to
       simulate real LLM call latency and ensure AC-1 60-minute coverage.

    2. Failure Injection: raises RuntimeError with probability
       FAILURE_INJECTION_RATE. NalaLoop retries automatically up to
       max_retries_per_step times.

    3. Phase-Aware Payload:
       Phase 1 (steps   1-200): Light sentinel dict (NORMAL context baseline)
       Phase 2 (steps 201-400): 16 KB system log (Stage 1 regex path, AC-3a)
       Phase 3 (steps 401-900): Alternates manifest (Stage 2, AC-3b) and
                                 log+blob (Stage 1, AC-3a) on even/odd idx
       Phase 4 (steps 901-1200): Light settling dict (post-compaction cooldown)

    4. Dual-Write Telemetry (CRITICAL -- both (a) and (b) MUST be populated):
       (a) StepResult.prompt_tokens / .completion_tokens / .cost_usd
           -> NalaLoop._update_telemetry() -> StateMatrix.add_llm_call()
       (b) output["_meta_tokens_in"] / ["_meta_tokens_out"] / ["_meta_cost_usd"]
           -> StateMatrixValidator.validate_reconstructed() for AC-6 ARIES floor

    Parameters
    ----------
    step : TaskStep
        The step to execute.
    session : SessionState
        The live session state (read-only in this function).

    Returns
    -------
    StepResult
        A fully populated StepResult with dual-written telemetry.

    Raises
    ------
    RuntimeError
        Raised with probability FAILURE_INJECTION_RATE for transient failure
        simulation. NalaLoop will retry automatically.
    """
    # -- 1. Pacing -------------------------------------------------------------
    time.sleep(random.uniform(*STEP_PACING_S))

    # -- 2. Transient Failure Injection ----------------------------------------
    if random.random() < FAILURE_INJECTION_RATE:
        raise RuntimeError(
            f"[SoakWorkload] Simulated transient tool failure on step "
            f"'{step.step_id}' (rate={FAILURE_INJECTION_RATE:.0%})."
        )

    # -- 3. Phase-Aware Payload Selection --------------------------------------
    phase: int = _resolve_phase(step.step_id)

    try:
        base = (
            step.step_id
            .replace("_join", "")
            .replace("_branch_0", "")
            .replace("_branch_1", "")
            .replace("_branch_2", "")
        )
        numeric_idx: int = int(base.split("_")[2])
    except (IndexError, ValueError):
        numeric_idx = 1

    if phase == 1:
        payload: Dict[str, Any] = {
            "note":    "light sentinel step -- Phase 1 (NORMAL context)",
            "step_id": step.step_id,
            "ts":      utcnow().isoformat(),
        }

    elif phase == 2:
        payload = {
            "log":     generate_system_log_snippet(target_bytes=16 * 1024),
            "step_id": step.step_id,
            "phase":   2,
        }

    elif phase == 3:
        if numeric_idx % 2 == 0:
            payload = {
                **generate_manifest_payload(n_entries=220),
                "step_id": step.step_id,
                "phase":   3,
                "profile": "manifest_stage2",
            }
        else:
            payload = {
                "log":     generate_system_log_snippet(target_bytes=100 * 1024),
                "blob":    generate_high_entropy_base64(size_bytes=4 * 1024),
                "step_id": step.step_id,
                "phase":   3,
                "profile": "log_blob_stage1",
            }

    else:  # phase == 4
        payload = {
            "note":    "settling step -- Phase 4 (post-compaction cooldown)",
            "step_id": step.step_id,
            "ts":      utcnow().isoformat(),
        }

    # -- 4. Fixed Telemetry (Dual-Write) ---------------------------------------
    tokens_in:  int   = 120
    tokens_out: int   = 40
    cost_usd:   float = 0.0006

    return StepResult(
        success=True,
        output={
            **payload,
            # (b) ARIES floor metadata -- consumed by StateMatrixValidator
            "_meta_tokens_in":  tokens_in,
            "_meta_tokens_out": tokens_out,
            "_meta_cost_usd":   cost_usd,
        },
        # (a) Standard telemetry -- consumed by NalaLoop._update_telemetry()
        prompt_tokens=tokens_in,
        completion_tokens=tokens_out,
        cost_usd=cost_usd,
        model="soak-mock-v1",
    )
