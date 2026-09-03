"""
Unit tests for the Pramāṇa Router (PramanaRouter).
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
from core.interaction import pramana_router
from core.interaction.pramana_router import (
    PramanaRouter, get_pramana_router, update_router, get_current_model
)


class TestPramanaRouter(unittest.TestCase):
    """Unit tests for the Pramāṇa Router."""

    def setUp(self) -> None:
        # Reset the global singleton before each test
        pramana_router._pramana_router = None

    def test_router_initialization(self) -> None:
        """Test that the router initializes with correct attributes."""
        router = PramanaRouter(history_size=3, hysteresis_margin=0.03)
        self.assertEqual(router.history_size, 3)
        self.assertEqual(router.hysteresis_margin, 0.03)
        self.assertIsNone(router.get_current_model())
        self.assertEqual(router.get_score_history(), [])

        # Check calculated boundaries
        self.assertAlmostEqual(router._enter_paroksha, 0.63)
        self.assertAlmostEqual(router._exit_paroksha_low, 0.57)
        self.assertAlmostEqual(router._enter_shiva, 0.98)
        self.assertAlmostEqual(router._exit_shiva_low, 0.92)

    def test_router_initialization_limits(self) -> None:
        """Test router initialization parameter boundaries."""
        # Minimum history size should be 1
        router = PramanaRouter(history_size=0, hysteresis_margin=-0.1)
        self.assertEqual(router.history_size, 1)
        self.assertEqual(router.hysteresis_margin, 0.0)

        # Maximum hysteresis margin is clamped to 0.1
        router_max = PramanaRouter(history_size=5, hysteresis_margin=0.25)
        self.assertEqual(router_max.hysteresis_margin, 0.1)

    def test_determine_model_empty_history(self) -> None:
        """Test default model returned when history is empty."""
        router = PramanaRouter()
        self.assertEqual(router._determine_model_from_history(), "Sarasvatī-model")

    def test_initial_state_determination(self) -> None:
        """Test initial model assignment based on first updates."""
        # Low score -> Gaṇeśa
        router = PramanaRouter(history_size=1)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.45):
            new_model = router.update_score()
            self.assertEqual(new_model, "Gaṇeśa-model")
            self.assertEqual(router.get_current_model(), "Gaṇeśa-model")

        # Medium score -> Sarasvatī
        router = PramanaRouter(history_size=1)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.75):
            new_model = router.update_score()
            self.assertEqual(new_model, "Sarasvatī-model")
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # High score -> Śiva
        router = PramanaRouter(history_size=1)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.97):
            new_model = router.update_score()
            self.assertEqual(new_model, "Śiva-model")
            self.assertEqual(router.get_current_model(), "Śiva-model")

    def test_hysteresis_transitions(self) -> None:
        """Test state transitions with hysteresis boundaries."""
        # Create router: enter_paroksha = 0.65, exit_paroksha = 0.55
        router = PramanaRouter(history_size=3, hysteresis_margin=0.05)

        # 1. Start in Gaṇeśa (low)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.3):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Gaṇeśa-model")

        # Update with score = 0.62. Average: (0.3+0.3+0.62)/3 = 0.406.
        # Still Gaṇeśa.
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.62):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Gaṇeśa-model")

        # Update with score = 0.8. Average: (0.3+0.62+0.8)/3 = 0.573.
        # Still Gaṇeśa because avg (0.573) is not above enter_paroksha (0.65).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.8):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Gaṇeśa-model")

        # Update with score = 0.8. Average: (0.62+0.8+0.8)/3 = 0.74.
        # Transitions to Sarasvatī because avg (0.74) is above enter_paroksha (0.65).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.8):
            changed = router.update_score()
            self.assertEqual(changed, "Sarasvatī-model")
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # 2. Stay in Sarasvatī if score drops slightly.
        # Update with score = 0.58. Average: (0.8+0.8+0.58)/3 = 0.726.
        # Still Sarasvatī.
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.58):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # Update with score = 0.4. Average: (0.8+0.58+0.4)/3 = 0.593.
        # Still Sarasvatī because avg (0.593) is not below exit_paroksha_low (0.55).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.4):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # Update with score = 0.4. Average: (0.58+0.4+0.4)/3 = 0.46.
        # Transitions back to Gaṇeśa because avg (0.46) is below exit_paroksha_low (0.55).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.4):
            changed = router.update_score()
            self.assertEqual(changed, "Gaṇeśa-model")

    def test_shiva_transitions(self) -> None:
        """Test transitions into and out of Śiva-model with hysteresis."""
        # Create router: enter_shiva = 0.99, exit_shiva_low = 0.90
        router = PramanaRouter(history_size=2, hysteresis_margin=0.05)

        # Start in Sarasvatī
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.75):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # Update with 1.0. Average: (0.75+1.0)/2 = 0.875.
        with patch("core.interaction.pramana_router.get_rta_score", return_value=1.0):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")

        # Update with 1.0. Average: (1.0+1.0)/2 = 1.0.
        # Transitions to Śiva-model because avg (1.0) is above enter_shiva (0.99).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=1.0):
            changed = router.update_score()
            self.assertEqual(changed, "Śiva-model")
            self.assertEqual(router.get_current_model(), "Śiva-model")

        # Drop score slightly to 0.92. Average: (1.0+0.92)/2 = 0.96.
        # Remains in Śiva-model.
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.92):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_model(), "Śiva-model")

        # Drop score to 0.85. Average: (0.92+0.85)/2 = 0.885.
        # Transitions back to Sarasvatī because avg (0.885) is below exit_shiva_low (0.90).
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.85):
            changed = router.update_score()
            self.assertEqual(changed, "Sarasvatī-model")

    def test_invalid_scores(self) -> None:
        """Test that invalid score updates are discarded."""
        router = PramanaRouter(history_size=3)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.75):
            router.update_score()

        # Update with out of bounds score (1.5)
        with patch("core.interaction.pramana_router.get_rta_score", return_value=1.5):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_score(), 0.75)

        # Update with type error (string)
        with patch("core.interaction.pramana_router.get_rta_score", return_value="invalid"):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_score(), 0.75)

        # Exception during get_rta_score
        with patch("core.interaction.pramana_router.get_rta_score", side_effect=ValueError("Error")):
            self.assertIsNone(router.update_score())
            self.assertEqual(router.get_current_score(), 0.75)

    def test_reset(self) -> None:
        """Test reset functionality clearing history and current model."""
        router = PramanaRouter()
        with patch("core.interaction.pramana_router.get_rta_score", return_value=0.75):
            router.update_score()
            self.assertEqual(router.get_current_model(), "Sarasvatī-model")
            self.assertEqual(router.get_current_score(), 0.75)

        router.reset()
        self.assertIsNone(router.get_current_model())
        self.assertIsNone(router.get_current_score())
        self.assertEqual(router.get_score_history(), [])

    def test_global_singleton_methods(self) -> None:
        """Test convenience wrappers around global singleton router."""
        # Verify get_pramana_router returns same instance
        router1 = get_pramana_router()
        router2 = get_pramana_router()
        self.assertIs(router1, router2)

        # Mock the singleton updates
        with patch.object(router1, "update_score", return_value="Gaṇeśa-model") as mock_update:
            res = update_router()
            mock_update.assert_called_once()
            self.assertEqual(res, "Gaṇeśa-model")

        with patch.object(router1, "get_current_model", return_value="Sarasvatī-model") as mock_get:
            res = get_current_model()
            mock_get.assert_called_once()
            self.assertEqual(res, "Sarasvatī-model")


if __name__ == "__main__":
    unittest.main()
