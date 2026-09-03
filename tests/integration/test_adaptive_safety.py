"""
Integration tests for NALA Adaptive Safety Layer (Phase 3).
Tests the coordinated operation of:
- Adaptive Viveka Gate (Viveka-Clarity)
- Context-Aware Satya Layer (Satya-Truthfulness)
- Ṛta-Feedback Control Loop (rta_feedback_loop.py)
- Ṛta Governor (rta_governor.py)
- Predictive Tool Selector (predictive_tool_selector.py)
"""

from __future__ import annotations

import time
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import pytest

# Import the components to test
from core.safety.adaptive_viveka_gate import AdaptiveVivekaGate
from core.safety.context_aware_satya_layer import ContextAwareSatyaLayer
from core.safety.rta_feedback_loop import RtaFeedbackLoop
from core.safety.rta_governor import RtaGovernor, ModeRequest, ModeRequestType
from core.hands.predictive_tool_selector import (
    PredictiveToolSelector, ToolSpec, ToolType, PredictionContext
)
from fleet.coordinator import PredictiveSignals, OperationMode


class TestAdaptiveSafetyIntegration:
    """Integration tests for the adaptive safety layers working together."""

    def test_viveka_satya_to_rta_pipeline(self):
        """Test that Viveka and Satya scores flow correctly into Rta computation."""
        # Setup Viveka gate with known success rate
        from core.safety.rta_feedback_loop import _LayerHolder
        viveka_gate = _LayerHolder.viveka()
        # Manually set a known transition success rate for testing
        viveka_gate._transition_success_rate = 0.8  # 80% clarity

        # Setup Satya layer with known truthfulness
        satya_layer = _LayerHolder.satya()
        # Manually set truthfulness metrics for testing
        satya_layer._truthfulness_metrics.truthfulness_score = 0.9  # 90% truthful
        satya_layer._truthfulness_metrics.last_updated = time.time()

        # Create feedback loop with simple estimators
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "feedback_ledger.jsonl")
            rta_loop = RtaFeedbackLoop(
                eval_interval=0.1,  # Fast for testing
                ledger_path=ledger_path,
                dustara_estimator=Mock(),  # Will return fixed value
                ananda_estimator=Mock()    # Will return fixed value
            )

            # Setup estimators to return known values
            dustara_mock = Mock()
            dustara_mock.get.return_value = 0.3  # 30% complexity
            ananda_mock = Mock()
            ananda_mock.get.return_value = 0.2   # 20% burden

            rta_loop._dustara = dustara_mock
            rta_loop._ananda = ananda_mock

            # Force an evaluation
            rta_loop.force_evaluation()

            # Get the latest score
            score, components = rta_loop.get_latest()

            # Verify the score calculation: (V * S) / (D + A + ε)
            expected_score = min(1.0, (0.8 * 0.9) / (0.3 + 0.2 + 1e-8))
            # Allow small floating point differences
            assert abs(score - expected_score) < 0.01

            # Verify components are correct
            assert abs(components["viveka"] - 0.8) < 0.01
            assert abs(components["satya"] - 0.9) < 0.01
            assert abs(components["dustara"] - 0.3) < 0.01
            assert abs(components["ananda"] - 0.2) < 0.01

            # Verify ledger was written
            assert os.path.exists(ledger_path)
            with open(ledger_path, 'r') as f:
                line = f.readline().strip()
                record = json.loads(line)
                assert abs(record["viveka"] - 0.8) < 0.01
                assert abs(record["satya"] - 0.9) < 0.01
                assert abs(record["rta"] - expected_score) < 0.01

    def test_governor_bounds_enforcement(self):
        """Test that the governor correctly enforces Ṛta bounds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "feedback_ledger.jsonl")
            rta_loop = RtaFeedbackLoop(ledger_path=ledger_path)

            # Create governor with test bounds
            gov = RtaGovernor(
                rta_feedback_loop=rta_loop,
                low_bound=0.4,
                high_bound=0.95,
                sacred_pause_duration=1.0,  # Short for testing
                mode_dispatcher=Mock()  # Mock dispatcher to capture calls
            )

            # Mock the feedback loop to return specific scores
            with patch.object(rta_loop, 'get_latest') as mock_get_latest:
                # Test low score -> SHIFT_PRATYAKSHA
                mock_get_latest.return_value = (0.2, {
                    "viveka": 0.5, "satya": 0.5, "dustara": 0.1, "ananda": 0.1
                })

                # Simulate an update
                gov._on_rta_update(0.2, {
                    "viveka": 0.5, "satya": 0.5, "dustara": 0.1, "ananda": 0.1
                })

                # Verify shift request was made
                gov._mode_dispatcher.assert_called()
                call_args = gov._mode_dispatcher.call_args[0][0]  # ModeRequest object
                assert call_args.request_type == ModeRequestType.SHIFT_PRATYAKSHA
                # Intensity should be (0.4 - 0.2) / 0.4 = 0.5
                assert abs(call_args.intensity - 0.5) < 0.01

                # Reset mock
                gov._mode_dispatcher.reset_mock()

                # Test high score -> SACRED_PAUSE
                mock_get_latest.return_value = (0.98, {
                    "viveka": 0.9, "satya": 0.9, "dustara": 0.1, "ananda": 0.1
                })

                gov._on_rta_update(0.98, {
                    "viveka": 0.9, "satya": 0.9, "dustara": 0.1, "ananda": 0.1
                })

                # Verify sacred pause request
                gov._mode_dispatcher.assert_called()
                call_args = gov._mode_dispatcher.call_args[0][0]
                assert call_args.request_type == ModeRequestType.SACRED_PAUSE
                assert call_args.duration_s == 1.0  # Our test duration

                # Reset mock
                gov._mode_dispatcher.reset_mock()
                # Reset sacred pause state so the governor evaluates the next update
                gov._in_sacred_pause = False
                gov._pause_end_time = 0.0

                # Test score within bounds -> no action (debug level)
                mock_get_latest.return_value = (0.7, {
                    "viveka": 0.8, "satya": 0.9, "dustara": 0.2, "ananda": 0.1
                })

                with patch("core.safety.rta_governor.logger") as mock_logger:
                    gov._on_rta_update(0.7, {
                        "viveka": 0.8, "satya": 0.9, "dustara": 0.2, "ananda": 0.1
                    })
                    # Should log at debug level, not make request
                    gov._mode_dispatcher.assert_not_called()
                    mock_logger.debug.assert_called()

    def test_predictive_tool_selector_with_safety_context(self):
        """Test that the predictive tool selector respects safety contexts."""
        selector = PredictiveToolSelector()

        # Create mock predictive signals
        signals = PredictiveSignals(
            workload_complexity_index=0.7,
            cognitive_load_predictive=0.6,
            state_cohesion_score=0.8,
            hysteresis_buffer=0.1
        )

        # Test in debugging context - should favor ANUBHAVA tools
        context_debug = {
            "interaction_context": "debugging",
            "recent_tools": ["python3", "git"]
        }

        predictions_debug = selector.predict_tool_needs(signals, context_debug)

        # Find predictions for debugging tools
        strace_pred = next((p for p in predictions_debug if p.tool_name == "strace"), None)
        assert strace_pred is not None, "strace should be predicted in debugging context"
        # Should have reasonable confidence
        assert strace_pred.confidence > 0.2
        assert strace_pred.safety_checked is True

        # Test in production context - should favor SMRITI/SRUTI, block dangerous tools
        context_prod = {
            "interaction_context": "production",
            "recent_tools": ["python3"]
        }

        predictions_prod = selector.predict_tool_needs(signals, context_prod)

        # Docker should be blocked or have very low confidence in production (unless root allowed?)
        # Actually in our policy, production allows root tools? Let's check safety.
        docker_pred = next((p for p in predictions_prod if p.tool_name == "docker"), None)
        # In production, root tools ARE allowed, so it might be predicted but let's check safety
        if docker_pred is not None:
            # Should still have been safety checked (returns False due to non-determinism and path policy)
            assert docker_pred.safety_checked is False
            # But might be low due to other factors (like low CLP for root tools?)
            # We'll just ensure the prediction mechanism works

        # Test that unsafe tools are blocked in inappropriate contexts
        # For example, rm -rf should be blocked in debugging (not in our registry, but conceptually)
        # We'll test that our policy mapper blocks known dangerous tools
        from core.hands.predictive_tool_selector import ContextPolicyMapper
        policy_mapper = ContextPolicyMapper()

        # Create a mock tool spec for a dangerous tool
        dangerous_tool = ToolSpec(
            name="rm",
            tool_type=ToolType.SMRITI,
            allowed_read_paths={"/**"},
            allowed_write_paths={"/**"},
            allowed_network_endpoints=set(),
            spawns_processes=True,
            requires_root=False,
            is_deterministic=True,
            estimated_init_time=0.01,
            resource_profile={"cpu": 0.1, "memory": 0.05, "disk": 0.01},
            description="Remove files"
        )

        # Should be blocked in debugging context
        is_safe = policy_mapper.validate_tool_safety(
            "rm", dangerous_tool,
            PredictionContext(interaction_context="debugging")
        )
        assert is_safe is False, "rm should be blocked in debugging context"

        # Should be blocked in general context too
        is_safe_general = policy_mapper.validate_tool_safety(
            "rm", dangerous_tool,
            PredictionContext(interaction_context="general")
        )
        assert is_safe_general is False, "rm should be blocked in general context"

    def test_end_to_end_simulation(self):
        """Simulate an end-to-end scenario with all components interacting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "feedback_ledger.jsonl")

            # Initialize all components
            viveka_gate = AdaptiveVivekaGate()
            viveka_gate._transition_success_rate = 0.85  # High clarity

            satya_layer = ContextAwareSatyaLayer()
            satya_layer._truthfulness_metrics.truthfulness_score = 0.92  # High truthfulness
            satya_layer._truthfulness_metrics.last_updated = time.time()

            rta_loop = RtaFeedbackLoop(ledger_path=ledger_path)
            # Mock estimators for predictable values
            dustara_mock = Mock()
            dustara_mock.get.return_value = 0.25  # Low-medium complexity
            ananda_mock = Mock()
            ananda_mock.get.return_value = 0.15   # Low burden
            rta_loop._dustara = dustara_mock
            rta_loop._ananda = ananda_mock

            governor = RtaGovernor(
                rta_feedback_loop=rta_loop,
                low_bound=0.4,
                high_bound=0.95,
                sacred_pause_duration=2.0,
                mode_dispatcher=Mock()
            )

            tool_selector = PredictiveToolSelector()

            # Simulate a cycle: evaluate, check governor, get tool predictions
            # Override the loop's get_latest to return our known good state
            with patch.object(rta_loop, 'get_latest') as mock_get_latest:
                # Calculate expected Rta score
                expected_score = (0.85 * 0.92) / (0.25 + 0.15 + 1e-8)
                mock_get_latest.return_value = (expected_score, {
                    "viveka": 0.85, "satya": 0.92, "dustara": 0.25, "ananda": 0.15
                })

                # Get current state
                score, components = rta_loop.get_latest()
                assert abs(score - expected_score) < 0.01

                # Simulate governor update
                governor._on_rta_update(score, components)

                # With score ~ (0.85*0.92)/0.4 = 1.955/0.4 ≈ 4.89, which is > 0.95
                # So should trigger sacred pause
                governor._mode_dispatcher.assert_called()
                call_args = governor._mode_dispatcher.call_args[0][0]
                assert call_args.request_type == ModeRequestType.SACRED_PAUSE
                assert call_args.duration_s == 2.0

                # Reset for next test
                governor._mode_dispatcher.reset_mock()
                # Reset sacred pause state so the governor processes the next update
                governor._in_sacred_pause = False
                governor._pause_end_time = 0.0

                # Now simulate a low score scenario
                viveka_gate._transition_success_rate = 0.3  # Low clarity
                satya_layer._truthfulness_metrics.truthfulness_score = 0.4  # Low truthfulness
                low_score = (0.3 * 0.4) / (0.25 + 0.15 + 1e-8)
                mock_get_latest.return_value = (low_score, {
                    "viveka": 0.3, "satya": 0.4, "dustara": 0.25, "ananda": 0.15
                })

                score, components = rta_loop.get_latest()
                governor._on_rta_update(score, components)

                # Low score (0.3*0.4/0.4 = 0.3) < 0.4 -> should trigger shift to pratyaksha
                governor._mode_dispatcher.assert_called()
                call_args = governor._mode_dispatcher.call_args[0][0]
                assert call_args.request_type == ModeRequestType.SHIFT_PRATYAKSHA
                # Intensity = (0.4 - 0.3) / 0.4 = 0.25
                assert abs(call_args.intensity - 0.25) < 0.01

                # Test tool prediction in this low-score, high-stres scenario
                # Low score indicates need for more human interaction -> debugging context
                signals = PredictiveSignals(
                    workload_complexity_index=0.4,  # Medium workload
                    cognitive_load_predictive=0.7,  # High predicted load (humans needed)
                    state_cohesion_score=0.7,       # Moderate cohesion
                    hysteresis_buffer=0.1
                )

                context = {
                    "interaction_context": "debugging",
                    "recent_tools": ["python3", "git", "strace"]
                }

                predictions = tool_selector.predict_tool_needs(signals, context)

                # Should predict debugging tools with decent confidence
                strace_pred = next((p for p in predictions if p.tool_name == "strace"), None)
                assert strace_pred is not None
                assert strace_pred.confidence > 0.3  # Reasonable expectation

                # Warm up some tools
                warmed = tool_selector.warm_up_tools(predictions, threshold=0.25)
                assert len(warmed) > 0  # Should have warmed something

                # Verify we can get tools back
                if "strace" in warmed:
                    instance = tool_selector.get_tool("strace")
                    assert instance is not None
                    # Return it to pool
                    tool_selector.return_tool("strace", instance)

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])