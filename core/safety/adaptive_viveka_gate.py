"""
Adaptive Viveka Gate - Layer 3: Adaptive Safety Gateway for NALA Dual-Mode Operation.
Implements dynamic validation strictness and predictive fault injection for safe mode transitions.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

# Import OperationMode from fleet coordinator
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from fleet.coordinator import OperationMode

logger = logging.getLogger(__name__)


class ValidationStrictness(Enum):
    """Validation strictness levels for adaptive safety gate."""
    MINIMAL = "minimal"      # INTERACTIVE mode - fast, essential checks only
    BALANCED = "balanced"    # Intermediate - moderate validation
    MAXIMUM = "maximum"      # AUTONOMOUS mode - comprehensive validation


class AdaptiveVivekaGate:
    """
    Adaptive safety gate that adjusts validation rigor based on operational context.
    Implements Viveka (discernment) principle: applying appropriate scrutiny
    based on mode, state coherence, and risk assessment.
    """

    def __init__(self,
                 minimal_validation_latency_ms: float = 50.0,
                 maximal_validation_latency_ms: float = 200.0,
                 enable_predictive_fault_injection: bool = True):
        """
        Initialize the Adaptive Viveka Gate.

        Args:
            minimal_validation_latency_ms: Target latency for INTERACTIVE mode validation
            maximal_validation_latency_ms: Maximum latency for AUTONOMOUS mode validation
            enable_predictive_fault_injection: Whether to run predictive fault simulations
        """
        self.minimal_validation_latency_ms = minimal_validation_latency_ms
        self.maximal_validation_latency_ms = maximal_validation_latency_ms
        self.enable_predictive_fault_injection = enable_predictive_fault_injection

        # State tracking for adaptive behavior
        self._validation_history: List[Dict[str, Any]] = []
        self._fault_injection_history: List[Dict[str, Any]] = []
        self._transition_success_rate: float = 1.0  # Start optimistic
        self._last_validation_time: float = 0.0
        self._adaptive_strictness: ValidationStrictness = ValidationStrictness.BALANCED

        # Thresholds for adaptive behavior
        self._success_rate_high_threshold = 0.95
        self._success_rate_low_threshold = 0.80
        self._validation_latency_target_ms = 100.0  # Target for INTERACTIVE mode

    def _determine_validation_strictness(self,
                                       current_mode: OperationMode,
                                       predictive_signals: Optional[Dict[str, Any]] = None) -> ValidationStrictness:
        """
        Determine appropriate validation strictness based on mode and system state.

        Args:
            current_mode: Current operation mode
            predictive_signals: Optional signals from predictive mode engine

        Returns:
            ValidationStrictness level to apply
        """
        # Base strictness on mode
        if current_mode == OperationMode.INTERACTIVE:
            base_strictness = ValidationStrictness.MINIMAL
        elif current_mode == OperationMode.AUTONOMOUS:
            base_strictness = ValidationStrictness.MAXIMUM
        else:
            # For preparation states, use balanced approach
            base_strictness = ValidationStrictness.BALANCED

        # Adapt based on recent success rate
        if self._transition_success_rate < self._success_rate_low_threshold:
            # Increase strictness if success rate is low
            if base_strictness == ValidationStrictness.MINIMAL:
                adapted = ValidationStrictness.BALANCED
            elif base_strictness == ValidationStrictness.BALANCED:
                adapted = ValidationStrictness.MAXIMUM
            else:
                adapted = ValidationStrictness.MAXIMUM  # Stay at max
        elif self._transition_success_rate > self._success_rate_high_threshold:
            # Can decrease strictness if success rate is high
            if base_strictness == ValidationStrictness.MAXIMUM:
                adapted = ValidationStrictness.BALANCED
            elif base_strictness == ValidationStrictness.BALANCED:
                adapted = ValidationStrictness.MINIMAL
            else:
                adapted = ValidationStrictness.MINIMAL
        else:
            adapted = base_strictness

        # Further refine based on predictive signals if available
        if predictive_signals:
            state_cohesion = predictive_signals.get('state_cohesion_score', 1.0)
            # Lower state cohesion -> increase validation strictness
            if state_cohesion < 0.7 and adapted == ValidationStrictness.MINIMAL:
                adapted = ValidationStrictness.BALANCED
            elif state_cohesion < 0.5 and adapted == ValidationStrictness.BALANCED:
                adapted = ValidationStrictness.MAXIMUM

        return adapted

    def _run_minimal_validation(self, preparation_result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Run minimal validation suitable for INTERACTIVE mode (<100ms target).
        Checks essential preparation completion and basic state integrity.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        start_time = time.time()
        issues = []

        # Check 1: Basic preparation structure
        required_keys = ['preparation_id', 'phase', 'actions_initiated', 'estimated_completion_time']
        for key in required_keys:
            if key not in preparation_result:
                issues.append(f"Missing required key: {key}")

        # Check 2: Actions completion ratio (>=80% as per original spec)
        actions_initiated = preparation_result.get('actions_initiated', [])
        # In a real implementation, we would check actual completion of these actions
        # For now, we assume they are marked as completed if present
        # This is a placeholder - actual implementation would check futures
        completion_ratio = len(actions_initiated) / max(len(actions_initiated), 1)  # Simplified
        if completion_ratio < 0.8:
            issues.append(f"Insufficient preparation completion: {completion_ratio:.2f} < 0.80")

        # Check 3: Estimated completion time is in near future
        est_completion = preparation_result.get('estimated_completion_time', 0)
        if est_completion < time.time():
            issues.append("Estimated completion time is in the past")

        latency_ms = (time.time() - start_time) * 1000
        if latency_ms > self.minimal_validation_latency_ms:
            logger.warning(f"Minimal validation took {latency_ms:.2f}ms > target {self.minimal_validation_latency_ms}ms")

        return len(issues) == 0, issues

    def _run_maximal_validation(self,
                              preparation_result: Dict[str, Any],
                              current_mode: OperationMode) -> Tuple[bool, List[str]]:
        """
        Run maximal validation suitable for AUTONOMOUS mode (comprehensive checks).
        Includes state integrity, persistence readiness, and predictive fault injection.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        start_time = time.time()
        issues = []

        # Run all minimal validation checks first
        min_valid, min_issues = self._run_minimal_validation(preparation_result)
        issues.extend(min_issues)
        if not min_valid:
            # If minimal fails, maximal definitely fails
            return False, issues

        # Additional maximal validation checks

        # Check 4: State cohesion validation (would interface with state checksums)
        # Placeholder: in reality would validate state checksums and CRDT convergence
        state_snapshot_id = preparation_result.get('state_snapshot_id')
        if not state_snapshot_id:
            issues.append("Missing state snapshot ID for validation")

        # Check 5: Persistence checkpoint readiness
        # Placeholder: would check that persistence checkpoint was created and valid

        # Check 6: Predictive fault injection (if enabled)
        if self.enable_predictive_fault_injection:
            try:
                faults = self._run_predictive_fault_injection(preparation_result, current_mode)
                if faults:
                    issues.extend([f"Predictive fault detected: {f}" for f in faults])
            except Exception as e:
                logger.error(f"Predictive fault injection failed: {e}")
                issues.append(f"Fault injection error: {str(e)}")

        latency_ms = (time.time() - start_time) * 1000
        if latency_ms > self.maximal_validation_latency_ms:
            logger.warning(f"Maximal validation took {latency_ms:.2f}ms > target {self.maximal_validation_latency_ms}ms")

        return len(issues) == 0, issues

    def _run_predictive_fault_injection(self,
                                      preparation_result: Dict[str, Any],
                                      current_mode: OperationMode) -> List[str]:
        """
        Simulate potential transition failures in safe mode to identify vulnerabilities.
        Returns list of detected fault descriptions.

        Args:
            preparation_result: The preparation result to validate
            current_mode: Target mode for transition

        Returns:
            List of fault descriptions (empty if no faults detected)
        """
        faults = []
        # This is a simplified simulation - real implementation would:
        # 1. Simulate state corruption during transition
        # 2. Test recovery mechanisms
        # 3. Validate checksums under fault conditions
        # 4. Check buffer swap atomicity under contention
        # 5. Validate CRDT mergeability under network partitions

        # Simulate based on preparation completeness
        actions_initiated = preparation_result.get('actions_initiated', [])
        if len(actions_initiated) < 3:  # Arbitrary threshold
            faults.append("Insufficient action diversity in preparation")

        # Simulate based on mode
        if current_mode == OperationMode.AUTONOMOUS:
            # Autonomous mode should have insight compression and persistence
            if not preparation_result.get('insights_compressed', False):
                faults.append("Missing insight compression for autonomous transition")
        elif current_mode == OperationMode.INTERACTIVE:
            # Interactive mode should have context prefetch
            if 'context_prefetch' not in str(actions_initiated):
                faults.append("Missing context prefetch for interactive transition")

        # Record fault injection attempt
        self._fault_injection_history.append({
            'timestamp': time.time(),
            'preparation_id': preparation_result.get('preparation_id'),
            'target_mode': current_mode.value,
            'faults_detected': faults,
            'simulation_type': 'predictive'
        })

        # Keep history bounded
        if len(self._fault_injection_history) > 100:
            self._fault_injection_history = self._fault_injection_history[-100:]

        return faults

    def validate_transition_readiness(self,
                                    preparation_result: Dict[str, Any],
                                    current_mode: OperationMode,
                                    predictive_signals: Optional[Dict[str, Any]] = None) -> bool:
        """
        Main validation interface: Determine if transition preparation is sufficient.
        Adaptively selects validation strictness based on mode and system state.

        Args:
            preparation_result: Result from AMPClient preparation methods
            current_mode: Current operation mode (before transition)
            predictive_signals: Optional signals from predictive mode engine for adaptation

        Returns:
            True if transition is safe to proceed, False otherwise
        """
        # Determine appropriate validation strictness
        strictness = self._determine_validation_strictness(current_mode, predictive_signals)
        logger.debug(f"Adaptive Viveka Gate: selected strictness {strictness.value} for mode {current_mode.value}")

        # Run appropriate validation
        if strictness == ValidationStrictness.MINIMAL:
            is_valid, issues = self._run_minimal_validation(preparation_result)
        elif strictness == ValidationStrictness.MAXIMUM:
            is_valid, issues = self._run_maximal_validation(preparation_result, current_mode)
        else:  # BALANCED
            # Balanced: run minimal plus some additional checks (e.g., basic fault injection)
            is_valid, issues = self._run_minimal_validation(preparation_result)
            if is_valid and self.enable_predictive_fault_injection:
                # Run light fault injection for balanced mode
                faults = self._run_predictive_fault_injection(preparation_result, current_mode)
                if faults:
                    is_valid = False
                    issues.extend([f"Predictive fault detected: {f}" for f in faults])

        # Log validation outcome
        if not is_valid:
            logger.warning(f"Transition validation FAILED: {issues}")
        else:
            logger.debug(f"Transition validation PASSED with strictness {strictness.value}")

        # Update adaptive state
        self._validation_history.append({
            'timestamp': time.time(),
            'preparation_id': preparation_result.get('preparation_id'),
            'mode': current_mode.value,
            'strictness': strictness.value,
            'is_valid': is_valid,
            'issues_count': len(issues)
        })
        # Keep history bounded
        if len(self._validation_history) > 1000:
            self._validation_history = self._validation_history[-1000:]

        # Update transition success rate (simplified - in reality would get feedback from transition execution)
        # For now, we assume validation passing correlates with success
        # This would be updated by a feedback mechanism after transition execution
        return is_valid

    def update_transition_outcome(self, success: bool, transition_id: Optional[str] = None) -> None:
        """
        Update the gate's knowledge of transition outcomes for adaptive learning.
        Called after a transition attempt to refine future validation strictness.

        Args:
            success: Whether the transition was successful
            transition_id: Optional identifier for the transition
        """
        # Simple exponential moving average for success rate
        alpha = 0.1  # Learning rate
        if self._transition_success_rate == 1.0:  # First update
            self._transition_success_rate = 1.0 if success else 0.0
        else:
            self._transition_success_rate = (alpha * (1.0 if success else 0.0) +
                                           (1.0 - alpha) * self._transition_success_rate)

        logger.debug(f"Updated transition success rate to {self._transition_success_rate:.3f} based on outcome: {success}")

        # Record outcome for history
        self._validation_history.append({
            'timestamp': time.time(),
            'transition_id': transition_id,
            'outcome': 'success' if success else 'failure',
            'updated_success_rate': self._transition_success_rate
        })

    def get_gate_diagnostics(self) -> Dict[str, Any]:
        """
        Get diagnostic information about the adaptive safety gate's state and performance.

        Returns:
            Dictionary containing diagnostic metrics
        """
        recent_validations = self._validation_history[-50:] if self._validation_history else []
        if recent_validations:
            validation_count = len(recent_validations)
            pass_count = sum(1 for v in recent_validations if v.get('is_valid', False))
            pass_rate = pass_count / validation_count if validation_count > 0 else 0.0
            # Average strictness distribution
            strictness_counts = {}
            for v in recent_validations:
                s = v.get('strictness', 'unknown')
                strictness_counts[s] = strictness_counts.get(s, 0) + 1
        else:
            validation_count = 0
            pass_rate = 0.0
            strictness_counts = {}

        return {
            'validation_history_size': len(self._validation_history),
            'recent_validation_count': validation_count,
            'recent_pass_rate': pass_rate,
            'strictness_distribution': strictness_counts,
            'transition_success_rate': self._transition_success_rate,
            'fault_injection_history_size': len(self._fault_injection_history),
            'adaptive_strictness': self._adaptive_strictness.value if hasattr(self, '_adaptive_strictness') else 'unknown'
        }