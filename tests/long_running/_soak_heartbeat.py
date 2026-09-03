"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_heartbeat.py
Ticket  : JIRA-007-B — Advanced Soak Orchestrator (Addition 1: Live Heartbeat)
Sections: JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md §3 (Live Heartbeat File)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
Lets a human glance at "what is NALA doing right now?" — via
``cat soak_status.json`` over Tailscale from a phone — without tailing raw
logs. The Executor subprocess is the SOLE writer (it holds the freshest live
state: current step, context status, compaction count); no cross-process
locking or merging is needed because nothing else ever writes this file.

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. ATOMIC WRITE-THEN-RENAME, WITH ``fsync()`` BEFORE THE RENAME.
   Writing directly to ``soak_status.json`` risks a reader (``cat`` from a
   phone, mid-write) seeing a truncated/torn JSON document. Writing to a
   sibling ``.tmp`` file, ``flush()``-ing the Python buffer, ``fsync()``-ing
   the OS buffer to disk, and only THEN calling ``os.replace()`` guarantees
   any reader either sees the complete previous file or the complete new
   one — never a partial write. ``os.replace()`` is atomic on both POSIX and
   Windows for same-filesystem renames, which this always is (the ``.tmp``
   file lives next to its final target).

2. ``format_elapsed_human()`` SUPPORTS HOURS, NOT JUST "Xm Ys".
   The ticket's own example format is "14m 32s", correct for a single
   60-minute soak run. But this module is written to also serve NALA's
   longer-term goal of continuous multi-hour/multi-day monitoring — a
   heartbeat that silently overflows into "127m 3s" past the 2-hour mark is
   needlessly harder to read than "2h 7m 3s". Hours are only shown when
   non-zero, so the common case stays exactly as specified.

3. ``resolve_phase()`` IMPORTS ``PHASE_BOUNDARIES`` FROM ``_soak_workload``
   RATHER THAN DUPLICATING IT. Phase boundaries are workload-owned data
   (``_soak_workload.py`` is the single source of truth). Duplicating the
   ``[0, 200, 400, 900, 1200]`` list here would silently drift out of sync
   the moment someone tunes the workload for a different step count —
   importing it guarantees the heartbeat's reported phase always matches
   exactly what the executor is actually doing.

4. ``read_heartbeat()`` NEVER RAISES — IT IS A VIEWER-SIDE PRIMITIVE.
   A future lightweight CLI/phone viewer built on top of this function must
   be able to poll a heartbeat file that might not exist yet, might be
   mid-write despite the atomic-rename design (e.g. a concurrent NFS mount
   edge case), or might be from an older schema version with missing/extra
   fields. Every failure mode collapses to a clean ``None`` rather than
   propagating an exception into a monitoring tool that should never crash.

5. ``write_heartbeat()`` DOES RAISE ON GENUINE I/O FAILURE.
   Unlike the reader, the writer is called from inside the Executor's hot
   ``on_step_success`` hook path. A silent failure there would mean the
   heartbeat quietly goes stale for the rest of the run with no signal
   anywhere. Raising lets the CALLER (the entrypoint's hook closure) decide
   whether to log-and-continue or propagate — this module does not make
   that policy decision on the caller's behalf.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover — defensive; psutil is a hard
                      # dependency of the wider soak suite, but this module
                      # degrades gracefully rather than failing at import
                      # time if it is ever missing in a minimal environment.
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False

try:
    from tests.long_running._soak_workload import PHASE_BOUNDARIES
except ImportError:  # pragma: no cover — defensive fallback matching the
                      # documented default in _soak_workload.py, so this
                      # module remains importable/testable in isolation.
    PHASE_BOUNDARIES = [0, 200, 400, 900, 1200]

_logger = logging.getLogger("nala.soak.heartbeat")

_STEP_INDEX_PATTERN = re.compile(r"soak_step_(\d+)")


# ==============================================================================
# SECTION 1 — HeartbeatSnapshot
# ==============================================================================

@dataclasses.dataclass
class HeartbeatSnapshot:
    """
    A single point-in-time snapshot of Executor subprocess state, written to
    ``soak_status.json`` roughly every 30 seconds and safe to read from any
    external process (a phone, a monitoring script) at any moment.

    Fields
    ------
    ts                    : ``time.time()`` at the moment this snapshot was built.
    run_start_ts          : ``time.time()`` of the very first generation of the
                            whole soak run (passed down from SoakSupervisor via
                            ``--run-start-ts`` so elapsed time is correct even
                            across handoff/crash-recovery generation boundaries).
    elapsed_s             : ``ts - run_start_ts``, clamped to ``>= 0.0``.
    elapsed_human         : Human-readable rendering of ``elapsed_s`` — see
                            ``format_elapsed_human()``.
    session_id            : The session_id of the CURRENT generation.
    generation_index      : 1-based index of the current generation within
                            the whole soak run (1 = initial, 2 = first
                            handoff/crash-recovery, etc.).
    spawn_reason          : ``"initial"`` / ``"handoff"`` / ``"crash_recovery"``.
    phase                 : 1-4, resolved from ``current_step_id`` against
                            ``_soak_workload.PHASE_BOUNDARIES`` — see
                            ``resolve_phase()``.
    current_step_id       : The ``step_id`` of the step currently being
                            dispatched, or the most recently completed one if
                            called between dispatches. ``None`` before the
                            first step has been attempted.
    steps_completed       : Count of SUCCESS steps in the current session so far.
    steps_total           : Total steps in the TaskGraph.
    context_status        : ``"NORMAL"`` / ``"WARNING"`` / ``"COMPACTING"`` /
                            ``"EXHAUSTED"`` — the ``ContextStatus.value`` at
                            the moment of this snapshot.
    compactions_this_gen  : Number of ``DronagiriCompactor.compact()`` calls
                            observed so far in THIS generation (resets to 0
                            on every new process — the process itself cannot
                            know the cross-generation total).
    rss_mb                : Self-reported resident memory of THIS process,
                            in MB, via ``psutil.Process(os.getpid())``.
                            ``-1.0`` if psutil is unavailable or the read fails.
    total_cost_usd        : Cumulative ``StateMatrix.estimated_cost`` for the
                            current session at snapshot time.
    last_updated_human    : ISO 8601 UTC timestamp string, for staleness
                            detection by a reader (e.g. "this file hasn't
                            moved in 10 minutes — something is stuck").
    """

    ts:                    float
    run_start_ts:          float
    elapsed_s:              float
    elapsed_human:          str
    session_id:             str
    generation_index:       int
    spawn_reason:           str
    phase:                  int
    current_step_id:        Optional[str]
    steps_completed:        int
    steps_total:            int
    context_status:         str
    compactions_this_gen:   int
    rss_mb:                 float
    total_cost_usd:         float
    last_updated_human:     str


# ==============================================================================
# SECTION 2 — Formatting & Derivation Helpers
# ==============================================================================

def format_elapsed_human(elapsed_s: float) -> str:
    """
    Render a duration in seconds as a compact human-readable string.

    Handles the common single-run case exactly as specified ("14m 32s"), and
    additionally scales to hours for longer-running monitoring use cases
    (module docstring, design decision #2). Negative input (possible from
    clock skew if ``run_start_ts`` and the local clock disagree) is clamped
    to zero rather than producing a nonsensical negative duration string.

    Parameters
    ----------
    elapsed_s : Elapsed duration in seconds. May be a float; truncated to
                whole seconds for display.

    Returns
    -------
    str
        ``"Xm Ys"`` for durations under one hour, or ``"Xh Ym Zs"`` once the
        duration reaches one hour or more.
    """
    total_seconds = int(max(0.0, elapsed_s))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def resolve_phase(current_step_id: Optional[str]) -> int:
    """
    Resolve the 1-4 workload phase from a ``soak_step_NNNN``-style step_id,
    using the SAME ``PHASE_BOUNDARIES`` boundaries ``mock_step_executor``
    itself uses (imported directly from ``_soak_workload`` — module
    docstring, design decision #3) — guaranteeing the heartbeat's reported
    phase can never drift out of sync with what the executor is actually doing.

    Matches step ids in any of the three shapes ``build_soak_task_graph``
    produces: ``soak_step_0123``, ``soak_step_0100_branch_2``, and
    ``soak_step_0100_join`` — the leading ``soak_step_(\\d+)`` prefix is
    identical across all three, so a single regex handles all of them.

    Parameters
    ----------
    current_step_id : The step_id currently being dispatched, or ``None`` if
                      no step has been attempted yet in this generation.

    Returns
    -------
    int
        1-4. Defaults to 1 if ``current_step_id`` is ``None`` or does not
        match the expected pattern (e.g. an unrelated step-id scheme).
        Clamps to the final phase if the parsed index exceeds every
        configured boundary (defensive against an off-by-one at the very
        last step).
    """
    if current_step_id is None:
        return 1

    match = _STEP_INDEX_PATTERN.match(current_step_id)
    if match is None:
        return 1

    index = int(match.group(1))
    boundary_pairs: list[Tuple[int, int]] = list(
        zip(PHASE_BOUNDARIES, PHASE_BOUNDARIES[1:])
    )

    for phase_number, (lower, upper) in enumerate(boundary_pairs, start=1):
        if lower < index <= upper:
            return phase_number

    # Beyond the last configured boundary — clamp rather than return an
    # out-of-range phase number.
    return len(boundary_pairs)


def capture_self_rss_mb() -> float:
    """
    Self-report the CURRENT process's resident memory in MB via
    ``psutil.Process(os.getpid())``.

    This is deliberately self-reporting (the Executor reads its own memory,
    rather than the supervisor sampling it externally) — the supervisor's
    OS-level psutil sampling in ``_soak_supervisor.py`` already covers
    cross-process RSS tracking every 10 seconds for the final AC-5
    assertion; this reading exists purely so a live heartbeat glance doesn't
    require correlating two different files.

    Returns
    -------
    float
        Resident memory in MB, rounded to 2 decimal places. ``-1.0`` if
        psutil is unavailable (module docstring, design decision — defensive
        import) or if the read otherwise fails for any reason.
    """
    if not _PSUTIL_AVAILABLE:
        _logger.warning(
            "[capture_self_rss_mb] psutil is not available — reporting -1.0."
        )
        return -1.0

    try:
        proc = psutil.Process(os.getpid())
        rss_bytes = proc.memory_info().rss
        return round(rss_bytes / (1024 * 1024), 2)
    except Exception as exc:  # noqa: BLE001 — a heartbeat read must never
                               # raise and disrupt the caller's hot loop.
        _logger.warning("[capture_self_rss_mb] Failed to read self RSS: %s", exc)
        return -1.0


def build_snapshot(
    run_start_ts:          float,
    session_id:             str,
    generation_index:       int,
    spawn_reason:           str,
    current_step_id:        Optional[str],
    steps_completed:        int,
    steps_total:            int,
    context_status:         str,
    compactions_this_gen:   int,
    total_cost_usd:         float,
) -> HeartbeatSnapshot:
    """
    Convenience builder that assembles a complete ``HeartbeatSnapshot``,
    internally computing every DERIVED field (``ts``, ``elapsed_s``,
    ``elapsed_human``, ``phase``, ``rss_mb``, ``last_updated_human``) so the
    caller (the entrypoint's ``on_step_success`` hook) only needs to supply
    the raw, directly-known values.

    Parameters
    ----------
    run_start_ts          : Epoch seconds when the FIRST generation of the
                            whole soak run started (passed down via
                            ``--run-start-ts``, constant across every
                            generation of the same run).
    session_id             : Current generation's session_id.
    generation_index       : 1-based generation counter.
    spawn_reason           : ``"initial"`` / ``"handoff"`` / ``"crash_recovery"``.
    current_step_id        : step_id currently being dispatched, or ``None``.
    steps_completed        : Current SUCCESS count.
    steps_total             : Total steps in the TaskGraph.
    context_status          : ``ContextStatus.value`` string at snapshot time.
    compactions_this_gen    : Compaction count observed so far this generation.
    total_cost_usd          : Current ``StateMatrix.estimated_cost``.

    Returns
    -------
    HeartbeatSnapshot
        Fully populated, ready to pass directly to ``write_heartbeat()``.
    """
    now = time.time()
    elapsed_s = max(0.0, now - run_start_ts)

    return HeartbeatSnapshot(
        ts=now,
        run_start_ts=run_start_ts,
        elapsed_s=elapsed_s,
        elapsed_human=format_elapsed_human(elapsed_s),
        session_id=session_id,
        generation_index=generation_index,
        spawn_reason=spawn_reason,
        phase=resolve_phase(current_step_id),
        current_step_id=current_step_id,
        steps_completed=steps_completed,
        steps_total=steps_total,
        context_status=context_status,
        compactions_this_gen=compactions_this_gen,
        rss_mb=capture_self_rss_mb(),
        total_cost_usd=total_cost_usd,
        last_updated_human=datetime.now(timezone.utc).isoformat(),
    )


# ==============================================================================
# SECTION 3 — Atomic Write / Defensive Read
# ==============================================================================

def write_heartbeat(path: Path, snapshot: HeartbeatSnapshot) -> None:
    """
    Atomically write ``snapshot`` to ``path`` as JSON.

    Sequence (module docstring, design decision #1):
      1. Serialize to JSON.
      2. Write to a sibling ``{path.name}.tmp`` file.
      3. ``flush()`` the Python-level buffer.
      4. ``os.fsync()`` the OS-level buffer to disk.
      5. ``os.replace(tmp, path)`` — atomic rename on POSIX and Windows.

    A reader polling ``path`` at any point in time therefore always sees
    either the complete PREVIOUS snapshot or the complete NEW one — never a
    torn/partial JSON document.

    Parameters
    ----------
    path     : Final target path (e.g. ``.../soak_status.json``). Parent
              directories are created if they do not already exist.
    snapshot : The ``HeartbeatSnapshot`` to persist.

    Raises
    ------
    OSError
        If the write, fsync, or replace step fails. This function does NOT
        swallow I/O errors (module docstring, design decision #5) — the
        CALLER (typically a hook closure in a hot loop) is responsible for
        deciding whether a heartbeat write failure should be logged-and-
        ignored or allowed to propagate.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")

    payload: Dict[str, Any] = dataclasses.asdict(snapshot)
    serialized = json.dumps(payload, indent=2)

    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except OSError:
        # Best-effort cleanup of the partially-written temp file so a failed
        # write attempt does not leave stale .tmp debris behind on disk.
        tmp_path.unlink(missing_ok=True)
        raise


def read_heartbeat(path: Path) -> Optional[HeartbeatSnapshot]:
    """
    Defensively read and parse a heartbeat file written by
    ``write_heartbeat()``.

    NEVER raises (module docstring, design decision #4) — every failure
    mode (missing file, empty file, invalid JSON, schema mismatch from an
    older/newer version of this module) collapses to a clean ``None``,
    since this function is intended as a viewer-side primitive for tooling
    that must keep polling indefinitely without ever crashing.

    Parameters
    ----------
    path : Path to the heartbeat JSON file (e.g. ``.../soak_status.json``).

    Returns
    -------
    Optional[HeartbeatSnapshot]
        The parsed snapshot, or ``None`` if the file does not exist, is
        empty, is not valid JSON, or does not match the
        ``HeartbeatSnapshot`` field schema.
    """
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.debug("[read_heartbeat] Failed to read '%s': %s", path, exc)
        return None

    if not raw.strip():
        return None

    try:
        data: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        _logger.debug("[read_heartbeat] Invalid JSON in '%s': %s", path, exc)
        return None

    try:
        return HeartbeatSnapshot(**data)
    except TypeError as exc:
        # Field mismatch — e.g. an older heartbeat file written by a prior
        # schema version with missing or renamed keys.
        _logger.debug(
            "[read_heartbeat] Schema mismatch parsing '%s' into "
            "HeartbeatSnapshot: %s", path, exc,
        )
        return None


__all__ = [
    "HeartbeatSnapshot",
    "format_elapsed_human",
    "resolve_phase",
    "capture_self_rss_mb",
    "build_snapshot",
    "write_heartbeat",
    "read_heartbeat",
]
