"""
Pramāṇa Router for NALA Transcendent Reasoning Engine
====================================================

Dynamically selects interaction modality (Gaṇeśa, Sarasvatī, Śiva models)
based on real-time Ṛta-Score from the RTA feedback loop, with hysteresis
prevention to avoid rapid model switching.

Implements the transcendent framework mapping:
- PRATYAKSHA (Direct Perception): Ṛta-Score < 0.60 → Gaṇeśa-model
- PAROKSHA (Transcendent Inference): 0.60 ≤ Ṛta-Score ≤ 0.95 → Sarasvatī-model
- ATHAPRAPTI (Direct Attainment): Ṛta-Score > 0.95 → Śiva-model

Integrates with interaction_contract.py for state management.
"""

import logging
from typing import Optional, List
from collections import deque

# Import core NALA components
try:
    from core.safety.rta_feedback_loop import get_default_rta_loop
    def get_rta_score() -> float:
        """Helper to fetch the live Rta-Score from the default loop."""
        try:
            score, _ = get_default_rta_loop().get_latest()
            return score
        except Exception:
            return 0.5
except ImportError:
    # Fallback for development/testing
    def get_rta_score() -> float:
        """Placeholder for RTA feedback loop - returns neutral score."""
        return 0.5

try:
    from core.interaction.interaction_contract \
        import update_model_state, get_current_model as get_contract_model
except ImportError:
    # Fallback stubs
    def update_model_state(model_id: str) -> None:
        pass

    def get_contract_model() -> Optional[str]:
        return None

logger = logging.getLogger(__name__)


class PramanaRouter:
    """
    Routes requests to appropriate transcendental models based on Ṛta-Score.

    Attributes:
        history_size: Number of recent scores to consider for hysteresis
        hysteresis_margin: Minimum margin required to trigger state change
        _score_history: Rolling window of recent Ṛta-Scores
        _current_model: Currently selected model identifier
        _stable_thresholds: Hysteresis-adjusted thresholds for each state
    """

    # Base thresholds from transcendent framework
    PRATYAKSHA_MAX = 0.60   # Below this: Gaṇeśa-model (obstacle-removing)
    PAROKSHA_MAX = 0.95     # Up to this: Sarasvatī-model (wisdom-seeking)
    # Above this: Śiva-model (destroyer-of-illusion)

    def __init__(self,
                 history_size: int = 5,
                 hysteresis_margin: float = 0.05):
        """
        Initialize the Pramāṇa router.

        Args:
            history_size: Number of recent scores to track for hysteresis
            hysteresis_margin: Minimum margin to prevent rapid switching
        """
        self.history_size = max(1, history_size)
        self.hysteresis_margin = max(0.0, min(hysteresis_margin, 0.1))
        self._score_history: deque = deque(maxlen=self.history_size)
        self._current_model: Optional[str] = None

        # Calculate hysteresis-adjusted thresholds
        self._prepare_hysteresis_thresholds()

        logger.info(f"Pramāṇa Router initialized: "
                   f"history={self.history_size}, "
                   f"hysteresis={self.hysteresis_margin}")

    def _prepare_hysteresis_thresholds(self) -> None:
        """Prepare thresholds with hysteresis buffer."""
        # With hysteresis, we need different thresholds for entering vs leaving states
        self._enter_paroksha = self.PRATYAKSHA_MAX + self.hysteresis_margin
        self._exit_paroksha_low = self.PRATYAKSHA_MAX - self.hysteresis_margin
        self._enter_shiva = min(0.99, self.PAROKSHA_MAX + self.hysteresis_margin)
        self._exit_shiva_low = self.PAROKSHA_MAX - self.hysteresis_margin

        logger.debug(f"Hysteresis thresholds: "
                     f"enter_paroksha>{self._enter_paroksha:.3f}, "
                     f"exit_paroksha<{self._exit_paroksha_low:.3f}, "
                     f"enter_shiva>{self._enter_shiva:.3f}, "
                     f"exit_shiva<{self._exit_shiva_low:.3f}")

    def update_score(self) -> Optional[str]:
        """
        Update the current Ṛta-Score and determine if model should change.

        Returns:
            New model identifier if changed, None if no change.
        """
        # Get latest Ṛta-Score from RTA feedback loop
        try:
            score = get_rta_score()
            if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                logger.warning(f"Invalid Ṛta-Score received: {score}. Using previous.")
                return None
        except Exception as e:
            logger.error(f"Failed to get Ṛta-Score: {e}")
            return None

        # Add to history
        self._score_history.append(score)
        logger.debug(f"Ṛta-Score: {score:.3f}, "
                    f"history: {[round(s, 3) for s in self._score_history]}")

        # Determine if we should change model
        new_model = self._determine_model_from_history()

        if new_model != self._current_model:
            logger.info(f"Model transition: {self._current_model} → {new_model} "
                       f"(Ṛta-Score: {score:.3f})")
            self._current_model = new_model
            # Update interaction contract state
            try:
                update_model_state(new_model)
            except Exception as e:
                logger.error(f"Failed to update interaction contract: {e}")
            return new_model

        return None

    def _determine_model_from_history(self) -> str:
        """
        Determine appropriate model based on recent score history with hysteresis.

        Returns:
            Model identifier string.
        """
        if not self._score_history:
            # No history yet - default to Paroksha (middle path)
            return "Sarasvatī-model"

        # Use average of recent scores for stability
        avg_score = sum(self._score_history) / len(self._score_history)
        # Alternatively could use median or require N consecutive readings

        current = self._current_model

        # State transition logic with hysteresis
        if current is None:
            # Initial state determination using base thresholds
            if avg_score < self.PRATYAKSHA_MAX:
                return "Gaṇeśa-model"
            elif avg_score > self.PAROKSHA_MAX:
                return "Śiva-model"
            else:
                return "Sarasvatī-model"

        elif current == "Gaṇeśa-model":
            # Currently in Pratyksha (low) region
            if avg_score > self._enter_paroksha:
                # Enough evidence to move to Paroksha
                return "Sarasvatī-model"
            else:
                # Stay in current state
                return "Gaṇeśa-model"

        elif current == "Sarasvatī-model":
            # Currently in Paroksha (middle) region
            if avg_score < self._exit_paroksha_low:
                # Sufficient evidence to drop to Pratyksha
                return "Gaṇeśa-model"
            elif avg_score > self._enter_shiva:
                # Sufficient evidence to rise to Aparapti
                return "Śiva-model"
            else:
                # Stay in middle
                return "Sarasvatī-model"

        elif current == "Śiva-model":
            # Currently in Aparapti (high) region
            if avg_score < self._exit_shiva_low:
                # Drop back to Paroksha
                return "Sarasvatī-model"
            else:
                # Stay in high state
                return "Śiva-model"

        else:
            # Unknown state - reset to middle
            return "Sarasvatī-model"

    def get_current_model(self) -> Optional[str]:
        """
        Get the currently selected model without updating score.

        Returns:
            Current model identifier or None if not initialized.
        """
        return self._current_model

    def get_current_score(self) -> Optional[float]:
        """
        Get the most recent Ṛta-Score.

        Returns:
            Latest score or None if no score available.
        """
        if self._score_history:
            return self._score_history[-1]
        return None

    def get_score_history(self) -> List[float]:
        """
        Get copy of recent score history.

        Returns:
            List of recent Ṛta-Scores.
        """
        return list(self._score_history)

    def reset(self) -> None:
        """Reset router state to initial conditions."""
        self._score_history.clear()
        self._current_model = None
        logger.info("Pramāṇa Router reset")


# Global router instance for easy access
_pramana_router: Optional[PramanaRouter] = None


def get_pramana_router() -> PramanaRouter:
    """
    Get or create the global Pramāṇa router instance.

    Returns:
        Singleton PramanaRouter instance.
    """
    global _pramana_router
    if _pramana_router is None:
        _pramana_router = PramanaRouter()
    return _pramana_router


def update_router() -> Optional[str]:
    """
    Convenience function to update the global router.

    Returns:
        New model identifier if changed, None otherwise.
    """
    return get_pramana_router().update_score()


def get_current_model() -> Optional[str]:
    """
    Convenience function to get current model from global router.

    Returns:
        Current model identifier.
    """
    return get_pramana_router().get_current_model()


if __name__ == "__main__":
    # Simple demo/test when run directly
    logging.basicConfig(level=logging.INFO)

    router = PramanaRouter(history_size=3, hysteresis_margin=0.05)

    # Simulate some scores
    test_scores = [0.3, 0.4, 0.55, 0.62, 0.7, 0.8, 0.92, 0.96, 0.94, 0.88, 0.6, 0.5, 0.4]

    print("Testing Pramāṇa Router with hysteresis...")
    print(f"{'Score':>6} {'History':<20} {'Model':<20} {'Change'}")
    print("-" * 60)

    for score in test_scores:
        # Patch the get_rta_score helper directly in this module's namespace
        original_get_rta_score = get_rta_score
        get_rta_score = lambda: score

        change = router.update_score()
        history_str = str([round(s, 2) for s in router.get_score_history()])
        model = router.get_current_model() or "None"
        change_str = "YES" if change else " "

        print(f"{score:6.2f} {history_str:<20} {model:<20} {change_str}")

        # Restore original function
        get_rta_score = original_get_rta_score