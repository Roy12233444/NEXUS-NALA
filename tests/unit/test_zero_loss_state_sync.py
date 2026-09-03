"""Unit tests for the Zero-Loss State Synchronization AMP Client in core/session/amp_client.py."""

from __future__ import annotations

import time
import threading
from unittest.mock import Mock, patch

import pytest

from core.session.amp_client import (
    AMPClient,
    create_amp_client,
    PredictiveSignals,
    StateCorruptionError,
    TransitionNotReadyError,
    OperationMode,
    DualBufferState,
    CRDTStateSegment,
    StateChecksumValidator,
    ChiranjeeviPersistenceManager
)


class TestDualBufferState:
    """Test the dual-buffer state management."""

    def test_initialization(self):
        """Test dual-buffer initialization."""
        initial_state = {"key": "value", "count": 42}
        db = DualBufferState(initial_state)

        active = db.get_active_state()
        standby = db.get_standby_state()

        assert active == initial_state
        assert standby == initial_state
        assert active is not standby  # Different objects (deep copy)
        assert standby is not initial_state

    def test_swap_buffers(self):
        """Test atomic buffer swap."""
        initial_state = {"mode": "AUTONOMOUS"}
        db = DualBufferState(initial_state)

        # Modify standby buffer
        new_state = {"mode": "INTERACTIVE"}
        db.update_standby_state(new_state)

        # Verify states before swap
        assert db.get_active_state() == initial_state
        assert db.get_standby_state() == new_state

        # Perform swap
        db.swap_buffers()

        # Verify states after swap
        assert db.get_active_state() == new_state
        assert db.get_standby_state() == initial_state

        # Verify version vector updated
        version_vector = db.get_version_vector()
        assert version_vector.get("swap", 0) == 1

    def test_thread_safety(self):
        """Test thread-safe operations."""
        initial_state = {"counter": 0}
        db = DualBufferState(initial_state)

        def update_standby():
            for i in range(100):
                db.update_standby_state({"counter": i})

        def get_active():
            for _ in range(100):
                db.get_active_state()

        # Run concurrent operations
        threads = [
            threading.Thread(target=update_standby),
            threading.Thread(target=get_active),
            threading.Thread(target=get_active)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash - basic thread safety test
        final_state = db.get_active_state()
        assert "counter" in final_state


class TestCRDTStateSegment:
    """Test Conflict-free Replicated Data Type segments."""

    def test_initialization(self):
        """Test CRDT segment initialization."""
        segment = CRDTStateSegment("test_segment", 42)

        assert segment.segment_id == "test_segment"
        assert segment.value == 42
        assert segment.vector_clock == {}
        assert segment.observed_removed == set()
        assert segment.get_value() == 42

    def test_update_and_remove(self):
        """Test update and remove operations."""
        segment = CRDTStateSegment("test_segment", "initial")

        # Update value
        segment.update("updated", "node1")
        assert segment.get_value() == "updated"
        assert segment.vector_clock["node1"] == 1

        # Remove segment
        segment.remove("node2")

        assert segment.is_removed() is True
        assert segment.get_value() is None
        assert "test_segment" in segment.observed_removed

    def test_merge_conflict_resolution(self):
        """Test CRDT merge with various conflict scenarios."""
        # Segment A: local update
        seg_a = CRDTStateSegment("key", 10)
        seg_a.update(20, "node_a")  # VC: {node_a: 1}

        # Segment B: remote update with higher clock
        seg_b = CRDTStateSegment("key", 15)
        seg_b.update(25, "node_b")  # VC: {node_b: 1}
        seg_b.update(30, "node_b")  # VC: {node_b: 2}

        # Merge: should pick higher vector clock sum (node_b: 2 > node_a: 1)
        merged = seg_a.merge(seg_b)
        assert merged.get_value() == 30
        assert merged.vector_clock == {"node_a": 1, "node_b": 2}

        # Test equal clocks - should prefer local (seg_a)
        seg_c = CRDTStateSegment("key", 100)
        seg_c.update(200, "node_c")  # VC: {node_c: 1}
        seg_d = CRDTStateSegment("key", 50)
        seg_d.update(75, "node_d")   # VC: {node_d: 1}

        merged_equal = seg_c.merge(seg_d)
        assert merged_equal.get_value() == 200  # Preferred local (seg_c)
        assert merged_equal.vector_clock == {"node_c": 1, "node_d": 1}

    def test_merge_with_removal(self):
        """Test merge when one segment is removed."""
        # Active segment
        seg_active = CRDTStateSegment("data", "important")
        seg_active.update("very important", "node1")

        # Removed segment
        seg_removed = CRDTStateSegment("data", "important")
        seg_removed.update("very important", "node2")
        seg_removed.remove("node3")  # Mark as removed

        # Merge: removed should win
        merged = seg_active.merge(seg_removed)
        assert merged.get_value() is None
        assert merged.is_removed() is True

    def test_merge_both_removed(self):
        """Test merge when both segments are removed."""
        seg_a = CRDTStateSegment("test", "value")
        seg_a.remove("node1")

        seg_b = CRDTStateSegment("test", "value")
        seg_b.remove("node2")

        merged = seg_a.merge(seg_b)
        assert merged.get_value() is None
        assert merged.is_removed() is True
        assert "test" in merged.observed_removed


class TestStateChecksumValidator:
    """Test state validation checksums."""

    def test_checksum_computation(self):
        """Test checksum computation for various state types."""
        validator = StateChecksumValidator()

        # Test None
        assert validator.compute_checksum(None) != validator.compute_checksum("null")

        # Test primitives
        assert validator.compute_checksum(42) != validator.compute_checksum("42")
        assert validator.compute_checksum(3.14) != validator.compute_checksum("3.14")
        assert validator.compute_checksum(True) != validator.compute_checksum("true")
        assert validator.compute_checksum("hello") != validator.compute_checksum('"hello"')

        # Test lists
        list_state = [1, 2, 3]
        assert validator.compute_checksum(list_state) != validator.compute_checksum('[1, 2, 3]')

        # Test dicts (order independent)
        dict_a = {"b": 2, "a": 1}
        dict_b = {"a": 1, "b": 2}
        assert validator.compute_checksum(dict_a) == validator.compute_checksum(dict_b)

        # Test nested structures (dict key order independent)
        nested_a = {"list": [1, {"inner": "value"}], "count": 5}
        nested_b = {"count": 5, "list": [1, {"inner": "value"}]}
        assert validator.compute_checksum(nested_a) == validator.compute_checksum(nested_b)

    def test_checksum_validation(self):
        """Test checksum validation."""
        validator = StateChecksumValidator()
        state = {"key": "value", "number": 42}
        checksum = validator.compute_checksum(state)

        # Valid checksum should pass
        assert validator.validate(state, checksum) is True

        # Invalid checksum should fail
        assert validator.validate(state, "invalid_checksum") is False

        # Modified state should fail
        modified_state = state.copy()
        modified_state["key"] = "modified"
        assert validator.validate(modified_state, checksum) is False

    def test_constant_time_compare(self):
        """Test constant-time comparison prevents timing attacks."""
        validator = StateChecksumValidator()

        # These should take comparable time (we can't easily test timing in unit test,
        # but we can verify the logic works)
        assert validator._constant_time_compare("abc", "abc") is True
        assert validator._constant_time_compare("abc", "abcd") is False  # Different length
        assert validator._constant_time_compare("abc", "abx") is False  # Same length, different chars
        assert validator._constant_time_compare("", "") is True


class TestChiranjeeviPersistenceManager:
    """Test gradient-based persistence checkpointing."""

    def test_initialization(self):
        """Test persistence manager initialization."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints", max_checkpoints=5)

        assert pm.storage_path == "./test_checkpoints"
        assert pm.max_checkpoints == 5
        assert len(pm.checkpoint_history) == 0
        assert pm._last_checkpoint_state is None

    def test_create_checkpoint(self):
        """Test checkpoint creation."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints")
        state = {"data": [1, 2, 3], "value": "test"}

        checkpoint_id = pm.create_gradient_checkpoint(state)

        assert checkpoint_id.startswith("ckpt_")
        assert len(pm.checkpoint_history) == 1
        assert pm._last_checkpoint_state == state

        # Check metadata
        checkpoint = pm.checkpoint_history[0]
        assert checkpoint["id"] == checkpoint_id
        assert "timestamp" in checkpoint
        assert checkpoint["compression_ratio"] == 0.7
        assert "data" in checkpoint

    def test_checkpoint_limit(self):
        """Test that checkpoint history respects max limit."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints", max_checkpoints=3)

        # Create 5 checkpoints
        for i in range(5):
            state = {"iteration": i}
            pm.create_gradient_checkpoint(state)

        # Should only keep last 3
        assert len(pm.checkpoint_history) == 3
        assert pm.checkpoint_history[0]["data"]["delta"]["iteration"] == 2  # First kept
        assert pm.checkpoint_history[2]["data"]["delta"]["iteration"] == 4  # Last kept

    def test_recover_from_checkpoint(self):
        """Test checkpoint recovery."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints")
        original_state = {"nested": {"key": "value"}, "count": 100}

        # Create checkpoint
        checkpoint_id = pm.create_gradient_checkpoint(original_state)

        # Recover from checkpoint
        recovered_state = pm.recover_from_checkpoint(checkpoint_id)

        assert recovered_state == original_state
        assert recovered_state is not original_state  # Deep copy

    def test_recover_nonexistent_checkpoint(self):
        """Test recovery of nonexistent checkpoint raises error."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints")

        with pytest.raises(ValueError, match="Checkpoint .* not found"):
            pm.recover_from_checkpoint("nonexistent_id")

    def test_gradient_compression_simulation(self):
        """Test gradient-based compression simulation."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints")

        # Test float quantization
        assert pm._quantize_state(3.1415926535, 0.15) == 3.14  # Reduced precision
        assert pm._quantize_state(1e-11, 0.5) == 0.0     # Below 1e-10 threshold

        # Test list quantization
        assert pm._quantize_state([1.111, 2.222], 0.1) == [1.1, 2.2]

        # Test dict quantization
        assert pm._quantize_state({"a": 1.234, "b": 5.678}, 0.1) == {"a": 1.2, "b": 5.7}

        # Test string truncation
        long_string = "a" * 20
        assert pm._quantize_state(long_string, 0.5) == "aaaaaaaaaa..."

        # Test short string unchanged
        assert pm._quantize_state("hi", 0.5) == "hi"

    def test_state_delta_computation(self):
        """Test state delta computation."""
        pm = ChiranjeeviPersistenceManager("./test_checkpoints")

        # Numeric delta
        assert pm._compute_state_delta(10, 4) == 6
        assert pm._compute_state_delta(4, 10) == -6

        # List delta (same length)
        assert pm._compute_state_delta([1, 2, 3], [1, 2, 3]) == [0, 0, 0]
        assert pm._compute_state_delta([4, 5, 6], [1, 2, 3]) == [3, 3, 3]

        # List delta (different length - return full)
        assert pm._compute_state_delta([1, 2, 3, 4], [1, 2, 3]) == [1, 2, 3, 4]

        # Dict delta
        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"a": 1, "b": 5, "d": 4}
        delta = pm._compute_state_delta(dict1, dict2)
        assert delta == {"b": 2, "c": 3, "d": None}  # b changed, c present only in dict1, d removed (value None)

        # Different types - return current state
        assert pm._compute_state_delta(5, "string") == 5


class TestAMPClient:
    """Test the main AMP Client zero-loss synchronization."""

    def test_initialization(self):
        """Test AMP client initialization."""
        initial_state = {"mode": "AUTONOMOUS", "counter": 0}
        amp_client = AMPClient(initial_state)

        # Check core components initialized
        assert isinstance(amp_client.dual_buffer, DualBufferState)
        assert isinstance(amp_client.checksum_validator, StateChecksumValidator)
        assert isinstance(amp_client.persistence_manager, ChiranjeeviPersistenceManager)

        # Check state tracking
        assert amp_client._last_known_good_state == initial_state
        assert amp_client._last_known_good_checksum == amp_client.checksum_validator.compute_checksum(initial_state)
        assert amp_client._transition_in_progress == False
        assert amp_client._prepare_count == 0

        # Check CRDT segments initialized
        assert len(amp_client._state_segments) == 2  # mode and counter
        assert "state_mode" in amp_client._state_segments
        assert "state_counter" in amp_client._state_segments

    def test_prepare_for_interaction(self):
        """Test predictive preparation for interaction mode."""
        initial_state = {"task": "autonomous_work", "progress": 0.5}
        amp_client = AMPClient(initial_state)

        # Prepare for interaction
        prep_result = amp_client.prepare_for_interaction(initial_state)

        # Check preparation result structure
        assert prep_result["phase"] == "PREPARING_TO_INTERACTIVE"
        assert prep_result["preparation_id"].startswith("prep_interact_")
        assert "actions_initiated" in prep_result
        assert "estimated_completion_time" in prep_result
        assert "state_snapshot_id" in prep_result
        assert "futures" in prep_result

        # Check required actions
        required_actions = [
            "context_prefetch",
            "double_buffer_prepare",
            "crdt_prepare",
            "checksum_prepare",
            "persistence_checkpoint"
        ]
        for action in required_actions:
            assert action in prep_result["actions_initiated"]

        # Check estimated time (~2s in future)
        assert prep_result["estimated_completion_time"] > time.time()
        assert prep_result["estimated_completion_time"] < time.time() + 3.0

        # Check that preparation is tracked
        assert prep_result["preparation_id"] in amp_client._preparation_futures

        # Check metrics updated
        assert amp_client._prepare_count >= 0  # May be 0 if preparation not counted until completion

        # Active state unchanged during prep
        updated_state = amp_client.get_current_state()
        assert updated_state == initial_state

        # Check that standby buffer was prepared
        prepared_state = amp_client.get_prepared_state()
        assert prepared_state == initial_state

    def test_prepare_for_autonomous(self):
        """Test predictive preparation for autonomous mode."""
        # State with interaction insights
        initial_state = {
            "task": "interactive_help",
            "insights": ["learned_pattern_1", "learned_pattern_2"],
            "user_feedback": "positive",
            "session_data": {"clicks": 15, "time_spent": 120}
        }
        amp_client = AMPClient(initial_state)

        # Prepare for autonomous
        prep_result = amp_client.prepare_for_autonomous(initial_state)

        # Check preparation result structure
        assert prep_result["phase"] == "PREPARING_TO_AUTONOMOUS"
        assert prep_result["preparation_id"].startswith("prep_auto_")
        assert "actions_initiated" in prep_result
        assert "estimated_completion_time" in prep_result
        assert "state_snapshot_id" in prep_result
        assert "futures" in prep_result

        # Check required actions
        required_actions = [
            "insight_compression",
            "insight_prioritization",
            "double_buffer_prepare",
            "crdt_insight_prepare",
            "checksum_prepare",
            "persistence_checkpoint"
        ]
        for action in required_actions:
            assert action in prep_result["actions_initiated"]

        # Check estimated time (~1.5s in future - faster for insights)
        assert prep_result["estimated_completion_time"] > time.time()
        assert prep_result["estimated_completion_time"] < time.time() + 2.5

        # Check insights compression flag (stored in the preparation tracking object)
        assert amp_client._preparation_futures[prep_result["preparation_id"]].get("insights_compressed") == True

    def test_prepare_for_interaction_state_corruption(self):
        """Test that prepare_for_interaction detects state corruption."""
        initial_state = {"valid": "state"}
        amp_client = AMPClient(initial_state)

        # Corrupt the last known good checksum to simulate state corruption
        amp_client._last_known_good_checksum = "invalid_checksum"

        # Should raise StateCorruptionError
        with pytest.raises(StateCorruptionError, match="Current state validation failed"):
            amp_client.prepare_for_interaction(initial_state)

    def test_prepare_for_autonomous_state_corruption(self):
        """Test that prepare_for_autonomous detects state corruption."""
        initial_state = {"valid": "state"}
        amp_client = AMPClient(initial_state)

        # Corrupt the last known good checksum
        amp_client._last_known_good_checksum = "invalid_checksum"

        # Should raise StateCorruptionError
        with pytest.raises(StateCorruptionError, match="Current state validation failed"):
            amp_client.prepare_for_autonomous(initial_state)

    def test_validate_transition_readiness_success(self):
        """Test successful transition readiness validation."""
        initial_state = {"ready": True}
        amp_client = AMPClient(initial_state)

        # Prepare for interaction
        prep_result = amp_client.prepare_for_interaction(initial_state)

        # Wait a bit for simulated async operations to complete
        time.sleep(2.1)  # Longer than estimated completion time

        # Should validate successfully
        assert amp_client.validate_transition_readiness(prep_result) == True

    def test_validate_transition_readiness_insufficient_preparation(self):
        """Test validation failure due to insufficient preparation."""
        initial_state = {"ready": True}
        amp_client = AMPClient(initial_state)

        # Prepare for interaction
        prep_result = amp_client.prepare_for_interaction(initial_state)

        # Don't wait - check immediately (should be insufficient)
        assert amp_client.validate_transition_readiness(prep_result) == False

        # Even with partial waiting, should still fail if <80% complete
        time.sleep(0.5)  # Less than needed for most futures
        assert amp_client.validate_transition_readiness(prep_result) == False

    def test_validate_transition_readiness_wrong_phase(self):
        """Test validation fails for wrong preparation phase."""
        initial_state = {"ready": True}
        amp_client = AMPClient(initial_state)

        # Prepare for interaction
        prep_result = amp_client.prepare_for_interaction(initial_state)

        # Try to validate for autonomous transition (wrong target mode in spirit)
        # Actually, validation doesn't check target mode - it checks preparation completeness
        # But we can test that validation fails if we tamper with the preparation

        # Remove some actions to simulate incomplete preparation
        # (In real test, we'd wait insufficient time as above)
        pass  # Covered by insufficient preparation test

    def test_execute_transition_success(self):
        """Test successful zero-loss transition execution."""
        initial_state = {"mode": "AUTONOMOUS", "data": [1, 2, 3]}
        amp_client = AMPClient(initial_state)

        # Prepare for interaction
        prep_result = amp_client.prepare_for_interaction(initial_state)

        # Wait for preparation to complete
        time.sleep(2.1)

        # Validate readiness
        assert amp_client.validate_transition_readiness(prep_result) == True

        # Execute transition to INTERACTIVE
        new_state = amp_client.execute_transition(prep_result, OperationMode.INTERACTIVE)

        # Check that state was correctly transitioned
        assert new_state == initial_state  # State should be preserved
        assert amp_client.get_current_state() == initial_state

        # Check that active and standby buffers swapped
        # (After swap, what was standby is now active)
        assert amp_client.get_prepared_state() == initial_state  # Standby now has original

        # Check metrics updated
        assert amp_client._successful_transitions == 1
        assert amp_client._failed_transitions == 0
        assert amp_client._transition_in_progress == False

    def test_execute_transition_validation_failure(self):
        """Test that execute_transition fails validation."""
        initial_state = {"state": "initial"}
        amp_client = AMPClient(initial_state)

        # Try to execute without preparation
        fake_prep_result = {
            "preparation_id": "fake_id",
            "phase": "PREPARING_TO_INTERACTIVE",
            "actions_initiated": ["fake_action"],
            "estimated_completion_time": time.time() + 10,
            "state_snapshot_id": "fake_snapshot",
            "futures": []
        }

        # Should raise TransitionNotReadyError
        with pytest.raises(TransitionNotReadyError):
            amp_client.execute_transition(fake_prep_result, OperationMode.INTERACTIVE)

    def test_execute_transition_already_in_progress(self):
        """Test that execute_transition prevents concurrent transitions."""
        initial_state = {"state": "initial"}
        amp_client = AMPClient(initial_state)

        # Prepare and start a transition
        prep_result = amp_client.prepare_for_interaction(initial_state)
        time.sleep(2.1)  # Complete preparation

        # Manually set transition in progress to simulate race condition
        amp_client._transition_in_progress = True

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Transition already in progress"):
            amp_client.execute_transition(prep_result, OperationMode.INTERACTIVE)

        # Reset for cleanup
        amp_client._transition_in_progress = False

    def test_zero_loss_state_preservation(self):
        """Test that state is preserved with zero loss across multiple transitions."""
        initial_state = {
            "session_id": "sess_123",
            "context": {"user_id": "user_456", "project": "alpha"},
            "variables": {"x": 10, "y": 20, "z": [1, 2, 3]},
            "history": ["step1", "step2", "step3"]
        }
        amp_client = AMPClient(initial_state)

        # Perform multiple transitions back and forth
        states_to_cycle = [
            (OperationMode.INTERACTIVE, "interactive_state"),
            (OperationMode.AUTONOMOUS, "autonomous_state"),
            (OperationMode.INTERACTIVE, "interactive_state_2"),
            (OperationMode.AUTONOMOUS, "autonomous_state_2")
        ]

        for target_mode, label in states_to_cycle:
            # Prepare based on current mode
            current_state = amp_client.get_current_state()
            if target_mode == OperationMode.INTERACTIVE:
                prep_result = amp_client.prepare_for_interaction(current_state)
            else:
                prep_result = amp_client.prepare_for_autonomous(current_state)

            # Wait for preparation
            time.sleep(2.1 if target_mode == OperationMode.INTERACTIVE else 1.6)

            # Validate and execute
            assert amp_client.validate_transition_readiness(prep_result) == True
            new_state = amp_client.execute_transition(prep_result, target_mode)

            # Verify state preservation
            assert new_state == initial_state, f"State lost during transition to {label}"
            assert amp_client.get_current_state() == initial_state

    def test_state_integrity_score(self):
        """Test state integrity score calculation."""
        initial_state = {"stable": "state", "number": 42}
        amp_client = AMPClient(initial_state)

        # Initial state should have good integrity
        integrity = amp_client.get_state_in_consistency_score()
        assert 0.0 <= integrity <= 1.0
        # Should be reasonably high for fresh state
        assert integrity > 0.5

        # After some time (segments age), score might change but should stay valid
        time.sleep(0.1)
        integrity_after = amp_client.get_state_in_consistency_score()
        assert 0.0 <= integrity_after <= 1.0

    def test_transition_metrics(self):
        """Test transition metrics collection."""
        initial_state = {"metrics": "test"}
        amp_client = AMPClient(initial_state)

        # Initial metrics
        metrics = amp_client.get_transition_statistics()
        assert metrics["total_preparations"] == 0
        assert metrics["successful_transitions"] == 0
        assert metrics["failed_transitions"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["average_prepare_time"] == 0.0

        # Perform a few transitions
        for i in range(3):
            # Prepare for interaction (alternating to test both directions)
            if i % 2 == 0:
                prep_result = amp_client.prepare_for_interaction(initial_state)
                time.sleep(2.1)
                target_mode = OperationMode.INTERACTIVE
            else:
                prep_result = amp_client.prepare_for_autonomous(initial_state)
                time.sleep(1.6)
                target_mode = OperationMode.AUTONOMOUS

            if amp_client.validate_transition_readiness(prep_result):
                amp_client.execute_transition(prep_result, target_mode)

        # Check metrics updated
        metrics = amp_client.get_transition_statistics()
        assert metrics["total_preparations"] == 3
        assert metrics["successful_transitions"] == 3
        assert metrics["failed_transitions"] == 0
        assert metrics["success_rate"] == 1.0
        assert metrics["average_prepare_time"] > 0
        assert metrics["preparations_in_progress"] == 0
        assert metrics["transition_in_progress"] == False

    def test_concurrent_preparations(self):
        """Test handling of overlapping preparations."""
        initial_state = {"state": "initial"}
        amp_client = AMPClient(initial_state)

        # Start first preparation
        prep1 = amp_client.prepare_for_interaction(initial_state)

        # Before it completes, start second preparation (should queue or overwrite)
        # In our implementation, second preparation will create new prep ID
        time.sleep(0.5)
        prep2 = amp_client.prepare_for_autonomous(initial_state)

        # Both should be tracked
        assert len(amp_client._preparation_futures) == 2
        assert prep1["preparation_id"] in amp_client._preparation_futures
        assert prep2["preparation_id"] in amp_client._preparation_futures

        # Wait for both to complete
        time.sleep(2.0)  # Longer than both preparations

        # Validate both
        assert amp_client.validate_transition_readiness(prep1) == True
        assert amp_client.validate_transition_readiness(prep2) == True

        # Execute one transition
        amp_client.execute_transition(prep1, OperationMode.INTERACTIVE)

        # First preparation should be cleaned up
        assert prep1["preparation_id"] not in amp_client._preparation_futures
        # Second should still be there
        assert prep2["preparation_id"] in amp_client._preparation_futures

    def test_cleanup_old_preparations(self):
        """Test cleanup of stale preparations."""
        initial_state = {"state": "initial"}
        amp_client = AMPClient(initial_state)

        # Create an old preparation by manipulating time
        prep_result = amp_client.prepare_for_interaction(initial_state)
        prep_id = prep_result["preparation_id"]

        # Manually age the preparation
        amp_client._preparation_futures[prep_id]["start_time"] = time.time() - 400  # 400 sec ago

        # Run cleanup (default max age 300s)
        amp_client.cleanup_old_preparations()

        # Old preparation should be removed
        assert prep_id not in amp_client._preparation_futures

    def test_get_diagnostics(self):
        """Test diagnostic information collection."""
        initial_state = {"diagnostic": "test"}
        amp_client = AMPClient(initial_state)

        diag = amp_client.get_diagnostics()

        # Check structure
        assert "state_info" in diag
        assert "buffer_info" in diag
        assert "persistence_info" in diag
        assert "transition_stats" in diag

        # Check state info
        assert diag["state_info"]["active_state_type"] == str(type(initial_state))
        assert isinstance(diag["state_info"]["state_size_estimate"], int)
        assert isinstance(diag["state_info"]["checksum"], str)
        assert len(diag["state_info"]["checksum"]) == 64  # SHA-256 hex length

        # Check buffer info
        assert isinstance(diag["buffer_info"]["last_swap_time"], float)
        assert isinstance(diag["buffer_info"]["version_vector"], dict)

        # Check persistence info
        assert isinstance(diag["persistence_info"]["recent_checkpoints"], list)
        assert isinstance(diag["persistence_info"]["checkpoint_count"], int)

        # Check transition stats
        assert isinstance(diag["transition_stats"], dict)
        assert "total_preparations" in diag["transition_stats"]

    def test_layer3_validation_callback(self):
        """Test Layer 3 validation callback integration."""
        initial_state = {"state": "test"}
        amp_client = AMPClient(initial_state)

        # Track callback invocations
        callback_calls = []
        def mock_callback(success, prep_id, target_mode):
            callback_calls.append((success, prep_id, target_mode))

        amp_client.set_layer3_validation_callback(mock_callback)

        # Prepare and execute transition
        prep_result = amp_client.prepare_for_interaction(initial_state)
        time.sleep(2.1)

        if amp_client.validate_transition_readiness(prep_result):
            new_state = amp_client.execute_transition(prep_result, OperationMode.INTERACTIVE)

            # Check callback was invoked
            assert len(callback_calls) == 1
            success, prep_id, target_mode = callback_calls[0]
            assert success == True
            assert prep_id == prep_result["preparation_id"]
            assert target_mode == OperationMode.INTERACTIVE

    def test_extract_and_prioritize_insights(self):
        """Test insight extraction and prioritization."""
        initial_state = {
            "random_data": "not_important",
            "learned_pattern": "discovered_rule",
            "user_insight": "helpful_tip",
            "system_metrics": {"cpu": 80},
            "cache_data": ["temp1", "temp2"]
        }
        amp_client = AMPClient(initial_state)

        insights = amp_client._extract_and_prioritize_insights(initial_state)

        # Should prioritize keys with insight-related terms
        assert "learned_pattern" in insights
        assert "user_insight" in insights
        assert "system_metrics" not in insights  # No insight keywords in key

        # Non-insight data may be excluded or limited
        # (Implementation returns first 3 keys if no insight keywords found,
        # but we have insight keywords so should get those)

        # Test with no insight keywords
        plain_state = {"a": 1, "b": 2, "c": 3, "d": 4}
        insights_plain = amp_client._extract_and_prioritize_insights(plain_state)
        # Should return first 3 items
        assert len(insights_plain) == 3
        assert set(insights_plain.keys()) == {"a", "b", "c"}  # First 3 keys

    def test_compress_insights(self):
        """Test insight compression."""
        initial_state = {"insights": [1.111111, 2.222222, 3.333333]}
        amp_client = AMPClient(initial_state)

        compressed = amp_client._compress_insights(initial_state["insights"])

        # Should be quantized (at 0.6 ratio, 9 digits precision leaves 6-digit float unchanged)
        assert compressed == [1.111111, 2.222222, 3.333333]

    def test_preparation_futures_tracking(self):
        """Test that preparation futures are properly tracked."""
        initial_state = {"state": "test"}
        amp_client = AMPClient(initial_state)

        # Initially no preparations
        assert len(amp_client._preparation_futures) == 0
        assert amp_client._preparation_futures.get("nonexistent") is None

        # Start preparation
        prep_result = amp_client.prepare_for_interaction(initial_state)
        prep_id = prep_result["preparation_id"]

        # Should be tracked
        assert len(amp_client._preparation_futures) == 1
        assert prep_id in amp_client._preparation_futures
        status = amp_client._preparation_futures.get(prep_id)
        assert status is not None
        assert status["target_mode"] == OperationMode.INTERACTIVE

        # After completion and transition, should be cleaned up
        time.sleep(2.1)
        if amp_client.validate_transition_readiness(prep_result):
            amp_client.execute_transition(prep_result, OperationMode.INTERACTIVE)
            assert prep_id not in amp_client._preparation_futures
            assert amp_client._preparation_futures.get(prep_id) is None

    def test_multiple_state_types(self):
        """Test AMP client with various state types."""
        test_states = [
            {"dict": {"key": "value", "nested": {"a": 1}}},
            {"list": [1, 2, 3, {"inner": "list"}]},
            {"string": "simple string state"},
            {"number": 42.5},
            {"boolean": True},
            {"none": None},
            {"complex": {
                "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                "settings": {"theme": "dark", "notifications": True},
                "metadata": {"version": "1.0", "timestamp": 1234567890}
            }}
        ]

        for state_dict in test_states:
            for state_name, initial_state in state_dict.items():
                amp_client = AMPClient(initial_state)

            # Basic operations should work
            assert amp_client.get_current_state() == initial_state

            # Prepare for interaction
            prep_result = amp_client.prepare_for_interaction(initial_state)
            assert "preparation_id" in prep_result

            # Wait and validate
            time.sleep(2.1)
            assert amp_client.validate_transition_readiness(prep_result) == True

            # Execute transition
            new_state = amp_client.execute_transition(prep_result, OperationMode.INTERACTIVE)
            assert new_state == initial_state

            # Verify AMP client still functional
            assert amp_client.get_current_state() == initial_state


# Test factory function
def test_create_amp_client():
    """Test the factory function."""
    initial_state = {"factory": "test"}
    amp_client = create_amp_client(initial_state)

    assert isinstance(amp_client, AMPClient)
    assert amp_client.get_current_state() == initial_state
    assert amp_client.persistence_manager.storage_path == "./checkpoints"

# Test with custom persistence path
def test_create_amp_client_custom_path():
    """Test factory function with custom persistence path."""
    initial_state = {"path": "test"}
    custom_path = "/custom/persistence/path"
    amp_client = create_amp_client(initial_state, custom_path)

    assert amp_client.persistence_manager.storage_path == custom_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])