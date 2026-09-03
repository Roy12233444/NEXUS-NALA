"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : core/harness/context_tracker.py
Ticket  : JIRA-004 — Context Window Tracker & Dronagiri Compactor
Phase   : 1 — Core Harness (Survival Foundation)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

PURPOSE
-------
Provides NALA's full context window survival infrastructure:

  1. ContextTracker     — Monitors live token projection via tiktoken.
                          Emits one of four lifecycle statuses:
                          NORMAL → WARNING → COMPACTING → EXHAUSTED
                          based on configurable thresholds in TrackerConfig.
                          Does NOT use StateMatrix.total_tokens (RISK-022).

  2. DronagiriCompactor — Executes a 2-stage compaction pipeline when the
                          projected prompt size crosses the COMPACTING threshold.
                          Stage 1: deterministic 6-pattern regex pruning
                                   (zero LLM cost, zero API calls).
                          Stage 2: LLM-based step crystallization via
                                   Golden Prompt (only if Stage 1 fails).
                          Forces a post-compaction checkpoint after any
                          mutation to disk (RISK-021).

  3. HandoffSpore       — Writes a Pydantic v2-validated JSON spore file
                          when ContextStatus.EXHAUSTED is confirmed and
                          compaction cannot recover the session.
                          The spore is a self-contained bootstrap document:
                          crystallized history, remaining tasks, telemetry,
                          active variables, and bootstrap instructions for
                          a new NALA session to resume seamlessly.

RISK MITIGATIONS EMBEDDED
--------------------------
  RISK-016 — Token count desync:
              +per_message_overhead (default 20) per message; independent
              tiktoken projection never trusts StateMatrix.total_tokens.
  RISK-017 — "Lost in the Middle":
              n_preserve_tail (default 3) tail steps always excluded from
              LLM summarization in Stage 2.
  RISK-018 — Orphaned tool calls:
              _prune_tool_call_pairs_atomically() enforces atomic assistant
              + tool message pair pruning. Never prunes one without the other.
  RISK-019 — Runaway LLM summarization cost:
              Stage 2 is only invoked if Stage 1 was insufficient.
  RISK-020 — Handoff state loss:
              Pydantic v2 model_validate_json() on both write and load.
              Extra fields forbidden (extra="forbid").
  RISK-021 — Mutation without checkpoint:
              _force_checkpoint() called after every compaction mutation.
  RISK-022 — StateMatrix token count desync:
              _project_token_count() uses independent tiktoken; ignores
              StateMatrix.total_tokens entirely.

INTEGRATION POINT
-----------------
  Injected in NalaLoop._execute_loop() per JIRA-004 Section 5.2:
  AFTER the RISK-014 deadlock guard, BEFORE step.mark_running().

  if self.context_tracker is not None:
      ctx_status = self.context_tracker.monitor_context(self.session)
      if ctx_status == ContextStatus.WARNING:
          ...
      elif ctx_status == ContextStatus.COMPACTING:
          success = self.compactor.compact(self.session)
          ...
      if ctx_status == ContextStatus.EXHAUSTED:
          self._save_checkpoint("pre-handoff")
          HandoffSpore.write_spore(self.session, spore_path)
          return LoopStatus.PAUSED

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── third-party ───────────────────────────────────────────────────────────────
import pydantic
import tiktoken
from pydantic import BaseModel, ConfigDict, Field

# ── local ─────────────────────────────────────────────────────────────────────
from core.harness.session_contract import (
    SessionState,
    TaskStatus,
    utcnow,
)

# ── module-level loggers ──────────────────────────────────────────────────────
_logger_tracker   = logging.getLogger("nala.context_tracker")
_logger_compactor = logging.getLogger("nala.dronagiri_compactor")
_logger_handoff   = logging.getLogger("nala.handoff_spore")


# ==============================================================================
# SECTION 0 — Custom Exceptions
# ==============================================================================

# JIRA-006: Extracted to core.harness.session_handoff. Re-exported here for
# backwards compatibility with existing harness components.
from core.harness.session_handoff import (
    ContextExhaustedSignal,
    SporeValidationError,
)


# ==============================================================================
# SECTION 1 — ContextStatus Enum
# ==============================================================================

class ContextStatus(str, Enum):
    """
    Lifecycle state returned by ContextTracker.monitor_context() representing
    the current urgency of context window pressure for the active session.

    Inherits from ``str`` for direct JSON serialization compatibility and for
    use in log messages without explicit .value access.

    States (ordered by urgency, lowest to highest)
    -----------------------------------------------
    NORMAL     — Projected token usage is safely below the warning threshold.
                 No action required.
    WARNING    — Token usage has crossed warning_percent threshold.
                 Log and continue; do NOT pause dispatch.
    COMPACTING — Token usage has crossed compaction_percent threshold.
                 Invoke DronagiriCompactor immediately before dispatch.
    EXHAUSTED  — Token usage has crossed the hard safety ceiling.
                 Write HandoffSpore immediately; do NOT attempt compaction.
    """

    NORMAL     = "NORMAL"
    WARNING    = "WARNING"
    COMPACTING = "COMPACTING"
    EXHAUSTED  = "EXHAUSTED"


# ==============================================================================
# SECTION 2 — TrackerConfig
# ==============================================================================

@dataclass(frozen=True)
class TrackerConfig:
    """
    Immutable, fully-typed configuration for ContextTracker and DronagiriCompactor.

    Using a frozen dataclass guarantees that once a ContextTracker is initialized
    with a given config, its thresholds cannot drift mid-session.

    All threshold properties are derived from the base float fractions, ensuring
    a single source of truth when changing the model's context window size.

    Fields
    ------
    max_context_tokens      : Hard token limit of the target LLM's context window.
    warning_percent         : Fraction of max_context_tokens at which WARNING fires.
                              Default: 0.70 → 89,600 tokens for a 128K model.
    compaction_percent      : Fraction at which DronagiriCompactor is invoked.
                              Default: 0.85 → 108,800 tokens for a 128K model.
    safety_buffer_fraction  : Fraction reserved as a hard ceiling beyond which
                              EXHAUSTED is emitted and HandoffSpore is written.
                              Default: 0.05 → 6,400 token buffer for a 128K model.
    model_encoding          : tiktoken encoding name for the target LLM.
                              Must match the tokenizer of the model making calls.
    n_preserve_tail         : Number of most-recent SUCCESS steps NEVER to
                              summarize in DronagiriCompactor Stage 2. (RISK-017)
    per_message_overhead    : Conservative token overhead added per message-bearing
                              step (RISK-016). OpenAI guideline: 4 tokens/msg minimum;
                              NALA uses 20 for cross-provider safety headroom.

    Computed Properties
    -------------------
    warning_threshold_tokens    → int: absolute token count for WARNING boundary.
    compaction_threshold_tokens → int: absolute token count for COMPACTING boundary.
    safety_ceiling_tokens       → int: absolute hard ceiling for EXHAUSTED boundary.
    """

    max_context_tokens:     int   = 128_000
    warning_percent:        float = 0.70
    compaction_percent:     float = 0.85
    safety_buffer_fraction: float = 0.05
    model_encoding:         str   = "cl100k_base"
    n_preserve_tail:        int   = 3
    per_message_overhead:   int   = 20

    @property
    def warning_threshold_tokens(self) -> int:
        """Tokens at or above which ContextStatus.WARNING is returned."""
        return int(self.max_context_tokens * self.warning_percent)

    @property
    def compaction_threshold_tokens(self) -> int:
        """Tokens at or above which ContextStatus.COMPACTING is returned."""
        return int(self.max_context_tokens * self.compaction_percent)

    @property
    def safety_ceiling_tokens(self) -> int:
        """
        Absolute hard ceiling beyond which ContextStatus.EXHAUSTED is returned.
        Computed as: max_context_tokens * (1.0 - safety_buffer_fraction).
        Any projected token count at or above this value skips compaction
        and triggers an immediate HandoffSpore write.
        """
        return int(self.max_context_tokens * (1.0 - self.safety_buffer_fraction))


# ==============================================================================
# SECTION 3 — Module-Level Regex Pruning Pipeline
# ==============================================================================

# P1 — Python traceback blocks
#      Matches the full traceback from "Traceback (most recent call last):"
#      until the first non-indented line or end-of-string.
_RE_TRACEBACK: re.Pattern[str] = re.compile(
    r"Traceback \(most recent call last\):.*?(?:\n\S[^\n]*|\Z)",
    re.DOTALL,
)

# P2 — ANSI terminal escape sequences
#      Matches all ANSI color, cursor, and reset codes.
_RE_ANSI: re.Pattern[str] = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)

# P3 — Tool / debug output section headers
#      Matches separator-wrapped labels like "--- Tool Output ---" or
#      "=== Debug ===" and their trailing newline, case-insensitively.
_RE_TOOL_HEADER: re.Pattern[str] = re.compile(
    r"^[-=]{3,}\s*(?:Tool Output|Debug|Verbose|stdout|stderr|Log)\s*[-=]{3,}\n?",
    re.MULTILINE | re.IGNORECASE,
)

# P4 — Base64 / binary blob lines
#      Matches blocks of 3+ consecutive lines each containing 60+ base64 chars.
#      These appear in step results that contain encoded file contents or payloads.
_RE_BASE64_BLOB: re.Pattern[str] = re.compile(
    r"(?:[A-Za-z0-9+/]{60,}\n?){3,}"
)

# P5 — Repeated visual separator lines
#      Matches entire lines consisting of 20+ repeated dash/equals/hash/tilde/star
#      characters, common in ASCII-art borders and terminal output dividers.
_RE_SEPARATOR: re.Pattern[str] = re.compile(
    r"^[-=*#~]{20,}\s*$\n?",
    re.MULTILINE,
)

# P6 — Excessive blank lines
#      Collapses 3+ consecutive newlines to exactly 2, preserving paragraph breaks
#      without preserving large empty gaps from stripped content.
_RE_EXCESS_BLANK: re.Pattern[str] = re.compile(r"\n{3,}")

# Ordered pipeline list — must be applied in exactly this sequence.
# Tuple format: (label: str, pattern: re.Pattern[str], replacement: str)
_PRUNE_PIPELINE: List[Tuple[str, re.Pattern[str], str]] = [
    ("traceback",   _RE_TRACEBACK,    ""),
    ("ansi",        _RE_ANSI,         ""),
    ("tool_header", _RE_TOOL_HEADER,  ""),
    ("base64_blob", _RE_BASE64_BLOB,  "[BINARY_CONTENT_REDACTED]"),
    ("separator",   _RE_SEPARATOR,    ""),
    ("blank_lines", _RE_EXCESS_BLANK, "\n\n"),
]


def _apply_prune_pipeline(text: str) -> str:
    """
    Apply the full deterministic 6-stage regex pruning pipeline to a text
    string and return the pruned, stripped result.

    This function implements the zero-API-cost Stage 1 of the Dronagiri
    Compactor. It is safe to call on any string, including serialized JSON
    payloads, because it only targets known bloat patterns (tracebacks, ANSI
    codes, base64 blobs, tool output headers, separator lines, excess blanks)
    that appear in the *values* of JSON strings, not in structural keys.

    The pipeline is applied in this exact order to prevent earlier substitutions
    from masking later patterns (e.g. ANSI codes inside a traceback are stripped
    in the ANSI pass, not re-matched by the traceback pass).

    Risk mitigated: RISK-019 — Runaway LLM summarization cost.

    Parameters
    ----------
    text : str
        Raw text to prune. Typically the JSON-serialized form of a
        TaskStep.result dict.

    Returns
    -------
    str
        Pruned string with all matched bloat patterns removed or replaced.
        Leading and trailing whitespace is stripped from the final output.
        Returns the original string unchanged if it is empty or None-like.
    """
    if not text:
        return text
    for _label, pattern, replacement in _PRUNE_PIPELINE:
        text = pattern.sub(replacement, text)
    return text.strip()


def _prune_tool_call_pairs_atomically(
    messages:  List[Dict[str, Any]],
    keep_tail: int,
) -> List[Dict[str, Any]]:
    """
    Prune the oldest tool-call message pairs from a messages list while
    strictly preserving the last ``keep_tail`` complete pairs and all
    non-tool-call messages.

    Tool-call messages in the OpenAI / Anthropic message format exist as
    locked atomic pairs:

        messages[i]   = {"role": "assistant", "tool_calls": [...]}  ← CALL
        messages[i+1] = {"role": "tool",      "content":   "..."}  ← RESPONSE

    Pruning index ``i`` without ``i+1`` leaves an orphaned tool response
    message, which causes an LLM API validation error on the very next
    dispatch call (the API rejects a tool response without a preceding call).
    This function identifies pairs by their structural signatures and prunes
    them together as an atomic unit, never individually.

    Non-pair messages (system prompts, plain user/assistant messages) are
    always preserved regardless of their position in the list.

    Risk mitigated: RISK-018 — Orphaned tool calls after context pruning.

    Parameters
    ----------
    messages  : List[Dict[str, Any]]
        Ordered list of LLM chat message dicts. Caller must not mutate this
        list externally during the call.
    keep_tail : int
        Number of complete tool-call pairs to preserve at the end of the list.
        All pairs before the tail boundary are candidates for removal.
        Non-pair messages are never counted toward this limit.

    Returns
    -------
    List[Dict[str, Any]]
        A new list with the oldest tool-call pairs removed. The original list
        is never mutated. Non-pair messages are preserved at their original
        positions relative to the remaining pairs.
    """
    if not messages:
        return messages

    # Phase 1: Identify all complete atomic pair locations (start_idx, end_idx)
    pair_indices: List[Tuple[int, int]] = []
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]
        nxt = messages[i + 1]
        if (
            isinstance(msg, dict)
            and msg.get("role") == "assistant"
            and "tool_calls" in msg
            and isinstance(nxt, dict)
            and nxt.get("role") == "tool"
        ):
            pair_indices.append((i, i + 1))
            i += 2  # Both messages consumed — advance by 2 to skip the pair
        else:
            i += 1

    # Phase 2: Determine which pairs to prune (all except the last keep_tail)
    n_pairs_to_prune = max(0, len(pair_indices) - keep_tail)
    pairs_to_prune   = pair_indices[:n_pairs_to_prune]

    if not pairs_to_prune:
        return messages  # Nothing to prune — return the original list unchanged

    # Phase 3: Build a set of indices to remove and filter
    remove_indices: set[int] = set()
    for start_idx, end_idx in pairs_to_prune:
        remove_indices.add(start_idx)
        remove_indices.add(end_idx)

    return [
        msg
        for idx, msg in enumerate(messages)
        if idx not in remove_indices
    ]


# ==============================================================================
# SECTION 4 — ContextTracker
# ==============================================================================

class ContextTracker:
    """
    Token projection engine for NALA's context window management.

    ContextTracker independently estimates the projected token size of the
    next LLM dispatch prompt by serializing the TaskGraph's current step
    payloads and counting with tiktoken. It does NOT rely on
    StateMatrix.total_tokens for threshold decisions — that counter is
    cumulative across all calls and diverges from per-call prompt size
    (RISK-022 mitigation).

    The projection is conservative (RISK-016 mitigation):
      - Each step description and result adds ``per_message_overhead`` tokens.
      - Token counting uses tiktoken.encode() with disallowed_special=() to
        prevent exceptions on file paths or special tokens in step text.

    This class is intended to be constructed once per NalaLoop instance and
    reused across all iterations of _execute_loop().

    Public API
    ----------
    monitor_context(session: SessionState) → ContextStatus
        Main entry point. Called from NalaLoop._execute_loop() injection block.

    project_token_count(session: SessionState) → int
        Public alias for testing (T01–T04). Returns the raw projected count.
    """

    def __init__(self, config: TrackerConfig) -> None:
        """
        Parameters
        ----------
        config : TrackerConfig
            Frozen configuration with threshold fractions and encoding name.
        """
        self.config   = config
        self.encoding = tiktoken.get_encoding(config.model_encoding)
        self._logger  = _logger_tracker

    # ── Public API ────────────────────────────────────────────────────────────

    def monitor_context(self, session: SessionState) -> ContextStatus:
        """
        Compute the projected prompt token count for the given session state
        and return the corresponding ContextStatus.

        This is the primary method called from NalaLoop._execute_loop().
        It is designed to be fast: a single pass over TaskGraph.steps,
        encoding each text field with tiktoken.

        Parameters
        ----------
        session : SessionState
            The live session being executed. Read-only in this call.

        Returns
        -------
        ContextStatus
            NORMAL / WARNING / COMPACTING / EXHAUSTED as appropriate.
        """
        projected = self._project_token_count(session)
        status    = self._classify(projected)

        self._logger.info(
            "[ContextTracker] session_id=%s | LSN=%d | "
            "projected=%d | ceiling=%d | compaction_at=%d | "
            "warning_at=%d | status=%s",
            session.session_id,
            session.checkpoint_meta.lsn,
            projected,
            self.config.safety_ceiling_tokens,
            self.config.compaction_threshold_tokens,
            self.config.warning_threshold_tokens,
            status.value,
        )
        return status

    def project_token_count(self, session: SessionState) -> int:
        """
        Public alias for _project_token_count().

        Exposed as a public method to allow direct invocation in unit tests
        (T01–T04) without triggering the full monitor_context() log output.

        Parameters
        ----------
        session : SessionState
            The session to project token usage for.

        Returns
        -------
        int
            Estimated prompt token count for the next LLM dispatch.
        """
        return self._project_token_count(session)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _project_token_count(self, session: SessionState) -> int:
        """
        Estimate the total prompt tokens the next LLM call would consume
        by serializing the TaskGraph's step payloads and encoding via tiktoken.

        Projection formula
        ------------------
        total = count(session.objective)  + per_message_overhead
              + Σ per step:
                  count(step.description) + per_message_overhead
                + if step.result:
                      count(json.dumps(step.result)) + per_message_overhead
                + if step.error_message:
                      count(step.error_message) + per_message_overhead

        The session objective is counted because it is embedded in every
        LLM system prompt as the agent's goal anchor.

        Step descriptions are always counted because the full plan context
        is sent with every dispatch (the agent must know what comes next).

        Step results are the primary source of context growth: each SUCCESS
        step adds its full result payload to the prompt history.

        Risk mitigated: RISK-022 — StateMatrix desync.
        Risk mitigated: RISK-016 — Per-message overhead for tokenizer variance.

        Parameters
        ----------
        session : SessionState
            The session to estimate token usage for.

        Returns
        -------
        int
            Conservative estimated prompt token count.
        """
        total = 0
        cfg   = self.config

        # Session objective — present in every LLM system prompt
        total += self._count(session.objective) + cfg.per_message_overhead

        for step in session.task_graph.steps:
            # Step description — full plan always present in prompt context
            total += self._count(step.description) + cfg.per_message_overhead

            # Step result payload — primary source of context window growth
            if step.result is not None:
                try:
                    result_text = json.dumps(
                        step.result, ensure_ascii=False, default=str
                    )
                    total += self._count(result_text) + cfg.per_message_overhead
                except (TypeError, ValueError):
                    # Unserializable result — count a conservative estimate
                    total += 50 + cfg.per_message_overhead

            # Error messages — FAILED steps include these for retry planning
            if step.error_message:
                total += self._count(step.error_message) + cfg.per_message_overhead

        return total

    def _count(self, text: str) -> int:
        """
        Return the tiktoken token count for a single string.

        Uses ``disallowed_special=()`` to prevent tiktoken from raising
        ValueError on strings containing special token sequences like
        ``<|endoftext|>`` or ``<|im_start|>`` that can appear in file paths,
        code snippets, or model outputs included in step results.

        Parameters
        ----------
        text : str
            Any UTF-8 string to encode.

        Returns
        -------
        int
            Number of tokens as counted by the configured tiktoken encoding.
            Returns 0 for empty or None-like input.
        """
        if not text:
            return 0
        return len(self.encoding.encode(text, disallowed_special=()))

    def _classify(self, projected_tokens: int) -> ContextStatus:
        """
        Map a projected token count to its corresponding ContextStatus.

        Threshold precedence (evaluated from highest urgency first):
          EXHAUSTED  ← projected >= safety_ceiling_tokens
          COMPACTING ← projected >= compaction_threshold_tokens
          WARNING    ← projected >= warning_threshold_tokens
          NORMAL     ← projected < warning_threshold_tokens

        Parameters
        ----------
        projected_tokens : int
            The output of _project_token_count().

        Returns
        -------
        ContextStatus
        """
        cfg = self.config
        if projected_tokens >= cfg.safety_ceiling_tokens:
            return ContextStatus.EXHAUSTED
        if projected_tokens >= cfg.compaction_threshold_tokens:
            return ContextStatus.COMPACTING
        if projected_tokens >= cfg.warning_threshold_tokens:
            return ContextStatus.WARNING
        return ContextStatus.NORMAL


# ==============================================================================
# SECTION 5 — Pydantic v2 Spore Models
# ==============================================================================

# JIRA-006: Extracted to core.harness.session_handoff. Re-exported here for
# backwards compatibility with existing harness components.
from core.harness.session_handoff import (
    SporeTaskGraphSummary,
    SporeTelemetry,
    HandoffSporeModel,
)


# ==============================================================================
# SECTION 6 — HandoffSpore (Static Write / Load)
# ==============================================================================

# JIRA-006: Extracted to core.harness.session_handoff. Re-exported here for
# backwards compatibility with existing harness components.
from core.harness.session_handoff import HandoffSpore

# ==============================================================================
# SECTION 7 — DronagiriCompactor
# ==============================================================================

class DronagiriCompactor:
    """
    2-stage context compaction engine for NALA's long-running agent loop.

    DronagiriCompactor is invoked by the JIRA-004 injection block inside
    NalaLoop._execute_loop() when ContextTracker.monitor_context() returns
    ContextStatus.COMPACTING. It attempts to reduce the session's projected
    prompt size below the compaction threshold through two sequential stages.

    Stage 1 — Deterministic Pruning (zero API cost, zero LLM calls):
        Applies the 6-pattern regex pipeline (_apply_prune_pipeline) to the
        serialized JSON of every SUCCESS step's result payload. Additionally,
        if any result contains a "messages" list with tool-call pairs, applies
        _prune_tool_call_pairs_atomically to remove oldest pairs while
        preserving the n_preserve_tail most recent pairs (RISK-018).

    Stage 2 — LLM-Based Crystallization (API cost; only if Stage 1 fails):
        Calls the injected summarizer_fn with a structured Dronagiri Golden
        Prompt (from JIRA-004 spec Section 3.D). The summarizer returns a
        JSON payload of crystallized step summaries. Each summarized step's
        result is replaced in-place with a compact crystallized dict. The
        last n_preserve_tail SUCCESS steps are NEVER sent to the summarizer
        and are preserved exactly as-is (RISK-017).

    After ANY mutation in either stage, _force_checkpoint() is called via
    checkpoint_fn to write the compacted state to disk BEFORE returning
    control to the loop (RISK-021).

    The class is designed to be injected into NalaLoop.__init__() and reused
    across all iterations. The summarizer_fn and checkpoint_fn are injected
    as callables to keep this class decoupled from both the LLM client and
    the NalaLoop internals.
    """

    def __init__(
        self,
        tracker:       ContextTracker,
        summarizer_fn: Callable[[str, str], str],
        checkpoint_fn: Callable[[str], Path],
    ) -> None:
        """
        Parameters
        ----------
        tracker       : ContextTracker
            The configured ContextTracker instance shared with NalaLoop.
            Used to re-evaluate token count after each compaction stage.
        summarizer_fn : Callable[[str, str], str]
            Injectable LLM call function with signature:
              (system_prompt: str, user_prompt: str) → str
            Must return a raw JSON string conforming to:
              {"crystallized_steps": [{"step_id": "...", "status": "...",
               "summary": "...", "key_outputs": {...}, "errors": null}]}
            If the function raises an exception, Stage 2 is aborted safely.
        checkpoint_fn : Callable[[str], Path]
            Reference to NalaLoop._save_checkpoint(label: str) → Path.
            Called after any mutation to persist the compacted state.
            Risk mitigated: RISK-021 — Mutation without checkpoint.
        """
        self.tracker       = tracker
        self.summarizer_fn = summarizer_fn
        self.checkpoint_fn = checkpoint_fn
        self._logger       = _logger_compactor

    # ── Public API ────────────────────────────────────────────────────────────

    def compact(self, session: SessionState) -> bool:
        """
        Execute the 2-stage compaction pipeline on the live session.

        Execution order:
          1. Stage 1: deterministic regex pruning via _stage1_deterministic_prune().
          2. Re-evaluate ContextStatus after Stage 1.
          3. If status is NORMAL or WARNING: write checkpoint and return True.
          4. If status is still COMPACTING or EXHAUSTED: invoke Stage 2.
          5. Write post-compaction checkpoint (always, after any mutation).
          6. Re-evaluate final status and return True (recovered) or False (failed).

        A post-compaction checkpoint is ALWAYS written after any state mutation,
        regardless of which stage completed. A compaction without a persisted
        checkpoint is a RISK-021 violation.

        Parameters
        ----------
        session : SessionState
            The live session whose TaskGraph.steps will be mutated in-place.
            The caller (NalaLoop) retains ownership; this method does not
            acquire any locks.

        Returns
        -------
        bool
            True  — compaction succeeded; projected tokens are now below
                    compaction_percent. Loop can resume dispatch.
            False — compaction failed after both stages; caller must write
                    HandoffSpore and exit with LoopStatus.PAUSED.
        """
        self._logger.info(
            "[Dronagiri] Compaction pipeline START. session_id=%s | LSN=%d",
            session.session_id,
            session.checkpoint_meta.lsn,
        )

        # ── Stage 1: Deterministic Pruning ─────────────────────────────────
        stage1_mutations = self._stage1_deterministic_prune(session)
        self._logger.info(
            "[Dronagiri] Stage 1 complete. mutations=%d | session_id=%s",
            stage1_mutations,
            session.session_id,
        )

        # Re-evaluate status after Stage 1
        post_s1_status = self.tracker.monitor_context(session)
        if post_s1_status in (ContextStatus.NORMAL, ContextStatus.WARNING):
            # Stage 1 was sufficient — write checkpoint and return success
            self._force_checkpoint(session, "post-compaction-stage1")
            self._logger.info(
                "[Dronagiri] Stage 1 sufficient. post_s1_status=%s. Returning True.",
                post_s1_status.value,
            )
            return True

        # ── Stage 2: LLM-Based Crystallization ────────────────────────────
        self._logger.info(
            "[Dronagiri] Stage 1 insufficient (post_s1_status=%s). "
            "Invoking Stage 2 LLM crystallization. session_id=%s",
            post_s1_status.value,
            session.session_id,
        )
        stage2_success = self._stage2_llm_summarize(session)

        # Always write checkpoint after Stage 2 — any mutation must be persisted
        # (RISK-021: even a partial Stage 2 crystallization must be checkpointed)
        self._force_checkpoint(session, "post-compaction-stage2")

        # Re-evaluate final status
        post_s2_status = self.tracker.monitor_context(session)
        final_result   = post_s2_status in (ContextStatus.NORMAL, ContextStatus.WARNING)

        self._logger.info(
            "[Dronagiri] Stage 2 complete. stage2_success=%s | "
            "post_s2_status=%s | compact_result=%s. session_id=%s",
            stage2_success,
            post_s2_status.value,
            final_result,
            session.session_id,
        )

        return final_result

    # ── Stage 1 ───────────────────────────────────────────────────────────────

    def _stage1_deterministic_prune(self, session: SessionState) -> int:
        """
        Apply the deterministic regex pruning pipeline to every SUCCESS step's
        result payload in-place, and prune tool-call message pairs atomically.

        For each SUCCESS step:
          a. Serialize step.result to JSON string.
          b. Apply _apply_prune_pipeline() — strips tracebacks, ANSI codes,
             tool output headers, base64 blobs, separator lines, excess blanks.
          c. If the text changed, attempt JSON parse-back and update step.result.
             If parse-back fails (pruning broke JSON structure), skip this step.
          d. If result contains "messages" key with a list, apply
             _prune_tool_call_pairs_atomically() to enforce RISK-018.

        Steps with status != SUCCESS or result == None are never touched.
        Already-crystallized steps (result["crystallized"] == True) are also
        skipped since their payloads are already minimal.

        Risk mitigated: RISK-018 — Orphaned tool calls.
        Risk mitigated: RISK-019 — Zero LLM API cost.

        Parameters
        ----------
        session : SessionState
            Live session to mutate in-place.

        Returns
        -------
        int
            Number of TaskStep result payloads that were actually mutated.
        """
        mutations = 0
        cfg       = self.tracker.config

        for step in session.task_graph.steps:
            # Skip non-SUCCESS steps and steps with no result payload
            if step.result is None or step.status != TaskStatus.SUCCESS:
                continue

            # Skip already-crystallized steps — their payload is already minimal
            if step.result.get("crystallized") is True:
                continue

            result_copy  = dict(step.result)
            step_mutated = False

            # ── Regex pipeline on serialized JSON string ──────────────────
            try:
                original_json = json.dumps(
                    result_copy, ensure_ascii=False, default=str
                )
                pruned_json = _apply_prune_pipeline(original_json)

                if pruned_json != original_json:
                    try:
                        result_copy  = json.loads(pruned_json)
                        step_mutated = True
                    except json.JSONDecodeError:
                        # Regex pipeline modified a JSON structural character —
                        # this should not happen with well-formed result dicts
                        # but is handled defensively. Skip text-level prune.
                        self._logger.warning(
                            "[Dronagiri] Stage 1: regex prune produced invalid JSON "
                            "for step '%s' — skipping text prune for this step.",
                            step.step_id,
                        )
            except (TypeError, ValueError) as exc:
                self._logger.warning(
                    "[Dronagiri] Stage 1: failed to serialize result for step '%s': %s "
                    "— skipping.",
                    step.step_id,
                    exc,
                )
                continue

            # ── Tool-call pair atomicity (RISK-018) ───────────────────────
            if (
                "messages" in result_copy
                and isinstance(result_copy.get("messages"), list)
            ):
                original_messages = list(result_copy["messages"])
                pruned_messages   = _prune_tool_call_pairs_atomically(
                    original_messages,
                    keep_tail=cfg.n_preserve_tail,
                )
                if len(pruned_messages) != len(original_messages):
                    result_copy["messages"] = pruned_messages
                    step_mutated = True
                    self._logger.debug(
                        "[Dronagiri] Stage 1: tool-call pairs pruned for step '%s': "
                        "%d → %d messages.",
                        step.step_id,
                        len(original_messages),
                        len(pruned_messages),
                    )

            if step_mutated:
                step.result = result_copy
                mutations  += 1

        return mutations

    # ── Stage 2 ───────────────────────────────────────────────────────────────

    def _stage2_llm_summarize(self, session: SessionState) -> bool:
        """
        Invoke the Dronagiri Summarizer LLM on completed steps, crystallizing
        their verbose result payloads while preserving the n_preserve_tail
        most recent SUCCESS steps UNCHANGED.

        The steps to summarize are all SUCCESS steps EXCEPT the last
        n_preserve_tail (RISK-017 mitigation: "lost in the middle").
        If there are not enough steps to have anything to summarize (i.e.
        total SUCCESS steps <= n_preserve_tail), this method returns False.

        After a successful summarizer response, each summarized step's
        result is replaced in-place with a compact crystallized dict:
          {"crystallized": True, "summary": "...", "key_outputs": {...}, "errors": ...}

        Risk mitigated: RISK-017 — Lost in the Middle.
        Risk mitigated: RISK-019 — Runaway LLM cost (only called if S1 fails).

        Parameters
        ----------
        session : SessionState
            Live session to mutate in-place.

        Returns
        -------
        bool
            True  — at least one step was successfully crystallized.
            False — skipped (not enough steps) or summarizer returned invalid response.
        """
        cfg = self.tracker.config

        # Only SUCCESS steps are candidates for summarization
        completed = [
            s for s in session.task_graph.steps
            if s.status == TaskStatus.SUCCESS
        ]

        if len(completed) <= cfg.n_preserve_tail:
            self._logger.warning(
                "[Dronagiri] Stage 2 skipped: completed_steps=%d <= "
                "n_preserve_tail=%d — nothing to summarize.",
                len(completed),
                cfg.n_preserve_tail,
            )
            return False

        # Split: oldest steps are summarized; tail steps are preserved exactly
        steps_to_summarize = completed[: -cfg.n_preserve_tail]
        steps_to_preserve  = completed[-cfg.n_preserve_tail:]

        # Skip steps already crystallized by a previous compaction cycle
        summarizable = [s for s in steps_to_summarize if not s.result.get("crystallized")]
        if not summarizable:
            self._logger.info(
                "[Dronagiri] Stage 2: all candidate steps already crystallized. "
                "Skipping LLM call."
            )
            return False

        # Build the Dronagiri Golden Prompt (JIRA-004 spec Section 3.D)
        system_prompt = self._build_system_prompt(cfg.n_preserve_tail)
        user_prompt   = self._build_user_prompt(summarizable, cfg.n_preserve_tail)

        # Invoke the summarizer LLM
        try:
            raw_response = self.summarizer_fn(system_prompt, user_prompt)
        except Exception as exc:
            self._logger.error(
                "[Dronagiri] Stage 2: summarizer_fn raised an exception: %s. "
                "Aborting Stage 2 safely.",
                exc,
            )
            return False

        # Parse the JSON response
        try:
            parsed       = json.loads(raw_response)
            crystallized = parsed.get("crystallized_steps")
            if not isinstance(crystallized, list):
                raise ValueError(
                    f"'crystallized_steps' must be a list, "
                    f"got {type(crystallized).__name__}"
                )
        except (json.JSONDecodeError, ValueError) as exc:
            self._logger.error(
                "[Dronagiri] Stage 2: invalid summarizer response "
                "(expected JSON with 'crystallized_steps' list): %s. "
                "First 300 chars of raw response: %.300s",
                exc,
                raw_response,
            )
            return False

        # Map step_id → crystallized entry from the response
        cryst_by_id: Dict[str, Dict[str, Any]] = {
            c["step_id"]: c
            for c in crystallized
            if isinstance(c, dict) and "step_id" in c
        }

        # Apply crystallized results in-place to the summarized steps
        n_crystallized = 0
        for step in summarizable:
            if step.step_id in cryst_by_id:
                c = cryst_by_id[step.step_id]
                step.result = {
                    "crystallized": True,
                    "summary":      str(c.get("summary", "")),
                    "key_outputs":  c.get("key_outputs") or {},
                    "errors":       c.get("errors"),
                }
                n_crystallized += 1
            else:
                self._logger.warning(
                    "[Dronagiri] Stage 2: step '%s' not found in "
                    "crystallized_steps response — result left unchanged.",
                    step.step_id,
                )

        self._logger.info(
            "[Dronagiri] Stage 2 crystallization complete. "
            "crystallized=%d/%d steps | preserved=%d tail steps.",
            n_crystallized,
            len(summarizable),
            len(steps_to_preserve),
        )

        return n_crystallized > 0

    # ── Checkpoint helper ─────────────────────────────────────────────────────

    def _force_checkpoint(self, session: SessionState, label: str) -> None:
        """
        Write a post-compaction checkpoint by calling self.checkpoint_fn(label).

        This method is ALWAYS called after any stage that mutated session state,
        ensuring the compacted state is durably written to disk before the loop
        resumes. A compaction that modifies step results without persisting
        them is a RISK-021 violation.

        If checkpoint_fn raises any exception, it is logged as CRITICAL and
        re-raised. Silently swallowing a checkpoint failure here would leave
        the session in an un-persisted state, making the compaction worthless
        on crash recovery.

        Risk mitigated: RISK-021 — Compaction mutation without checkpoint.

        Parameters
        ----------
        session : SessionState
            The session whose state was just mutated. Passed for logging
            context; the checkpoint_fn captures the session reference via
            its NalaLoop closure.
        label   : str
            Human-readable checkpoint label written into CheckpointMeta
            (e.g. "post-compaction-stage1", "post-compaction-stage2").

        Raises
        ------
        Exception
            Any exception raised by checkpoint_fn. Never swallowed.
        """
        try:
            checkpoint_path = self.checkpoint_fn(label)
            self._logger.info(
                "[Dronagiri] Post-compaction checkpoint written. "
                "label=%s | path=%s | session_id=%s",
                label,
                checkpoint_path,
                session.session_id,
            )
        except Exception as exc:
            self._logger.critical(
                "[Dronagiri] CRITICAL: Post-compaction checkpoint FAILED. "
                "label=%s | error=%s | session_id=%s. "
                "RISK-021 VIOLATION: compacted state is NOT persisted. "
                "Re-raising to halt the loop.",
                label,
                exc,
                session.session_id,
            )
            raise  # Never swallow — a lost checkpoint is worse than a crash

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _build_system_prompt(self, n_preserve_tail: int) -> str:
        """
        Build the Dronagiri Compactor system prompt using the Golden Prompt
        Layout from JIRA-004 spec Section 3.D.

        The prompt is structured in XML-tagged sections to maximize
        instruction adherence across LLM providers. It explicitly forbids
        the summarizer from touching the n_preserve_tail most recent steps
        (RISK-017 mitigation) and from hallucinating information not present
        in the input (factual fidelity requirement).

        Parameters
        ----------
        n_preserve_tail : int
            Number of most-recent steps excluded from summarization.
            Injected into the prompt rules so the LLM is explicitly aware.

        Returns
        -------
        str
            Fully formatted system prompt string ready for the LLM call.
        """
        return (
            "<system_prompt>\n"
            "<task_context>\n"
            "You are the Dronagiri Compactor — the context crystallization engine of NALA\n"
            "(Nexus Autonomous Long-Running Agent). Your sole task is to compress the\n"
            "historical execution log of a long-running agent session into a compact,\n"
            "lossless crystallized summary that preserves all information necessary for\n"
            "the agent to resume execution without any regressions.\n"
            "</task_context>\n\n"
            "<tone>\n"
            "Be precise, terse, and technical. No prose, no filler. Output only structured\n"
            "summaries. Every variable name, error encountered, output value, and decision\n"
            "made must be preserved. Lossy compression is a failure mode.\n"
            "</tone>\n\n"
            "<data_format>\n"
            "The input is a JSON array of completed TaskStep objects from NALA's TaskGraph.\n"
            "Each object has: step_id, description, status, result (dict), error_message.\n"
            "</data_format>\n\n"
            "<rules>\n"
            f"1. DO NOT summarize or modify the last {n_preserve_tail} steps of the FULL\n"
            f"   history. These are excluded from the input payload and must not be referenced.\n"
            "2. DO NOT summarize or modify the session objective. It is not in this payload.\n"
            "3. For each step in the input payload, produce exactly one compressed entry.\n"
            "   Preserve: step_id, final status, key output variable names and values,\n"
            "   errors encountered, side effects confirmed (files written, APIs called,\n"
            "   DB rows inserted, test counts passed).\n"
            "4. If a step FAILED, preserve the exact error_message string verbatim.\n"
            "   Never discard or paraphrase failure reasons.\n"
            "5. If a step result contains a file path, URL, database ID, or any identifier\n"
            "   that could be referenced by a later step — preserve it exactly as written.\n"
            "6. Compress verbose terminal output, logs, and debug strings to a single\n"
            '   outcome line, e.g. "Executed shell cmd. Exit 0. 42 lines stdout."\n'
            "7. DO NOT invent, infer, or hallucinate any information not in the input.\n"
            "8. DO NOT include any text outside the JSON output structure.\n"
            "</rules>\n\n"
            "<output_format>\n"
            "Return ONLY valid JSON with no preamble, no markdown fences, no explanation.\n"
            "The root object must have exactly one key: 'crystallized_steps'.\n"
            "Each entry must have: step_id, status, summary, key_outputs, errors.\n\n"
            "{\n"
            '  "crystallized_steps": [\n'
            "    {\n"
            '      "step_id": "step_001_example",\n'
            '      "status": "SUCCESS",\n'
            '      "summary": "One to three factual sentences describing the outcome.",\n'
            '      "key_outputs": {"output_variable": "value"},\n'
            '      "errors": null\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "</output_format>\n"
            "</system_prompt>"
        )

    def _build_user_prompt(
        self,
        steps_to_summarize: List[Any],
        n_preserve_tail:    int,
    ) -> str:
        """
        Build the Dronagiri Compactor user prompt using the Golden Prompt
        Layout from JIRA-004 spec Section 3.D.

        Serializes the steps to summarize as a JSON array and wraps them
        in structured XML tags matching the system prompt's format.

        Parameters
        ----------
        steps_to_summarize : List[TaskStep]
            The TaskStep instances to be crystallized. These are the oldest
            completed steps (all SUCCESS steps except the tail).
        n_preserve_tail    : int
            Number of tail steps excluded from this payload (for context note).

        Returns
        -------
        str
            Fully formatted user prompt string ready for the LLM call.
        """
        payload = json.dumps(
            [s.model_dump(mode="json") for s in steps_to_summarize],
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        return (
            "<user_prompt>\n"
            "<history>\n"
            f"Summarize the following {len(steps_to_summarize)} completed TaskStep records.\n"
            f"The last {n_preserve_tail} steps of the full execution history are preserved\n"
            "separately and are NOT included in this payload. Do not reference or modify them.\n"
            "Compress every step in this payload into one crystallized_steps entry.\n"
            "</history>\n\n"
            "<immediate_request>\n"
            "Input TaskStep JSON array:\n"
            f"{payload}\n"
            "</immediate_request>\n"
            "</user_prompt>"
        )


# ==============================================================================
# SECTION 8 — Module __all__
# ==============================================================================

__all__ = [
    # Custom exceptions
    "ContextExhaustedSignal",
    "SporeValidationError",
    # Enum
    "ContextStatus",
    # Configuration
    "TrackerConfig",
    # Module-level regex utilities
    "_apply_prune_pipeline",
    "_prune_tool_call_pairs_atomically",
    "_PRUNE_PIPELINE",
    # Core classes
    "ContextTracker",
    "DronagiriCompactor",
    # Pydantic v2 models
    "SporeTaskGraphSummary",
    "SporeTelemetry",
    "HandoffSporeModel",
    # Handoff
    "HandoffSpore",
]
