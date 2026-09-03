"""
Unit tests for the RtaFeedbackLoop in core/safety/rta_feedback_loop.py.
"""

from __future__ import annotations

import json
import os
import time
import pytest
from unittest.mock import MagicMock, patch

from core.safety.rta_feedback_loop import (
    RtaFeedbackLoop,
    DustaraEstimator,
    AnandaEstimator,
    _LayerHolder
)
from fleet.coordinator import OperationMode


@pytest.fixture
def temp_ledger(tmp_path):
    """Fixture providing a temporary ledger file path."""
    return str(tmp_path / "test_feedback_ledger.jsonl")


def test_estimators_ema_logic():
    """Test EMA estimators clamp and normalize values properly."""
    # Test Dustara complexity estimator (max steps = 10)
    dustara = DustaraEstimator(max_steps=10.0, alpha=0.5)
    assert dustara.get() == 0.0

    # Feed a sample of 8 steps (EMA: 0.5 * 8.0 + 0.5 * 0.0 = 4.0 -> normalized: 4.0/10.0 = 0.4)
    dustara.update_steps(8)
    assert abs(dustara.get() - 0.4) < 0.01

    # Clamp check: feeding 15 steps should clamp to max_steps=10
    dustara.update_steps(15)
    # EMA: 0.5 * 10.0 + 0.5 * 4.0 = 7.0 -> normalized: 7.0/10.0 = 0.7
    assert abs(dustara.get() - 0.7) < 0.01

    # Test Ananda latency estimator (max latency = 30)
    ananda = AnandaEstimator(max_latency_sec=30.0, alpha=0.2)
    assert ananda.get() == 0.0
    ananda.update_latency(15.0)
    # EMA: 0.2 * 15.0 + 0.8 * 0.0 = 3.0 -> normalized: 3.0/30.0 = 0.1
    assert abs(ananda.get() - 0.1) < 0.01


def test_rta_score_calculation_and_clamping(temp_ledger):
    """Test that Rta-Score computes correctly and is clamped to [0.0, 1.0]."""
    # Mock safety layers to return fixed values
    mock_viveka = MagicMock()
    mock_viveka._transition_success_rate = 0.8

    mock_satya = MagicMock()
    mock_satya._truthfulness_metrics.truthfulness_score = 0.9

    with patch.object(_LayerHolder, 'viveka', return_value=mock_viveka), \
         patch.object(_LayerHolder, 'satya', return_value=mock_satya):

        # Setup loop with custom estimators
        dustara = DustaraEstimator(max_steps=10.0, alpha=1.0)
        ananda = AnandaEstimator(max_latency_sec=10.0, alpha=1.0)
        
        loop = RtaFeedbackLoop(
            eval_interval=0.1,
            dustara_estimator=dustara,
            ananda_estimator=ananda,
            ledger_path=temp_ledger
        )

        # Set low complexity values (D = 0.1, A = 0.1 -> denominator = 0.2)
        # Score formula: (0.8 * 0.9) / 0.2 = 0.72 / 0.2 = 3.6 -> Clamped to 1.0!
        dustara.update_steps(1)  # 1/10 = 0.1
        ananda.update_latency(1)  # 1/10 = 0.1
        
        loop.force_evaluation()
        score, components = loop.get_latest()
        
        assert score == 1.0  # Must be clamped to 1.0
        assert components["viveka"] == 0.8
        assert components["satya"] == 0.9
        assert components["dustara"] == pytest.approx(0.1)
        assert components["ananda"] == pytest.approx(0.1)

        # Set higher complexity values (D = 0.8, A = 0.7 -> denominator = 1.5)
        # Score formula: (0.8 * 0.9) / 1.5 = 0.72 / 1.5 = 0.48
        dustara.update_steps(8)  # 0.8
        ananda.update_latency(7)  # 0.7
        
        loop.force_evaluation()
        score, _ = loop.get_latest()
        assert abs(score - 0.48) < 0.01


def test_pub_sub_observer_pattern(temp_ledger):
    """Test subscribing and unsubscribing from the feedback loop."""
    loop = RtaFeedbackLoop(eval_interval=0.1, ledger_path=temp_ledger)
    
    callbacks_received = []
    def on_eval(score, components):
        callbacks_received.append((score, components))

    # Subscribe callback
    unsubscribe_fn = loop.subscribe(on_eval)
    
    # Run evaluation
    loop.force_evaluation()
    assert len(callbacks_received) == 1
    
    # Unsubscribe callback
    unsubscribe_fn()
    loop.force_evaluation()
    assert len(callbacks_received) == 1  # Should not have increased


def test_thread_lifecycle_immediate_shutdown(temp_ledger):
    """Test starting the feedback loop, running ticks, and stopping immediately."""
    loop = RtaFeedbackLoop(eval_interval=5.0, ledger_path=temp_ledger)  # Long sleep interval
    
    assert loop._running is False
    loop.start()
    assert loop._running is True
    assert loop._thread is not None
    assert loop._thread.is_alive()
    
    # Measure stop latency
    start_time = time.time()
    loop.stop()
    stop_latency = time.time() - start_time
    
    # Verify the thread stopped instantly due to the stop event rather than waiting 5 seconds
    assert loop._running is False
    assert stop_latency < 1.0  # Should be near-instantaneous (< 1.0 second)
    assert not loop._thread.is_alive()


def test_ledger_logging(temp_ledger):
    """Test that each evaluation tick writes a valid JSON log entry to the ledger."""
    loop = RtaFeedbackLoop(eval_interval=0.1, ledger_path=temp_ledger)
    
    if os.path.exists(temp_ledger):
        os.remove(temp_ledger)

    loop.force_evaluation()
    
    # Verify file was written
    assert os.path.exists(temp_ledger)
    with open(temp_ledger, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert "timestamp" in record
        assert "viveka" in record
        assert "satya" in record
        assert "dustara" in record
        assert "ananda" in record
        assert "rta" in record
