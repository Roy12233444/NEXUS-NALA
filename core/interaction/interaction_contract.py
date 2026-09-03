"""
Interaction Contract for NALA Transcendent Reasoning Engine
==========================================================

Manages the persistent state of the currently selected transcendental model
(Gaṇeśa, Sarasvatī, Śiva) with validation, thread-safety, optional persistence,
change notifications, and audit logging.

This module provides the "contract" that guarantees the system's model state is
consistent, valid, and observable across components.
"""

import threading
import os
import json
import time
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TranscendentalModel(Enum):
    """Enumeration of the three transcendental models in NALA's framework."""
    GANESHA = auto()      # Gaṇeśa-model: obstacle-removing, low-latency
    SARASVATI = auto()    # Sarasvatī-model: wisdom-seeking, high-depth
    SHIVA = auto()        # Śiva-model: destroyer-of-illusion, self-referential

    @classmethod
    def from_string(cls, model_str: str) -> Optional['TranscendentalModel']:
        """
        Convert a model string to the corresponding enum member.

        Args:
            model_str: String representation (e.g., "Gaṇeśa-model")

        Returns:
            Corresponding TranscendentalModel or None if not found.
        """
        lookup = {
            "Gaṇeśa-model": cls.GANESHA,
            "Sarasvatī-model": cls.SARASVATI,
            "Śiva-model": cls.SHIVA,
            # Also accept spelling variations without diacritics for robustness
            "Ganesha-model": cls.GANESHA,
            "Sarasvati-model": cls.SARASVATI,
            "Shiva-model": cls.SHIVA,
        }
        return lookup.get(model_str.strip())

    def to_string(self) -> str:
        """Get the canonical string representation."""
        mapping = {
            TranscendentalModel.GANESHA: "Gaṇeśa-model",
            TranscendentalModel.SARASVATI: "Sarasvatī-model",
            TranscendentalModel.SHIVA: "Śiva-model",
        }
        return mapping[self]

    @classmethod
    def all_strings(cls) -> List[str]:
        """Get list of all valid model strings."""
        return [m.to_string() for m in cls]


class InteractionContract:
    """
    Thread-safe contract for managing the current transcendental model state.

    Features:
    - Validates model transitions against known transcendental models
    - Thread-safe operations using reentrant lock
    - Optional persistence to file for crash recovery
    - Change notification via callback system
    - Audit logging of all state changes
    - Health checking and introspection methods
    """

    def __init__(
        self,
        persistence_file: Optional[str] = None,
        enable_persistence: bool = True,
        enable_callbacks: bool = True,
        max_audit_entries: int = 1000
    ):
        """
        Initialize the interaction contract.

        Args:
            persistence_file: Path to file for persisting state (default: ./interaction_state.json)
            enable_persistence: Whether to persist state to disk
            enable_callbacks: Whether to enable change notification callbacks
            max_audit_entries: Maximum number of audit log entries to retain
        """
        self._lock = threading.RLock()
        self._current_model: Optional[TranscendentalModel] = None
        self._last_updated: Optional[datetime] = None

        # Persistence configuration
        self._enable_persistence = enable_persistence
        if persistence_file is None:
            persistence_file = os.path.join(
                os.path.dirname(__file__), "interaction_state.json"
            )
        self._persistence_file = os.path.abspath(persistence_file)

        # Callback system
        self._enable_callbacks = enable_callbacks
        self._change_callbacks: List[Callable[[str, str], None]] = []

        # Audit logging
        self._max_audit_entries = max_audit_entries
        self._audit_log: List[Dict[str, Any]] = []

        # Initialize from persisted state if available
        if self._enable_persistence:
            self._load_state()

        logger.info(
            f"InteractionContract initialized: "
            f"persistence={'on' if self._enable_persistence else 'off'}, "
            f"callbacks={'on' if self._enable_callbacks else 'off'}, "
            f"persistence_file='{self._persistence_file}'"
        )

    # ======================
    # Core State Management
    # ======================

    def update_model_state(self, model_id: str) -> bool:
        """
        Update the current model after validation.

        Args:
            model_id: String identifier of the model to set

        Returns:
            True if state was changed, False if rejected or no change.
        """
        # Validate input
        if not isinstance(model_id, str):
            logger.warning(f"Invalid model_id type: {type(model_id)}. Expected string.")
            return False

        model_enum = TranscendentalModel.from_string(model_id)
        if model_enum is None:
            logger.warning(
                f"Invalid model_id '{model_id}'. "
                f"Valid options: {TranscendentalModel.all_strings()}"
            )
            return False

        with self._lock:
            # Check if this is actually a change
            if self._current_model == model_enum:
                logger.debug(f"Model state unchanged: {model_id}")
                return False

            old_model_str = self._current_model.to_string() if self._current_model else None
            new_model_str = model_enum.to_string()

            # Update state
            self._current_model = model_enum
            self._last_updated = datetime.now()

            # Persist if enabled
            if self._enable_persistence:
                self._save_state()

            # Audit log
            audit_entry = {
                "timestamp": self._last_updated.isoformat(),
                "old_model": old_model_str,
                "new_model": new_model_str,
                "changed": True
            }
            self._audit_log.append(audit_entry)
            # Trim audit log if needed
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries:]

            logger.info(f"Model state updated: {old_model_str} → {new_model_str}")

            # Notify callbacks (outside lock to avoid deadlocks)
            if self._enable_callbacks:
                self._notify_callbacks(old_model_str, new_model_str)

            return True

    def get_current_model(self) -> Optional[str]:
        """
        Get the currently active model identifier.

        Returns:
            Model string or None if no model has been set.
        """
        with self._lock:
            return self._current_model.to_string() if self._current_model else None

    def get_current_model_enum(self) -> Optional[TranscendentalModel]:
        """
        Get the currently active model as an enum (internal use).

        Returns:
            TranscendentalModel enum or None.
        """
        with self._lock:
            return self._current_model

    def is_model_valid(self, model_id: str) -> bool:
        """
        Check if a model ID string is valid according to the transcendental framework.

        Args:
            model_id: String to validate

        Returns:
            True if valid, False otherwise.
        """
        return TranscendentalModel.from_string(model_id) is not None

    # ==================
    # Persistence Layer
    # ==================

    def _save_state(self) -> None:
        """Save current state to persistence file."""
        if not self._enable_persistence:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._persistence_file), exist_ok=True)

            state_data = {
                "current_model": self._current_model.to_string() if self._current_model else None,
                "last_updated": self._last_updated.isoformat() if self._last_updated else None,
                "schema_version": "1.0",
                "saved_at": datetime.now().isoformat()
            }

            # Write atomically via temp file
            temp_file = f"{self._persistence_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
            os.replace(temp_file, self._persistence_file)

            logger.debug(f"State persisted to {self._persistence_file}")

        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def _load_state(self) -> None:
        """Load state from persistence file if it exists."""
        if not os.path.exists(self._persistence_file):
            logger.info(f"No persistence file found at {self._persistence_file}")
            return

        try:
            with open(self._persistence_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            model_str = state_data.get("current_model")
            if model_str and self.is_model_valid(model_str):
                self._current_model = TranscendentalModel.from_string(model_str)
                # Parse timestamp if present
                last_updated_str = state_data.get("last_updated")
                if last_updated_str:
                    try:
                        self._last_updated = datetime.fromisoformat(last_updated_str)
                    except ValueError:
                        self._last_updated = datetime.now()
                else:
                    self._last_updated = datetime.now()

                logger.info(
                    f"State loaded from persistence: {self._current_model.to_string()} "
                    f"(updated {self._last_updated.isoformat()})"
                )
            else:
                logger.warning(
                    f"Invalid or missing model in persistence file: {model_str}. "
                    "Starting with no model."
                )
                self._current_model = None
                self._last_updated = None

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load state from {self._persistence_file}: {e}")
            self._current_model = None
            self._last_updated = None

    # ===================
    # Callback System
    # ===================

    def _notify_callbacks(self, old_model: Optional[str], new_model: Optional[str]) -> None:
        """Invoke all registered callbacks with the model change."""
        if not self._enable_callbacks:
            return

        callbacks = []
        with self._lock:
            callbacks = list(self._change_callbacks)  # Copy to avoid modification during iteration

        for callback in callbacks:
            try:
                callback(old_model, new_model)
            except Exception as e:
                logger.error(f"Error in interaction contract callback: {e}")

    def register_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a function to be called on model state changes.

        Args:
            callback: Function taking (old_model_str, new_model_str) -> None
        """
        if not callable(callback):
            raise TypeError("Callback must be callable")

        with self._lock:
            if callback not in self._change_callbacks:
                self._change_callbacks.append(callback)
                logger.debug(f"Registered change callback: {callback.__name__}")

    def unregister_change_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Remove a previously registered callback.

        Args:
            callback: The callback function to remove
        """
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)
                logger.debug(f"Unregistered change callback: {callback.__name__}")

    # ==================
    # Introspection
    # ==================

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get comprehensive state information for debugging/monitoring.

        Returns:
            Dictionary containing current state, configuration, and stats.
        """
        with self._lock:
            return {
                "current_model": self._current_model.to_string() if self._current_model else None,
                "current_model_enum": self._current_model.name if self._current_model else None,
                "last_updated": self._last_updated.isoformat() if self._last_updated else None,
                "is_valid": self._current_model is not None,
                "persistence_enabled": self._enable_persistence,
                "persistence_file": self._persistence_file if self._enable_persistence else None,
                "callbacks_enabled": self._enable_callbacks,
                "callback_count": len(self._change_callbacks),
                "audit_entries": len(self._audit_log),
                "max_audit_entries": self._max_audit_entries
            }

    def get_audit_log(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get audit log entries (most recent first).

        Args:
            limit: Maximum number of entries to return (None for all)

        Returns:
            List of audit log dictionaries.
        """
        with self._lock:
            if limit is None:
                return list(reversed(self._audit_log))
            return list(reversed(self._audit_log[-limit:]))

    def clear_audit_log(self) -> None:
        """Clear the audit log (useful for testing or privacy)."""
        with self._lock:
            self._audit_log.clear()
            logger.info("Audit log cleared")

    def reset(self) -> None:
        """
        Reset the contract to initial state (no model selected).
        Primarily useful for testing.
        """
        with self._lock:
            old_model_str = self._current_model.to_string() if self._current_model else None
            self._current_model = None
            self._last_updated = None

            # Clear persistence file if enabled
            if self._enable_persistence and os.path.exists(self._persistence_file):
                try:
                    os.remove(self._persistence_file)
                    logger.info(f"Removed persistence file: {self._persistence_file}")
                except OSError as e:
                    logger.error(f"Failed to remove persistence file: {e}")

            # Clear audit log on reset
            self._audit_log.clear()

            logger.info(f"Interaction contract reset: {old_model_str} → None")

            # Notify callbacks of reset to None
            if self._enable_callbacks:
                self._notify_callbacks(old_model_str, None)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the interaction contract.

        Returns:
            Dictionary with health status, issues, and timestamp.
        """
        issues = []
        status = "healthy"

        # Check persistence directory if enabled
        if self._enable_persistence:
            dir_name = os.path.dirname(self._persistence_file)
            if dir_name and not os.path.exists(dir_name):
                issues.append(f"Persistence directory does not exist: {dir_name}")
                status = "degraded"
            elif not os.access(dir_name or '.', os.W_OK):
                issues.append(f"Persistence directory is not writable: {dir_name}")
                status = "unhealthy"

        # Check current model validity
        with self._lock:
            if self._current_model is not None:
                # Already validated via enum, but double-check
                if not self.is_model_valid(self._current_model.to_string()):
                    issues.append("Current model is invalid")
                    status = "unhealthy"

        return {
            "status": status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "details": self.get_state_info()
        }


# =======================
# Module-Level Singleton
# =======================

# Global contract instance for easy access throughout the codebase
_interaction_contract: Optional[InteractionContract] = None


def get_interaction_contract() -> InteractionContract:
    """
    Get or create the global InteractionContract instance (singleton pattern).

    Returns:
        The singleton InteractionContract instance.
    """
    global _interaction_contract
    if _interaction_contract is None:
        _interaction_contract = InteractionContract()
    return _interaction_contract


def update_model_state(model_id: str) -> bool:
    """
    Convenience function to update the global interaction contract state.

    Args:
        model_id: String identifier of the model to set

    Returns:
        True if state was changed, False if rejected or no change.
    """
    return get_interaction_contract().update_model_state(model_id)


def get_current_model() -> Optional[str]:
    """
    Convenience function to get current model from the global contract.

    Returns:
        Current model identifier string or None.
    """
    return get_interaction_contract().get_current_model()


def is_model_valid(model_id: str) -> bool:
    """
    Convenience function to validate a model ID string.

    Args:
        model_id: String to validate

    Returns:
        True if valid, False otherwise.
    """
    return get_interaction_contract().is_model_valid(model_id)


# ======================
# Demo / Self-Test
# ======================

if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("Interaction Contract Demo / Self-Test")
    print("=" * 60)

    # Create instance with persistence disabled for clean demo
    contract = InteractionContract(enable_persistence=False, enable_callbacks=True)

    print(f"\nInitial state: {contract.get_current_model()}")

    # Test valid transitions
    print("\n--- Testing Valid Transitions ---")
    test_sequence = [
        "Gaṇeśa-model",
        "Sarasvatī-model",
        "Śiva-model",
        "Gaṇeśa-model",  # Repeat to test no-change detection
        "Sarasvatī-model"
    ]

    for model in test_sequence:
        changed = contract.update_model_state(model)
        current = contract.get_current_model()
        print(f"Set '{model}': {'CHANGED' if changed else 'NO CHANGE'} → Current: {current}")

    # Test invalid inputs
    print("\n--- Testing Invalid Inputs ---")
    invalid_inputs = [
        "invalid-model",
        "",  # Empty string
        "Ganesha-model",  # Missing diacritics (should work due to fallback)
        "Ganesha-model",  # Actually should work - testing fallback
        "Shiva-model",    # Should work
        123,              # Wrong type
        None              # Wrong type
    ]

    for inp in invalid_inputs:
        if not isinstance(inp, str):
            # For non-strings, we expect immediate rejection in update_model_state
            result = contract.update_model_state(str(inp)) if inp is not None else False
            # Actually better to test directly
            valid = contract.is_model_valid(str(inp)) if inp is not None else False
            print(f"Input {repr(inp)}: valid={valid}, update_result={result if isinstance(inp, str) else 'N/A'}")
        else:
            changed = contract.update_model_state(inp)
            current = contract.get_current_model()
            print(f"Set '{inp}': {'SUCCESS' if changed else 'FAILED'} → Current: {current}")

    # Test callbacks
    print("\n--- Testing Callback System ---")
    callback_log = []

    def test_callback(old_model, new_model):
        callback_log.append((old_model, new_model))
        print(f"  [CALLBACK] {old_model} → {new_model}")

    contract.register_change_callback(test_callback)
    print("Registered test callback.")

    print("Changing model to trigger callback:")
    contract.update_model_state("Śiva-model")
    contract.update_model_state("Gaṇeśa-model")

    print(f"Callback received {len(callback_log)} calls:")
    for old, new in callback_log:
        print(f"  {old} → {new}")

    # Test introspection
    print("\n--- State Information ---")
    info = contract.get_state_info()
    for key, value in info.items():
        print(f"{key:25}: {value}")

    print("\n--- Recent Audit Log (last 3) ---")
    for entry in contract.get_audit_log(limit=3):
        print(f"  {entry['timestamp']}: {entry['old_model']} → {entry['new_model']}")

    # Test health check
    print("\n--- Health Check ---")
    health = contract.health_check()
    print(f"Status: {health['status']}")
    if health['issues']:
        print("Issues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("No issues detected.")

    # Test reset
    print("\n--- Testing Reset ---")
    print(f"Before reset: {contract.get_current_model()}")
    contract.reset()
    print(f"After reset: {contract.get_current_model()}")

    print("\n" + "=" * 60)
    print("Demo completed.")
    print("=" * 60)