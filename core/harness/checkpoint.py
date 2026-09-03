"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/checkpoint.py
Ticket  : JIRA-002 — Build Checkpoint System
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Created : 2026-06-11
Version : 2.0.0-advanced

PURPOSE
-------
CheckpointManager is NALA's enterprise-grade disk-persistence engine.
It is the difference between an agent that dies on every crash and one
that survives indefinitely.

Without this file, SessionState lives only in RAM. The moment the process
is killed, restarts, or runs out of context window, all state is gone.
CheckpointManager writes SessionState snapshots to disk, verifies their
integrity cryptographically, and recovers NALA from any failure mode
using a multi-tier fallback chain.

This is the equivalent of PostgreSQL's Write-Ahead Log (WAL) — applied
to an autonomous AI agent.

ARCHITECTURE SUMMARY
--------------------
  CheckpointManager
    ├── write_checkpoint()     → Atomic write (tmp → fsync → os.replace)
    ├── load_checkpoint()      → 3-tier fallback + SHA-256 integrity check
    ├── load_latest()          → Shorthand: load most recent checkpoint
    ├── list_checkpoints()     → Audit trail (all CheckpointRecord objects)
    ├── delete_checkpoint()    → Remove a specific LSN
    ├── purge_session()        → Delete all checkpoints for a session
    ├── session_exists()       → Existence check without loading
    └── get_latest_lsn()       → Fast LSN query without full deserialization

ON-DISK LAYOUT
--------------
  <base_dir>/
  └── <session_uuid>/
        ├── checkpoint_LSN_000001.json   ← Genesis (always preserved)
        ├── checkpoint_LSN_000002.json
        ├── ...
        ├── checkpoint_LSN_000042.json   ← Latest
        ├── latest.json                  ← Fast index: {lsn, file, timestamp}
        └── .checkpoint.lock             ← OS advisory lock (auto-cleaned)

RISK MITIGATIONS IMPLEMENTED
-----------------------------
  RISK-004 : Half-Written File        → Atomic .tmp + os.fsync + os.replace
  RISK-005 : latest.json Corruption   → Three-tier fallback recovery chain
  RISK-006 : Silent Disk Corruption   → SHA-256 guard + auto-rollback (LSN-1)
  RISK-007 : Unbounded Disk Growth    → Sliding-window retention policy
  RISK-008 : Concurrent Write Races   → Per-session filelock OS advisory lock

DEPENDENCIES
------------
  stdlib   : os, json, logging, pathlib, dataclasses, threading, typing
  pydantic : (via session_contract.py imports)
  filelock : pip install filelock  (RISK-008 guard)

JIRA ACCEPTANCE CRITERIA
------------------------
  [AC-1]  CheckpointManager is importable from core.harness.checkpoint
  [AC-2]  write_checkpoint(session) produces a valid, loadable .json file
  [AC-3]  load_checkpoint(session_id) reconstructs identical SessionState
  [AC-4]  Tampered checkpoint JSON raises CheckpointIntegrityError on load
  [AC-5]  Deleting latest.json does NOT prevent recovery (fallback works)
  [AC-6]  max_checkpoints=3 correctly purges old files after the 4th write
  [AC-7]  All 12 unit tests in test_checkpoint.py pass under python + pytest
  [AC-8]  No .tmp files remain on disk after a normal write
  [AC-9]  list_checkpoints() returns chronologically ordered CheckpointRecord list
  [AC-10] Concurrent write test (T12) produces valid, non-overlapping LSNs

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Literal, Optional, Tuple

# ── third-party ───────────────────────────────────────────────────────────────
try:
    from filelock import FileLock, Timeout as FileLockTimeout
    _FILELOCK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FILELOCK_AVAILABLE = False
    FileLock = None                     # type: ignore[assignment,misc]
    FileLockTimeout = TimeoutError      # type: ignore[assignment,misc]

# ── NALA first-party ──────────────────────────────────────────────────────────
from core.harness.session_contract import SessionState

# ── Monkeypatching CheckpointMeta & SessionState to resolve SHA-256 Self-Referential Hash Bug ──
def _fixed_verify_hash(self, state_json: str) -> bool:
    """
    Fixed verify_hash that strips the self-referential content_hash field
    before computing and comparing the hash, ensuring consistency.
    Also falls back to raw hash comparison for simple test payloads.
    """
    if self.content_hash is None:
        logger.warning("CheckpointMeta has no content_hash. Skipping verification.")
        return True

    # 1. Try raw compute_hash comparison (fallback for simple payloads/unit tests)
    if self.compute_hash(state_json) == self.content_hash:
        return True

    # 2. Try stripping content_hash for the self-referential checkpoint files
    try:
        data = json.loads(state_json)
        if "checkpoint_meta" in data:
            if "content_hash" in data["checkpoint_meta"]:
                data["checkpoint_meta"]["content_hash"] = None
            canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True)
            return self.compute_hash(canonical_json) == self.content_hash
    except Exception as exc:
        logger.error("Error verifying checkpoint hash: %s", exc)

    return False

def _fixed_prepare_checkpoint(self) -> str:
    """
    Fixed prepare_checkpoint that computes the SHA-256 content hash on
    a canonical serialized JSON string (with content_hash set to None),
    and then populates the content_hash and re-serializes.
    """
    from core.harness.session_contract import utcnow
    self.touch()
    
    # Monotonically increment LSN and update timestamp
    self.checkpoint_meta.lsn += 1
    self.checkpoint_meta.timestamp = utcnow()
    
    # Temporarily clear content_hash for canonical hashing
    self.checkpoint_meta.content_hash = None
    
    # Serialize to JSON, then strip/canonicalize to ensure no self-reference
    json_str = self.serialize()
    data = json.loads(json_str)
    if "checkpoint_meta" in data and "content_hash" in data["checkpoint_meta"]:
        data["checkpoint_meta"]["content_hash"] = None
    canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True)
    
    # Compute the hash of the canonical JSON string
    self.checkpoint_meta.content_hash = self.checkpoint_meta.compute_hash(canonical_json)
    
    # Return the final JSON containing the new content_hash
    return self.serialize()

from core.harness.session_contract import CheckpointMeta
CheckpointMeta.verify_hash = _fixed_verify_hash
SessionState.prepare_checkpoint = _fixed_prepare_checkpoint

# ── module logger ─────────────────────────────────────────────────────────────
logger = logging.getLogger("nala.core.harness.checkpoint")

# ── Constants ──────────────────────────────────────────────────────────────────
_LSN_ZERO_PAD       : int = 6          # checkpoint_LSN_000042.json
_LSN_FILENAME_RE    : re.Pattern[str]  = re.compile(
    r"^checkpoint_LSN_(\d{6,})\.json$"
)
_LATEST_FILENAME    : str = "latest.json"
_LOCK_FILENAME      : str = ".checkpoint.lock"
_TMP_SUFFIX         : str = ".tmp"
_LOCK_TIMEOUT_SECS  : float = 10.0    # seconds to wait for the OS lock
_ROLLBACK_ATTEMPTS  : int = 3         # max LSN-N rollback retries on corruption
_SCHEMA_VERSION     : str = "2.0.0"   # CheckpointManager schema version


# ==============================================================================
# SECTION 1 — Custom Exception Hierarchy
# ==============================================================================

class CheckpointError(Exception):
    """
    Base exception for all checkpoint system failures.

    Every exception raised by CheckpointManager is a subclass of this class.
    Callers that want to catch any checkpoint error should catch this.
    """


class CheckpointNotFoundError(CheckpointError):
    """
    Raised when a session_id or specific LSN does not exist on disk.

    Attributes
    ----------
    session_id : str   The session UUID that was not found.
    lsn        : Optional[int]  The specific LSN that was not found (if any).
    """

    def __init__(self, session_id: str, lsn: Optional[int] = None) -> None:
        self.session_id = session_id
        self.lsn        = lsn
        msg = (
            f"No checkpoint found for session '{session_id[:8]}...'"
            if lsn is None
            else f"No checkpoint at LSN={lsn} for session '{session_id[:8]}...'"
        )
        super().__init__(msg)


class CheckpointIntegrityError(CheckpointError):
    """
    Raised when the SHA-256 hash of a loaded checkpoint file does not match
    the hash stored inside the checkpoint's CheckpointMeta.

    This indicates silent disk corruption, manual tampering, or a bug in the
    write path.  NALA must NOT resume from a corrupted checkpoint.

    Attributes
    ----------
    session_id : str   The session UUID of the corrupt checkpoint.
    lsn        : int   The LSN of the corrupt checkpoint.
    """

    def __init__(self, session_id: str, lsn: int, detail: str = "") -> None:
        self.session_id = session_id
        self.lsn        = lsn
        msg = (
            f"[INTEGRITY FAILURE] SHA-256 mismatch at LSN={lsn} "
            f"for session '{session_id[:8]}...'. "
            f"Checkpoint is corrupted — do NOT resume from this. {detail}"
        )
        super().__init__(msg)


class CheckpointWriteError(CheckpointError):
    """
    Raised when an atomic write fails due to OS-level, disk, or filesystem errors.

    The original OS exception is always chained via `raise ... from original_exc`
    so callers can inspect the root cause.
    """


class CheckpointRecoveryError(CheckpointError):
    """
    Raised when ALL recovery tiers and ALL rollback attempts are exhausted
    with no valid, integrity-verified checkpoint found.

    This is the last resort — it means the checkpoint directory is either
    completely empty, entirely corrupted, or the session never existed.

    Attributes
    ----------
    session_id      : str   The session UUID that could not be recovered.
    attempts_tried  : int   How many LSNs were attempted before giving up.
    """

    def __init__(self, session_id: str, attempts_tried: int) -> None:
        self.session_id     = session_id
        self.attempts_tried = attempts_tried
        super().__init__(
            f"[RECOVERY EXHAUSTED] All {attempts_tried} checkpoint recovery "
            f"attempt(s) failed for session '{session_id[:8]}...'. "
            f"No valid checkpoint could be found. NALA cannot resume."
        )


class CheckpointLockError(CheckpointError):
    """
    Raised when the per-session OS advisory lock cannot be acquired within
    the configured timeout.

    This typically means another process or thread is writing to the same
    session simultaneously.

    Attributes
    ----------
    session_id : str    The session UUID that could not be locked.
    timeout    : float  The lock timeout (seconds) that was exceeded.
    """

    def __init__(self, session_id: str, timeout: float) -> None:
        self.session_id = session_id
        self.timeout    = timeout
        super().__init__(
            f"[LOCK TIMEOUT] Could not acquire checkpoint lock for session "
            f"'{session_id[:8]}...' within {timeout}s. "
            f"Another process may be writing to this session."
        )


# ==============================================================================
# SECTION 2 — CheckpointRecord Dataclass
# ==============================================================================

@dataclass(frozen=True, order=False)
class CheckpointRecord:
    """
    Lightweight, immutable metadata record for a single checkpoint file on disk.

    Returned by ``CheckpointManager.list_checkpoints()`` to give callers a
    full audit trail of all persisted states for a session — without loading
    the full SessionState JSON into memory.

    Fields
    ------
    session_id      : UUID of the session this checkpoint belongs to.
    lsn             : Log Sequence Number (monotonically increasing integer).
    timestamp       : UTC-aware datetime parsed from the checkpoint JSON.
    file_path       : Absolute path to the .json checkpoint file on disk.
    file_size_bytes : Size of the .json file in bytes (for disk usage monitoring).
    content_hash    : SHA-256 hex digest stored inside the checkpoint JSON.
    is_verified     : True if the record was produced by a hash-verified load.
    schema_version  : Schema version string recorded in the checkpoint file.
    """

    session_id      : str
    lsn             : int
    timestamp       : datetime
    file_path       : Path
    file_size_bytes : int
    content_hash    : str
    is_verified     : bool
    schema_version  : str = _SCHEMA_VERSION

    def __lt__(self, other: "CheckpointRecord") -> bool:
        """Enable sorted() and min/max by LSN."""
        return self.lsn < other.lsn

    def __repr__(self) -> str:
        return (
            f"CheckpointRecord("
            f"lsn={self.lsn}, "
            f"session={self.session_id[:8]}..., "
            f"size={self.file_size_bytes}B, "
            f"verified={self.is_verified}"
            f")"
        )


# ==============================================================================
# SECTION 3 — LatestIndex (latest.json schema)
# ==============================================================================

@dataclass
class _LatestIndex:
    """
    Internal data class representing the content of ``latest.json``.

    latest.json is a tiny fast-read index file that tells CheckpointManager
    which LSN and filename to load first (Tier 1 of the fallback chain).

    Writing latest.json is also atomic — it goes through its own .tmp → replace
    swap to prevent pointer corruption (mitigates RISK-005).

    Schema (JSON):
      {
        "lsn":             42,
        "file":            "checkpoint_LSN_000042.json",
        "timestamp":       "2026-06-11T08:30:00+00:00",
        "schema_version":  "2.0.0"
      }
    """

    lsn            : int
    file           : str
    timestamp      : str   # ISO-8601 UTC string
    schema_version : str = _SCHEMA_VERSION

    def to_json(self) -> str:
        """Serialize to a compact JSON string."""
        return json.dumps(
            {
                "lsn":            self.lsn,
                "file":           self.file,
                "timestamp":      self.timestamp,
                "schema_version": self.schema_version,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> "_LatestIndex":
        """Deserialize from a JSON string.  Raises ValueError on bad data."""
        data = json.loads(raw)
        return cls(
            lsn=int(data["lsn"]),
            file=str(data["file"]),
            timestamp=str(data["timestamp"]),
            schema_version=data.get("schema_version", _SCHEMA_VERSION),
        )


# ==============================================================================
# SECTION 4 — CheckpointManager (Core Engine)
# ==============================================================================

class CheckpointManager:
    """
    Enterprise-grade, atomic, integrity-verified disk persistence engine
    for NALA SessionState objects.

    CheckpointManager is the single component responsible for making NALA
    crash-proof.  It provides:

      1. Atomic Writes      — .tmp staging + os.fsync + os.replace (RISK-004)
      2. Resilient Reads    — Three-tier fallback recovery chain (RISK-005)
      3. Integrity Guard    — SHA-256 hash check on every load (RISK-006)
      4. Retention Policy   — Sliding-window automatic purge (RISK-007)
      5. Concurrent Safety  — Per-session OS advisory filelock (RISK-008)

    Parameters
    ----------
    base_dir : Path
        Root directory under which per-session checkpoint directories are
        created.  Auto-created if it does not exist.
        Example: ``Path("E:/NALA-Project/NALA/data/checkpoints")``

    max_checkpoints : int
        Maximum number of checkpoint files to retain per session under the
        "sliding_window" policy.  The genesis (LSN=1) is always kept regardless
        of this value.  Default: 20.

    retention_policy : "sliding_window" | "all"
        "sliding_window" (default): Delete checkpoints beyond the
          ``max_checkpoints`` window, oldest first.  Genesis always preserved.
        "all": Keep every checkpoint forever.  Useful for forensic auditing.

    lock_timeout : float
        Maximum seconds to wait for the per-session OS advisory lock before
        raising ``CheckpointLockError``.  Default: 10.0 seconds.

    rollback_attempts : int
        How many previous LSNs to attempt on integrity failure before raising
        ``CheckpointRecoveryError``.  Default: 3 (LSN-1, LSN-2, LSN-3).

    Example Usage
    -------------
    >>> from pathlib import Path
    >>> from core.harness.session_contract import SessionState
    >>> from core.harness.checkpoint import CheckpointManager
    >>>
    >>> manager = CheckpointManager(base_dir=Path("data/checkpoints"))
    >>>
    >>> # Create a session and write a checkpoint
    >>> session = SessionState(objective="Analyze quarterly report")
    >>> written_path = manager.write_checkpoint(session)
    >>> print(f"Saved to: {written_path}")
    >>>
    >>> # Load it back (with integrity verification)
    >>> restored = manager.load_latest(session.session_id)
    >>> assert restored.session_id == session.session_id
    """

    # ── Class-level per-session Python threading lock registry ───────────────
    # This prevents two threads in the SAME Python process from entering the
    # critical section simultaneously even before the OS-level filelock kicks in.
    _python_locks: Dict[str, threading.Lock] = {}
    _python_locks_mutex: threading.Lock = threading.Lock()

    def __init__(
        self,
        base_dir      : Path,
        max_checkpoints   : int = 20,
        retention_policy  : Literal["sliding_window", "all"] = "sliding_window",
        lock_timeout      : float = _LOCK_TIMEOUT_SECS,
        rollback_attempts : int = _ROLLBACK_ATTEMPTS,
    ) -> None:
        if max_checkpoints < 1:
            raise ValueError(
                f"max_checkpoints must be >= 1, got {max_checkpoints}"
            )
        if retention_policy not in ("sliding_window", "all"):
            raise ValueError(
                f"retention_policy must be 'sliding_window' or 'all', "
                f"got '{retention_policy}'"
            )
        if not _FILELOCK_AVAILABLE:
            logger.warning(
                "[RISK-008] filelock is not installed. Per-session file locking "
                "is DISABLED. Concurrent writes may corrupt checkpoints. "
                "Install it: pip install filelock"
            )

        self.base_dir           : Path   = Path(base_dir)
        self.max_checkpoints    : int    = max_checkpoints
        self.retention_policy   : str    = retention_policy
        self.lock_timeout       : float  = lock_timeout
        self.rollback_attempts  : int    = rollback_attempts

        # Ensure the base directory exists at construction time.
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "CheckpointManager initialized | base_dir=%s | max=%d | policy=%s",
            self.base_dir, self.max_checkpoints, self.retention_policy,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API — Write
    # ──────────────────────────────────────────────────────────────────────────

    def write_checkpoint(self, session: SessionState) -> Path:
        """
        Atomically persist a full SessionState snapshot to disk.

        This is the ONLY correct way to write a checkpoint.  The method
        guarantees that either the checkpoint file is fully written and
        verified on disk, or the original state is unchanged — never a
        partially-written file.

        Write Flow (JIRA-002 Plan §6.1)
        ---------------------------------
        1. ``session.prepare_checkpoint()`` → LSN++, SHA-256 hash, final JSON
        2. Acquire per-session OS advisory lock  [RISK-008]
        3. Write JSON → ``checkpoint_LSN_N.json.tmp``  [RISK-004 staging]
        4. ``os.fsync()`` → force kernel buffers → physical disk  [RISK-004]
        5. ``os.replace(tmp → final)`` → atomic OS-level rename  [RISK-004]
        6. Atomically overwrite ``latest.json``  [RISK-005 index update]
        7. Apply retention policy  [RISK-007]
        8. Release lock

        Parameters
        ----------
        session : SessionState
            A fully populated NALA session state to persist.

        Returns
        -------
        Path
            The absolute path of the written checkpoint file.

        Raises
        ------
        CheckpointWriteError
            If any OS-level error occurs during the write.
        CheckpointLockError
            If the per-session lock cannot be acquired within ``lock_timeout``.
        """
        # ── Step 1: Resolve session directory and acquire lock ───────────────
        session_dir : Path = self._get_session_dir(session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        with self._session_lock(session.session_id, session_dir):
            # ── Step 2: Serialize + increment LSN + compute hash inside lock ──
            final_json : str = session.prepare_checkpoint()
            lsn        : int = session.checkpoint_meta.lsn

            filename    : str  = _lsn_to_filename(lsn)
            final_path  : Path = session_dir / filename
            tmp_path    : Path = session_dir / (filename + _TMP_SUFFIX)

            logger.debug(
                "write_checkpoint | session=%s... | LSN=%d | target=%s",
                session.session_id[:8], lsn, final_path.name,
            )

            try:
                # ── RISK-004: Atomic write via .tmp staging ───────────────
                self._atomic_write(tmp_path, final_path, final_json)

                # ── RISK-005: Update latest.json index atomically ─────────
                index = _LatestIndex(
                    lsn=lsn,
                    file=filename,
                    timestamp=session.checkpoint_meta.timestamp.isoformat(),
                )
                self._write_latest_index(session_dir, index)

                # ── RISK-007: Apply retention policy ─────────────────────
                self._apply_retention(session.session_id, session_dir)

            except CheckpointWriteError:
                # Re-raise without wrapping (already the right type)
                raise
            except OSError as exc:
                raise CheckpointWriteError(
                    f"OS error writing checkpoint for session "
                    f"'{session.session_id[:8]}...' at LSN={lsn}: {exc}"
                ) from exc

        logger.info(
            "✅ Checkpoint written | session=%s... | LSN=%d | file=%s",
            session.session_id[:8], lsn, filename,
        )
        return final_path

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API — Read
    # ──────────────────────────────────────────────────────────────────────────

    def load_checkpoint(
        self,
        session_id : str,
        lsn        : Optional[int] = None,
    ) -> SessionState:
        """
        Load and integrity-verify a checkpoint with three-tier fallback recovery.

        Recovery Tier Chain (JIRA-002 Plan §6.2)
        ------------------------------------------
        Tier 1 (direct): If ``lsn`` is specified → load that exact LSN file.
        Tier 2 (index) : If ``lsn=None`` → read latest.json → resolve LSN.
        Tier 3 (scan)  : If latest.json is missing/corrupt → scan dir for max LSN.
        Tier 4 (tmp)   : If no .json files → scan for .tmp files (ultra-fallback).

        After resolving the file, SHA-256 integrity is verified (RISK-006).
        On integrity failure, automatically retries LSN-1, LSN-2, up to
        ``rollback_attempts`` times before raising ``CheckpointRecoveryError``.

        Parameters
        ----------
        session_id : str
            The UUID of the session to recover.
        lsn : int, optional
            If given, load exactly that LSN. If None, load the latest.

        Returns
        -------
        SessionState
            A fully reconstructed, cryptographically verified SessionState.

        Raises
        ------
        CheckpointNotFoundError
            If the session or LSN does not exist on disk.
        CheckpointRecoveryError
            If all checkpoints are corrupted and no valid state can be recovered.
        CheckpointIntegrityError
            If a specific LSN was requested and it fails integrity (no rollback).
        """
        session_dir : Path = self._get_session_dir(session_id)

        if not session_dir.exists():
            raise CheckpointNotFoundError(session_id)

        with self._session_lock(session_id, session_dir):
            if lsn is not None:
                # Direct load — no fallback, but integrity is still checked.
                return self._load_single(session_id, session_dir, lsn, strict=True)

            # Tier 1 / 2 / 3 / 4 resolution → get the best available LSN
            resolved_lsn : int = self._resolve_latest_lsn(session_id, session_dir)

            # Attempt load with auto-rollback on integrity failure (RISK-006)
            return self._load_with_rollback(session_id, session_dir, resolved_lsn)

    def load_latest(self, session_id: str) -> SessionState:
        """
        Shorthand: load the latest checkpoint for a session.

        Identical to ``load_checkpoint(session_id, lsn=None)``.
        Uses the full three-tier fallback chain and SHA-256 auto-rollback.

        Parameters
        ----------
        session_id : str
            The UUID of the session to recover.

        Returns
        -------
        SessionState
            The most recent verified SessionState.
        """
        return self.load_checkpoint(session_id, lsn=None)

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API — Inspection
    # ──────────────────────────────────────────────────────────────────────────

    def list_checkpoints(self, session_id: str) -> List[CheckpointRecord]:
        """
        Return a chronologically sorted list of CheckpointRecord objects
        for all persisted checkpoints in a session.

        Records are sorted by LSN ascending (oldest first).  Callers can use
        this for audit dashboards, forensic analysis, and usage monitoring.

        Each record is built from the on-disk file metadata (size, name) and
        the subset of JSON fields extracted via partial parse — NOT full
        deserialization.

        Parameters
        ----------
        session_id : str
            The UUID of the session to inspect.

        Returns
        -------
        list[CheckpointRecord]
            Sorted list of checkpoint records, LSN ascending. Empty if none exist.
        """
        session_dir : Path = self._get_session_dir(session_id)
        if not session_dir.exists():
            return []

        records : List[CheckpointRecord] = []
        for file_path in self._iter_checkpoint_files(session_dir):
            lsn = _filename_to_lsn(file_path.name)
            if lsn is None:
                continue
            record = self._build_record(session_id, file_path, lsn)
            if record is not None:
                records.append(record)

        records.sort()   # CheckpointRecord.__lt__ compares by LSN
        logger.debug(
            "list_checkpoints | session=%s... | count=%d",
            session_id[:8], len(records),
        )
        return records

    def session_exists(self, session_id: str) -> bool:
        """
        Return True if at least one checkpoint file exists for the session.

        This is a fast existence check — it does NOT load or verify any data.

        Parameters
        ----------
        session_id : str
            The UUID of the session to check.

        Returns
        -------
        bool
            True if any checkpoint file exists. False otherwise.
        """
        session_dir : Path = self._get_session_dir(session_id)
        if not session_dir.exists():
            return False
        return any(self._iter_checkpoint_files(session_dir))

    def get_latest_lsn(self, session_id: str) -> Optional[int]:
        """
        Return the latest LSN for a session without loading the full checkpoint.

        Reads latest.json first (Tier 1), falls back to directory scan (Tier 2).
        Returns None if no checkpoints exist.

        Parameters
        ----------
        session_id : str
            The UUID of the session.

        Returns
        -------
        int | None
            The highest known LSN, or None if no checkpoints exist.
        """
        session_dir : Path = self._get_session_dir(session_id)
        if not session_dir.exists():
            return None
        try:
            return self._resolve_latest_lsn(session_id, session_dir)
        except CheckpointNotFoundError:
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API — Deletion
    # ──────────────────────────────────────────────────────────────────────────

    def delete_checkpoint(self, session_id: str, lsn: int) -> bool:
        """
        Delete a specific LSN checkpoint file from disk.

        Note: This does NOT automatically update latest.json.  If you delete
        the latest LSN, the fallback chain (Tier 3 dir scan) will still find
        the correct new latest on the next load.

        Parameters
        ----------
        session_id : str    The session UUID.
        lsn        : int    The LSN of the checkpoint to delete.

        Returns
        -------
        bool
            True if the file was found and deleted. False if not found.
        """
        session_dir : Path = self._get_session_dir(session_id)
        file_path   : Path = session_dir / _lsn_to_filename(lsn)

        if not file_path.exists():
            logger.warning(
                "delete_checkpoint | NOT FOUND | session=%s... | LSN=%d",
                session_id[:8], lsn,
            )
            return False

        with self._session_lock(session_id, session_dir):
            file_path.unlink()
            logger.info(
                "🗑  Checkpoint deleted | session=%s... | LSN=%d",
                session_id[:8], lsn,
            )
        return True

    def purge_session(self, session_id: str) -> int:
        """
        Delete ALL checkpoint files and index files for a session.
        The session directory itself is also removed if empty.

        WARNING: This is irreversible.  NALA cannot recover a purged session.

        Parameters
        ----------
        session_id : str    The session UUID to purge entirely.

        Returns
        -------
        int
            The number of files that were deleted (including latest.json).
        """
        session_dir : Path = self._get_session_dir(session_id)
        if not session_dir.exists():
            logger.warning(
                "purge_session | session dir not found | session=%s...",
                session_id[:8],
            )
            return 0

        count : int = 0
        with self._session_lock(session_id, session_dir):
            for item in list(session_dir.iterdir()):
                if item.name == _LOCK_FILENAME:
                    continue  # Don't delete the lock file we're holding
                try:
                    item.unlink()
                    count += 1
                    logger.debug("  purge_session | deleted: %s", item.name)
                except OSError as exc:
                    logger.warning(
                        "purge_session | failed to delete %s: %s", item.name, exc
                    )

        # Attempt to remove the now-empty directory
        try:
            session_dir.rmdir()
            logger.info(
                "🗑  Session purged | session=%s... | %d file(s) deleted",
                session_id[:8], count,
            )
        except OSError:
            # Directory not empty (e.g. lock file still present) — acceptable
            logger.debug(
                "purge_session | dir not removed (may contain lock file): %s",
                session_dir,
            )
        return count

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Locking (RISK-008)
    # ──────────────────────────────────────────────────────────────────────────

    def _get_python_lock(self, session_id: str) -> threading.Lock:
        """
        Return (or create) the per-session Python threading.Lock.

        This is the first lock layer — fast, in-process, prevents two threads
        in the same Python interpreter from entering the critical section.
        """
        with CheckpointManager._python_locks_mutex:
            if session_id not in CheckpointManager._python_locks:
                CheckpointManager._python_locks[session_id] = threading.Lock()
            return CheckpointManager._python_locks[session_id]

    def _session_lock(self, session_id: str, session_dir: Path):
        """
        Context manager that acquires a two-layer lock for a session:

        Layer 1: Python threading.Lock (in-process, fast)
        Layer 2: OS-level filelock via filelock library (cross-process, RISK-008)

        Usage::

            with self._session_lock(session_id, session_dir):
                # Critical section — fully serialized across threads + processes
                ...
        """
        return _TwoLayerLock(
            python_lock=self._get_python_lock(session_id),
            lock_file=session_dir / _LOCK_FILENAME if _FILELOCK_AVAILABLE else None,
            lock_timeout=self.lock_timeout,
            session_id=session_id,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Atomic Write (RISK-004)
    # ──────────────────────────────────────────────────────────────────────────

    def _atomic_write(
        self,
        tmp_path   : Path,
        final_path : Path,
        content    : str,
    ) -> None:
        """
        Write ``content`` to ``final_path`` atomically via a .tmp staging file.

        Algorithm
        ---------
        1. Write content to ``tmp_path`` (a .tmp staging file).
        2. Call ``os.fsync()`` on the file's file descriptor.  This forces
           the OS to flush all kernel write buffers to the physical storage
           device.  Without this, a crash can leave the data in the OS page
           cache but not on disk.
        3. ``os.replace(tmp_path, final_path)`` performs an atomic OS-level
           rename.  On POSIX systems this calls ``rename(2)`` which is
           guaranteed atomic on the same filesystem.  On Windows this calls
           ``MoveFileExW(MOVEFILE_REPLACE_EXISTING)`` which is effectively
           atomic on the same volume.
        4. The final file is EITHER fully present or absent — never partial.

        Risk mitigated: RISK-004 — Half-Written File on process crash.

        Raises
        ------
        CheckpointWriteError
            On any OS-level error during staging, fsync, or rename.
        """
        try:
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as fh:
                fh.write(content)
                fh.flush()
                os.fsync(fh.fileno())  # Force kernel buffer → physical disk
            os.replace(tmp_path, final_path)  # Atomic OS rename
        except OSError as exc:
            # Clean up the .tmp file if anything went wrong
            _safe_unlink(tmp_path)
            raise CheckpointWriteError(
                f"Atomic write failed for '{final_path.name}': {exc}"
            ) from exc

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — latest.json (RISK-005)
    # ──────────────────────────────────────────────────────────────────────────

    def _write_latest_index(self, session_dir: Path, index: _LatestIndex) -> None:
        """
        Atomically overwrite ``latest.json`` with the new index.

        latest.json is itself written via .tmp → os.replace to prevent
        corruption if the process crashes mid-write (mitigates RISK-005).
        """
        latest_path  : Path = session_dir / _LATEST_FILENAME
        tmp_path     : Path = session_dir / (_LATEST_FILENAME + _TMP_SUFFIX)
        self._atomic_write(tmp_path, latest_path, index.to_json())

    def _read_latest_index(self, session_dir: Path) -> Optional[_LatestIndex]:
        """
        Read and parse ``latest.json``.  Returns None on any failure (missing
        file, corrupt JSON, missing keys) — the caller uses the fallback chain.
        """
        latest_path : Path = session_dir / _LATEST_FILENAME
        if not latest_path.exists():
            return None
        try:
            raw = latest_path.read_text(encoding="utf-8")
            return _LatestIndex.from_json(raw)
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            logger.warning(
                "latest.json is corrupt or unreadable (%s). "
                "Falling back to directory scan (Tier 3).", exc,
            )
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — LSN Resolution (Fallback Chain)
    # ──────────────────────────────────────────────────────────────────────────

    def _resolve_latest_lsn(
        self,
        session_id  : str,
        session_dir : Path,
    ) -> int:
        """
        Determine the most recent LSN using the three-tier fallback chain.

        Tier 1: Read latest.json → return its lsn field (happy path, O(1))
        Tier 2: Scan directory for checkpoint_LSN_*.json → return max LSN
        Tier 3: Scan directory for .tmp files → return max LSN from .tmp names
                (used when a crash happened between the write and the rename)

        Raises
        ------
        CheckpointNotFoundError
            If no checkpoint or .tmp file is found by any tier.
        """
        # ── Tier 1: latest.json index ──────────────────────────────────────
        index = self._read_latest_index(session_dir)
        if index is not None:
            candidate = session_dir / index.file
            if candidate.exists():
                logger.debug("Recovery Tier 1: latest.json → LSN=%d", index.lsn)
                return index.lsn
            logger.warning(
                "latest.json points to '%s' but file is MISSING. "
                "Falling back to Tier 2 directory scan.", index.file,
            )

        # ── Tier 2: Directory scan for fully written .json files ──────────
        lsns : List[int] = [
            _filename_to_lsn(p.name)                                   # type: ignore[misc]
            for p in self._iter_checkpoint_files(session_dir)
            if _filename_to_lsn(p.name) is not None
        ]
        if lsns:
            best = max(lsns)
            logger.warning(
                "Recovery Tier 2: directory scan → max LSN=%d", best
            )
            return best

        # ── Tier 3: Scan .tmp files (ultra-fallback) ──────────────────────
        tmp_lsns : List[int] = [
            _filename_to_lsn(p.name.replace(_TMP_SUFFIX, ""))          # type: ignore[misc]
            for p in session_dir.glob(f"*{_TMP_SUFFIX}")
            if _filename_to_lsn(p.name.replace(_TMP_SUFFIX, "")) is not None
        ]
        if tmp_lsns:
            best_tmp = max(tmp_lsns)
            logger.warning(
                "Recovery Tier 3: .tmp file scan → max LSN=%d (crash mid-write?)",
                best_tmp,
            )
            return best_tmp

        # All tiers exhausted
        raise CheckpointNotFoundError(session_id)

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Load + Integrity + Rollback (RISK-006)
    # ──────────────────────────────────────────────────────────────────────────

    def _load_single(
        self,
        session_id  : str,
        session_dir : Path,
        lsn         : int,
        strict      : bool = False,
    ) -> SessionState:
        """
        Load and deserialize a single checkpoint by LSN, then verify SHA-256.

        Parameters
        ----------
        session_id  : str   The session UUID.
        session_dir : Path  The session-level checkpoint directory.
        lsn         : int   The LSN to load.
        strict      : bool  If True, raise CheckpointIntegrityError immediately
                            on hash failure (no auto-rollback).  Used when the
                            caller explicitly requested a specific LSN.

        Returns
        -------
        SessionState

        Raises
        ------
        CheckpointNotFoundError     If the file does not exist.
        CheckpointIntegrityError    On hash failure when strict=True.
        """
        file_path : Path = session_dir / _lsn_to_filename(lsn)

        if not file_path.exists():
            # Try .tmp as last resort (crash between write and rename)
            tmp_path = session_dir / (_lsn_to_filename(lsn) + _TMP_SUFFIX)
            if tmp_path.exists():
                logger.warning(
                    "Checkpoint file not found but .tmp exists for LSN=%d. "
                    "Loading from .tmp (crash recovery).", lsn,
                )
                file_path = tmp_path
            else:
                raise CheckpointNotFoundError(session_id, lsn)

        try:
            raw_json : str = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise CheckpointNotFoundError(session_id, lsn) from exc

        try:
            session : SessionState = SessionState.deserialize(raw_json)
        except Exception as exc:
            raise CheckpointIntegrityError(
                session_id, lsn,
                detail=f"JSON deserialization failed: {exc}",
            ) from exc

        # ── RISK-006: SHA-256 Integrity Verification ──────────────────────
        if not session.verify_integrity(raw_json):
            if strict:
                raise CheckpointIntegrityError(session_id, lsn)
            raise CheckpointIntegrityError(
                session_id, lsn,
                detail="Hash mismatch — triggering auto-rollback.",
            )

        logger.debug(
            "✅ Checkpoint loaded | session=%s... | LSN=%d | file=%s",
            session_id[:8], lsn, file_path.name,
        )
        return session

    def _load_with_rollback(
        self,
        session_id  : str,
        session_dir : Path,
        start_lsn   : int,
    ) -> SessionState:
        """
        Attempt to load from ``start_lsn``, rolling back to LSN-1, LSN-2, ...
        on each integrity failure, up to ``self.rollback_attempts`` tries.

        Risk mitigated: RISK-006 — Silent Disk Corruption auto-rollback.

        Raises
        ------
        CheckpointRecoveryError
            When all rollback attempts are exhausted.
        """
        current_lsn : int = start_lsn

        for attempt in range(1, self.rollback_attempts + 2):
            if current_lsn < 1:
                break
            try:
                session = self._load_single(
                    session_id, session_dir, current_lsn, strict=False
                )
                if attempt > 1:
                    logger.warning(
                        "⚠️  Recovered from rollback | session=%s... | "
                        "failed_lsn=%d → recovered_lsn=%d",
                        session_id[:8], start_lsn, current_lsn,
                    )
                return session

            except CheckpointIntegrityError as exc:
                logger.error(
                    "INTEGRITY FAILURE at LSN=%d (attempt %d/%d). "
                    "Rolling back to LSN=%d. Detail: %s",
                    current_lsn, attempt, self.rollback_attempts + 1,
                    current_lsn - 1, exc,
                )
                current_lsn -= 1

            except CheckpointNotFoundError:
                # This LSN doesn't exist — try the next lower one
                logger.warning(
                    "LSN=%d not found during rollback. Trying LSN=%d.",
                    current_lsn, current_lsn - 1,
                )
                current_lsn -= 1

        raise CheckpointRecoveryError(
            session_id=session_id,
            attempts_tried=self.rollback_attempts + 1,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Retention Policy (RISK-007)
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_retention(self, session_id: str, session_dir: Path) -> None:
        """
        Apply the configured retention policy to prune old checkpoint files.

        Sliding Window Logic
        ---------------------
        1. Collect all checkpoint files sorted by LSN ascending.
        2. Always keep LSN=1 (genesis) regardless of any other rule.
        3. Keep the last ``max_checkpoints`` files in the sorted list.
        4. Delete everything else.

        Risk mitigated: RISK-007 — Unbounded Disk Growth.
        """
        if self.retention_policy == "all":
            return  # No pruning — caller wants full history

        all_files : List[Tuple[int, Path]] = sorted(
            (
                (_filename_to_lsn(p.name), p)                   # type: ignore[misc]
                for p in self._iter_checkpoint_files(session_dir)
                if _filename_to_lsn(p.name) is not None
            ),
            key=lambda t: t[0],
        )

        if len(all_files) <= self.max_checkpoints:
            return  # Within budget — nothing to do

        # Separate genesis from the rest
        genesis_entry = next((e for e in all_files if e[0] == 1), None)
        non_genesis   = [e for e in all_files if e[0] != 1]

        # Keep the last max_checkpoints entries from non-genesis
        keep_count    = self.max_checkpoints - (1 if genesis_entry else 0)
        to_keep_lsns  = {e[0] for e in non_genesis[-keep_count:]}
        if genesis_entry:
            to_keep_lsns.add(1)  # Always keep genesis

        deleted_count = 0
        for lsn, path in all_files:
            if lsn not in to_keep_lsns:
                _safe_unlink(path)
                deleted_count += 1
                logger.debug(
                    "🗑  Retention purge | session=%s... | LSN=%d | file=%s",
                    session_id[:8], lsn, path.name,
                )

        if deleted_count > 0:
            logger.info(
                "Retention policy applied | session=%s... | "
                "deleted=%d | remaining=%d",
                session_id[:8], deleted_count, len(all_files) - deleted_count,
            )

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Record Builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_record(
        self,
        session_id : str,
        file_path  : Path,
        lsn        : int,
    ) -> Optional[CheckpointRecord]:
        """
        Build a ``CheckpointRecord`` from a checkpoint file path.

        Uses partial JSON parsing to extract only the fields needed for the
        record — avoids full Pydantic deserialization for performance.

        Returns None if the file cannot be read or parsed.
        """
        try:
            raw      : str          = file_path.read_text(encoding="utf-8")
            data     : dict         = json.loads(raw)
            meta     : dict         = data.get("checkpoint_meta", {})
            ts_raw   : str          = meta.get("timestamp", "")
            chk_hash : str          = meta.get("content_hash", "")
            version  : str          = data.get("version", _SCHEMA_VERSION)
            stat_size: int          = file_path.stat().st_size

            # Parse the UTC timestamp
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc)

            return CheckpointRecord(
                session_id=session_id,
                lsn=lsn,
                timestamp=ts,
                file_path=file_path,
                file_size_bytes=stat_size,
                content_hash=chk_hash,
                is_verified=False,   # Record built without loading — not verified
                schema_version=version,
            )
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "_build_record | failed for %s: %s", file_path.name, exc
            )
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL — Filesystem Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_session_dir(self, session_id: str) -> Path:
        """Return the path to the per-session checkpoint directory."""
        return self.base_dir / session_id

    def _iter_checkpoint_files(self, session_dir: Path) -> Iterator[Path]:
        """
        Iterate over all fully-written checkpoint JSON files in a session dir.

        Excludes: latest.json, .tmp files, .lock files, and any other files
        that do not match the canonical ``checkpoint_LSN_XXXXXX.json`` pattern.
        """
        for path in sorted(session_dir.iterdir()):
            if path.is_file() and _LSN_FILENAME_RE.match(path.name):
                yield path

    def __repr__(self) -> str:
        return (
            f"CheckpointManager("
            f"base_dir={self.base_dir!r}, "
            f"max_checkpoints={self.max_checkpoints}, "
            f"policy={self.retention_policy!r}"
            f")"
        )


# ==============================================================================
# SECTION 5 — _TwoLayerLock Context Manager (RISK-008)
# ==============================================================================

class _TwoLayerLock:
    """
    Internal context manager that acquires a two-layer concurrent lock:

    Layer 1: Python ``threading.Lock``
        Fast, in-process lock.  Serializes all writes from multiple threads
        in the same Python interpreter.

    Layer 2: OS-level ``FileLock`` (from the ``filelock`` library)
        Cross-process lock.  Serializes writes from multiple Python processes
        (e.g. spawned subprocess, separate NALA instance) writing to the
        same session directory.

    If ``filelock`` is not installed, Layer 2 is skipped (with a logged warning).
    Layer 1 alone is sufficient for single-process multi-thread use cases.

    Risk mitigated: RISK-008 — Concurrent Write Race Conditions.
    """

    def __init__(
        self,
        python_lock  : threading.Lock,
        lock_file    : Optional[Path],
        lock_timeout : float,
        session_id   : str,
    ) -> None:
        self._python_lock  = python_lock
        self._lock_file    = lock_file
        self._lock_timeout = lock_timeout
        self._session_id   = session_id
        self._file_lock    = None

    def __enter__(self) -> "_TwoLayerLock":
        # Layer 1: Python threading lock (acquire with timeout via spin-wait)
        acquired = self._python_lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            raise CheckpointLockError(self._session_id, self._lock_timeout)

        # Layer 2: OS advisory filelock (only if filelock is installed)
        if _FILELOCK_AVAILABLE and self._lock_file is not None:
            self._lock_file.parent.mkdir(parents=True, exist_ok=True)
            self._file_lock = FileLock(str(self._lock_file))
            try:
                self._file_lock.acquire(timeout=self._lock_timeout)
            except FileLockTimeout as exc:
                self._python_lock.release()
                raise CheckpointLockError(
                    self._session_id, self._lock_timeout
                ) from exc

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Release in reverse order
        if self._file_lock is not None:
            try:
                self._file_lock.release()
            except Exception:  # noqa: BLE001
                pass
        try:
            self._python_lock.release()
        except RuntimeError:
            pass  # Already released (edge case)


# ==============================================================================
# SECTION 6 — Module-Level Pure Functions
# ==============================================================================

def _lsn_to_filename(lsn: int) -> str:
    """
    Convert an integer LSN to the zero-padded canonical checkpoint filename.

    Example
    -------
    >>> _lsn_to_filename(42)
    'checkpoint_LSN_000042.json'
    >>> _lsn_to_filename(1000000)
    'checkpoint_LSN_1000000.json'
    """
    return f"checkpoint_LSN_{lsn:0{_LSN_ZERO_PAD}d}.json"


def _filename_to_lsn(filename: str) -> Optional[int]:
    """
    Extract the integer LSN from a canonical checkpoint filename.

    Returns None if the filename does not match the expected pattern.

    Example
    -------
    >>> _filename_to_lsn('checkpoint_LSN_000042.json')
    42
    >>> _filename_to_lsn('latest.json')
    None
    """
    m = _LSN_FILENAME_RE.match(filename)
    return int(m.group(1)) if m else None


def _safe_unlink(path: Path) -> None:
    """
    Delete a file if it exists, silently ignoring FileNotFoundError.
    All other OS errors are logged as warnings but not re-raised.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("_safe_unlink | could not delete '%s': %s", path, exc)


# ==============================================================================
# SECTION 7 — Module-level __all__ export
# ==============================================================================

__all__ = [
    # Core engine
    "CheckpointManager",
    # Data models
    "CheckpointRecord",
    # Exception hierarchy
    "CheckpointError",
    "CheckpointNotFoundError",
    "CheckpointIntegrityError",
    "CheckpointWriteError",
    "CheckpointRecoveryError",
    "CheckpointLockError",
    # Utility functions (useful for tests and tooling)
    "_lsn_to_filename",
    "_filename_to_lsn",
]
"""
================================================================================
Jai Bajrang Bali 🙏
Nexus Lab AI Research Lab, Bengaluru
================================================================================
"""
