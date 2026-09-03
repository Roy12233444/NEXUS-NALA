"""
Unit tests for the ContextAwareSatyaLayer in core/safety/context_aware_satya_layer.py.
"""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest

from core.safety.context_aware_satya_layer import (
    ContextAwareSatyaLayer,
    TruthfulnessLevel,
    FactCheckResult,
    SatyaMetrics
)
from fleet.coordinator import OperationMode


class TestContextAwareSatyaLayer:
    """Test the ContextAwareSatyaLayer for truthfulness validation."""

    def test_initialization(self):
        """Test that the satya layer initializes with correct defaults."""
        satya_layer = ContextAwareSatyaLayer()

        # Check initial state
        assert satya_layer.min_fact_check_latency_ms == 25.0
        assert satya_layer.max_fact_check_latency_ms == 150.0
        assert satya_layer.enable_consistency_tracking is True
        assert satya_layer.enable_contextual_validation is True
        assert satya_layer.truth_decay_rate == 0.01

        # Check initial metrics
        metrics = satya_layer.get_satya_metrics()
        assert metrics['truthfulness_score'] == pytest.approx(1.0, abs=1e-3)
        assert metrics['consistency_rate'] == pytest.approx(1.0, abs=1e-3)
        assert metrics['fact_check_latency_ms'] == 0.0
        assert metrics['contradiction_count'] == 0

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        satya_layer = ContextAwareSatyaLayer(
            min_fact_check_latency_ms=50.0,
            max_fact_check_latency_ms=200.0,
            enable_consistency_tracking=False,
            enable_contextual_validation=False,
            truth_decay_rate=0.05
        )

        assert satya_layer.min_fact_check_latency_ms == 50.0
        assert satya_layer.max_fact_check_latency_ms == 200.0
        assert satya_layer.enable_consistency_tracking is False
        assert satya_layer.enable_contextual_validation is False
        assert satya_layer.truth_decay_rate == 0.05

    def test_basic_fact_consistency_check(self):
        """Test basic factual consistency checking."""
        satya_layer = ContextAwareSatyaLayer()

        # Test with correct fact
        output_data = {"statement": "2 + 2 equals 4", "result": 4}
        context = {"operation_mode": OperationMode.INTERACTIVE}

        result = satya_layer.validate_output_truthfulness(output_data, OperationMode.INTERACTIVE, context)
        # Should be consistent since 2+2=4 is a known fact
        # Note: This is a simplified check - actual implementation uses string matching

        # Verify we get a FactCheckResult back from internal methods
        with patch.object(satya_layer, '_check_factual_consistency') as mock_check:
            mock_check.return_value = FactCheckResult(
                is_consistent=True,
                confidence_score=0.9,
                contradictions=[],
                supporting_evidence=["Fact confirmed: 2 + 2"],
                validation_latency_ms=10.0
            )

            result = satya_layer.validate_output_truthfulness(
                output_data, OperationMode.INTERACTIVE, context
            )
            assert result is True
            mock_check.assert_called_once()

    def test_fact_contradiction_detection(self):
        """Test detection of factual contradictions."""
        satya_layer = ContextAwareSatyaLayer()

        # Test with incorrect fact
        output_data = {"statement": "2 + 2 equals 5", "result": 5}
        context = {"operation_mode": OperationMode.INTERACTIVE}

        with patch.object(satya_layer, '_check_factual_consistency') as mock_check:
            mock_check.return_value = FactCheckResult(
                is_consistent=False,
                confidence_score=0.4,
                contradictions=["Fact contradiction: 2 + 2 != expected"],
                supporting_evidence=[],
                validation_latency_ms=10.0
            )

            result = satya_layer.validate_output_truthfulness(
                output_data, OperationMode.INTERACTIVE, context
            )
            assert result is False

    def test_truthfulness_level_determination(self):
        """Test that truthfulness level is determined correctly based on mode."""
        satya_layer = ContextAwareSatyaLayer()

        # Test INTERACTIVE mode -> MINIMAL
        level = satya_layer._determine_truthfulness_level(OperationMode.INTERACTIVE)
        assert level == TruthfulnessLevel.MINIMAL

        # Test AUTONOMOUS mode -> RIGOROUS
        level = satya_layer._determine_truthfulness_level(OperationMode.AUTONOMOUS)
        assert level == TruthfulnessLevel.RIGOROUS

        # Test ATHAPRAPTI mode -> TRANSCENDENT
        with patch.object(OperationMode, 'ATHAPRAPTI', create=True):
            level = satya_layer._determine_truthfulness_level(OperationMode.ATHAPRAPTI)
            assert level == TruthfulnessLevel.TRANSCENDENT

        # Test other modes -> STANDARD
        level = satya_layer._determine_truthfulness_level(OperationMode.PREPARING_TO_AUTONOMOUS)
        assert level == TruthfulnessLevel.STANDARD

    def test_truthfulness_level_with_context(self):
        """Test that truthfulness level adjusts based on context."""
        satya_layer = ContextAwareSatyaLayer()

        # High stress should reduce strictness
        context_high_stress = {"stress_level": 0.8}
        level = satya_layer._determine_truthfulness_level(
            OperationMode.AUTONOMOUS, context_high_stress
        )
        # Should downgrade from RIGOROUS to STANDARD due to high stress
        assert level == TruthfulnessLevel.STANDARD

        # Critical operation should increase strictness
        context_critical = {"is_critical_operation": True}
        level = satya_layer._determine_truthfulness_level(
            OperationMode.INTERACTIVE, context_critical
        )
        # Should upgrade from MINIMAL to STANDARD due to critical operation
        assert level == TruthfulnessLevel.STANDARD

    def test_apply_truthfulness_validation_levels(self):
        """Test that different truthfulness levels apply correct thresholds."""
        satya_layer = ContextAwareSatyaLayer()

        # Create a mock result with borderline confidence
        mock_result = FactCheckResult(
            is_consistent=True,
            confidence_score=0.75,
            contradictions=[],
            supporting_evidence=["Some evidence"],
            validation_latency_ms=10.0
        )

        # MINIMAL level: should pass with confidence >= 0.5
        result = satya_layer._apply_truthfulness_validation(
            {}, TruthfulnessLevel.MINIMAL, {}
        )
        # We're mocking the internal check, so directly test the logic
        assert satya_layer._apply_truthfulness_validation.__code__ is not None  # Just checking method exists

        # Test the actual level logic by mocking _check_factual_consistency
        with patch.object(satya_layer, '_check_factual_consistency', return_value=mock_result):
            # MINIMAL: confidence 0.75 >= 0.5 -> should pass
            result = satya_layer._apply_truthfulness_validation(
                {}, TruthfulnessLevel.MINIMAL, {}
            )
            assert result.is_consistent is True

            # STANDARD: confidence 0.75 >= 0.7 -> should pass
            result = satya_layer._apply_truthfulness_validation(
                {}, TruthfulnessLevel.STANDARD, {}
            )
            assert result.is_consistent is True

            # RIGOROUS: confidence 0.75 < 0.85 -> should fail
            result = satya_layer._apply_truthfulness_validation(
                {}, TruthfulnessLevel.RIGOROUS, {}
            )
            assert result.is_consistent is False

            # TRANSCENDENT: confidence 0.75 < 0.95 -> should fail
            result = satya_layer._apply_truthfulness_validation(
                {}, TruthfulnessLevel.TRANSCENDENT, {}
            )
            assert result.is_consistent is False

    def test_internal_consistency_check(self):
        """Test internal consistency checking."""
        satya_layer = ContextAwareSatyaLayer()

        # Test internally consistent data
        consistent_data = {
            "probability": 0.8,
            "is_valid": True,
            "is_invalid": False  # Not contradictory with is_valid
        }
        assert satya_layer._check_internal_consistency(consistent_data) is True

        # Test internally inconsistent data (probability out of range)
        inconsistent_data = {
            "probability": 1.5,  # Invalid probability
            "is_valid": True
        }
        assert satya_layer._check_internal_consistency(inconsistent_data) is False

        # Test boolean contradiction
        bool_contradiction = {
            "is_true": True,
            "is_false": True  # Contradiction: both can't be true
        }
        assert satya_layer._check_internal_consistency(bool_contradiction) is False

    def test_contextual_validation(self):
        """Test context-specific validation constraints."""
        satya_layer = ContextAwareSatyaLayer()

        # Test response time constraint for INTERACTIVE mode
        output_data = {"response_time_ms": 6000}  # Exceeds 5000ms limit
        context = {"operation_mode": OperationMode.INTERACTIVE}
        is_valid, violations = satya_layer._validate_contextual_constraints(
            output_data, context
        )
        assert is_valid is False
        assert any("Response time" in v and "exceeds maximum" in v for v in violations)

        # Test within limit
        output_data = {"response_time_ms": 3000}
        is_valid, violations = satya_layer._validate_contextual_constraints(
            output_data, context
        )
        assert is_valid is True
        assert len(violations) == 0

        # Test citation requirement for AUTONOMOUS mode
        output_data = {"response_time_ms": 1000}  # OK time
        context = {"operation_mode": OperationMode.AUTONOMOUS}  # Requires citations
        is_valid, violations = satya_layer._validate_contextual_constraints(
            output_data, context
        )
        assert is_valid is False
        assert any("Citations required" in v for v in violations)

        # Test with citations provided
        output_data = {"response_time_ms": 1000, "citations": ["source1"]}
        is_valid, violations = satya_layer._validate_contextual_constraints(
            output_data, context
        )
        assert is_valid is True

    def test_metrics_update(self):
        """Test that metrics are updated correctly after validation."""
        satya_layer = ContextAwareSatyaLayer()

        initial_metrics = satya_layer.get_satya_metrics()
        assert initial_metrics['truthfulness_score'] == pytest.approx(1.0, abs=1e-3)
        assert initial_metrics['consistency_rate'] == pytest.approx(1.0, abs=1e-3)

        # Mock a successful validation
        with patch.object(satya_layer, '_apply_truthfulness_validation') as mock_validate:
            mock_validate.return_value = FactCheckResult(
                is_consistent=True,
                confidence_score=0.9,
                contradictions=[],
                supporting_evidence=["Evidence"],
                validation_latency_ms=50.0
            )

            # Perform validation
            satya_layer.validate_output_truthfulness(
                {"test": "data"}, OperationMode.INTERACTIVE, {}
            )

            # Check metrics were updated
            updated_metrics = satya_layer.get_satya_metrics()
            # Truthfulness should be updated (since first measurement, set directly to 0.9)
            assert abs(updated_metrics['truthfulness_score'] - 0.9) < 0.01
            # Consistency rate should be updated (since first measurement, set directly to 1.0)
            assert abs(updated_metrics['consistency_rate'] - 1.0) < 0.01
            # Latency should be updated
            assert abs(updated_metrics['fact_check_latency_ms'] - 50.0) < 0.01

    def test_failed_validation_metrics(self):
        """Test metrics update when validation fails."""
        satya_layer = ContextAwareSatyaLayer()

        # Mock a failed validation
        with patch.object(satya_layer, '_apply_truthfulness_validation') as mock_validate:
            mock_validate.return_value = FactCheckResult(
                is_consistent=False,
                confidence_score=0.4,
                contradictions=["Contradiction 1", "Contradiction 2"],
                supporting_evidence=[],
                validation_latency_ms=30.0
            )

            # Perform validation
            satya_layer.validate_output_truthfulness(
                {"test": "data"}, OperationMode.INTERACTIVE, {}
            )

            # Check metrics were updated for failure (since it is the first measurement, it is set directly to 0.4)
            updated_metrics = satya_layer.get_satya_metrics()
            assert abs(updated_metrics['truthfulness_score'] - 0.4) < 0.01
            assert abs(updated_metrics['consistency_rate'] - 0.0) < 0.01
            # Contradiction count should increase by 2
            assert updated_metrics['contradiction_count'] == 2

    def test_truth_decay_application(self):
        """Test that truth decay is applied to metrics."""
        satya_layer = ContextAwareSatyaLayer(truth_decay_rate=0.1)  # Higher decay for testing

        # Set an old last_updated time to simulate aging
        old_time = time.time() - (2 * 3600)  # 2 hours ago
        satya_layer._truthfulness_metrics.last_updated = old_time
        satya_layer._truthfulness_metrics.truthfulness_score = 1.0
        satya_layer._truthfulness_metrics.consistency_rate = 1.0

        metrics = satya_layer.get_satya_metrics()
        # Decay factor = max(0, 1 - (0.1 * 2)) = 0.8
        expected_score = 1.0 * 0.8
        assert abs(metrics['truthfulness_score'] - expected_score) < 0.01
        expected_rate = 1.0 * 0.8
        assert abs(metrics['consistency_rate'] - expected_rate) < 0.01

    def test_feedback_update(self):
        """Test that feedback updates truthfulness score."""
        satya_layer = ContextAwareSatyaLayer()

        initial_score = satya_layer.get_satya_metrics()['truthfulness_score']
        assert initial_score == pytest.approx(1.0, abs=1e-3)

        # Provide negative feedback
        satya_layer.update_truthfulness_feedback(False)

        # Score should decrease: 0.1 * 0.0 + 0.9 * 1.0 = 0.9
        updated_score = satya_layer.get_satya_metrics()['truthfulness_score']
        assert abs(updated_score - 0.9) < 0.01

        # Provide positive feedback
        satya_layer.update_truthfulness_feedback(True)

        # Score should increase somewhat: 0.1 * 1.0 + 0.9 * 0.9 = 0.91
        final_score = satya_layer.get_satya_metrics()['truthfulness_score']
        assert abs(final_score - 0.91) < 0.01

    def test_add_known_fact(self):
        """Test adding new facts to the knowledge base."""
        satya_layer = ContextAwareSatyaLayer()

        initial_kb_size = sum(len(v) for v in satya_layer._known_facts.values())

        # Add a new fact
        satya_layer.add_known_fact("The sky is blue", True, ["observation"])

        # Check it was added
        new_kb_size = sum(len(v) for v in satya_layer._known_facts.values())
        assert new_kb_size == initial_kb_size + 1

        # Verify the fact is in the user_provided category
        assert "user_provided" in satya_layer._known_facts
        assert "the sky is blue" in satya_layer._known_facts["user_provided"]
        assert satya_layer._known_facts["user_provided"]["the sky is blue"] is True

    def test_diagnostics_report(self):
        """Test that diagnostics report includes expected information."""
        satya_layer = ContextAwareSatyaLayer()

        # Run a few validations to populate history
        with patch.object(satya_layer, '_apply_truthfulness_validation') as mock_validate:
            mock_validate.return_value = FactCheckResult(
                is_consistent=True,
                confidence_score=0.85,
                contradictions=[],
                supporting_evidence=["Evidence"],
                validation_latency_ms=25.0
            )

            # Run 3 validations
            for i in range(3):
                satya_layer.validate_output_truthfulness(
                    {"test": f"data{i}"}, OperationMode.INTERACTIVE, {}
                )

        diagnostics = satya_layer.get_satya_diagnostics()

        # Check that all expected sections are present
        assert 'truthfulness_metrics' in diagnostics
        assert 'recent_consistency_rate' in diagnostics
        assert 'recent_avg_confidence' in diagnostics
        assert 'knowledge_base_size' in diagnostics
        assert 'contextual_rules_active' in diagnostics
        assert 'total_fact_checks' in diagnostics
        assert 'total_contradictions' in diagnostics

        # Check values
        assert diagnostics['total_fact_checks'] == 3
        assert diagnostics['total_contradictions'] == 0
        assert diagnostics['recent_consistency_rate'] == 1.0
        assert abs(diagnostics['recent_avg_confidence'] - 0.85) < 0.01

    def test_athaprapti_mode_transcendent_validation(self):
        """Test that ATHAPRAPTI mode uses TRANSCENDENT validation level."""
        satya_layer = ContextAwareSatyaLayer()

        # Mock to return a result that would pass lower levels but not TRANSCENDENT
        borderline_result = FactCheckResult(
            is_consistent=True,
            confidence_score=0.9,  # Good but not excellent
            contradictions=[],
            supporting_evidence=["Some evidence"],  # Only 1 piece, need 2 for TRANSCENDENT
            validation_latency_ms=10.0
        )

        with patch.object(satya_layer, '_check_factual_consistency', return_value=borderline_result):
            with patch.object(OperationMode, 'ATHAPRAPTI', create=True):
                # For ATHAPRAPTI, should use TRANSCENDENT level
                result = satya_layer.validate_output_truthfulness(
                    {"test": "data"}, OperationMode.ATHAPRAPTI, {}
                )

                # Should fail because:
                # - Confidence 0.9 < 0.95 required for TRANSCENDENT
                # - Only 1 supporting evidence < 2 required for TRANSCENDENT
                assert result is False

if __name__ == "__main__":
    pytest.main([__file__])