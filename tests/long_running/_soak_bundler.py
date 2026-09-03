"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_bundler.py
Ticket  : JIRA-007-B — Advanced Soak Orchestrator (Addition 5: Failure Bundler)
Sections: JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md §7
          (Auto-Bundled Failure Report)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
A 2 AM failure should produce ONE artifact you hand over the next morning —
not four scattered files you have to hunt for first.

When test_soak_1hr.py's orchestration loop catches any assertion or unexpected
exception, it calls bundle_failure_artifacts() BEFORE re-raising. This ensures
pytest still reports the failure normally, AND a self-contained ZIP archive
lands in checkpoint_base_dir for immediate hand-off.

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. SIZE-BOUNDED BUNDLE (RISK-H05).
   Supervisor log files can grow large over a 60-minute run (one file per
   generation, each containing the full stdout+stderr of the Executor). Naively
   zipping all of them could produce a bundle too large to quickly share.
   Instead, each log file is read line-by-line and only the LAST 500 lines are
   written into the archive, bounding each log contribution to a predictable,
   shareable size. If the file is shorter than 500 lines, the whole file is
   included.

2. SESSION-ID-SCOPED LOG FILTERING.
   The supervisor log directory may contain logs from prior incomplete runs
   (e.g. a test run that failed early, was re-invoked, and ran again). When a
   session_id IS provided, only logs whose filenames contain that session_id are
   included — keeping the bundle focused on the failing run. When session_id is
   None, all .log files are included (e.g. if the orchestrator itself crashed
   before a session_id was assigned).

3. CHECKPOINT SELECTION — LAST 3 BY LSN.
   Including every checkpoint file for a session could be enormous. Only the
   last 3 (by numeric LSN) are included — these are the ones the recovery
   engine will examine first and are most likely to contain the relevant state
   at the point of failure.

4. GRACEFUL MISSING-FILE HANDLING.
   Every individual file addition is wrapped in its own try/except. A missing
   soak_metrics.jsonl (e.g. if the run died before any metrics were written)
   will not prevent the bundle from being created with the files that DO exist.
   Each skip is logged at DEBUG level.

5. BUNDLE IS WRITTEN BEFORE RE-RAISE.
   The contract (documented in the public function's docstring) is:
     - Caller wraps its entire orchestration block in try/except.
     - On exception: call bundle_failure_artifacts() FIRST.
     - Then re-raise the original exception.
   This module does NOT catch or suppress exceptions — it is the caller's
   responsibility to re-raise after bundling.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

_logger = logging.getLogger("nala.soak.bundler")

# Maximum number of lines to include from each supervisor log file (RISK-H05).
_LOG_TAIL_LINES: int = 500

# Maximum number of checkpoint files (by LSN) to include per session.
_MAX_CHECKPOINTS: int = 3

# Regex matching checkpoint filenames: checkpoint_LSN_000042.json
_CHECKPOINT_RE: re.Pattern[str] = re.compile(
    r"^checkpoint_LSN_(\d{6,})\.json$"
)

# Flat filenames looked for directly under checkpoint_base_dir.
_ROOT_ARTIFACT_NAMES: Tuple[str, ...] = (
    "soak_failure_report.json",
    "soak_metrics.jsonl",
    "heap_leaks.jsonl",
    "soak_status.json",
)


# ==============================================================================
# SECTION 1 — Internal Helpers
# ==============================================================================

def _tail_lines(path: Path, n: int) -> str:
    """
    Read the last ``n`` lines of a text file and return them as a single
    string (with a trailing newline). If the file contains fewer than ``n``
    lines, the entire file content is returned.

    Never raises: any OSError is caught and an informative placeholder string
    is returned instead (so the bundle still contains an entry for the file,
    just with an error message rather than silently omitting it).

    Parameters
    ----------
    path : Path to the log file to read.
    n    : Maximum number of lines to return (from the end of the file).

    Returns
    -------
    str
        The tail content, or an error message string if the file cannot be read.
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _logger.debug("[_tail_lines] Cannot read '%s': %s", path, exc)
        return f"[ERROR: could not read file — {exc}]\n"

    lines = raw.splitlines(keepends=True)
    if len(lines) <= n:
        return raw
    tail = lines[-n:]
    header = (
        f"[TRUNCATED — showing last {n} of {len(lines)} lines "
        f"from {path.name}]\n"
    )
    return header + "".join(tail)


def _collect_checkpoint_files(
    checkpoint_base_dir: Path,
    session_id: str,
    max_count: int,
) -> List[Path]:
    """
    Locate the last ``max_count`` checkpoint files for ``session_id``, sorted
    by descending LSN (highest LSN first).

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory.
    session_id          : Session whose checkpoint directory will be scanned.
    max_count           : Maximum number of checkpoint files to return.

    Returns
    -------
    List[Path]
        Up to ``max_count`` checkpoint file paths, highest LSN first. Empty
        list if the session directory does not exist or contains no matching
        files.
    """
    session_dir = checkpoint_base_dir / session_id
    if not session_dir.is_dir():
        _logger.debug(
            "[_collect_checkpoint_files] Session dir '%s' does not exist.",
            session_dir,
        )
        return []

    candidates: List[Tuple[int, Path]] = []
    for entry in session_dir.iterdir():
        if not entry.is_file():
            continue
        match = _CHECKPOINT_RE.match(entry.name)
        if match is None:
            continue
        lsn = int(match.group(1))
        candidates.append((lsn, entry))

    candidates.sort(key=lambda t: t[0], reverse=True)
    return [path for _, path in candidates[:max_count]]


def _collect_supervisor_logs(
    checkpoint_base_dir: Path,
    session_id: Optional[str],
) -> List[Path]:
    """
    Locate all supervisor log files relevant to ``session_id``.

    Log files live under ``{checkpoint_base_dir}/supervisor_logs/`` and are
    named ``{session_id}__gen{NN}__{reason}.log`` (per _soak_supervisor.py's
    own naming convention).

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory.
    session_id          : If provided, only logs whose filenames contain this
                          session_id are returned. If None, all .log files in
                          the log directory are returned.

    Returns
    -------
    List[Path]
        Matched .log file paths, in directory-scan order (typically by name,
        which encodes generation index).
    """
    log_dir = checkpoint_base_dir / "supervisor_logs"
    if not log_dir.is_dir():
        _logger.debug(
            "[_collect_supervisor_logs] Log dir '%s' does not exist.", log_dir,
        )
        return []

    results: List[Path] = []
    for entry in sorted(log_dir.iterdir()):
        if not entry.is_file() or entry.suffix != ".log":
            continue
        if session_id is not None and session_id not in entry.name:
            continue
        results.append(entry)

    return results


# ==============================================================================
# SECTION 2 — Public API
# ==============================================================================

def bundle_failure_artifacts(
    checkpoint_base_dir: Path,
    session_id:          Optional[str],
) -> Path:
    """
    Collect all relevant soak-run failure diagnostics, package them into a
    single ZIP archive, and return the path to the archive.

    Archive name: ``soak_failure_bundle_<UTC_YYYYMMDD_HHMMSS>.zip``, written
    directly under ``checkpoint_base_dir``.

    Bundle contents (all items included only if they exist on disk):
    ---------------------------------------------------------------
    1. ``soak_failure_report.json``  — failure diagnostics from SoakSupervisor.
    2. ``soak_metrics.jsonl``        — full run telemetry.
    3. ``heap_leaks.jsonl``          — per-generation heap leak data.
    4. ``soak_status.json``          — last known heartbeat before failure.
    5. Last 3 checkpoint files by LSN for ``session_id`` (if provided).
    6. Supervisor log files for ``session_id``, each truncated to the last
       500 lines to bound bundle size (RISK-H05).

    Contract with caller (test_soak_1hr.py)
    ----------------------------------------
    This function does NOT suppress or catch the original failure exception.
    The caller is expected to:
      1. Catch the exception in its own except block.
      2. Call bundle_failure_artifacts() to generate the ZIP.
      3. Re-raise the original exception so pytest reports it normally.

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory where SoakSupervisor wrote
                          all run artifacts (CheckpointManager.base_dir).
    session_id          : Session ID of the final generation at the time of
                          failure. Used to locate checkpoint files and filter
                          supervisor logs. May be None if the orchestrator
                          crashed before any session was created.

    Returns
    -------
    Path
        Absolute path to the created ZIP archive.

    Raises
    ------
    OSError
        If the ZIP file itself cannot be created (e.g., full disk). Individual
        missing artifact files are silently skipped (design decision #4).
    """
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"soak_failure_bundle_{ts_str}.zip"
    bundle_path = checkpoint_base_dir / bundle_name

    checkpoint_base_dir.mkdir(parents=True, exist_ok=True)

    files_added: int = 0

    _logger.info(
        "[bundle_failure_artifacts] Creating failure bundle: %s", bundle_path,
    )

    with zipfile.ZipFile(bundle_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── 1. Root artifact flat files ───────────────────────────────────────
        for artifact_name in _ROOT_ARTIFACT_NAMES:
            src = checkpoint_base_dir / artifact_name
            if not src.is_file():
                _logger.debug(
                    "[bundle_failure_artifacts] Skipping missing artifact: '%s'",
                    src,
                )
                continue
            try:
                zf.write(src, arcname=artifact_name)
                files_added += 1
                _logger.debug(
                    "[bundle_failure_artifacts] Added root artifact: %s",
                    artifact_name,
                )
            except OSError as exc:
                _logger.warning(
                    "[bundle_failure_artifacts] Could not add '%s': %s. "
                    "Skipping.", src, exc,
                )

        # ── 2. Last 3 checkpoints by LSN ─────────────────────────────────────
        if session_id is not None:
            checkpoint_files = _collect_checkpoint_files(
                checkpoint_base_dir, session_id, _MAX_CHECKPOINTS,
            )
            if not checkpoint_files:
                _logger.debug(
                    "[bundle_failure_artifacts] No checkpoint files found for "
                    "session_id='%s'.", session_id,
                )
            for ckpt_path in checkpoint_files:
                arcname = f"checkpoints/{ckpt_path.name}"
                try:
                    zf.write(ckpt_path, arcname=arcname)
                    files_added += 1
                    _logger.debug(
                        "[bundle_failure_artifacts] Added checkpoint: %s",
                        ckpt_path.name,
                    )
                except OSError as exc:
                    _logger.warning(
                        "[bundle_failure_artifacts] Could not add checkpoint "
                        "'%s': %s. Skipping.", ckpt_path, exc,
                    )

        # ── 3. Supervisor logs — size-bounded tails (RISK-H05) ───────────────
        log_files = _collect_supervisor_logs(checkpoint_base_dir, session_id)
        if not log_files:
            _logger.debug(
                "[bundle_failure_artifacts] No supervisor log files found "
                "(session_id=%s).", session_id,
            )
        for log_path in log_files:
            arcname = f"supervisor_logs/{log_path.name}"
            tail_content = _tail_lines(log_path, _LOG_TAIL_LINES)
            try:
                zf.writestr(arcname, tail_content)
                files_added += 1
                _logger.debug(
                    "[bundle_failure_artifacts] Added log tail (last %d lines): %s",
                    _LOG_TAIL_LINES, log_path.name,
                )
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "[bundle_failure_artifacts] Could not write log tail for "
                    "'%s': %s. Skipping.", log_path, exc,
                )

    _logger.warning(
        "[bundle_failure_artifacts] Failure bundle created: %s "
        "(%d file(s) included). session_id=%s",
        bundle_path, files_added, session_id,
    )
    return bundle_path


def bundle_success_artifacts(
    checkpoint_base_dir: Path,
    session_id:          Optional[str],
) -> Path:
    """
    Collect all successful soak-run artifacts, package them into a
    single ZIP archive, clean up uncompressed files/folders, and return
    the path to the archive.

    Archive name: ``soak_success_bundle_<UTC_YYYYMMDD_HHMMSS>.zip``, written
    directly under ``checkpoint_base_dir``.

    Parameters
    ----------
    checkpoint_base_dir : Root checkpoint directory.
    session_id          : Session ID of the final generation.

    Returns
    -------
    Path
        Absolute path to the created ZIP archive.
    """
    import shutil

    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"soak_success_bundle_{ts_str}.zip"
    bundle_path = checkpoint_base_dir / bundle_name

    checkpoint_base_dir.mkdir(parents=True, exist_ok=True)
    files_added: int = 0

    _logger.info(
        "[bundle_success_artifacts] Creating success bundle: %s", bundle_path,
    )

    with zipfile.ZipFile(bundle_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── 1. Root flat files ────────────────────────────────────────────────
        for name in _ROOT_ARTIFACT_NAMES:
            src = checkpoint_base_dir / name
            if not src.is_file():
                continue
            try:
                zf.write(src, arcname=name)
                files_added += 1
            except OSError as exc:
                _logger.warning(
                    "[bundle_success_artifacts] Could not add '%s': %s", name, exc
                )

        # ── 2. Last 3 checkpoints ─────────────────────────────────────────────
        if session_id is not None:
            checkpoint_files = _collect_checkpoint_files(
                checkpoint_base_dir, session_id, _MAX_CHECKPOINTS
            )
            for ckpt_path in checkpoint_files:
                try:
                    zf.write(ckpt_path, arcname=f"checkpoints/{ckpt_path.name}")
                    files_added += 1
                except OSError as exc:
                    _logger.warning(
                        "[bundle_success_artifacts] Could not add checkpoint '%s': %s",
                        ckpt_path.name, exc
                    )

        # ── 3. Full supervisor logs (no truncation for success) ─────────────
        log_files = _collect_supervisor_logs(checkpoint_base_dir, session_id)
        for log_path in log_files:
            try:
                zf.write(log_path, arcname=f"supervisor_logs/{log_path.name}")
                files_added += 1
            except OSError as exc:
                _logger.warning(
                    "[bundle_success_artifacts] Could not add log '%s': %s",
                    log_path.name, exc
                )

    # ── 4. Clean up temporary directories ─────────────────────────────────────
    # Walk through checkpoint_base_dir and remove:
    # - Any directory whose name looks like a UUID (temporary session folder)
    # - The supervisor_logs directory
    for entry in checkpoint_base_dir.iterdir():
        if entry.is_dir():
            if entry.name == "supervisor_logs":
                try:
                    shutil.rmtree(entry)
                    _logger.debug("[bundle_success_artifacts] Removed directory: %s", entry.name)
                except OSError as exc:
                    _logger.warning("[bundle_success_artifacts] Could not remove '%s': %s", entry.name, exc)
            elif len(entry.name) == 36 and entry.name.count("-") == 4:
                # UUID format check
                try:
                    shutil.rmtree(entry)
                    _logger.debug("[bundle_success_artifacts] Cleaned up temporary session: %s", entry.name)
                except OSError as exc:
                    _logger.warning("[bundle_success_artifacts] Could not remove '%s': %s", entry.name, exc)

    _logger.info(
        "[bundle_success_artifacts] Success bundle created: %s (%d files included)",
        bundle_path, files_added,
    )
    return bundle_path


__all__ = [
    "bundle_failure_artifacts",
    "bundle_success_artifacts",
]

