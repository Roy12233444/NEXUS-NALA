"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_history.py
Ticket  : JIRA-007-B — Advanced Soak Orchestrator (Addition 4: Regression History)
Sections: JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md §6
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
Maintains a durable, per-workload-version run history that survives across
individual test invocations and surfaces statistically meaningful drift
warnings before they become production incidents.

A single soak-test pass/fail number is invisible to the most dangerous class
of production failure: slow, monotonic decay. RSS creeping up 3 % every run
for two weeks straight is undetectable by any single-run threshold, but it is
exactly the pattern that triggers an OOM kill on day 20 of a 30-day mission.

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. STORAGE PATH IS OUTSIDE ANY PER-RUN checkpoint_base_dir.
   Each soak run creates its own fresh checkpoint_base_dir (keyed by a new
   session UUID). Placing soak_history.jsonl under any of those directories
   would cause it to be silently lost on the next run's fresh directory.
   The caller supplies the concrete path; this module imposes no layout opinion.

2. WORKLOAD-VERSION ISOLATION (RISK-H04).
   History regression checks are meaningless when different workloads are
   compared. Every SoakRunSummary carries a workload_version field (first 12
   hex chars of SHA-256 of canonical repr of PHASE_BOUNDARIES + n_steps).
   check_regression() filters STRICTLY to the same workload_version.

3. FILE ROTATION USES AN ATOMIC WRITE, NOT IN-PLACE TRUNCATION (RISK-H03).
   record_run() reads all entries, appends, slices to 100, then stages to a
   .tmp file and atomically os.replace()-s it into place.

4. MEDIAN OVER MEAN — resistant to one-off GC spikes.

5. check_regression() IS A WARNING EMITTER, NEVER A HARD-ASSERT.
   Returns a list of human-readable strings. The caller decides whether to
   log-and-continue or escalate.

6. MINIMUM BASELINE GUARD — 3 MATCHING RUNS required before any warning fires.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

_logger = logging.getLogger("nala.soak.history")

_MIN_BASELINE_RUNS: int = 3
_MAX_HISTORY_ENTRIES: int = 100


# ==============================================================================
# SECTION 1 — SoakRunSummary dataclass
# ==============================================================================

@dataclasses.dataclass
class SoakRunSummary:
    """
    A single, serialisable record of one completed soak run.

    Fields
    ------
    ts                  : time.time() at the moment the run completed or failed.
    workload_version    : First 12 hex chars of SHA-256 of repr(PHASE_BOUNDARIES + [n_steps]).
                          Runs with different workload_version are never compared (RISK-H04).
    peak_rss_mb         : Peak RSS (MB) observed by SoakSupervisor across the run.
    total_compactions   : Total DronagiriCompactor.compact() calls across all generations.
    total_cost_usd      : Cumulative StateMatrix.estimated_cost across all generations.
    total_generations   : Number of Executor subprocess generations in this run.
    passed              : True if all assertions passed, False if any failed.
    """

    ts:                 float
    workload_version:   str
    peak_rss_mb:        float
    total_compactions:  int
    total_cost_usd:     float
    total_generations:  int
    passed:             bool


# ==============================================================================
# SECTION 2 — Workload Version Helper
# ==============================================================================

def compute_workload_version(phase_boundaries: List[int], n_steps: int) -> str:
    """
    Compute a stable, short workload-version tag for a given combination of
    phase_boundaries and n_steps.

    The tag is the first 12 hex characters of the SHA-256 digest of the
    canonical repr of phase_boundaries + [n_steps], e.g. "a3f9c1e72b04".

    Parameters
    ----------
    phase_boundaries : The PHASE_BOUNDARIES list from _soak_workload.
    n_steps          : The n_steps arg passed to build_soak_task_graph().

    Returns
    -------
    str
        A 12-character lowercase hex string.
    """
    key = repr(list(phase_boundaries) + [n_steps])
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# ==============================================================================
# SECTION 3 — Record Run (Append + Rotate)
# ==============================================================================

def record_run(history_path: Path, summary: SoakRunSummary) -> None:
    """
    Persist summary to history_path as one JSON line, then rotate the file
    to at most _MAX_HISTORY_ENTRIES (100) entries atomically (RISK-H03).

    Write sequence:
      1. Read all existing entries.
      2. Append the new serialised summary.
      3. Slice to the most recent 100 entries.
      4. Write to a sibling .tmp file, fsync(), then os.replace() over the
         original — guarantees a reader always sees a complete file.

    Parameters
    ----------
    history_path : Full path to the JSONL history file.
                   Parent directories are created automatically.
    summary      : The completed run record to append.

    Raises
    ------
    OSError
        Propagated from the underlying I/O operations if the write fails.
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)

    entries: List[str] = []
    if history_path.exists():
        try:
            raw = history_path.read_text(encoding="utf-8")
            for line in raw.splitlines():
                stripped = line.strip()
                if stripped:
                    entries.append(stripped)
        except OSError as exc:
            _logger.warning(
                "[record_run] Could not read existing history at '%s': %s. "
                "Proceeding with an empty baseline.",
                history_path, exc,
            )
            entries = []

    new_line = json.dumps(dataclasses.asdict(summary), separators=(",", ":"))
    entries.append(new_line)

    if len(entries) > _MAX_HISTORY_ENTRIES:
        entries = entries[-_MAX_HISTORY_ENTRIES:]

    tmp_path = history_path.with_name(history_path.name + ".tmp")
    combined = "\n".join(entries) + "\n"

    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(combined)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, history_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise

    _logger.info(
        "[record_run] Recorded soak run to '%s'. "
        "Total entries after rotation: %d. passed=%s peak_rss_mb=%.2f",
        history_path, len(entries), summary.passed, summary.peak_rss_mb,
    )


# ==============================================================================
# SECTION 4 — Median Helper
# ==============================================================================

def _compute_median(values: List[float]) -> float:
    """
    Compute the median of a non-empty list using only the standard library.
    For even-length lists, returns the average of the two central values.

    Raises
    ------
    ValueError
        If values is empty.
    """
    if not values:
        raise ValueError("Cannot compute median of an empty list.")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


# ==============================================================================
# SECTION 5 — Regression Check (Median Drift Detector)
# ==============================================================================

def check_regression(
    history_path:    Path,
    current:         SoakRunSummary,
    lookback:        int   = 5,
    drift_threshold: float = 0.15,
) -> List[str]:
    """
    Compare current against the MEDIAN of the last lookback completed soak
    runs sharing the SAME workload_version, and return human-readable warning
    strings for any metric that has drifted beyond drift_threshold.

    This function NEVER raises. Every failure mode (missing file, malformed
    JSON, insufficient history) collapses to an empty list.

    Metrics checked
    ---------------
    - peak_rss_mb       — primary slow-leak signal.
    - total_compactions — growing count signals increasing context pressure.
    - total_cost_usd    — cost creep can indicate runaway retry loops.

    Parameters
    ----------
    history_path     : Path to the JSONL history file.
    current          : The just-completed run's summary. Must NOT have been
                       appended to history yet, or it will bias its own baseline.
    lookback         : Number of same-workload-version runs to include in the
                       median. Default 5.
    drift_threshold  : Fraction above median that triggers a WARNING. Default
                       0.15 (15%). e.g. median=519 MB, current=612 MB -> 18% warning.

    Returns
    -------
    List[str]
        Zero or more human-readable warning strings. Empty list = no regression
        detected OR insufficient history (< _MIN_BASELINE_RUNS = 3 entries).

    Example
    -------
    >>> warnings = check_regression(Path(".soak_history/soak_history.jsonl"), summary)
    >>> # Output example:
    >>> # "WARNING: peak_rss_mb=612.4 is 18% above the 5-run median of 519.1 ..."
    """
    warnings: List[str] = []

    if not history_path.exists():
        _logger.debug(
            "[check_regression] History file '%s' does not exist. "
            "Skipping regression check.", history_path,
        )
        return warnings

    try:
        raw = history_path.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.warning(
            "[check_regression] Cannot read history file '%s': %s. "
            "Returning empty warning list.", history_path, exc,
        )
        return warnings

    raw_entries: List[SoakRunSummary] = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
            raw_entries.append(SoakRunSummary(**data))
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            _logger.debug(
                "[check_regression] Skipping malformed history line %d: %s",
                line_no, exc,
            )

    matching: List[SoakRunSummary] = [
        e for e in raw_entries
        if e.workload_version == current.workload_version
    ]
    baseline_entries = matching[-lookback:] if len(matching) >= lookback else matching

    if len(baseline_entries) < _MIN_BASELINE_RUNS:
        _logger.info(
            "[check_regression] Only %d same-workload-version run(s) in history "
            "(minimum %d required). Skipping regression check.",
            len(baseline_entries), _MIN_BASELINE_RUNS,
        )
        return warnings

    median_rss         = _compute_median([e.peak_rss_mb for e in baseline_entries])
    median_compactions = _compute_median([float(e.total_compactions) for e in baseline_entries])
    median_cost        = _compute_median([e.total_cost_usd for e in baseline_entries])
    n_runs = len(baseline_entries)

    # peak_rss_mb drift check
    if median_rss > 0.0:
        drift = (current.peak_rss_mb - median_rss) / median_rss
        if drift > drift_threshold:
            pct = int(round(drift * 100))
            warnings.append(
                f"\u26a0\ufe0f  REGRESSION WARNING: peak_rss_mb={current.peak_rss_mb:.1f} "
                f"is {pct}% above the {n_runs}-run median of {median_rss:.1f} "
                f"— trending upward across recent runs."
            )
            _logger.warning(
                "[check_regression] peak_rss_mb drift: current=%.2f median=%.2f +%d%%",
                current.peak_rss_mb, median_rss, pct,
            )

    # total_compactions drift check
    if median_compactions > 0.0:
        drift = (float(current.total_compactions) - median_compactions) / median_compactions
        if drift > drift_threshold:
            pct = int(round(drift * 100))
            warnings.append(
                f"\u26a0\ufe0f  REGRESSION WARNING: total_compactions={current.total_compactions} "
                f"is {pct}% above the {n_runs}-run median of {median_compactions:.1f} "
                f"— context pressure trending upward across recent runs."
            )
            _logger.warning(
                "[check_regression] total_compactions drift: current=%d median=%.1f +%d%%",
                current.total_compactions, median_compactions, pct,
            )

    # total_cost_usd drift check
    if median_cost > 0.0:
        drift = (current.total_cost_usd - median_cost) / median_cost
        if drift > drift_threshold:
            pct = int(round(drift * 100))
            warnings.append(
                f"\u26a0\ufe0f  REGRESSION WARNING: total_cost_usd={current.total_cost_usd:.6f} "
                f"is {pct}% above the {n_runs}-run median of {median_cost:.6f} "
                f"— API cost trending upward across recent runs."
            )
            _logger.warning(
                "[check_regression] total_cost_usd drift: current=%.6f median=%.6f +%d%%",
                current.total_cost_usd, median_cost, pct,
            )

    if not warnings:
        _logger.info(
            "[check_regression] No regression detected against %d same-workload-version run(s).",
            n_runs,
        )

    return warnings


# ==============================================================================
# SECTION 6 — Load All History (utility)
# ==============================================================================

def load_history(
    history_path: Path,
    workload_version: Optional[str] = None,
) -> List[SoakRunSummary]:
    """
    Load and parse all entries from history_path, optionally filtered to a
    single workload_version. Returns an empty list if the file does not exist.
    Silently skips malformed lines.

    Parameters
    ----------
    history_path      : Path to the JSONL history file.
    workload_version  : If provided, only entries with a matching version are returned.

    Returns
    -------
    List[SoakRunSummary]
        All (or filtered) parsed entries, in file order (oldest first).
    """
    results: List[SoakRunSummary] = []
    if not history_path.exists():
        return results
    try:
        raw = history_path.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.warning("[load_history] Cannot read '%s': %s.", history_path, exc)
        return results
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
            summary = SoakRunSummary(**data)
            if workload_version is None or summary.workload_version == workload_version:
                results.append(summary)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return results


__all__ = [
    "SoakRunSummary",
    "compute_workload_version",
    "record_run",
    "check_regression",
    "load_history",
]
