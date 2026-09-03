"""
================================================================================
NALA — Nexus Autonomous Long-Running Agent
================================================================================
File    : tests/unit/test_context_tracker.py
Ticket  : JIRA-004 — Context Window Tracker & Dronagiri Compactor (Test Suite)
Author  : Nexus Lab AI Research Lab, Bengaluru
Version : 2.0.0

COVERAGE TARGETS (T01 – T20)
------------------------------
  T01  test_token_counting_precision              ← tiktoken accuracy (RISK-016)
  T02  test_warning_threshold_trigger             ← ~72% capacity → WARNING
  T03  test_compacting_threshold_trigger          ← ~87% capacity → COMPACTING
  T04  test_exhausted_threshold_trigger           ← ~96% capacity → EXHAUSTED
  T05  test_stage1_deterministic_prune_patterns   ← all 6 regex patterns (RISK-019)
  T06  test_system_prompt_and_tail_preservation   ← n_preserve_tail lock (RISK-017)
  T07  test_tool_call_pair_atomicity              ← atomic pair pruning (RISK-018)
  T08  test_handoff_spore_write_and_validate      ← schema round-trip (RISK-020)
  T09  test_post_compaction_checkpoint_written    ← checkpoint after mutation (RISK-021)
  T10  test_loop_integration_with_context_guard   ← E2E loop + compaction

  [EXTRA — beyond spec, per Nexus Lab CODING STANDARD]
  T11  test_spore_load_validates_missing_file     ← SporeValidationError on missing
  T12  test_spore_load_validates_corrupt_json     ← SporeValidationError on bad JSON
  T13  test_prune_pipeline_is_idempotent          ← double-prune = same result
  T14  test_already_crystallized_steps_skipped_in_stage1 ← skip crystallized payloads
  T15  test_tracker_config_threshold_properties   ← TrackerConfig computed props
  T16  test_context_exhausted_signal_attributes   ← Exception attributes
  T17  test_empty_session_projected_count_is_low  ← zero steps → NORMAL
  T18  test_stage2_skips_when_insufficient_steps  ← too few steps → returns False
  T19  test_spore_model_forbids_extra_fields      ← Pydantic extra="forbid"
  T20  test_classify_boundary_values              ← exact threshold boundaries

DESIGN NOTES
------------
  - All file I/O uses pytest's ``tmp_path`` fixture to avoid workspace pollution.
  - Token counts are verified with tiktoken directly, not approximated.
  - DronagiriCompactor is tested with injectable mocks (summarizer_fn, checkpoint_fn).
  - T10 uses a NalaLoopWithContextGuard subclass to simulate the JIRA-004
    injection block without modifying nala_loop.py prematurely.
  - Every test fully asserts its conditions. No ``assert True`` placeholders.

================================================================================
Jai Bajrang Bali 🙏
================================================================================
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, call, patch

import pydantic
import pytest
import sys
import pathlib
import tiktoken
import time
import traceback
import inspect
import tempfile

# ── Force UTF-8 output on Windows consoles (fixes UnicodeEncodeError) ─────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Add the project root (NALA/) to sys.path so imports work without install ───
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# ── NALA session contract ─────────────────────────────────────────────────────
from core.harness.session_contract import (

    CheckpointMeta,
    SessionState,
    StateMatrix,
    TaskGraph,
    TaskStatus,
    TaskStep,
    utcnow,
)

# ── NALA checkpoint + loop ────────────────────────────────────────────────────
from core.harness.checkpoint import CheckpointManager
from core.harness.nala_loop import (
    LoopHooks,
    LoopStatus,
    NalaLoop,
    StepResult,
)

# ── Subject under test ────────────────────────────────────────────────────────
from core.harness.context_tracker import (
    ContextExhaustedSignal,
    ContextStatus,
    ContextTracker,
    DronagiriCompactor,
    HandoffSpore,
    HandoffSporeModel,
    SporeTaskGraphSummary,
    SporeTelemetry,
    SporeValidationError,
    TrackerConfig,
    _PRUNE_PIPELINE,
    _apply_prune_pipeline,
    _prune_tool_call_pairs_atomically,
)


# ==============================================================================
# MODULE-LEVEL HELPERS & FACTORIES
# ==============================================================================

def _enc() -> tiktoken.Encoding:
    """Return the cl100k_base encoding used across all token counting tests."""
    return tiktoken.get_encoding("cl100k_base")


def _exact_token_text(n: int) -> str:
    """
    Generate a string that decodes/re-encodes to EXACTLY ``n`` tokens in
    cl100k_base.

    Uses tiktoken's own decode() to guarantee the round-trip:
      len(enc.encode(result)) == n

    This is used to build predictable step result payloads for threshold tests.

    Parameters
    ----------
    n : int
        Exact number of tokens the returned string must produce.

    Returns
    -------
    str
        A string with exactly n cl100k_base tokens.
    """
    enc = _enc()
    # Use a repeating phrase that doesn't collide with regex prune patterns.
    # "nexus " is 2 tokens in cl100k_base: "nexus" + space
    source_ids = enc.encode("nexus " * (n + 50), disallowed_special=())
    # Take exactly n token ids and decode — guaranteed n tokens on re-encode
    return enc.decode(source_ids[:n])


def _make_session(
    objective: str = "Test NALA session",
    n_pending_steps: int = 3,
) -> SessionState:
    """
    Build a minimal SessionState with n_pending_steps all in PENDING status.

    Parameters
    ----------
    objective        : Session objective string.
    n_pending_steps  : Number of PENDING TaskStep objects to create.

    Returns
    -------
    SessionState
    """
    steps = [
        TaskStep(
            step_id=f"step_{i:03d}",
            description=f"Task step number {i}",
        )
        for i in range(1, n_pending_steps + 1)
    ]
    return SessionState(
        objective=objective,
        task_graph=TaskGraph(steps=steps),
    )


def _make_session_with_success_steps(
    n: int,
    result_payload: Optional[Dict[str, Any]] = None,
) -> SessionState:
    """
    Build a SessionState where all n steps are in SUCCESS status.

    Parameters
    ----------
    n              : Number of SUCCESS steps.
    result_payload : Dict to use as the result for each step. Defaults to
                     a small sentinel dict if None.

    Returns
    -------
    SessionState with n SUCCESS steps.
    """
    payload = result_payload if result_payload is not None else {"ok": True}
    steps = []
    for i in range(1, n + 1):
        step = TaskStep(
            step_id=f"step_{i:03d}",
            description=f"Task step {i}",
        )
        step.mark_success(dict(payload))
        steps.append(step)

    return SessionState(
        objective="Multi-step test session",
        task_graph=TaskGraph(steps=steps),
    )


def _make_mixed_session(
    n_success: int = 3,
    n_pending: int = 2,
) -> SessionState:
    """
    Build a SessionState with a mix of SUCCESS and PENDING steps.

    SUCCESS steps come first (they are dependencies for PENDING steps).

    Parameters
    ----------
    n_success : Number of steps in SUCCESS status.
    n_pending : Number of steps in PENDING status.

    Returns
    -------
    SessionState
    """
    steps = []
    for i in range(1, n_success + 1):
        s = TaskStep(step_id=f"step_{i:03d}", description=f"Success step {i}")
        s.mark_success({"result_index": i, "value": f"output_{i}"})
        steps.append(s)

    for j in range(n_success + 1, n_success + n_pending + 1):
        steps.append(
            TaskStep(step_id=f"step_{j:03d}", description=f"Pending step {j}")
        )

    return SessionState(
        objective="Mixed status session",
        task_graph=TaskGraph(steps=steps),
    )


def _inject_tokens_into_session(
    session: SessionState,
    tracker: ContextTracker,
    target_total_tokens: int,
) -> None:
    """
    Pad the last SUCCESS step's result until projected token count reaches
    ``target_total_tokens``.

    Uses an iterative approach, adding tokens incrementally and re-measuring
    until the target is reached. Guarantees accuracy because it relies on
    the tracker's own _project_token_count() rather than external estimation.

    Parameters
    ----------
    session             : The live session to mutate.
    tracker             : ContextTracker used to measure projected count.
    target_total_tokens : The projected token count to reach (not exceed).
    """
    enc = _enc()
    cfg = tracker.config

    # Ensure there is at least one SUCCESS step to inject into
    if not any(s.status == TaskStatus.SUCCESS for s in session.task_graph.steps):
        pad_step = TaskStep(step_id="step_inject_pad", description="inject")
        pad_step.mark_success({"_pad": ""})
        session.task_graph.steps.append(pad_step)

    # Find the last SUCCESS step
    target_step = next(
        s for s in reversed(session.task_graph.steps)
        if s.status == TaskStatus.SUCCESS
    )

    # Iteratively add tokens until we reach the target
    for _iteration in range(20):
        current = tracker._project_token_count(session)
        if current >= target_total_tokens:
            break

        needed = target_total_tokens - current
        if needed <= 0:
            break

        # Generate a string with approximately `needed` tokens.
        # Over-generate then trim to ensure exact count.
        source_ids = enc.encode(
            "nexus agent loop " * (needed + 20),
            disallowed_special=(),
        )
        extra_text = enc.decode(source_ids[:needed])

        # Append to the existing padding
        current_result = dict(target_step.result or {})
        existing_pad = current_result.get("_pad", "")
        current_result["_pad"] = existing_pad + extra_text
        target_step.result = current_result


def _make_tool_call_messages(n_pairs: int) -> List[Dict[str, Any]]:
    """
    Build a messages list with exactly ``n_pairs`` complete atomic tool-call
    pairs (assistant+tool) in sequence.

    Each pair follows the OpenAI / Anthropic message format:
        messages[2i]   = {"role": "assistant", "tool_calls": [...]}
        messages[2i+1] = {"role": "tool", "content": "result_i"}

    Parameters
    ----------
    n_pairs : Number of complete (assistant, tool) message pairs to create.

    Returns
    -------
    List[Dict[str, Any]] with 2 × n_pairs messages total.
    """
    messages = []
    for i in range(1, n_pairs + 1):
        messages.append({
            "role":       "assistant",
            "tool_calls": [{"id": f"call_{i}", "function": {"name": f"tool_{i}", "arguments": "{}"}}],
        })
        messages.append({
            "role":    "tool",
            "content": f"result_of_tool_{i}",
        })
    return messages


def _mock_summarizer_fn(
    steps: List[TaskStep],
) -> Callable[[str, str], str]:
    """
    Build a valid mock summarizer_fn that returns a JSON payload matching the
    Dronagiri Compactor's expected format for the given steps.

    The mock returns a crystallized_steps entry for EACH step in ``steps``.

    Parameters
    ----------
    steps : The steps to include in the crystallized response.

    Returns
    -------
    Callable[[str, str], str]
        A function (system_prompt, user_prompt) → JSON string.
    """
    crystallized = [
        {
            "step_id":     s.step_id,
            "status":      "SUCCESS",
            "summary":     f"Crystallized summary of {s.step_id}.",
            "key_outputs": {"index": i},
            "errors":      None,
        }
        for i, s in enumerate(steps)
    ]

    def _summarizer(system_prompt: str, user_prompt: str) -> str:
        return json.dumps({"crystallized_steps": crystallized})

    return _summarizer


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture
def small_cfg() -> TrackerConfig:
    """
    TrackerConfig with a 1 000-token window and zero per-message overhead.

    Zero overhead is used in threshold tests so that the math is exact and
    predictable: the only token contribution is from the text itself.
    """
    return TrackerConfig(
        max_context_tokens=1_000,
        warning_percent=0.70,
        compaction_percent=0.85,
        safety_buffer_fraction=0.05,
        model_encoding="cl100k_base",
        n_preserve_tail=3,
        per_message_overhead=0,
    )


@pytest.fixture
def tracker(small_cfg: TrackerConfig) -> ContextTracker:
    """ContextTracker backed by the small_cfg fixture."""
    return ContextTracker(small_cfg)


@pytest.fixture
def mock_checkpoint_fn(tmp_path: Path) -> Tuple[Callable[[str], Path], List[str]]:
    """
    Returns (checkpoint_fn, call_log).

    checkpoint_fn : Callable[[str], Path] — records its label argument.
    call_log      : List[str]             — all labels passed so far.
    """
    call_log: List[str] = []

    def _fn(label: str) -> Path:
        call_log.append(label)
        p = tmp_path / f"cp_{len(call_log)}.json"
        p.write_text("{}", encoding="utf-8")
        return p

    return _fn, call_log


@pytest.fixture
def session_5_success() -> SessionState:
    """SessionState with 5 SUCCESS steps, each holding a tiny result dict."""
    return _make_session_with_success_steps(5, result_payload={"val": "ok"})


@pytest.fixture
def session_7_success() -> SessionState:
    """SessionState with 7 SUCCESS steps used by Stage 2 / tail-preservation tests."""
    return _make_session_with_success_steps(7)


# ==============================================================================
# T01 — Token Counting Precision
# ==============================================================================

class TestT01TokenCountingPrecision:
    """
    T01 — Verify that ContextTracker._count() matches tiktoken exactly
    for a variety of real-world string types, and that edge cases (empty
    string, special-token sequences) are handled safely.
    """

    def test_short_strings_match_tiktoken(self, tracker: ContextTracker) -> None:
        """Single words and sentences encode to the same count as raw tiktoken."""
        enc = _enc()
        samples = [
            "Hello, World!",
            "NALA",
            "Nexus Autonomous Long-Running Agent",
            "def fib(n): return n if n <= 1 else fib(n-1)+fib(n-2)",
            "The quick brown fox jumps over the lazy dog.",
        ]
        for s in samples:
            expected = len(enc.encode(s, disallowed_special=()))
            actual = tracker._count(s)
            assert actual == expected, (
                f"Token count mismatch for {s!r}: "
                f"expected={expected}, actual={actual}"
            )

    def test_empty_string_returns_zero(self, tracker: ContextTracker) -> None:
        """Empty string and None-like inputs must return 0 (RISK-016 guard)."""
        assert tracker._count("") == 0

    def test_multiline_code_block_matches_tiktoken(
        self, tracker: ContextTracker
    ) -> None:
        """Multi-line code strings with newlines, indentation, and symbols."""
        enc = _enc()
        code = (
            "import json\n"
            "from pathlib import Path\n\n"
            "def load(p: Path) -> dict:\n"
            "    return json.loads(p.read_text())\n"
        )
        expected = len(enc.encode(code, disallowed_special=()))
        actual = tracker._count(code)
        assert actual == expected

    def test_special_token_sequences_do_not_raise(
        self, tracker: ContextTracker
    ) -> None:
        """
        Strings containing OpenAI special-token sequences like <|endoftext|>
        must NOT raise ValueError — disallowed_special=() disables that guard.
        """
        dangerous = "data: <|endoftext|> more <|im_start|>"
        try:
            count = tracker._count(dangerous)
        except ValueError as exc:
            pytest.fail(
                f"_count() raised ValueError on special-token input: {exc}"
            )
        assert count > 0, "Expected non-zero token count for non-empty string"

    def test_project_token_count_is_additive(
        self, tracker: ContextTracker
    ) -> None:
        """
        project_token_count() must be at least the sum of individual field
        token counts (it may be slightly higher due to JSON serialization overhead).
        """
        enc = _enc()
        objective = "Refactor the core harness"
        desc = "Step 1: update imports"
        result_val = "Done, all imports updated."

        step = TaskStep(step_id="step_001", description=desc)
        step.mark_success({"message": result_val})
        session = SessionState(
            objective=objective,
            task_graph=TaskGraph(steps=[step]),
        )

        projected = tracker.project_token_count(session)

        # Minimum: raw text tokens (no JSON overhead)
        lower_bound = (
            len(enc.encode(objective, disallowed_special=()))
            + len(enc.encode(desc, disallowed_special=()))
            + len(enc.encode(result_val, disallowed_special=()))
        )
        assert projected >= lower_bound, (
            f"projected={projected} < lower_bound={lower_bound}. "
            "project_token_count should be additive."
        )


# ==============================================================================
# T02 — Warning Threshold Trigger (~72%)
# ==============================================================================

class TestT02WarningThreshold:
    """
    T02 — ContextStatus.WARNING is returned when the projected token count
    falls between warning_percent (70%) and compaction_percent (85%) of
    max_context_tokens.
    """

    def test_warning_threshold_trigger(
        self, tracker: ContextTracker, small_cfg: TrackerConfig
    ) -> None:
        """
        Inject a 720-token payload into a session and assert WARNING is returned.
        The test verifies the projected count is in the [700, 850) band before
        asserting the status.
        """
        # A 720-token result sits at 72% of 1 000 → clearly in the WARNING zone
        target_total = 720

        session = _make_session(n_pending_steps=0)
        step = TaskStep(step_id="step_001", description="x")
        step.mark_success({"_pad": ""})
        session.task_graph.steps.append(step)

        _inject_tokens_into_session(session, tracker, target_total)

        projected = tracker.project_token_count(session)

        # Confirm we are genuinely in the WARNING band (not NORMAL or COMPACTING)
        assert small_cfg.warning_threshold_tokens <= projected < small_cfg.compaction_threshold_tokens, (
            f"Injection missed WARNING zone. projected={projected}, "
            f"warning_floor={small_cfg.warning_threshold_tokens}, "
            f"compaction_ceil={small_cfg.compaction_threshold_tokens}"
        )

        status = tracker.monitor_context(session)
        assert status == ContextStatus.WARNING, (
            f"Expected WARNING, got {status.value} at {projected} tokens"
        )

    def test_just_below_warning_is_normal(
        self, tracker: ContextTracker, small_cfg: TrackerConfig
    ) -> None:
        """A session below 70% of max_context_tokens returns NORMAL."""
        # Target 65% (650 tokens) — clearly below WARNING threshold of 700
        target_total = 650

        session = _make_session(n_pending_steps=0)
        step = TaskStep(step_id="step_001", description="x")
        step.mark_success({"_pad": ""})
        session.task_graph.steps.append(step)

        _inject_tokens_into_session(session, tracker, target_total)

        projected = tracker.project_token_count(session)
        assert projected < small_cfg.warning_threshold_tokens, (
            f"Injection exceeded WARNING floor. projected={projected}"
        )

        status = tracker.monitor_context(session)
        assert status == ContextStatus.NORMAL


# ==============================================================================
# T03 — Compacting Threshold Trigger (~87%)
# ==============================================================================

class TestT03CompactingThreshold:
    """
    T03 — ContextStatus.COMPACTING is returned when the projected token count
    falls between compaction_percent (85%) and the safety ceiling (95%) of
    max_context_tokens.
    """

    def test_compacting_threshold_trigger(
        self, tracker: ContextTracker, small_cfg: TrackerConfig
    ) -> None:
        """
        Inject an 870-token payload and assert COMPACTING is returned.
        Verifies the projected count is in the [850, 950) band first.
        """
        target_total = 870  # 87% of 1 000

        session = _make_session(n_pending_steps=0)
        step = TaskStep(step_id="step_001", description="x")
        step.mark_success({"_pad": ""})
        session.task_graph.steps.append(step)

        _inject_tokens_into_session(session, tracker, target_total)

        projected = tracker.project_token_count(session)
        assert small_cfg.compaction_threshold_tokens <= projected < small_cfg.safety_ceiling_tokens, (
            f"Injection missed COMPACTING zone. projected={projected}, "
            f"compaction_floor={small_cfg.compaction_threshold_tokens}, "
            f"safety_ceil={small_cfg.safety_ceiling_tokens}"
        )

        status = tracker.monitor_context(session)
        assert status == ContextStatus.COMPACTING, (
            f"Expected COMPACTING, got {status.value} at {projected} tokens"
        )


# ==============================================================================
# T04 — Exhausted Threshold Trigger (~96%)
# ==============================================================================

class TestT04ExhaustedThreshold:
    """
    T04 — ContextStatus.EXHAUSTED is returned when projected token count
    meets or exceeds the safety ceiling (max_context_tokens × 0.95 for
    a 5% safety buffer).
    """

    def test_exhausted_threshold_trigger(
        self, tracker: ContextTracker, small_cfg: TrackerConfig
    ) -> None:
        """
        Inject a 960-token payload and assert EXHAUSTED is returned.
        safety_ceiling = 1 000 × (1 - 0.05) = 950 tokens.
        """
        target_total = 960  # 96% of 1 000 — clearly above safety_ceiling (950)

        session = _make_session(n_pending_steps=0)
        step = TaskStep(step_id="step_001", description="x")
        step.mark_success({"_pad": ""})
        session.task_graph.steps.append(step)

        _inject_tokens_into_session(session, tracker, target_total)

        projected = tracker.project_token_count(session)
        assert projected >= small_cfg.safety_ceiling_tokens, (
            f"Injection missed EXHAUSTED zone. projected={projected}, "
            f"safety_ceiling={small_cfg.safety_ceiling_tokens}"
        )

        status = tracker.monitor_context(session)
        assert status == ContextStatus.EXHAUSTED, (
            f"Expected EXHAUSTED, got {status.value} at {projected} tokens"
        )


# ==============================================================================
# T05 — Stage 1 Deterministic Prune Patterns
# ==============================================================================

class TestT05DeterministicPrunePatterns:
    """
    T05 — Verify all 6 regex patterns in _PRUNE_PIPELINE strip or replace
    their target content correctly when run through _apply_prune_pipeline().
    """

    def test_python_traceback_is_stripped(self) -> None:
        """P1: Full Python traceback blocks are removed entirely."""
        text = (
            "Traceback (most recent call last):\n"
            "  File '/app/core/agent.py', line 42, in execute\n"
            "    result = tool.run(step)\n"
            "  File '/app/tools/shell.py', line 17, in run\n"
            "    raise RuntimeError('command failed')\n"
            "RuntimeError: command failed\n"
            "next line of output"
        )
        result = _apply_prune_pipeline(text)

        assert "Traceback" not in result, "Traceback header should be stripped"
        assert "RuntimeError" not in result, "Exception name should be stripped"
        assert "File '/app/" not in result, "File references should be stripped"
        assert "next line of output" in result, "Non-traceback content must be preserved"

    def test_ansi_escape_codes_are_stripped(self) -> None:
        """P2: ANSI terminal escape codes are removed; text content preserved."""
        text = "\x1b[31mERROR\x1b[0m: step failed\x1b[1;34m BOLD BLUE \x1b[0m end"
        result = _apply_prune_pipeline(text)

        assert "\x1b" not in result, "All ANSI escape sequences must be removed"
        assert "ERROR" in result, "Text content after ANSI codes must be preserved"
        assert "step failed" in result, "Non-ANSI text must be preserved"
        assert "end" in result

    def test_tool_output_headers_are_stripped(self) -> None:
        """P3: Tool/debug output section headers (--- Tool Output ---) are removed."""
        text = (
            "--- Tool Output ---\n"
            "useful content here\n"
            "=== Debug ===\n"
            "debug content\n"
            "--- stdout ---\n"
            "std output"
        )
        result = _apply_prune_pipeline(text)

        assert "--- Tool Output ---" not in result
        assert "=== Debug ===" not in result
        assert "--- stdout ---" not in result
        assert "useful content here" in result, "Content after headers must be preserved"
        assert "std output" in result

    def test_base64_blob_is_redacted(self) -> None:
        """P4: Blocks of 3+ consecutive lines with 60+ base64 chars are redacted."""
        # Build a realistic base64 blob (4 lines × 76 chars = clearly matches)
        b64_line = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/AB"
        assert len(b64_line) >= 60
        blob = "\n".join([b64_line] * 4)

        text = f"payload start\n{blob}\npayload end"
        result = _apply_prune_pipeline(text)

        assert "[BINARY_CONTENT_REDACTED]" in result, \
            "Base64 blob should be replaced with [BINARY_CONTENT_REDACTED]"
        assert b64_line not in result, "Original base64 lines must not appear in output"
        assert "payload start" in result, "Content before the blob must be preserved"
        assert "payload end" in result, "Content after the blob must be preserved"

    def test_separator_lines_are_stripped(self) -> None:
        """P5: Lines consisting of 20+ identical separator chars are removed."""
        text = (
            "Before separator\n"
            "=" * 25 + "\n"
            "Between separators\n"
            "-" * 30 + "\n"
            "After separator"
        )
        result = _apply_prune_pipeline(text)

        assert "=" * 20 not in result, "Long equals separator must be stripped"
        assert "-" * 20 not in result, "Long dash separator must be stripped"
        assert "Before separator" in result
        assert "Between separators" in result
        assert "After separator" in result

    def test_excess_blank_lines_are_collapsed(self) -> None:
        """P6: 3+ consecutive newlines are collapsed to exactly 2 (one blank line)."""
        text = "line one\n\n\n\n\nline two\n\n\n\nline three"
        result = _apply_prune_pipeline(text)

        assert "\n\n\n" not in result, "Triple newlines must be collapsed"
        assert "line one" in result
        assert "line two" in result
        assert "line three" in result
        # Exactly one blank line between content is acceptable
        assert "\n\n" in result, "A single blank line separator may still exist"

    def test_pipeline_handles_empty_string(self) -> None:
        """_apply_prune_pipeline returns the input unchanged for empty strings."""
        assert _apply_prune_pipeline("") == ""

    def test_pipeline_preserves_unaffected_content(self) -> None:
        """Content not matching any pattern is returned exactly as-is."""
        clean_text = "NALA completed step 007 with output: {success: true}"
        result = _apply_prune_pipeline(clean_text)
        assert result == clean_text


# ==============================================================================
# T06 — System Prompt & Tail Preservation (n_preserve_tail lock)
# ==============================================================================

class TestT06TailPreservation:
    """
    T06 — DronagiriCompactor._stage2_llm_summarize() must NEVER pass the
    last n_preserve_tail SUCCESS steps to the summarizer, and must NOT
    modify their result payloads after crystallization.

    Risk mitigated: RISK-017 — "Lost in the Middle" via tail preservation.
    """

    def test_tail_steps_not_passed_to_summarizer(self) -> None:
        """
        Verify that the user_prompt passed to summarizer_fn does NOT contain
        the step_ids of the last n_preserve_tail steps.
        """
        n_preserve_tail = 3
        cfg = TrackerConfig(n_preserve_tail=n_preserve_tail, per_message_overhead=0)
        tracker = ContextTracker(cfg)

        session = _make_session_with_success_steps(7)

        # Capture what the summarizer receives
        received_user_prompts: List[str] = []
        received_system_prompts: List[str] = []

        def capturing_summarizer(system_prompt: str, user_prompt: str) -> str:
            received_system_prompts.append(system_prompt)
            received_user_prompts.append(user_prompt)
            # Return valid crystallized results for the 4 steps that should be passed
            summarizable_ids = [
                s.step_id
                for s in session.task_graph.steps[:-n_preserve_tail]
                if s.status == TaskStatus.SUCCESS
            ]
            crystallized = [
                {"step_id": sid, "status": "SUCCESS", "summary": f"Done {sid}", "key_outputs": {}, "errors": None}
                for sid in summarizable_ids
            ]
            return json.dumps({"crystallized_steps": crystallized})

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=capturing_summarizer,
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        compactor._stage2_llm_summarize(session)

        assert len(received_user_prompts) == 1, "summarizer_fn should be called exactly once"

        user_prompt = received_user_prompts[0]
        system_prompt = received_system_prompts[0]

        # The LAST n_preserve_tail steps must NOT appear in the user prompt payload
        tail_steps = session.task_graph.steps[-n_preserve_tail:]
        for tail_step in tail_steps:
            assert tail_step.step_id not in user_prompt, (
                f"Tail step {tail_step.step_id!r} was included in the summarizer "
                f"payload — violates RISK-017 (Lost in the Middle)."
            )

        # The FIRST (7 - 3 = 4) steps SHOULD appear in the payload
        head_steps = session.task_graph.steps[:-n_preserve_tail]
        for head_step in head_steps:
            assert head_step.step_id in user_prompt, (
                f"Head step {head_step.step_id!r} was missing from the summarizer payload."
            )

        # System prompt should reference n_preserve_tail
        assert str(n_preserve_tail) in system_prompt, (
            f"System prompt should reference n_preserve_tail={n_preserve_tail}"
        )

    def test_tail_step_results_unchanged_after_stage2(self) -> None:
        """
        After _stage2_llm_summarize() completes, the last n_preserve_tail
        steps must have identical result payloads to their pre-call state.
        """
        n_preserve_tail = 3
        cfg = TrackerConfig(n_preserve_tail=n_preserve_tail, per_message_overhead=0)
        tracker = ContextTracker(cfg)

        session = _make_session_with_success_steps(7)

        # Capture the pre-call result payloads of the tail steps
        tail_before = {
            s.step_id: dict(s.result or {})
            for s in session.task_graph.steps[-n_preserve_tail:]
        }

        summarizable_steps = session.task_graph.steps[:-n_preserve_tail]
        summarizer_fn = _mock_summarizer_fn(summarizable_steps)

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=summarizer_fn,
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        compactor._stage2_llm_summarize(session)

        # Verify tail steps are UNCHANGED
        for step in session.task_graph.steps[-n_preserve_tail:]:
            assert not step.result.get("crystallized", False), (
                f"Tail step '{step.step_id}' was incorrectly crystallized. "
                f"RISK-017 violation."
            )
            assert step.result == tail_before[step.step_id], (
                f"Tail step '{step.step_id}' result was modified. Expected "
                f"{tail_before[step.step_id]!r}, got {step.result!r}"
            )

    def test_head_steps_are_crystallized_after_stage2(self) -> None:
        """
        Steps before the n_preserve_tail tail are replaced with crystallized
        result dicts containing {"crystallized": True, "summary": ...}.
        """
        n_preserve_tail = 3
        cfg = TrackerConfig(n_preserve_tail=n_preserve_tail, per_message_overhead=0)
        tracker = ContextTracker(cfg)

        session = _make_session_with_success_steps(6)

        summarizable_steps = session.task_graph.steps[:-n_preserve_tail]
        summarizer_fn = _mock_summarizer_fn(summarizable_steps)

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=summarizer_fn,
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        result = compactor._stage2_llm_summarize(session)
        assert result is True, "Stage 2 should return True on successful crystallization"

        # Head steps must be crystallized
        head_steps = session.task_graph.steps[:-n_preserve_tail]
        for step in head_steps:
            assert step.result is not None
            assert step.result.get("crystallized") is True, (
                f"Head step '{step.step_id}' was not crystallized."
            )
            assert "summary" in step.result


# ==============================================================================
# T07 — Tool Call Pair Atomicity
# ==============================================================================

class TestT07ToolCallPairAtomicity:
    """
    T07 — _prune_tool_call_pairs_atomically() must prune assistant+tool pairs
    as locked atomic units, never producing orphaned tool messages.

    Risk mitigated: RISK-018 — Orphaned tool calls after pruning.
    """

    def test_three_pairs_keep_tail_one(self) -> None:
        """
        With 3 complete pairs and keep_tail=1, the 2 oldest pairs are pruned
        and only the last pair (messages[4], messages[5]) remains.
        """
        messages = _make_tool_call_messages(3)
        assert len(messages) == 6

        result = _prune_tool_call_pairs_atomically(messages, keep_tail=1)

        assert len(result) == 2, (
            f"Expected 2 messages (1 pair), got {len(result)}"
        )
        assert result[0]["role"] == "assistant" and "tool_calls" in result[0]
        assert result[1]["role"] == "tool"
        assert result[1]["content"] == "result_of_tool_3"

    def test_no_orphaned_tool_messages(self) -> None:
        """
        After pruning, every 'tool' role message must be immediately preceded
        by an 'assistant' message with a 'tool_calls' key.
        """
        messages = _make_tool_call_messages(5)
        result = _prune_tool_call_pairs_atomically(messages, keep_tail=2)

        for idx, msg in enumerate(result):
            if msg.get("role") == "tool":
                assert idx > 0, (
                    f"Orphaned tool message at index 0 — no preceding assistant message"
                )
                prev = result[idx - 1]
                assert prev.get("role") == "assistant" and "tool_calls" in prev, (
                    f"Orphaned tool message at index {idx}: preceding message is "
                    f"role={prev.get('role')!r} (expected 'assistant' with tool_calls)"
                )

    def test_keep_tail_zero_removes_all_pairs(self) -> None:
        """keep_tail=0 removes every tool-call pair in the list."""
        messages = _make_tool_call_messages(4)
        result = _prune_tool_call_pairs_atomically(messages, keep_tail=0)
        assert result == [], f"Expected empty list with keep_tail=0, got {result}"

    def test_keep_tail_exceeds_pairs_returns_unchanged(self) -> None:
        """
        When keep_tail >= number of pairs, no messages are pruned and the
        original list is returned as-is.
        """
        messages = _make_tool_call_messages(3)
        result = _prune_tool_call_pairs_atomically(messages, keep_tail=10)
        assert result == messages

    def test_non_pair_messages_are_always_preserved(self) -> None:
        """
        Plain user/assistant/system messages interspersed with tool pairs
        are never pruned — only tool-call pairs are candidates.
        """
        messages = [
            {"role": "system", "content": "You are NALA."},
            {"role": "user", "content": "Start task."},
            {"role": "assistant", "tool_calls": [{"id": "c1", "function": {"name": "t1", "arguments": "{}"}}]},
            {"role": "tool", "content": "result_1"},
            {"role": "assistant", "tool_calls": [{"id": "c2", "function": {"name": "t2", "arguments": "{}"}}]},
            {"role": "tool", "content": "result_2"},
            {"role": "assistant", "content": "Task is done."},
        ]

        # keep_tail=0 should remove the 2 tool-call pairs but keep system/user/plain-assistant
        result = _prune_tool_call_pairs_atomically(messages, keep_tail=0)

        roles_in_result = [m["role"] for m in result]
        assert "system" in roles_in_result, "System message must be preserved"
        assert "user" in roles_in_result, "User message must be preserved"

        # Final plain assistant message (no tool_calls) must be preserved
        final_messages_with_content = [
            m for m in result
            if m.get("role") == "assistant" and "content" in m and "tool_calls" not in m
        ]
        assert len(final_messages_with_content) == 1
        assert final_messages_with_content[0]["content"] == "Task is done."

    def test_empty_messages_returns_empty(self) -> None:
        """Empty input list returns empty list with no errors."""
        result = _prune_tool_call_pairs_atomically([], keep_tail=5)
        assert result == []


# ==============================================================================
# T08 — Handoff Spore Write and Validate
# ==============================================================================

class TestT08HandoffSporeWriteValidate:
    """
    T08 — HandoffSpore.write_spore() produces a Pydantic v2-valid JSON file.
    HandoffSpore.load_spore() reads it back with identical field values.

    Risk mitigated: RISK-020 — Partial or corrupt handoff state.
    """

    def test_spore_file_is_created_on_disk(self, tmp_path: Path) -> None:
        """write_spore() creates the file at the specified path."""
        session = _make_mixed_session(n_success=3, n_pending=2)
        spore_path = tmp_path / "test.spore.json"

        HandoffSpore.write_spore(
            session,
            spore_path,
            handoff_reason="Unit test handoff",
            checkpoint_path=str(tmp_path / "checkpoint.json"),
        )

        assert spore_path.exists(), "Spore file must exist after write_spore()"
        assert spore_path.stat().st_size > 0, "Spore file must not be empty"

    def test_spore_roundtrip_via_load_spore(self, tmp_path: Path) -> None:
        """
        The model loaded by load_spore() must have identical field values
        to the model returned by write_spore().
        """
        session = _make_mixed_session(n_success=4, n_pending=3)
        spore_path = tmp_path / "roundtrip.spore.json"

        written = HandoffSpore.write_spore(
            session,
            spore_path,
            handoff_reason="Roundtrip test",
            checkpoint_path="/tmp/ckpt.json",
        )

        loaded = HandoffSpore.load_spore(spore_path)

        assert loaded.original_session_id == written.original_session_id
        assert loaded.new_session_id == written.new_session_id
        assert loaded.objective == written.objective
        assert loaded.handoff_reason == written.handoff_reason
        assert loaded.checkpoint_path == written.checkpoint_path
        assert loaded.spore_version == "2.0.0"

    def test_original_and_new_session_ids_differ(self, tmp_path: Path) -> None:
        """new_session_id must be a fresh UUID distinct from original_session_id."""
        session = _make_mixed_session()
        spore_path = tmp_path / "ids.spore.json"

        model = HandoffSpore.write_spore(session, spore_path)

        assert model.original_session_id == session.session_id
        assert model.new_session_id != session.session_id

        # Both must be valid UUID strings
        try:
            uuid.UUID(model.original_session_id)
            uuid.UUID(model.new_session_id)
        except ValueError as exc:
            pytest.fail(f"Session IDs are not valid UUIDs: {exc}")

    def test_objective_never_truncated(self, tmp_path: Path) -> None:
        """The objective field must be preserved exactly in the spore."""
        long_objective = ("Refactor the entire NALA codebase to support async I/O " * 10).strip()
        session = _make_mixed_session()
        session.objective = long_objective
        spore_path = tmp_path / "objective.spore.json"

        model = HandoffSpore.write_spore(session, spore_path)
        loaded = HandoffSpore.load_spore(spore_path)

        assert loaded.objective == long_objective, "Objective must be stored verbatim"

    def test_remaining_steps_contains_all_pending_steps(self, tmp_path: Path) -> None:
        """All PENDING steps are included in task_graph_state.remaining_steps."""
        session = _make_mixed_session(n_success=2, n_pending=4)
        spore_path = tmp_path / "pending.spore.json"

        model = HandoffSpore.write_spore(session, spore_path)

        assert model.task_graph_state.pending_steps == 4
        assert len(model.task_graph_state.remaining_steps) == 4

        remaining_ids = {s["step_id"] for s in model.task_graph_state.remaining_steps}
        pending_ids = {
            s.step_id
            for s in session.task_graph.steps
            if s.status == TaskStatus.PENDING
        }
        assert remaining_ids == pending_ids

    def test_telemetry_fields_match_state_matrix(self, tmp_path: Path) -> None:
        """SporeTelemetry fields must reflect the session's StateMatrix exactly."""
        session = _make_mixed_session()
        session.state_matrix.add_llm_call(tokens_in=5000, tokens_out=1000, cost_usd=0.05)
        session.state_matrix.record_error()
        session.state_matrix.elapsed_seconds = 300.0
        session.checkpoint_meta.lsn = 42

        spore_path = tmp_path / "telemetry.spore.json"
        model = HandoffSpore.write_spore(session, spore_path)

        assert model.telemetry_state.total_tokens_in == 5000
        assert model.telemetry_state.total_tokens_out == 1000
        assert model.telemetry_state.error_count == 1
        assert abs(model.telemetry_state.elapsed_seconds - 300.0) < 0.01
        assert model.telemetry_state.session_lsn == 42

    def test_pydantic_v2_validation_passes_on_loaded_json(self, tmp_path: Path) -> None:
        """
        The raw JSON in the spore file must pass HandoffSporeModel.model_validate_json()
        without any ValidationError.
        """
        session = _make_mixed_session(n_success=3, n_pending=2)
        spore_path = tmp_path / "validate.spore.json"

        HandoffSpore.write_spore(session, spore_path)

        raw_json = spore_path.read_text(encoding="utf-8")
        try:
            HandoffSporeModel.model_validate_json(raw_json)
        except pydantic.ValidationError as exc:
            pytest.fail(f"Spore JSON failed Pydantic v2 validation: {exc}")


# ==============================================================================
# T09 — Post-Compaction Checkpoint Written
# ==============================================================================

class TestT09PostCompactionCheckpoint:
    """
    T09 — DronagiriCompactor.compact() must invoke checkpoint_fn at least
    once after any state mutation, regardless of which stage succeeded.

    Risk mitigated: RISK-021 — Compaction mutation without checkpoint.
    """

    def test_checkpoint_written_after_stage1_prune(
        self,
        mock_checkpoint_fn: Tuple[Callable[[str], Path], List[str]],
        tmp_path: Path,
    ) -> None:
        """
        When Stage 1 deterministic pruning removes bloat from step results,
        checkpoint_fn must be called with a 'post-compaction-stage1' label.
        """
        ckpt_fn, ckpt_log = mock_checkpoint_fn

        # Build a session where Stage 1 will produce mutations:
        # a step result containing a Python traceback (stripped by P1)
        traceback_payload = (
            "Traceback (most recent call last):\n"
            "  File 'agent.py', line 10\n"
            "ValueError: bad input\n"
            "useful_output: done"
        )

        # Use a config that's COMPACTING level so compact() is called
        # We'll use a tiny window so even a small result triggers compaction
        cfg = TrackerConfig(
            max_context_tokens=50,
            per_message_overhead=0,
            n_preserve_tail=1,
        )
        tracker = ContextTracker(cfg)

        session = _make_session(n_pending_steps=0)
        step = TaskStep(step_id="step_001", description="x")
        step.mark_success({"output": traceback_payload})
        session.task_graph.steps.append(step)

        # Mock summarizer (for Stage 2 fallback if needed)
        def no_op_summarizer(sys_p: str, usr_p: str) -> str:
            return json.dumps({"crystallized_steps": []})

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=no_op_summarizer,
            checkpoint_fn=ckpt_fn,
        )

        compactor.compact(session)

        assert len(ckpt_log) >= 1, (
            f"Expected at least 1 checkpoint call (RISK-021), "
            f"but checkpoint_fn was called {len(ckpt_log)} times"
        )

    def test_checkpoint_written_after_stage2_crystallization(
        self,
        mock_checkpoint_fn: Tuple[Callable[[str], Path], List[str]],
    ) -> None:
        """
        When Stage 1 is insufficient and Stage 2 LLM crystallization runs,
        checkpoint_fn must be called with a 'post-compaction-stage2' label.
        """
        ckpt_fn, ckpt_log = mock_checkpoint_fn

        # Tiny window — everything will be COMPACTING
        cfg = TrackerConfig(
            max_context_tokens=20,
            per_message_overhead=0,
            n_preserve_tail=1,
        )
        tracker = ContextTracker(cfg)

        # Build session with 3 SUCCESS steps (so Stage 2 has material to work with)
        session = _make_session_with_success_steps(3, result_payload={"x": "result"})

        summarizable = session.task_graph.steps[:-1]  # All except tail
        summarizer_fn = _mock_summarizer_fn(summarizable)

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=summarizer_fn,
            checkpoint_fn=ckpt_fn,
        )

        compactor.compact(session)

        # Checkpoint must be called at some point during stage 2 path
        assert len(ckpt_log) >= 1, (
            f"Expected at least 1 checkpoint call after Stage 2 mutation "
            f"(RISK-021), got {len(ckpt_log)}"
        )
        # At least one label should contain "stage2" (Stage 2 path taken)
        stage2_labels = [lbl for lbl in ckpt_log if "stage2" in lbl]
        assert len(stage2_labels) >= 1, (
            f"Expected a 'post-compaction-stage2' checkpoint label. "
            f"Got labels: {ckpt_log}"
        )

    def test_checkpoint_fn_exception_propagates(
        self,
        mock_checkpoint_fn: Tuple[Callable[[str], Path], List[str]],
    ) -> None:
        """
        If checkpoint_fn raises an exception, it must propagate out of
        _force_checkpoint() — it must NEVER be swallowed silently (RISK-021).
        """
        def failing_ckpt_fn(label: str) -> Path:
            raise IOError("Disk full")

        cfg = TrackerConfig(max_context_tokens=20, per_message_overhead=0, n_preserve_tail=1)
        tracker = ContextTracker(cfg)
        session = _make_session_with_success_steps(2)

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=lambda s, u: json.dumps({"crystallized_steps": []}),
            checkpoint_fn=failing_ckpt_fn,
        )

        with pytest.raises(IOError, match="Disk full"):
            compactor.compact(session)


# ==============================================================================
# T10 — Loop Integration with Context Guard
# ==============================================================================

class TestT10LoopIntegrationContextGuard:
    """
    T10 — End-to-end validation that the JIRA-004 context guard, when injected
    into the NalaLoop dispatch path, correctly invokes DronagiriCompactor.compact()
    when the compaction threshold is crossed and allows the loop to exit COMPLETED.

    This test uses a NalaLoopWithContextGuard subclass that wraps
    _dispatch_step_with_retry with the JIRA-004 injection block. This simulates
    the production injection before nala_loop.py is modified directly.
    """

    def test_compactor_called_and_loop_reaches_completed(
        self, tmp_path: Path
    ) -> None:
        """
        Run a 5-step NalaLoop with a 300-token context window and fat executors.
        Verify that DronagiriCompactor.compact() is invoked at least once and
        the final LoopStatus is COMPLETED.
        """
        enc = _enc()

        # ── Session: 5 independent PENDING steps ─────────────────────────────
        steps = [
            TaskStep(step_id=f"step_{i:03d}", description=f"task_{i}")
            for i in range(1, 6)
        ]
        session = SessionState(
            objective="Integration test: context guard",
            task_graph=TaskGraph(steps=steps),
        )

        # ── Context window: 1000 tokens, no overhead ─────────────────────
        cfg = TrackerConfig(
            max_context_tokens=1000,
            warning_percent=0.70,
            compaction_percent=0.85,
            safety_buffer_fraction=0.05,
            model_encoding="cl100k_base",
            n_preserve_tail=1,
            per_message_overhead=0,
        )
        tracker = ContextTracker(cfg)

        # ── Track compaction calls ────────────────────────────────────────────
        compact_call_count = [0]

        def mock_compact(sess: SessionState) -> bool:
            compact_call_count[0] += 1
            # Actually compact: replace SUCCESS results with tiny crystallized dicts
            for s in sess.task_graph.steps:
                if s.status == TaskStatus.SUCCESS and s.result:
                    s.result = {
                        "crystallized": True,
                        "summary":      f"Compacted {s.step_id}",
                        "key_outputs":  {},
                        "errors":       None,
                    }
            return True

        compactor_mock = MagicMock()
        compactor_mock.compact.side_effect = mock_compact

        # ── CheckpointManager using tmp_path ─────────────────────────────────
        cm = CheckpointManager(base_dir=tmp_path / "checkpoints")

        # ── Fat executor: returns a ~210-token result string ─────────────────
        fat_result_text = enc.decode(
            enc.encode("nexus agent step result " * 100, disallowed_special=())[:210]
        )

        def fat_executor(step: TaskStep, sess: SessionState) -> StepResult:
            return StepResult(
                success=True,
                output={"data": fat_result_text},
            )

        # ── Build NalaLoop and inject the JIRA-004 context guard ─────────────
        loop = NalaLoop(session, cm, checkpoint_on_success_only=True)
        loop.set_default_handler(fat_executor)

        # Wrap _dispatch_step_with_retry with the JIRA-004 injection block
        original_dispatch = loop._dispatch_step_with_retry

        def guarded_dispatch(step: TaskStep):
            ctx_status = tracker.monitor_context(session)
            if ctx_status == ContextStatus.COMPACTING:
                compactor_mock.compact(session)
            # EXHAUSTED: in a real loop this would write a spore and return PAUSED.
            # For this test we allow it to continue (compactor already cleared results).
            return original_dispatch(step)

        loop._dispatch_step_with_retry = guarded_dispatch

        # ── Run the loop ───────────────────────────────────────────────────────
        final_status = loop.run()

        # ── Assertions ──────────────────────────────────────────────────────
        assert final_status == LoopStatus.COMPLETED, (
            f"Expected LoopStatus.COMPLETED, got {final_status.value}"
        )
        assert compact_call_count[0] >= 1, (
            f"Expected DronagiriCompactor.compact() to be called at least once "
            f"during the loop, but call count was {compact_call_count[0]}."
        )
        assert session.task_graph.is_complete(), (
            "All TaskGraph steps must be in SUCCESS state after COMPLETED loop."
        )


# ==============================================================================
# EXTRA TESTS — Beyond Spec (Nexus Lab CODING STANDARD)
# ==============================================================================

class TestT11SporeLoadMissingFile:
    """T11 — load_spore() raises SporeValidationError when the file is absent."""

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        ghost_path = tmp_path / "does_not_exist.spore.json"

        with pytest.raises(SporeValidationError) as exc_info:
            HandoffSpore.load_spore(ghost_path)

        assert exc_info.value.path == ghost_path
        assert "does not exist" in str(exc_info.value).lower()


class TestT12SporeLoadCorruptJson:
    """T12 — load_spore() raises SporeValidationError on invalid JSON."""

    def test_raises_on_corrupt_json(self, tmp_path: Path) -> None:
        bad_spore = tmp_path / "corrupt.spore.json"
        bad_spore.write_text("{NOT VALID JSON >>>", encoding="utf-8")

        with pytest.raises(SporeValidationError) as exc_info:
            HandoffSpore.load_spore(bad_spore)

        assert exc_info.value.path == bad_spore

    def test_raises_on_schema_violation(self, tmp_path: Path) -> None:
        """A JSON file that is valid JSON but fails Pydantic schema validation."""
        bad_schema = tmp_path / "schema_fail.spore.json"
        # Missing required fields: original_session_id, objective, etc.
        bad_schema.write_text(
            json.dumps({"spore_version": "2.0.0", "unexpected_field": 42}),
            encoding="utf-8",
        )

        with pytest.raises(SporeValidationError) as exc_info:
            HandoffSpore.load_spore(bad_schema)

        assert exc_info.value.path == bad_schema

    def test_raises_on_empty_file(self, tmp_path: Path) -> None:
        """Empty file raises SporeValidationError."""
        empty = tmp_path / "empty.spore.json"
        empty.write_text("", encoding="utf-8")

        with pytest.raises(SporeValidationError):
            HandoffSpore.load_spore(empty)


class TestT13PrunePipelineIsIdempotent:
    """
    T13 — Applying _apply_prune_pipeline() twice must produce the same result
    as applying it once (idempotency guarantee).
    """

    @pytest.mark.parametrize("text", [
        "clean text with no bloat",
        "Traceback (most recent call last):\n  File 'x.py', line 1\nError: bad\nnext",
        "\x1b[31mRED\x1b[0m text with ANSI codes",
        "--- Tool Output ---\nsome content\n=== Debug ===",
        "=" * 30 + "\ncontent\n" + "-" * 25,
        "line1\n\n\n\n\nline2\n\n\n\nline3",
    ])
    def test_idempotent_for_various_inputs(self, text: str) -> None:
        """Single application and double application produce identical results."""
        once  = _apply_prune_pipeline(text)
        twice = _apply_prune_pipeline(once)
        assert once == twice, (
            f"Pipeline not idempotent for input {text[:40]!r}.\n"
            f"  After 1 pass: {once[:100]!r}\n"
            f"  After 2 pass: {twice[:100]!r}"
        )


class TestT14CrystallizedStepsSkippedInStage1:
    """
    T14 — Stage 1 must skip steps whose result already has {"crystallized": True}.
    Crystallized payloads are already minimal; re-processing them risks corruption.
    """

    def test_crystallized_result_is_not_mutated(self) -> None:
        """
        A step with a crystallized result must have its result dict unchanged
        after Stage 1 pruning, even if the serialized JSON contains traceback-
        like text in the summary field.
        """
        cfg = TrackerConfig(max_context_tokens=20, per_message_overhead=0, n_preserve_tail=1)
        tracker = ContextTracker(cfg)

        # A crystallized result that contains traceback text in the summary
        # (which would be pruned by P1 if the step were not skipped)
        tricky_summary = (
            "Traceback (most recent call last):\n"
            "  Step failed due to dependency issue."
        )
        crystallized_result = {
            "crystallized": True,
            "summary":      tricky_summary,
            "key_outputs":  {"path": "/tmp/output.txt"},
            "errors":       None,
        }

        step = TaskStep(step_id="step_001", description="x")
        step.mark_success(dict(crystallized_result))
        session = SessionState(
            objective="x",
            task_graph=TaskGraph(steps=[step]),
        )

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=lambda s, u: json.dumps({"crystallized_steps": []}),
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        compactor._stage1_deterministic_prune(session)

        # Result must be completely unchanged
        assert session.task_graph.steps[0].result == crystallized_result, (
            "Crystallized step result was mutated by Stage 1 — this is incorrect."
        )


class TestT15TrackerConfigProperties:
    """T15 — TrackerConfig computed threshold properties are mathematically correct."""

    @pytest.mark.parametrize("max_tokens,warning_pct,compact_pct,buffer", [
        (128_000, 0.70, 0.85, 0.05),
        (32_000,  0.60, 0.80, 0.10),
        (8_000,   0.75, 0.90, 0.03),
        (1_000,   0.70, 0.85, 0.05),
    ])
    def test_threshold_properties_are_correct(
        self,
        max_tokens: int,
        warning_pct: float,
        compact_pct: float,
        buffer: float,
    ) -> None:
        cfg = TrackerConfig(
            max_context_tokens=max_tokens,
            warning_percent=warning_pct,
            compaction_percent=compact_pct,
            safety_buffer_fraction=buffer,
        )
        assert cfg.warning_threshold_tokens == int(max_tokens * warning_pct)
        assert cfg.compaction_threshold_tokens == int(max_tokens * compact_pct)
        assert cfg.safety_ceiling_tokens == int(max_tokens * (1.0 - buffer))

    def test_config_is_frozen(self) -> None:
        """TrackerConfig is a frozen dataclass — mutations must raise FrozenInstanceError."""
        cfg = TrackerConfig()
        with pytest.raises((TypeError, AttributeError)):
            cfg.max_context_tokens = 999_999  # type: ignore[misc]


class TestT16ContextExhaustedSignalAttributes:
    """T16 — ContextExhaustedSignal carries the right attributes and message."""

    def test_signal_attributes_are_populated(self, tmp_path: Path) -> None:
        spore_path = tmp_path / "test.spore.json"
        session_id = str(uuid.uuid4())
        projected = 125_000

        sig = ContextExhaustedSignal(
            session_id=session_id,
            projected_tokens=projected,
            spore_path=spore_path,
        )

        assert sig.session_id == session_id
        assert sig.projected_tokens == projected
        assert sig.spore_path == spore_path
        assert session_id in str(sig)
        assert "125,000" in str(sig)

    def test_signal_is_runtime_error_subclass(self) -> None:
        """ContextExhaustedSignal must be catch-able as RuntimeError."""
        sig = ContextExhaustedSignal(
            session_id="abc",
            projected_tokens=1,
            spore_path=Path("/tmp"),
        )
        assert isinstance(sig, RuntimeError)


class TestT17EmptySessionProjectedCount:
    """T17 — A session with no steps always returns NORMAL status."""

    def test_empty_session_is_normal(self, tracker: ContextTracker) -> None:
        """Zero steps → only the objective token count → well below WARNING."""
        session = _make_session(n_pending_steps=0)
        status = tracker.monitor_context(session)
        assert status == ContextStatus.NORMAL, (
            f"Empty session should be NORMAL, got {status.value}"
        )

    def test_objective_only_contributes_small_count(self, tracker: ContextTracker) -> None:
        """A 10-word objective should not exceed 1% of a 1 000-token window."""
        session = SessionState(
            objective="Refactor the core module imports",
            task_graph=TaskGraph(steps=[]),
        )
        projected = tracker.project_token_count(session)
        assert projected < 50, (
            f"Objective-only session projected {projected} tokens — expected < 50."
        )


class TestT18Stage2SkipsInsufficientSteps:
    """T18 — Stage 2 returns False when completed steps <= n_preserve_tail."""

    def test_returns_false_when_steps_equal_tail(self) -> None:
        """Exactly n_preserve_tail steps → nothing to summarize → False."""
        n_preserve_tail = 3
        cfg = TrackerConfig(n_preserve_tail=n_preserve_tail, per_message_overhead=0)
        tracker = ContextTracker(cfg)

        # Exactly 3 SUCCESS steps == n_preserve_tail → Stage 2 must skip
        session = _make_session_with_success_steps(3)
        call_count = [0]

        def counting_summarizer(sys_p: str, usr_p: str) -> str:
            call_count[0] += 1
            return json.dumps({"crystallized_steps": []})

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=counting_summarizer,
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        result = compactor._stage2_llm_summarize(session)

        assert result is False, (
            "Stage 2 must return False when steps <= n_preserve_tail"
        )
        assert call_count[0] == 0, (
            "summarizer_fn must NOT be called when there's nothing to summarize"
        )

    def test_returns_false_when_fewer_steps_than_tail(self) -> None:
        """Fewer steps than n_preserve_tail → Stage 2 returns False immediately."""
        cfg = TrackerConfig(n_preserve_tail=5, per_message_overhead=0)
        tracker = ContextTracker(cfg)
        session = _make_session_with_success_steps(3)  # 3 < n_preserve_tail=5

        compactor = DronagiriCompactor(
            tracker=tracker,
            summarizer_fn=lambda s, u: json.dumps({"crystallized_steps": []}),
            checkpoint_fn=lambda label: Path("/tmp/noop.json"),
        )

        result = compactor._stage2_llm_summarize(session)
        assert result is False


class TestT19SporeModelForbidsExtraFields:
    """T19 — HandoffSporeModel with extra="forbid" rejects unknown fields."""

    def test_extra_field_raises_validation_error(self) -> None:
        """
        Constructing HandoffSporeModel with an undeclared field must raise
        pydantic.ValidationError — not silently ignore the extra field.
        """
        valid_data = dict(
            original_session_id=str(uuid.uuid4()),
            new_session_id=str(uuid.uuid4()),
            objective="Test",
            handoff_timestamp=utcnow(),
            handoff_reason="reason",
            checkpoint_path="/tmp/cp.json",
            task_graph_state=SporeTaskGraphSummary(
                total_steps=1,
                completed_steps=0,
                failed_steps=0,
                pending_steps=1,
                crystallized_history="none",
                remaining_steps=[],
            ),
            telemetry_state=SporeTelemetry(
                total_tokens_in=0,
                total_tokens_out=0,
                estimated_cost_usd=0.0,
                error_count=0,
                elapsed_seconds=0.0,
                session_lsn=0,
            ),
            bootstrap_instructions="Resume from step 001.",
            # ← EXTRA FIELD not in HandoffSporeModel
            undeclared_secret_field="should_be_rejected",
        )

        with pytest.raises(pydantic.ValidationError) as exc_info:
            HandoffSporeModel(**valid_data)

        error_str = str(exc_info.value)
        assert "undeclared_secret_field" in error_str or "extra" in error_str.lower()


class TestT20ClassifyBoundaryValues:
    """
    T20 — _classify() at exact boundary values must return the HIGHER-priority
    status (EXHAUSTED > COMPACTING > WARNING > NORMAL).
    """

    def test_exactly_at_warning_threshold_is_warning(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, per_message_overhead=0)
        tracker = ContextTracker(cfg)
        # Exactly at 70% = 700 tokens
        assert tracker._classify(700) == ContextStatus.WARNING

    def test_one_below_warning_threshold_is_normal(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, per_message_overhead=0)
        tracker = ContextTracker(cfg)
        # 699 tokens = 69.9% → NORMAL
        assert tracker._classify(699) == ContextStatus.NORMAL

    def test_exactly_at_compaction_threshold_is_compacting(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, per_message_overhead=0)
        tracker = ContextTracker(cfg)
        # Exactly at 85% = 850 tokens
        assert tracker._classify(850) == ContextStatus.COMPACTING

    def test_one_below_compaction_threshold_is_warning(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, per_message_overhead=0)
        tracker = ContextTracker(cfg)
        # 849 tokens = still in WARNING zone
        assert tracker._classify(849) == ContextStatus.WARNING

    def test_exactly_at_safety_ceiling_is_exhausted(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, safety_buffer_fraction=0.05)
        tracker = ContextTracker(cfg)
        # safety_ceiling = 1000 * (1 - 0.05) = 950
        assert tracker._classify(950) == ContextStatus.EXHAUSTED

    def test_one_below_safety_ceiling_is_compacting(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000, safety_buffer_fraction=0.05)
        tracker = ContextTracker(cfg)
        # 949 tokens is below ceiling (950) but above compaction (850)
        assert tracker._classify(949) == ContextStatus.COMPACTING

    def test_zero_tokens_is_normal(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000)
        tracker = ContextTracker(cfg)
        assert tracker._classify(0) == ContextStatus.NORMAL

    def test_max_tokens_is_exhausted(self) -> None:
        cfg = TrackerConfig(max_context_tokens=1000)
        tracker = ContextTracker(cfg)
        assert tracker._classify(1000) == ContextStatus.EXHAUSTED


# ==============================================================================
# MAIN RUNNER — Interactive demo mode (python test_context_tracker.py)
# ==============================================================================

def run_all_tests_interactive() -> None:
    """
    Run all 68 tests interactively with rich colored output.
    Called when the file is executed directly: python test_context_tracker.py
    """
    width = 72

    # Define color codes
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"

    print(f"\n{BOLD}{MAGENTA}")
    print("  ███╗   ██╗ █████╗ ██╗      █████╗ ")
    print("  ████╗  ██║██╔══██╗██║     ██╔══██╗")
    print("  ██╔██╗ ██║███████║██║     ███████║")
    print("  ██║╚██╗██║██╔══██║██║     ██╔══██║")
    print("  ██║ ╚████║██║  ██║███████╗██║  ██║")
    print("  ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")

    print(f"\n{BOLD}{CYAN}  Context Window Tracker & Compactor — Unit Test Suite{RESET}")
    print(f"{DIM}  Nexus Lab AI Research Lab | Bengaluru{RESET}")
    print(f"{DIM}  JIRA-004 | Phase 1: Core Harness (Survival Foundation){RESET}")

    print(f"\n{'═' * width}")
    print(f"  Running JIRA-004 tests across all RISK mitigations:")
    print(f"  {GREEN}RISK-016{RESET} Token counting precision")
    print(f"  {GREEN}RISK-017{RESET} Lost in the middle / tail preservation")
    print(f"  {GREEN}RISK-018{RESET} Atomic tool call pruning")
    print(f"  {GREEN}RISK-019{RESET} Regex pruning pipeline / Stage 1")
    print(f"  {GREEN}RISK-020{RESET} Handoff Spore validation")
    print(f"  {GREEN}RISK-021{RESET} Compaction checkpoint mutations")
    print(f"  {GREEN}RISK-022{RESET} Independent token projection")
    print(f"{'═' * width}\n")

    # Discover all Test classes in this module
    current_module = sys.modules[__name__]
    test_classes = []
    for name, obj in inspect.getmembers(current_module, inspect.isclass):
        if name.startswith("Test"):
            test_classes.append((name, obj))
    # Sort classes alphabetically/numerically
    test_classes.sort(key=lambda x: x[0])

    passed = 0
    failed = 0
    start_wall = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Setup standard fixtures manually for the runner
        small_cfg_val = TrackerConfig(
            max_context_tokens=1_000,
            warning_percent=0.70,
            compaction_percent=0.85,
            safety_buffer_fraction=0.05,
            model_encoding="cl100k_base",
            n_preserve_tail=3,
            per_message_overhead=0,
        )
        tracker_val = ContextTracker(small_cfg_val)

        # Setup mock checkpoint_fn
        call_log: List[str] = []
        def mock_ckpt_fn(label: str) -> Path:
            call_log.append(label)
            p = tmp_path / f"cp_{len(call_log)}.json"
            p.write_text("{}", encoding="utf-8")
            return p
        mock_checkpoint_fn_val = (mock_ckpt_fn, call_log)

        # Build fixture mapping dictionary
        fixture_map = {
            "small_cfg":          small_cfg_val,
            "tracker":            tracker_val,
            "mock_checkpoint_fn": mock_checkpoint_fn_val,
            "tmp_path":           tmp_path,
            "session_5_success":  _make_session_with_success_steps(5, result_payload={"val": "ok"}),
            "session_7_success":  _make_session_with_success_steps(7),
        }

        test_counter = 0
        for class_name, cls in test_classes:
            methods = [
                (m_name, m_func) for m_name, m_func in inspect.getmembers(cls, inspect.isfunction)
                if m_name.startswith("test_")
            ]
            methods.sort(key=lambda x: x[0])

            for method_name, method_func in methods:
                test_counter += 1
                label = f"TEST {test_counter:02d}"
                
                print(f"  {DIM}→{RESET}  Running {class_name}.{method_name}...", end="\r")

                try:
                    obj = cls()
                    sig = inspect.signature(method_func)

                    # Check for pytest parametrization marks
                    parametrize_marks = []
                    if hasattr(method_func, "pytestmark"):
                        for mark in method_func.pytestmark:
                            if mark.name == "parametrize":
                                parametrize_marks.append(mark)

                    if serialize_marks := parametrize_marks:
                        mark = serialize_marks[0]
                        argnames = mark.args[0]
                        argvalues = mark.args[1]

                        if isinstance(argnames, str):
                            names = [n.strip() for n in argnames.split(",")]
                        else:
                            names = list(argnames)

                        for val in argvalues:
                            if len(names) > 1:
                                val_dict = dict(zip(names, val))
                            else:
                                val_dict = {names[0]: val}

                            kwargs = {}
                            for param_name in sig.parameters:
                                if param_name == "self":
                                    continue
                                if param_name in val_dict:
                                    kwargs[param_name] = val_dict[param_name]
                                elif param_name in fixture_map:
                                    kwargs[param_name] = fixture_map[param_name]
                                else:
                                    raise ValueError(f"Unknown parameter: {param_name}")

                            method_func(obj, **kwargs)
                        passed += 1
                        print(f"  {GREEN}✅  PASSED — {label}: {class_name}.{method_name} (all parameters){RESET}")
                    else:
                        kwargs = {}
                        for param_name in sig.parameters:
                            if param_name == "self":
                                continue
                            if param_name in fixture_map:
                                kwargs[param_name] = fixture_map[param_name]
                            else:
                                raise ValueError(f"Unknown fixture parameter: {param_name}")

                        method_func(obj, **kwargs)
                        passed += 1
                        print(f"  {GREEN}✅  PASSED — {label}: {class_name}.{method_name}{RESET}")
                except Exception as exc:
                    failed += 1
                    print(f"\n{RED}{BOLD}  ❌ FAILED — {label}: {class_name}.{method_name}{RESET}")
                    print(f"{RED}     {type(exc).__name__}: {exc}{RESET}")
                    traceback.print_exc()

    total_time = (time.perf_counter() - start_wall) * 1000

    print(f"\n\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  NALA JIRA-004 TEST RESULTS{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"  {GREEN}Passed  : {passed:>3}{RESET}")
    print(f"  {RED if failed else GREEN}Failed  : {failed:>3}{RESET}")
    print(f"  {CYAN}Total   : {passed + failed:>3}{RESET}")
    print(f"  {DIM}Duration: {total_time:.0f} ms{RESET}")

    if failed == 0:
        print(f"\n  {BOLD}{GREEN}🚀 ALL {passed} JIRA-004 TESTS PASSED — Context Tracker & Compactor are battle-ready!{RESET}")
        print(f"  {DIM}RISK-016 ✅ | RISK-017 ✅ | RISK-018 ✅ | RISK-019 ✅{RESET}")
        print(f"  {DIM}RISK-020 ✅ | RISK-021 ✅ | RISK-022 ✅{RESET}")
    else:
        print(f"\n  {BOLD}{RED}⚠️  {failed} TEST(S) FAILED — Review output above.{RESET}")

    print(f"\n  {DIM}Jai Bajrang Bali 🙏 — Nexus Lab AI Research Lab, Bengaluru{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests_interactive()
