"""
Context-Aware Satya Layer - Layer 4: Truthfulness Validation for NALA Dual-Mode Operation.
Implements Satya (truthfulness) principle: maintaining factual consistency and
veracity of outputs through contextual validation and coherence checking.
"""

from __future__ import annotations

import time
import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
import json

# Import OperationMode from fleet coordinator
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from fleet.coordinator import OperationMode

logger = logging.getLogger(__name__)


class TruthfulnessLevel(Enum):
    """Levels of truthfulness validation strictness."""
    MINIMAL = "minimal"      # INTERACTIVE mode - basic consistency checks
    STANDARD = "standard"    # Balanced validation for most operations
    RIGOROUS = "rigorous"    # AUTONOMOUS mode - comprehensive fact-checking
    TRANSCENDENT = "transcendent"  # Enhanced validation for critical operations


@dataclass
class FactCheckResult:
    """Result of a factual consistency check."""
    is_consistent: bool
    confidence_score: float  # 0.0 to 1.0
    contradictions: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    validation_latency_ms: float = 0.0


@dataclass
class SatyaMetrics:
    """Metrics for tracking truthfulness over time."""
    truthfulness_score: float = 1.0  # Running average of truthfulness
    consistency_rate: float = 1.0    # Percentage of consistent outputs
    fact_check_latency_ms: float = 0.0  # Average latency for fact checks
    contradiction_count: int = 0     # Total contradictions detected
    last_updated: float = field(default_factory=time.time)


class ContextAwareSatyaLayer:
    """
    Context-aware truthfulness layer that validates factual consistency
    of outputs based on operational context and knowledge coherence.
    Implements Satya (truthfulness) principle: commitment to truth and
    factual accuracy in all manifestations.
    """

    def __init__(self,
                 min_fact_check_latency_ms: float = 25.0,
                 max_fact_check_latency_ms: float = 150.0,
                 enable_consistency_tracking: bool = True,
                 enable_contextual_validation: bool = True,
                 truth_decay_rate: float = 0.01):
        """
        Initialize the Context-Aware Satya Layer.

        Args:
            min_fact_check_latency_ms: Target latency for INTERACTIVE mode fact checking
            max_fact_check_latency_ms: Maximum latency for AUTONOMOUS mode fact checking
            enable_consistency_tracking: Whether to track consistency over time
            enable_contextual_validation: Whether to use context-aware validation
            truth_decay_rate: Rate at which truthfulness scores decay over time
        """
        self.min_fact_check_latency_ms = min_fact_check_latency_ms
        self.max_fact_check_latency_ms = max_fact_check_latency_ms
        self.enable_consistency_tracking = enable_consistency_tracking
        self.enable_contextual_validation = enable_contextual_validation
        self.truth_decay_rate = truth_decay_rate

        # State tracking for adaptive behavior
        self._fact_check_history: List[Dict[str, Any]] = []
        self._contradiction_history: List[Dict[str, Any]] = []
        self._truthfulness_metrics = SatyaMetrics()
        self._known_facts: Dict[str, Any] = {}  # Simplified knowledge base
        self._contextual_constraints: Dict[str, Any] = {}  # Context-specific truth rules

        # Initialize with some basic truths (in practice, this would load from knowledge base)
        self._initialize_basic_truths()

        logger.info("Context-Aware Satya Layer initialized")

    def _initialize_basic_truths(self) -> None:
        """Initialize basic factual truths for validation."""
        # In a real implementation, this would load from a trusted knowledge base
        self._known_facts = {
            "mathematical": {
                "2 + 2": 4,
                "10 / 2": 5,
                "true": True,
                "false": False
            },
            "logical": {
                "All humans are mortal": True,
                "If A implies B and A is true, then B is true": True
            },
            "temporal": {
                "present": "Current time is verifiable",
                "causality": "Cause precedes effect"
            }
        }

        # Initialize contextual constraints for different modes
        self._contextual_constraints = {
            OperationMode.INTERACTIVE: {
                "max_response_time_ms": 5000,
                "require_citations": False,
                "allow_reasoning": True
            },
            OperationMode.PREPARING_TO_AUTONOMOUS: {
                "max_response_time_ms": 10000,
                "require_citations": True,
                "allow_reasoning": True
            },
            OperationMode.PREPARING_TO_INTERACTIVE: {
                "max_response_time_ms": 10000,
                "require_citations": True,
                "allow_reasoning": True
            },
            OperationMode.SYNCING_STATE: {
                "max_response_time_ms": 10000,
                "require_citations": True,
                "allow_reasoning": True
            },
            OperationMode.AUTONOMOUS: {
                "max_response_time_ms": 30000,
                "require_citations": True,
                "allow_reasoning": True,
                "require_peer_review": True
            }
        }

    def _get_current_timestamp(self) -> float:
        """Get current timestamp for consistency checking."""
        return time.time()

    def _apply_truth_decay(self, last_update_time: float) -> float:
        """
        Apply time-based decay to truthfulness scores.

        Args:
            last_update_time: Timestamp of last update

        Returns:
            Decay factor (0.0 to 1.0)
        """
        age_seconds = self._get_current_timestamp() - last_update_time
        return max(0.0, 1.0 - (self.truth_decay_rate * age_seconds / 3600))  # Decay per hour

    def _check_factual_consistency(self,
                                 output_data: Dict[str, Any],
                                 context: Optional[Dict[str, Any]] = None) -> FactCheckResult:
        """
        Check factual consistency of output data against known truths.

        Args:
            output_data: The output to validate for truthfulness
            context: Optional contextual information for validation

        Returns:
            FactCheckResult with consistency assessment
        """
        start_time = self._get_current_timestamp()
        contradictions = []
        supporting_evidence = []
        consistency_score = 1.0  # Start with perfect score

        # Convert output to string representation for analysis
        output_str = json.dumps(output_data, sort_keys=True)

        # Check Against Known Facts
        for category, facts in self._known_facts.items():
            for fact_statement, expected_value in facts.items():
                # Simple string matching - in reality would use NLP/semantic matching
                if fact_statement.lower() in output_str.lower():
                    # Found a stated fact, check if it matches expected value
                    # This is a simplified check - real implementation would be more sophisticated
                    if str(expected_value).lower() in output_str.lower():
                        supporting_evidence.append(f"Fact confirmed: {fact_statement}")
                    else:
                        contradictions.append(f"Fact contradiction: {fact_statement} != expected")
                        consistency_score *= 0.8  # Penalize contradictions

        # Contextual Validation (if enabled)
        if self.enable_contextual_validation and context:
            context_consistency, context_violations = self._validate_contextual_constraints(
                output_data, context
            )
            contradictions.extend(context_violations)
            if not context_consistency:
                consistency_score *= 0.9

        # Check for Internal Consistency
        internal_consistency = self._check_internal_consistency(output_data)
        if not internal_consistency:
            contradictions.append("Internal inconsistency detected")
            consistency_score *= 0.85

        # Final consistency determination
        is_consistent = consistency_score >= 0.7 and len(contradictions) == 0
        consistency_score = max(0.0, min(1.0, consistency_score))

        latency_ms = (self._get_current_timestamp() - start_time) * 1000

        return FactCheckResult(
            is_consistent=is_consistent,
            confidence_score=consistency_score,
            contradictions=contradictions,
            supporting_evidence=supporting_evidence,
            validation_latency_ms=latency_ms
        )

    def _validate_contextual_constraints(self,
                                       output_data: Dict[str, Any],
                                       context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate output against context-specific constraints.

        Args:
            output_data: The output to validate
            context: Contextual information (operation mode, user intent, etc.)

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        current_mode = context.get('operation_mode')

        if current_mode and current_mode in self._contextual_constraints:
            constraints = self._contextual_constraints[current_mode]

            # Check response time constraints
            if 'response_time_ms' in output_data:
                max_time = constraints.get('max_response_time_ms', float('inf'))
                if output_data['response_time_ms'] > max_time:
                    violations.append(f"Response time {output_data['response_time_ms']}ms exceeds maximum {max_time}ms for {current_mode.value} mode")

            # Check for required elements
            if constraints.get('require_citations', False):
                if 'citations' not in output_data or not output_data['citations']:
                    violations.append("Citations required but not provided")

            # Check for forbidden elements in certain contexts
            if not constraints.get('allow_reasoning', True):
                if 'reasoning_chain' in output_data and output_data['reasoning_chain']:
                    violations.append("Reasoning chain not allowed in this context")

        return len(violations) == 0, violations

    def _check_internal_consistency(self, output_data: Dict[str, Any]) -> bool:
        """
        Check for internal logical consistency within the output.

        Args:
            output_data: The output to check

        Returns:
            True if internally consistent, False otherwise
        """
        # Simplified internal consistency checks
        # In practice, this would use logical reasoning engines

        # Check for obvious contradictions in boolean fields
        bool_fields = [k for k, v in output_data.items() if isinstance(v, bool)]
        for i in range(len(bool_fields)):
            for j in range(i+1, len(bool_fields)):
                field1, field2 = bool_fields[i], bool_fields[j]
                val1, val2 = output_data[field1], output_data[field2]

                # Example: if both claim to be true and mutually exclusive (ends with _true / _false)
                is_excl = (
                    (field1.endswith('_false') and field2.endswith('_true')) or
                    (field1.endswith('_true') and field2.endswith('_false'))
                )
                if is_excl:
                    base1 = field1[:-6] if field1.endswith('_false') else field1[:-5]
                    base2 = field2[:-6] if field2.endswith('_false') else field2[:-5]
                    if base1 == base2 and val1 and val2:
                        return False

        # Check numerical consistency
        numeric_fields = {k: v for k, v in output_data.items()
                         if isinstance(v, (int, float)) and not isinstance(v, bool)}

        # Example: probability should be between 0 and 1
        for field, value in numeric_fields.items():
            if 'prob' in field.lower() or ' likelihood' in field.lower():
                if not (0.0 <= value <= 1.0):
                    return False

        return True

    def _determine_truthfulness_level(self,
                                    current_mode: OperationMode,
                                    context: Optional[Dict[str, Any]] = None) -> TruthfulnessLevel:
        """
        Determine appropriate truthfulness validation level based on context.

        Args:
            current_mode: Current operation mode
            context: Optional contextual information

        Returns:
            Appropriate TruthfulnessLevel for validation
        """
        # Base level on operation mode
        if current_mode == OperationMode.INTERACTIVE:
            base_level = TruthfulnessLevel.MINIMAL
        elif current_mode == OperationMode.AUTONOMOUS:
            base_level = TruthfulnessLevel.RIGOROUS
        else:
            # PREPARING_TO_INTERACTIVE, PREPARING_TO_AUTONOMOUS, SYNCING_STATE, etc.
            base_level = TruthfulnessLevel.STANDARD

        # Adjust based on context if available
        if context:
            # Reduce strictness if system is under stress
            stress_level = context.get('stress_level', 0.0)  # 0.0 to 1.0
            if stress_level > 0.7:
                # Under high stress, reduce validation strictness to maintain responsiveness
                if base_level == TruthfulnessLevel.RIGOROUS:
                    base_level = TruthfulnessLevel.STANDARD
                elif base_level == TruthfulnessLevel.STANDARD:
                    base_level = TruthfulnessLevel.MINIMAL

            # Increase strictness for critical operations
            if context.get('is_critical_operation', False):
                if base_level == TruthfulnessLevel.MINIMAL:
                    base_level = TruthfulnessLevel.STANDARD
                elif base_level == TruthfulnessLevel.STANDARD:
                    base_level = TruthfulnessLevel.RIGOROUS

        return base_level

    def _apply_truthfulness_validation(self,
                                     output_data: Dict[str, Any],
                                     level: TruthfulnessLevel,
                                     context: Optional[Dict[str, Any]] = None) -> FactCheckResult:
        """
        Apply truthfulness validation at the specified level.

        Args:
            output_data: The output to validate
            level: The truthfulness validation level to apply
            context: Optional contextual information

        Returns:
            FactCheckResult from the validation
        """
        # All levels use the same core validation, but differ in thresholds and additional checks
        result = self._check_factual_consistency(output_data, context)

        # Apply level-specific adjustments
        if level == TruthfulnessLevel.MINIMAL:
            # Only check for blatant inconsistencies
            result.is_consistent = result.is_consistent and (result.confidence_score >= 0.5)
        elif level == TruthfulnessLevel.STANDARD:
            # Standard consistency requirements
            result.is_consistent = result.is_consistent and (result.confidence_score >= 0.7)
        elif level == TruthfulnessLevel.RIGOROUS:
            # Strict consistency with evidence requirements
            result.is_consistent = result.is_consistent and \
                                 (result.confidence_score >= 0.85) and \
                                 (len(result.supporting_evidence) >= 1)
        elif level == TruthfulnessLevel.TRANSCENDENT:
            # Highest standard - near perfect consistency required
            result.is_consistent = result.is_consistent and \
                                 (result.confidence_score >= 0.95) and \
                                 (len(result.contradictions) == 0) and \
                                 (len(result.supporting_evidence) >= 2)

        return result

    def validate_output_truthfulness(self,
                                   output_data: Dict[str, Any],
                                   current_mode: OperationMode,
                                   context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Public interface: Validate the truthfulness of an output.

        Args:
            output_data: The output to validate for truthfulness
            current_mode: Current operation mode (before any transition)
            context: Optional contextual information (user intent, system state, etc.)

        Returns:
            True if output meets truthfulness requirements, False otherwise
        """
        # Determine appropriate validation level
        truth_level = self._determine_truthfulness_level(current_mode, context)
        logger.debug(f"Satya Layer: selected truthfulness level {truth_level.value} for mode {current_mode.value}")

        # Apply validation
        result = self._apply_truthfulness_validation(output_data, truth_level, context)

        # Update metrics and history
        self._update_metrics(result)

        # Log results
        if not result.is_consistent:
            logger.warning(f"Truthfulness validation FAILED: {result.contradictions} "
                         f"(confidence: {result.confidence_score:.2f})")
        else:
            logger.debug(f"Truthfulness validation PASSED with level {truth_level.value} "
                       f"(confidence: {result.confidence_score:.2f})")

        return result.is_consistent

    def _update_metrics(self, result: FactCheckResult) -> None:
        """Update internal metrics based on validation result."""
        if not self.enable_consistency_tracking:
            return

        # Update truthfulness metrics (exponential moving average)
        alpha = 0.1  # Learning rate
        new_truthfulness = result.confidence_score

        if self._truthfulness_metrics.truthfulness_score == 1.0:  # First measurement
            self._truthfulness_metrics.truthfulness_score = new_truthfulness
        else:
            self._truthfulness_metrics.truthfulness_score = (
                alpha * new_truthfulness +
                (1.0 - alpha) * self._truthfulness_metrics.truthfulness_score
            )

        # Update consistency rate
        is_consistent = 1.0 if result.is_consistent else 0.0
        if self._truthfulness_metrics.consistency_rate == 1.0:  # First measurement
            self._truthfulness_metrics.consistency_rate = is_consistent
        else:
            self._truthfulness_metrics.consistency_rate = (
                alpha * is_consistent +
                (1.0 - alpha) * self._truthfulness_metrics.consistency_rate
            )

        # Update average latency
        if self._truthfulness_metrics.fact_check_latency_ms == 0.0:  # First measurement
            self._truthfulness_metrics.fact_check_latency_ms = result.validation_latency_ms
        else:
            self._truthfulness_metrics.fact_check_latency_ms = (
                alpha * result.validation_latency_ms +
                (1.0 - alpha) * self._truthfulness_metrics.fact_check_latency_ms
            )

        # Update contradiction count
        if not result.is_consistent:
            self._truthfulness_metrics.contradiction_count += len(result.contradictions)

        self._truthfulness_metrics.last_updated = self._get_current_timestamp()

        # Record in history
        self._fact_check_history.append({
            'timestamp': self._get_current_timestamp(),
            'consistency_result': result.is_consistent,
            'confidence_score': result.confidence_score,
            'contradictions_count': len(result.contradictions)
        })

        # Keep history bounded
        if len(self._fact_check_history) > 1000:
            self._fact_check_history = self._fact_check_history[-1000:]

    def get_satya_metrics(self) -> Dict[str, Any]:
        """
        Get current truthfulness metrics.

        Returns:
            Dictionary of truthfulness metrics
        """
        # Apply time-based decay to metrics
        decay_factor = self._apply_truth_decay(self._truthfulness_metrics.last_updated)

        return {
            'truthfulness_score': self._truthfulness_metrics.truthfulness_score * decay_factor,
            'consistency_rate': self._truthfulness_metrics.consistency_rate * decay_factor,
            'fact_check_latency_ms': self._truthfulness_metrics.fact_check_latency_ms,
            'contradiction_count': self._truthfulness_metrics.contradiction_count,
            'history_size': len(self._fact_check_history),
            'last_updated': self._truthfulness_metrics.last_updated
        }

    def update_truthfulness_feedback(self, was_accurate: bool, output_id: Optional[str] = None) -> None:
        """
        Update the layer's knowledge based on feedback about output accuracy.

        Args:
            was_accurate: Whether the output was factually accurate
            output_id: Optional identifier for the output
        """
        # Simple feedback mechanism - in practice would be more sophisticated
        feedback_value = 1.0 if was_accurate else 0.0
        alpha = 0.1  # Learning rate

        current_score = self._truthfulness_metrics.truthfulness_score
        new_score = alpha * feedback_value + (1.0 - alpha) * current_score
        self._truthfulness_metrics.truthfulness_score = new_score
        self._truthfulness_metrics.last_updated = self._get_current_timestamp()

        logger.debug(f"Updated truthfulness score to {new_score:.3f} based on feedback: {was_accurate}")

    def add_known_fact(self, statement: str, is_true: bool, evidence: Optional[List[str]] = None) -> None:
        """
        Add a new verified fact to the knowledge base.

        Args:
            statement: The factual statement
            is_true: Whether the statement is true
            evidence: Optional supporting evidence
        """
        fact_key = statement.lower().strip()
        self._known_facts.setdefault("user_provided", {})[fact_key] = is_true

        if evidence:
            # In a real implementation, we would store evidence with the fact
            pass

        logger.info(f"Added fact to knowledge base: '{statement}' -> {is_true}")

    def get_satya_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostic information about the satya layer.

        Returns:
            Dictionary containing diagnostic metrics and state information
        """
        metrics = self.get_satya_metrics()

        # Calculate recent trends
        recent_checks = self._fact_check_history[-50:] if self._fact_check_history else []
        if recent_checks:
            recent_consistency = sum(1 for c in recent_checks if c['consistency_result']) / len(recent_checks)
            recent_avg_confidence = sum(c['confidence_score'] for c in recent_checks) / len(recent_checks)
        else:
            recent_consistency = 0.0
            recent_avg_confidence = 0.0

        return {
            'truthfulness_metrics': metrics,
            'recent_consistency_rate': recent_consistency,
            'recent_avg_confidence': recent_avg_confidence,
            'knowledge_base_size': sum(len(v) for v in self._known_facts.values()),
            'contextual_rules_active': len(self._contextual_constraints),
            'total_fact_checks': len(self._fact_check_history),
            'total_contradictions': self._truthfulness_metrics.contradiction_count
        }