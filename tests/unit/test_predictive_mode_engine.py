"""Unit tests for the enhanced PredictiveModeEngine in fleet/coordinator.py."""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest

from fleet.coordinator import (
    PredictiveModeEngine,
    OperationMode,
    PredictiveSignals,
    TransitionHistoryEntry,
    make_prediction_engine
)


class TestPredictiveModeEngineEnhanced:
    """Test the enhanced PredictiveModeEngine with advanced features."""

    def test_initialization(self):
        """Test that the engine initializes with correct defaults."""
        engine = PredictiveModeEngine()
        assert engine.get_current_mode() == OperationMode.AUTONOMOUS
        assert engine.get_preparation_phase() is None
        assert engine._transition_count == 0
        assert engine._successful_transitions == 0
        assert len(engine._transition_history) == 0
        assert len(engine._detailed_transition_history) == 0

    def test_initialization_with_custom_history_size(self):
        """Test initialization with custom history size."""
        engine = PredictiveModeEngine(history_size=50)
        # Just verify it doesn't crash - the deque maxlen is internal
        assert engine.get_current_mode() == OperationMode.AUTONOMOUS

    def test_compute_workload_complexity_index_basic(self):
        """Test WCI calculation with basic task graph."""
        engine = PredictiveModeEngine()

        # Test with no task graph
        assert engine.compute_workload_complexity_index(None) == 0.5

        # Test with empty task graph
        class EmptyGraph:
            def __init__(self):
                self.nodes = []
                self.edges = []

        assert engine.compute_workload_complexity_index(EmptyGraph()) == 0.0

        # Test with nodes only
        class NodeOnlyGraph:
            def __init__(self, node_count):
                self.nodes = list(range(node_count))

        graph = NodeOnlyGraph(50)  # 50 nodes
        # Should be 50/100 = 0.5
        assert abs(engine.compute_workload_complexity_index(graph) - 0.5) < 0.01

        graph = NodeOnlyGraph(100)  # 100 nodes
        # Should be min(1.0, 100/100) = 1.0
        assert engine.compute_workload_complexity_index(graph) == 1.0

        graph = NodeOnlyGraph(200)  # 200 nodes
        # Should be min(1.0, 200/100) = 1.0 (capped)
        assert engine.compute_workload_complexity_index(graph) == 1.0

    def test_compute_workload_complexity_index_with_edges(self):
        """Test WCI calculation with nodes and edges."""
        engine = PredictiveModeEngine()

        class GraphWithEdges:
            def __init__(self, node_count, edge_count):
                self.nodes = list(range(node_count))
                self.edges = [(i, i+1) for i in range(min(edge_count, node_count-1))]

        # Low complexity: 10 nodes, 5 edges
        graph = GraphWithEdges(10, 5)
        # Node factor: 10/100 = 0.1
        # Edge factor: 5/10 = 0.5 (connectivity = edges/nodes = 5/10 = 0.5, then /10 for normalization = 0.05)
        # WCI = 0.6 * 0.1 + 0.4 * 0.05 = 0.06 + 0.02 = 0.08
        wci = engine.compute_workload_complexity_index(graph)
        assert 0.07 < wci < 0.09

        # High complexity: 100 nodes, 50 edges
        graph = GraphWithEdges(100, 50)
        # Node factor: 100/100 = 1.0
        # Edge factor: 50/100 = 0.5 connectivity, then /10 = 0.05
        # WCI = 0.6 * 1.0 + 0.4 * 0.05 = 0.6 + 0.02 = 0.62
        wci = engine.compute_workload_complexity_index(graph)
        assert 0.61 < wci < 0.63

    def test_compute_cognitive_load_predictive(self):
        """Test CLP calculation with exponential smoothing."""
        engine = PredictiveModeEngine()

        # Test with empty history
        assert engine.compute_cognitive_load_predictive([]) == 0.5

        # Test with single value
        assert abs(engine.compute_cognitive_load_predictive([1.0]) - 0.18367) < 0.001

        # Test with multiple values - should use exponential smoothing
        history = [0.5, 1.0, 1.5, 2.0, 2.5]  # Increasing latencies
        clp = engine.compute_cognitive_load_predictive(history)
        # Should be between the normalized values of 1.5 and 2.5 due to smoothing
        assert 0.2 < clp < 0.6

        # Test boundary values
        # Very low latency
        assert engine.compute_cognitive_load_predictive([0.05]) == 0.0  # Clamped to 0
        # Very high latency
        assert engine.compute_cognitive_load_predictive([10.0]) == 1.0  # Clamped to 1

    def test_compute_state_cohesion_score(self):
        """Test SCS calculation."""
        engine = PredictiveModeEngine()

        # Test with None state
        score = engine.compute_state_cohesion_score(None)
        assert 0.8 <= score <= 1.0  # Around 0.9 with small variations

        # Test with various states (should return similar values due to placeholder)
        class MockState:
            pass

        score1 = engine.compute_state_cohesion_score(MockState())
        score2 = engine.compute_state_cohesion_score("anything")
        # Should be in similar range due to the simulated variance
        assert 0.8 <= score1 <= 1.0
        assert 0.8 <= score2 <= 1.0

    def test_compute_hysteresis_buffer_default(self):
        """Test hysteresis buffer with insufficient history."""
        engine = PredictiveModeEngine()
        assert engine.compute_hysteresis_buffer() == 0.1  # Default value

    def test_compute_hysteresis_buffer_with_history(self):
        """Test hysteresis buffer calculation with transition history."""
        engine = PredictiveModeEngine()
        now = time.time()

        # Add some transitions to history
        for i in range(10):
            engine._transition_history.append(now - i * 30)  # Every 30 seconds

        # Frequency = 10 transitions / 300 seconds = 0.033 transitions/second
        # Base buffer = min(0.2, 0.05 + (0.033 * 0.5)) = min(0.2, 0.05 + 0.0165) = 0.0665
        # With default success rate (0/0 -> treated as 1.0), learning_factor = 0
        # With no recent instability, instability_factor = 0
        # Expected: ~0.0665
        hb = engine.compute_hysteresis_buffer()
        assert 0.06 < hb < 0.08

        # Test with frequent transitions (should increase buffer)
        engine._transition_history.clear()
        for i in range(20):
            engine._transition_history.append(now - i * 5)  # Every 5 seconds = high frequency

        # Frequency = 20/300 = 0.067 transitions/second
        # Base buffer = min(0.2, 0.05 + (0.067 * 0.5)) = min(0.2, 0.05 + 0.0335) = 0.0835
        hb = engine.compute_hysteresis_buffer()
        assert 0.08 < hb < 0.12

        # Test saturation at high frequency
        engine._transition_history.clear()
        for i in range(100):  # Very frequent
            engine._transition_history.append(now - i * 2)  # Every 2 seconds

        # Should be capped at 0.2
        hb = engine.compute_hysteresis_buffer()
        assert hb <= 0.2
        assert hb > 0.15  # Should be high due to frequency

    def test_should_transition_to_interactive_from_autonomous(self):
        """Test transition logic from AUTONOMOUS to INTERACTIVE."""
        engine = PredictiveModeEngine()
        engine._transition_history.clear()  # Ensure default hysteresis of 0.1
        hb = engine.compute_hysteresis_buffer()

        # High CLP, low WCI, high SCS -> should transition to interactive
        # predicted_benefit = (clp * 0.4) + ((1 - wci) * 0.3) + (scs * 0.3)
        # = (0.9 * 0.4) + ((1 - 0.2) * 0.3) + (0.8 * 0.3)
        # = 0.36 + 0.24 + 0.24 = 0.84
        # Threshold = 0.5 + hb = 0.5 + 0.1 = 0.6
        # 0.84 > 0.6 -> should transition
        assert engine.should_transition_to_interactive(
            current_mode="AUTONOMOUS",
            wci=0.2,      # Low workload complexity
            clp=0.9,      # High predicted cognitive load
            scs=0.8,      # High state cohesion
            hb=hb
        ) is True

        # Low CLP, high WCI, low SCS -> should NOT transition
        # predicted_benefit = (0.2 * 0.4) + ((1 - 0.9) * 0.3) + (0.3 * 0.3)
        # = 0.08 + 0.03 + 0.09 = 0.20
        # Threshold = 0.6
        # 0.20 < 0.6 -> should NOT transition
        assert engine.should_transition_to_interactive(
            current_mode="AUTONOMOUS",
            wci=0.9,      # High workload complexity
            clp=0.2,      # Low predicted cognitive load
            scs=0.3,      # Low state cohesion
            hb=hb
        ) is False

    def test_should_transition_to_interactive_from_interactive(self):
        """Test transition logic from INTERACTIVE to AUTONOMOUS."""
        engine = PredictiveModeEngine()
        engine._transition_history.clear()  # Ensure default hysteresis of 0.1
        hb = engine.compute_hysteresis_buffer()

        # High WCI, low CLP, moderate SCS -> should transition to autonomous
        # autonomy_benefit = (wci * 0.5) + ((1 - clp) * 0.3) + (scs * 0.2)
        # = (0.9 * 0.5) + ((1 - 0.2) * 0.3) + (0.7 * 0.2)
        # = 0.45 + 0.24 + 0.14 = 0.83
        # Threshold = 0.6 + hb = 0.6 + 0.1 = 0.7
        # 0.83 > 0.7 -> should transition
        assert engine.should_transition_to_interactive(
            current_mode="INTERACTIVE",
            wci=0.9,      # High workload complexity
            clp=0.2,      # Low predicted cognitive load
            scs=0.7,      # Moderate-high state cohesion
            hb=hb
        ) is True

        # Low WCI, high CLP, low SCS -> should NOT transition (stay interactive)
        # autonomy_benefit = (0.2 * 0.5) + ((1 - 0.9) * 0.3) + (0.4 * 0.2)
        # = 0.10 + 0.03 + 0.08 = 0.21
        # Threshold = 0.7
        # 0.21 < 0.7 -> should NOT transition
        assert engine.should_transition_to_interactive(
            current_mode="INTERACTIVE",
            wci=0.2,      # Low workload complexity
            clp=0.9,      # High predicted cognitive load
            scs=0.4,      # Low state cohesion
            hb=hb
        ) is False

    def test_should_transition_to_autonomous_method(self):
        """Test the explicit should_transition_to_autonomous method."""
        engine = PredictiveModeEngine()
        engine._transition_history.clear()
        hb = engine.compute_hysteresis_buffer()

        # From INTERACTIVE to AUTONOMOUS
        assert engine.should_transition_to_autonomous(
            current_mode="INTERACTIVE",
            wci=0.9,
            clp=0.2,
            scs=0.7,
            hb=hb
        ) is True

        # From AUTONOMOUS - should return False (not transitioning TO autonomous when already there)
        assert engine.should_transition_to_autonomous(
            current_mode="AUTONOMOUS",
            wci=0.2,
            clp=0.9,
            scs=0.8,
            hb=hb
        ) is False

    def test_should_transition_to_interactive_explicit(self):
        """Test the explicit should_transition_to_interactive_explicit method."""
        engine = PredictiveModeEngine()
        engine._transition_history.clear()
        hb = engine.compute_hysteresis_buffer()

        # From AUTONOMOUS to INTERACTIVE
        assert engine.should_transition_to_interactive_explicit(
            current_mode="AUTONOMOUS",
            wci=0.2,
            clp=0.9,
            scs=0.8,
            hb=hb
        ) is True

        # From INTERACTIVE - should return False (not transitioning TO interactive when already there)
        assert engine.should_transition_to_interactive_explicit(
            current_mode="INTERACTIVE",
            wci=0.9,
            clp=0.2,
            scs=0.7,
            hb=hb
        ) is False

    def test_record_transition_basic(self):
        """Test recording a basic transition."""
        engine = PredictiveModeEngine()
        initial_len = len(engine._transition_history)
        initial_detailed_len = len(engine._detailed_transition_history)

        # Create mock signals
        signals = PredictiveSignals(
            workload_complexity_index=0.5,
            cognitive_load_predictive=0.5,
            state_cohesion_score=0.9,
            hysteresis_buffer=0.1
        )

        engine.record_transition(
            from_mode=OperationMode.AUTONOMOUS,
            to_mode=OperationMode.INTERACTIVE,
            signals=signals,
            duration_in_previous_mode=10.0
        )

        # Check that history was updated
        assert len(engine._transition_history) == initial_len + 1
        assert len(engine._detailed_transition_history) == initial_detailed_len + 1

        # Check the detailed entry
        entry = engine._detailed_transition_history[-1]
        assert isinstance(entry, TransitionHistoryEntry)
        assert entry.from_mode == OperationMode.AUTONOMOUS
        assert entry.to_mode == OperationMode.INTERACTIVE
        assert entry.trigger_signals == signals
        assert entry.duration_in_previous_mode == 10.0
        assert entry.timestamp > 0

        # Check that counters were updated
        assert engine._transition_count == 1
        assert engine._successful_transitions == 1

        # Check that current mode was updated
        assert engine.get_current_mode() == OperationMode.INTERACTIVE

    def test_record_transition_multiple(self):
        """Test recording multiple transitions."""
        engine = PredictiveModeEngine()

        signals1 = PredictiveSignals(0.3, 0.8, 0.9, 0.1)
        signals2 = PredictiveSignals(0.7, 0.3, 0.8, 0.15)

        # First transition: AUTONOMOUS -> INTERACTIVE
        engine.record_transition(
            OperationMode.AUTONOMOUS,
            OperationMode.INTERACTIVE,
            signals1,
            5.0
        )

        # Second transition: INTERACTIVE -> AUTONOMOUS
        engine.record_transition(
            OperationMode.INTERACTIVE,
            OperationMode.AUTONOMOUS,
            signals2,
            10.0
        )

        assert engine._transition_count == 2
        assert engine._successful_transitions == 2
        assert engine.get_current_mode() == OperationMode.AUTONOMOUS  # Last transition

        # Check history entries
        assert len(engine._detailed_transition_history) == 2
        assert engine._detailed_transition_history[0].from_mode == OperationMode.AUTONOMOUS
        assert engine._detailed_transition_history[0].to_mode == OperationMode.INTERACTIVE
        assert engine._detailed_transition_history[1].from_mode == OperationMode.INTERACTIVE
        assert engine._detailed_transition_history[1].to_mode == OperationMode.AUTONOMOUS

    def test_get_current_mode(self):
        """Test getting current mode."""
        engine = PredictiveModeEngine()
        assert engine.get_current_mode() == OperationMode.AUTONOMOUS

        # Change mode and verify
        engine._current_mode = OperationMode.INTERACTIVE
        assert engine.get_current_mode() == OperationMode.INTERACTIVE

    def test_preparation_phase_methods(self):
        """Test preparation phase getters and setters."""
        engine = PredictiveModeEngine()
        assert engine.get_preparation_phase() is None

        engine.set_preparation_phase(OperationMode.PREPARING_TO_INTERACTIVE)
        assert engine.get_preparation_phase() == OperationMode.PREPARING_TO_INTERACTIVE

        engine.set_preparation_phase(None)
        assert engine.get_preparation_phase() is None

    def test_get_time_in_current_mode(self):
        """Test getting time spent in current mode."""
        engine = PredictiveModeEngine()
        initial_time = engine._mode_entry_time

        # Should be very small initially
        time_in_mode = engine.get_time_in_current_mode()
        assert time_in_mode >= 0
        assert time_in_mode < 1.0  # Should be less than a second

        # Simulate time passing by manually setting entry time
        engine._mode_entry_time = time.time() - 5.0  # 5 seconds ago
        time_in_mode = engine.get_time_in_current_mode()
        assert 4.9 <= time_in_mode <= 5.1  # Allow small margin for timing

    def test_get_transition_statistics(self):
        """Test getting transition statistics."""
        engine = PredictiveModeEngine()

        # Test with no transitions
        stats = engine.get_transition_statistics()
        assert stats["total_transitions"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["recent_frequency"] == 0.0
        assert stats["average_time_between_transitions"] == 0.0

        # Add some transitions
        engine._transition_history.clear()
        now = time.time()
        for i in range(5):
            engine._transition_history.append(now - i * 50)  # Every 50 seconds

        # Manually set counters to match history
        engine._transition_count = 5
        engine._successful_transitions = 5

        stats = engine.get_transition_statistics()
        assert stats["total_transitions"] == 5
        assert stats["success_rate"] == 1.0

        # Recent frequency: 5 transitions in last 10 minutes (600 seconds)
        # But we only added transitions up to 200 seconds ago (4*50), so all 5 are recent
        # Frequency per minute = 5 / 10 = 0.5
        assert stats["recent_frequency"] == 0.5

        # Average time between transitions should be around 50 seconds
        assert 45 < stats["average_time_between_transitions"] < 55

    def test_prepare_for_interaction(self):
        """Test the prepare_for_interaction method (Layer 2 integration)."""
        engine = PredictiveModeEngine()
        mock_amp_state = {"key": "value"}

        result = engine.prepare_for_interaction(mock_amp_state)

        assert isinstance(result, dict)
        assert result["phase"] == "PREPARING_TO_INTERACTIVE"
        assert "actions_initiated" in result
        assert "estimated_completion_time" in result
        assert "state_snapshot_id" in result

        # Check that expected actions are present
        expected_actions = [
            "context_prefetch",
            "double_buffer_prepare",
            "crdt_prepare",
            "checksum_prepare",
            "persistence_checkpoint"
        ]
        for action in expected_actions:
            assert action in result["actions_initiated"]

        # Check that completion time is in the future
        assert result["estimated_completion_time"] > time.time()

        # Check that snapshot ID is formatted correctly
        assert result["state_snapshot_id"].startswith("prep_")

    def test_prepare_for_autonomous(self):
        """Test the prepare_for_autonomous method (Layer 2 integration)."""
        engine = PredictiveModeEngine()
        mock_amp_state = {"interaction_insights": ["insight1", "insight2"]}

        result = engine.prepare_for_autonomous(mock_amp_state)

        assert isinstance(result, dict)
        assert result["phase"] == "PREPARING_TO_AUTONOMOUS"
        assert "actions_initiated" in result
        assert "estimated_completion_time" in result
        assert "state_snapshot_id" in result

        # Check that expected actions are present
        expected_actions = [
            "insight_compression",
            "insight_prioritization",
            "double_buffer_prepare",
            "crdt_insight_prepare",
            "checksum_prepare",
            "persistence_checkpoint"
        ]
        for action in expected_actions:
            assert action in result["actions_initiated"]

        # Completion time should be in the future but sooner than interaction prep
        assert result["estimated_completion_time"] > time.time()

    def test_validate_transition_readiness(self):
        """Test the validate_transition_readiness method (Layer 3 integration)."""
        engine = PredictiveModeEngine()

        # Test with complete preparation
        complete_prep = {
            "actions_initiated": [
                "context_prefetch",
                "double_buffer_prepare",
                "crdt_prepare",
                "checksum_prepare",
                "persistence_checkpoint"
            ]
        }
        assert engine.validate_transition_readiness(complete_prep) is True

        # Test with incomplete preparation (< 80% complete)
        incomplete_prep = {
            "actions_initiated": [
                "context_prefetch",
                "double_buffer_prepare"
                # Missing 3 actions
            ]
        }
        assert engine.validate_transition_readiness(incomplete_prep) is False

        # Test with exactly 80% (4 out of 5)
        marginal_prep = {
            "actions_initiated": [
                "context_prefetch",
                "double_buffer_prepare",
                "crdt_prepare",
                "checksum_prepare"
                # Missing persistence_checkpoint
            ]
        }
        # 4/5 = 0.8 exactly - should pass
        assert engine.validate_transition_readiness(marginal_prep) is True

    def test_make_prediction_engine_factory(self):
        """Test the factory function."""
        engine = make_prediction_engine()
        assert isinstance(engine, PredictiveModeEngine)
        assert engine.get_current_mode() == OperationMode.AUTONOMOUS

    @patch('fleet.coordinator.np')
    def test_numpy_integration_placeholder(self, mock_np):
        """Test that numpy is imported and available (placeholder for future use)."""
        # Just verify the import doesn't break things
        engine = PredictiveModeEngine()
        assert engine is not None
        # The actual numpy usage would be implemented in real versions of the methods

    def test_operation_mode_enum(self):
        """Test that OperationMode enum has all expected values."""
        assert OperationMode.AUTONOMOUS.value == "AUTONOMOUS"
        assert OperationMode.INTERACTIVE.value == "INTERACTIVE"
        assert OperationMode.PREPARING_TO_INTERACTIVE.value == "PREPARING_TO_INTERACTIVE"
        assert OperationMode.PREPARING_TO_AUTONOMOUS.value == "PREPARING_TO_AUTONOMOUS"
        assert OperationMode.SYNCING_STATE.value == "SYNCING_STATE"

        # Test that we can iterate over them
        modes = list(OperationMode)
        assert len(modes) == 5
        assert OperationMode.AUTONOMOUS in modes
        assert OperationMode.INTERACTIVE in modes
        assert OperationMode.PREPARING_TO_INTERACTIVE in modes
        assert OperationMode.PREPARING_TO_AUTONOMOUS in modes
        assert OperationMode.SYNCING_STATE in modes

    def test_predictive_signals_dataclass(self):
        """Test PredictiveSignals dataclass."""
        signals = PredictiveSignals(
            workload_complexity_index=0.3,
            cognitive_load_predictive=0.7,
            state_cohesion_score=0.8,
            hysteresis_buffer=0.15
        )

        assert signals.workload_complexity_index == 0.3
        assert signals.cognitive_load_predictive == 0.7
        assert signals.state_cohesion_score == 0.8
        assert signals.hysteresis_buffer == 0.15
        assert isinstance(signals.timestamp, float)
        assert signals.timestamp > 0

    def test_transition_history_entry_dataclass(self):
        """Test TransitionHistoryEntry dataclass."""
        signals = PredictiveSignals(0.5, 0.5, 0.9, 0.1)
        entry = TransitionHistoryEntry(
            timestamp=time.time(),
            from_mode=OperationMode.AUTONOMOUS,
            to_mode=OperationMode.INTERACTIVE,
            trigger_signals=signals,
            duration_in_previous_mode=12.5
        )

        assert entry.from_mode == OperationMode.AUTONOMOUS
        assert entry.to_mode == OperationMode.INTERACTIVE
        assert entry.trigger_signals == signals
        assert entry.duration_in_previous_mode == 12.5
        assert isinstance(entry.timestamp, float)
        assert entry.timestamp > 0

    def test_edge_case_hysteresis_with_learning(self):
        """Test hysteresis buffer with learning from transition history."""
        engine = PredictiveModeEngine()
        now = time.time()

        # Add some successful transitions to history
        for i in range(10):
            engine._transition_history.append(now - i * 100)  # Every 100 seconds
            # Also add to detailed history with successful transitions
            signals = PredictiveSignals(0.5, 0.5, 0.9, 0.1)
            engine._detailed_transition_history.append(
                TransitionHistoryEntry(
                    timestamp=now - i * 100,
                    from_mode=OperationMode.AUTONOMOUS,
                    to_mode=OperationMode.INTERACTIVE,
                    trigger_signals=signals,
                    duration_in_previous_mode=50.0
                )
            )

        # Set counters to reflect successful transitions
        engine._transition_count = 10
        engine._successful_transitions = 10  # 100% success rate

        hb = engine.compute_hysteresis_buffer()
        # With 100% success rate, learning_factor should reduce the buffer
        # Base frequency: 10 transitions / (10*100) seconds = 0.01 trans/sec
        # Base buffer: min(0.2, 0.05 + (0.01 * 0.5)) = 0.055
        # Learning factor: 0.1 * (1.0 - 1.0) = 0.0
        # Expected: around 0.055
        assert 0.05 < hb < 0.07

    def test_edge_case_hysteresis_with_instability(self):
        """Test hysteresis buffer with instability factor."""
        engine = PredictiveModeEngine()
        now = time.time()

        # Add transitions that are very close together (indicating instability)
        for i in range(5):
            engine._transition_history.append(now - i * 2)  # Every 2 seconds - unstable

        # Add to detailed history to simulate instability
        signals = PredictiveSignals(0.5, 0.5, 0.9, 0.1)
        for i in range(5):
            engine._detailed_transition_history.append(
                TransitionHistoryEntry(
                    timestamp=now - i * 2,
                    from_mode=OperationMode.AUTONOMOUS,
                    to_mode=OperationMode.INTERACTIVE,
                    trigger_signals=signals,
                    duration_in_previous_mode=1.0  # Very short duration indicates instability
                )
            )

        hb = engine.compute_hysteresis_buffer()
        # Should be elevated due to instability factor
        # Base frequency: 5 transitions / (4*2) seconds = 0.625 trans/sec (over 8 second window)
        # Base buffer: min(0.2, 0.05 + (0.625 * 0.5)) = min(0.2, 0.05 + 0.3125) = 0.2 (capped)
        # Instability factor should add more, but it's already capped
        # Actually, let's check the calculation more carefully:
        # With 5 transitions in last 8 seconds: frequency = 5/8 = 0.625 per second
        # But we only look at last 5 minutes (300 seconds), so all 5 count
        # Frequency = 5/300 = 0.0167 transitions per second
        # Base buffer = min(0.2, 0.05 + (0.0167 * 0.5)) = min(0.2, 0.05 + 0.00835) = 0.05835
        # Plus instability factor (0.05) = ~0.108
        assert 0.10 < hb < 0.12

if __name__ == "__main__":
    pytest.main([__file__, "-v"])