"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/long_running/_soak_chaos.py
Ticket  : JIRA-007-B — Advanced Soak Orchestrator (Addition 2: Chaos Injection)
Sections: JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md §4
          (Multi-Failure Chaos Injection)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 1.0.0

PURPOSE
-------
The base JIRA-007 soak test only kills the Executor process (SIGKILL). A real
1-month deployment also faces **disk corruption / bit-rot** — a checkpoint
file with a flipped byte. ``ChaosInjector`` deliberately corrupts a real,
on-disk checkpoint file's numeric content once per soak run, forcing
``CheckpointManager``'s SHA-256 integrity guard and automatic LSN rollback
chain (JIRA-002/005) to fire for real under soak conditions — not just in an
isolated unit test.

KEY DESIGN DECISIONS (beyond the bare ticket spec)
---------------------------------------------------
1. CALLED ONLY FROM THE TEST ORCHESTRATOR, BETWEEN GENERATIONS.
   This class exposes no scheduling/threading of its own — the caller
   (``test_soak_1hr.py``'s own orchestration loop, per §9 of the plan) is
   responsible for invoking ``maybe_corrupt_latest_checkpoint()`` only in the
   gap between one Executor subprocess exiting and the next one being
   spawned. This guarantees the target checkpoint file is never being
   actively written by a live process at the moment it is corrupted —
   avoiding any write race entirely by construction, rather than by locking.

2. FILE DISCOVERY MIRRORS ``CheckpointManager``'S OWN TWO-TIER FALLBACK,
   WITHOUT IMPORTING IT. ``core.harness.checkpoint`` pulls in ``filelock``,
   full ``SessionState`` deserialization, and other production-weight
   dependencies that a lightweight test-harness chaos utility does not need.
   Instead, ``_locate_latest_checkpoint_file()`` re-implements the exact same
   ``latest.json`` fast-index (Tier 1) → directory-scan-for-max-LSN (Tier 2)
   resolution using the identical filename conventions
   (``checkpoint_LSN_NNNNNN.json``, ``latest.json``) that production code
   uses — genuinely compatible with what is actually on disk, with zero
   runtime dependency on the production module itself. This mirrors the same
   dependency-isolation philosophy already used in ``_soak_supervisor.py``
   (which reads handoff spores as raw JSON rather than via
   ``HandoffSporeModel`` for the identical reason).

3. THE HASH IS SELF-REFERENTIAL AND CANONICAL — SO *ANY* BARE-INTEGER FIELD
   IS A VALID CORRUPTION TARGET. ``checkpoint.py``'s ``_fixed_verify_hash()``
   re-parses the raw JSON, nulls only ``checkpoint_meta.content_hash``, then
   re-serializes with ``sort_keys=True`` before recomputing the SHA-256. This
   means flipping ANY OTHER numeric field anywhere in the file — not just
   inside ``checkpoint_meta`` — is guaranteed to invalidate the hash on
   reload, regardless of the file's on-disk formatting/indentation. A
   prioritized list of semantically meaningful fields (``lsn``,
   ``total_tokens_in``, ``total_tokens_out``, ``error_count``) is tried
   first for a deterministic, easily-explained corruption; an unprioritized
   fallback matches ANY bare integer field if none of those are present.

4. THE ARMED FLAG IS SET **AFTER** A SUCCESSFUL WRITE, NOT BEFORE.
   Unlike ``SoakSupervisor``'s SIGKILL injector (which arms its flag
   synchronously, before a background thread even starts, to close a
   multi-threaded race window), this class is only ever called synchronously
   from a single-threaded orchestration loop — there is no concurrent-call
   race to guard against. Setting ``self._corrupted = True`` only after a
   successful write means a transient I/O failure on one attempt does not
   permanently forfeit the soak run's only chaos-corruption exercise; the
   orchestrator may safely retry on the next generation boundary that still
   falls inside the corruption window.

5. A ROUND-TRIP ``json.loads()`` VALIDATES THE CORRUPTED TEXT BEFORE IT IS
   EVER WRITTEN TO DISK. A future change to the targeting regex could, in
   principle, introduce an edge case that breaks JSON syntax. Parsing the
   corrupted text back before persisting it converts any such regression
   into a clean, logged skip for this cycle rather than writing a
   genuinely-unparseable file to disk (which would test an entirely
   different — and unintended — failure mode: total file corruption, not
   the intended "one flipped digit, still valid JSON" bit-rot simulation).

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import ClassVar, Optional, Tuple

_logger = logging.getLogger("nala.soak.chaos")


# ==============================================================================
# ChaosInjector
# ==============================================================================

class ChaosInjector:
    """
    Fires AT MOST ONE checkpoint-corruption event per soak run, at any
    generation boundary whose elapsed time falls inside
    ``[CORRUPTION_WINDOW_START_S, CORRUPTION_WINDOW_END_S]``.

    This window (minutes 12–18) is deliberately placed BEFORE the base
    JIRA-007 SIGKILL window (minutes 20–45, in ``SoakSupervisor``), so that if
    the run aborts, log analysis can cleanly attribute the failure to one
    chaos mode or the other without ambiguity about which fired first.

    Constants
    ---------
    CORRUPTION_WINDOW_START_S : Earliest elapsed-time offset (seconds) at
                                which corruption may fire (720s = 12 min).
    CORRUPTION_WINDOW_END_S   : Latest elapsed-time offset (seconds) for the
                                corruption window (1080s = 18 min).
    """

    CORRUPTION_WINDOW_START_S: int = 720    # 12 minutes
    CORRUPTION_WINDOW_END_S:   int = 1080   # 18 minutes

    # Filename conventions — mirrored exactly from core.harness.checkpoint
    # (module docstring, design decision #2). Kept as local constants rather
    # than imported to preserve this module's lightweight dependency profile.
    _LSN_FILENAME_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"^checkpoint_LSN_(\d{6,})\.json$"
    )
    _LATEST_FILENAME: ClassVar[str] = "latest.json"

    # Semantically meaningful integer fields tried first, in priority order,
    # for a deterministic and easily-explained corruption target (module
    # docstring, design decision #3). Deliberately excludes any float field
    # (e.g. "estimated_cost") — the targeting regex itself also structurally
    # excludes floats via a negative lookahead, but listing only true integer
    # counters here keeps the *preferred* path self-documenting.
    _PREFERRED_CORRUPTION_KEYS: ClassVar[Tuple[str, ...]] = (
        "lsn",
        "total_tokens_in",
        "total_tokens_out",
        "error_count",
    )

    # Fallback pattern matching ANY bare (unquoted) integer JSON value.
    # Cannot ever match `"content_hash": "a1b2c3..."` — hash values are
    # always quoted hex strings, never unquoted digit sequences — so the
    # embedded hash itself is structurally unreachable by this regex.
    # The `(?!\.\d)` negative lookahead excludes the integer PART of a float
    # (e.g. the `0` in `"estimated_cost": 0.0006`), since incrementing only
    # the pre-decimal digits of a float is not a genuine bare-integer flip.
    _GENERIC_INT_FIELD_RE: ClassVar[re.Pattern[str]] = re.compile(
        r'"(\w+)"\s*:\s*(\d+)(?!\.\d)'
    )

    def __init__(self) -> None:
        """
        Initialize a fresh injector. ``_corrupted`` guarantees at most one
        corruption event fires across the ENTIRE lifetime of this instance —
        callers should construct exactly one ``ChaosInjector`` per soak run.
        """
        self._corrupted: bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def has_corrupted(self) -> bool:
        """Whether this instance has already injected its one corruption event."""
        return self._corrupted

    def reset(self) -> None:
        """
        Re-arm the injector for a fresh soak run. Only relevant if a single
        ``ChaosInjector`` instance is deliberately reused across multiple
        separate test invocations within one process — a normal single soak
        run should never need to call this.
        """
        self._corrupted = False

    def maybe_corrupt_latest_checkpoint(
        self,
        checkpoint_base_dir: Path,
        session_id:           str,
        elapsed_s:            float,
    ) -> Optional[Path]:
        """
        Corrupt the latest checkpoint file for ``session_id`` if, and only
        if, ALL of the following hold:

          1. No corruption has fired yet this run (``self._corrupted is False``).
          2. ``elapsed_s`` falls within
             ``[CORRUPTION_WINDOW_START_S, CORRUPTION_WINDOW_END_S]``.
          3. A checkpoint file can actually be located on disk for this session.
          4. The corruption can be applied and the result re-parses as valid JSON.

        Parameters
        ----------
        checkpoint_base_dir : Root checkpoint directory (CheckpointManager.base_dir).
        session_id           : Session whose latest checkpoint will be targeted.
        elapsed_s             : Seconds elapsed since the soak run's own
                                ``run_start_ts`` (NOT since this generation
                                started) — must be measured consistently with
                                how ``SoakSupervisor``'s own SIGKILL window is
                                measured, so the two chaos windows stay
                                correctly ordered relative to each other.

        Returns
        -------
        Optional[Path]
            The path of the checkpoint file that was corrupted, or ``None``
            if no corruption was injected this call (outside the window,
            already fired, no checkpoint found, or the corruption attempt
            itself failed and was safely skipped).
        """
        if self._corrupted:
            return None

        if not (self.CORRUPTION_WINDOW_START_S <= elapsed_s <= self.CORRUPTION_WINDOW_END_S):
            return None

        session_dir = checkpoint_base_dir / session_id
        target_path = self._locate_latest_checkpoint_file(session_dir)

        if target_path is None:
            _logger.info(
                "[ChaosInjector] elapsed_s=%.1f is inside the corruption "
                "window but no checkpoint file was found for session '%s' "
                "under '%s'. Will retry on the next generation boundary "
                "still inside the window.",
                elapsed_s, session_id, session_dir,
            )
            return None

        try:
            raw_text = target_path.read_text(encoding="utf-8")
            corrupted_text = self._flip_one_numeric_value(raw_text)
            # Defensive round-trip validation (module docstring, design
            # decision #5) — never persist a result that fails to re-parse.
            json.loads(corrupted_text)
            target_path.write_text(corrupted_text, encoding="utf-8")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            _logger.error(
                "[ChaosInjector] Failed to corrupt '%s': %s. Skipping this "
                "injection attempt; will retry on the next generation "
                "boundary still inside the window (self._corrupted remains "
                "False — module docstring, design decision #4).",
                target_path, exc,
            )
            return None

        self._corrupted = True
        _logger.warning(
            "[ChaosInjector] 🧨 Checkpoint corruption INJECTED. "
            "session_id=%s | path=%s | elapsed_s=%.1f",
            session_id, target_path, elapsed_s,
        )
        return target_path

    # ── Corruption mechanic ──────────────────────────────────────────────────

    def _flip_one_numeric_value(self, raw_json_text: str) -> str:
        """
        Locate a numeric value assigned to a key inside ``raw_json_text``
        and increment it by 1, returning the modified text.

        Tries ``_PREFERRED_CORRUPTION_KEYS`` in order first, for a
        deterministic and semantically meaningful target (e.g.
        ``"lsn": 4`` → ``"lsn": 5``). Falls back to matching ANY bare
        integer field if none of the preferred keys are present in this
        particular JSON payload.

        The targeting regex requires an unquoted digit sequence immediately
        following ``"key":`` — this can never match a quoted string value
        (such as ``content_hash``'s hex digest, or any timestamp string),
        and a trailing negative lookahead excludes matching only the
        integer portion of a float value. JSON structural characters
        (commas, braces, quotation marks) are never touched — only the
        digit characters captured by the regex are replaced.

        Parameters
        ----------
        raw_json_text : The full, unmodified text content of the checkpoint
                        file, exactly as read from disk.

        Returns
        -------
        str
            The text with exactly one integer value incremented by 1.

        Raises
        ------
        ValueError
            If no corruptible bare-integer field can be found anywhere in
            ``raw_json_text`` — this would indicate a checkpoint schema that
            no longer matches any expected shape, and corruption should not
            silently no-op.
        """
        for key in self._PREFERRED_CORRUPTION_KEYS:
            pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*(\d+)(?!\.\d)')
            match = pattern.search(raw_json_text)
            if match is not None:
                return self._splice_increment(raw_json_text, match, key, digit_group=1)

        generic_match = self._GENERIC_INT_FIELD_RE.search(raw_json_text)
        if generic_match is None:
            raise ValueError(
                "No corruptible bare-integer field found anywhere in the "
                "checkpoint JSON text — cannot simulate bit-rot corruption "
                "on this file."
            )
        key_name = generic_match.group(1)
        return self._splice_increment(raw_json_text, generic_match, key_name, digit_group=2)

    @staticmethod
    def _splice_increment(
        raw_json_text: str,
        match:          "re.Match[str]",
        key_name:       str,
        digit_group:    int,
    ) -> str:
        """
        Increment the digit substring captured at ``match.group(digit_group)``
        by 1 and splice the result back into ``raw_json_text`` at the exact
        byte offsets of that capture group — leaving every other character
        (including the surrounding key name, colon, whitespace, and every
        JSON structural character) completely untouched.
        """
        old_value = int(match.group(digit_group))
        new_value = old_value + 1
        start, end = match.span(digit_group)
        corrupted = raw_json_text[:start] + str(new_value) + raw_json_text[end:]

        _logger.debug(
            "[ChaosInjector] Flipped '%s': %d -> %d (byte offset %d).",
            key_name, old_value, new_value, start,
        )
        return corrupted

    # ── File discovery (mirrors CheckpointManager's own tiering) ────────────

    @staticmethod
    def _locate_latest_checkpoint_file(session_dir: Path) -> Optional[Path]:
        """
        Resolve the highest-LSN checkpoint file for a session, using the
        same two-tier fallback ``CheckpointManager`` itself uses (module
        docstring, design decision #2), without importing it.

        Tier 1 — ``latest.json`` fast index
            Read ``{session_dir}/latest.json``, extract its ``"file"``
            field, and use it directly if that file actually exists.
        Tier 2 — Directory scan
            If Tier 1 is missing, unreadable, malformed, or points at a
            file that no longer exists, scan ``session_dir`` for every file
            matching ``checkpoint_LSN_NNNNNN.json`` and return the one with
            the highest numeric LSN.

        Parameters
        ----------
        session_dir : ``{checkpoint_base_dir}/{session_id}``.

        Returns
        -------
        Optional[Path]
            The resolved checkpoint file path, or ``None`` if the session
            directory does not exist or contains no checkpoint files at all.
        """
        if not session_dir.exists():
            return None

        # ── Tier 1: latest.json fast index ──────────────────────────────────
        latest_index_path = session_dir / ChaosInjector._LATEST_FILENAME
        if latest_index_path.exists():
            try:
                index_data = json.loads(latest_index_path.read_text(encoding="utf-8"))
                candidate = session_dir / str(index_data["file"])
                if candidate.exists():
                    return candidate
                _logger.debug(
                    "[ChaosInjector] latest.json points to '%s', which does "
                    "not exist. Falling back to directory scan.", candidate,
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
                _logger.debug(
                    "[ChaosInjector] latest.json at '%s' is unreadable/"
                    "malformed (%s). Falling back to directory scan.",
                    latest_index_path, exc,
                )

        # ── Tier 2: directory scan for highest LSN ──────────────────────────
        best_path: Optional[Path] = None
        best_lsn: int = -1
        for entry in session_dir.iterdir():
            if not entry.is_file():
                continue
            match = ChaosInjector._LSN_FILENAME_RE.match(entry.name)
            if match is None:
                continue
            lsn = int(match.group(1))
            if lsn > best_lsn:
                best_lsn = lsn
                best_path = entry

        return best_path


__all__ = [
    "ChaosInjector",
]
