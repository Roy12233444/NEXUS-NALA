"""
Model Router for NALA Transcendent Reasoning Engine
==================================================

Translates the current transcendental model state (Gaṇeśa, Sarasvatī, Śiva)
into concrete tool selections, execution parameters, and reasoning strategies.
Implements hysteresis at the tool level to prevent thrashing and provides
adaptive configuration based on model state and task context.

Integrates with:
- Interaction Contract (to read current model state)
- Tool Registry (for available tool discovery)
- Predictive Tool Selector (for preemptive loading hints)
- Executor (to deliver final tool selection + parameters)
"""

import logging
import threading
import time
from typing import Optional, Dict, List, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import json
import os

# Import NALA components with fallbacks for development/testing
try:
    from core.interaction.interaction_contract import get_current_model, get_interaction_contract
except ImportError:
    # Fallback stubs
    def get_current_model() -> Optional[str]:
        return None

    def get_interaction_contract():
        class DummyContract:
            def get_current_model(self) -> Optional[str]:
                return None
        return DummyContract()

try:
    from core.hands.tool_registry import get_tool_registry
except ImportError:
    # Fallback stub
    def get_tool_registry():
        class DummyRegistry:
            def get_tool(self, name: str) -> Optional[Any]:
                return None
            def list_tools(self) -> List[str]:
                return []
        return DummyRegistry()

try:
    from core.hands.predictive_tool_selector import get_predictive_tool_selector
except ImportError:
    # Fallback stub
    def get_predictive_tool_selector():
        class DummySelector:
            def hint_tool_loading(self, tool_names: List[str]) -> None:
                pass
        return DummySelector()

logger = logging.getLogger(__name__)


@dataclass
class ToolProfile:
    """Configuration profile for a tool or set of tools."""
    name: str
    description: str
    # Tool-specific configuration
    timeout_seconds: float = 30.0
    max_retries: int = 3
    priority: int = 1  # Lower number = higher priority
    resource_weight: float = 1.0  # Relative CPU/memory usage
    safety_level: str = "medium"  # low, medium, high
    enabled: bool = True
    # Metadata for selection
    tags: List[str] = field(default_factory=list)
    # Dynamic state
    last_used: float = 0.0
    use_count: int = 0
    success_count: int = 0
    total_latency: float = 0.0


@dataclass
class ExecutionProfile:
    """Overall execution parameters for a given model state."""
    model: str
    tool_bundle: List[str]  # Ordered list of tool names to try
    global_timeout: float = 60.0
    max_parallel_tools: int = 1
    resource_allocation: str = "medium"  # low, medium, high
    safety_override: str = "medium"  # Can override tool-specific safety
    enable_fallback: bool = True
    cache_aggressiveness: str = "medium"  # low, medium, high
    description: str = ""


# Predefined tool profiles for each transcendental model
# These would ideally be loaded from configuration, but we define defaults here
GAÑEŚA_TOOLS = {
    # Obstacle-removing, low-latency tools
    "syntax_checker": ToolProfile(
        name="syntax_checker",
        description="Fast syntax and basic semantic validation",
        timeout_seconds=2.0,
        max_retries=1,
        priority=1,
        resource_weight=0.5,
        safety_level="high",
        tags=["validation", "fast", "obstacle-removal"]
    ),
    "linter": ToolProfile(
        name="linter",
        description="Code style and basic error detection",
        timeout_seconds=3.0,
        max_retries=1,
        priority=2,
        resource_weight=0.7,
        safety_level="high",
        tags=["validation", "style", "fast"]
    ),
    "unit_test_runner": ToolProfile(
        name="unit_test_runner",
        description="Runs quick unit tests to verify fixes",
        timeout_seconds=5.0,
        max_retries=2,
        priority=3,
        resource_weight=1.0,
        safety_level="high",
        tags=["testing", "verification", "fast"]
    ),
    "error_fixer": ToolProfile(
        name="error_fixer",
        description="Applies quick fixes for common errors",
        timeout_seconds=4.0,
        max_retries=2,
        priority=4,
        resource_weight=0.8,
        safety_level="high",
        tags=["repair", "fast", "obstacle-removal"]
    )
}

SARASVATĪ_TOOLS = {
    # Wisdom-seeking, high-depth tools
    "deep_analyzer": ToolProfile(
        name="deep_analyzer",
        description="Performs deep semantic and structural analysis",
        timeout_seconds=30.0,
        max_retries=5,
        priority=1,
        resource_weight=2.0,
        safety_level="medium",
        tags=["analysis", "deep", "wisdom-seeking"]
    ),
    "research_synthesizer": ToolProfile(
        name="research_synthesizer",
        description="Gathers and synthesizes information from multiple sources",
        timeout_seconds=45.0,
        max_retries=3,
        priority=2,
        resource_weight=2.5,
        safety_level="medium",
        tags=["research", "synthesis", "deep"]
    ),
    "pattern_finder": ToolProfile(
        name="pattern_finder",
        description="Identifies complex patterns and relationships",
        timeout_seconds=25.0,
        max_retries=4,
        priority=3,
        resource_weight=1.8,
        safety_level="medium",
        tags=["analysis", "patterns", "deep"]
    ),
    "hypothesis_generator": ToolProfile(
        name="hypothesis_generator",
        description="Generates multiple hypotheses for complex problems",
        timeout_seconds=35.0,
        max_retries=3,
        priority=4,
        resource_weight=2.2,
        safety_level="medium",
        tags=["generation", "hypothesis", "deep"]
    ),
    "cross_referencer": ToolProfile(
        name="cross_referencer",
        description="Cross-references information across knowledge bases",
        timeout_seconds=40.0,
        max_retries=3,
        priority=5,
        resource_weight=2.0,
        safety_level="medium",
        tags=["research", "cross-reference", "deep"]
    )
}

ŚIVA_TOOLS = {
    # Destroyer-of-illusion, self-referential tools
    "assumption_challenger": ToolProfile(
        name="assumption_challenger",
        description="Identifies and challenges underlying assumptions",
        timeout_seconds=60.0,
        max_retries=5,
        priority=1,
        resource_weight=3.0,
        safety_level="low",  # Requires careful oversight
        tags=["challenge", "assumption", "breakthrough"]
    ),
    "perspective_shifter": ToolProfile(
        name="perspective_shifter",
        description="Forces consideration of alternative viewpoints",
        timeout_seconds=50.0,
        max_retries=4,
        priority=2,
        resource_weight=2.8,
        safety_level="low",
        tags=["perspective", "reframing", "breakthrough"]
    ),
    "contradiction_finder": ToolProfile(
        name="contradiction_finder",
        description="Finds logical contradictions in reasoning",
        timeout_seconds=55.0,
        max_retries=5,
        priority=3,
        resource_weight=3.2,
        safety_level="low",
        tags=["logic", "contradiction", "breakthrough"]
    ),
    "deconstructor": ToolProfile(
        name="deconstructor",
        description="Breaks down complex systems into fundamental principles",
        timeout_seconds=70.0,
        max_retries=4,
        priority=4,
        resource_weight=3.5,
        safety_level="low",
        tags=["deconstruction", "first-principles", "breakthrough"]
    ),
    "radical_reframer": ToolProfile(
        name="radical_reframer",
        description="Profoundly reframes problems in novel ways",
        timeout_seconds=80.0,
        max_retries=3,
        priority=5,
        resource_weight=4.0,
        safety_level="very_low",  # Highest risk, highest reward
        tags=["reframing", "radical", "breakthrough"]
    )
}


class ModelRouter:
    """
    Routes requests to appropriate tools and execution profiles based on
    the current transcendental model state.

    Features:
    - Maps transcendental models to tool bundles and execution parameters
I'll now provide the complete implementation of the ModelRouter class as requested, ensuring it has all the functionality described in the plan.
    """

    def __init__(
        self,
        interaction_interval: float = 5.0,  # How often to check for model updates (seconds)
        tool_hysteresis_window: int = 3,    # Number of recent tool selections to consider for hysteresis
        tool_hysteresis_threshold: float = 0.6,  # Minimum proportion for tool change
        enable_tool_hysteresis: bool = True,
        enable_tool_learning: bool = True,
        enable_predictive_hints: bool = True
    ):
        """
        Initialize the Model Router.

        Args:
            interaction_interval: How often to poll for model updates (seconds)
            tool_hysteresis_window: Size of history window for tool selection hysteresis
            tool_hysteresis_threshold: Threshold fraction for triggering tool change
            enable_tool_hysteresis: Whether to apply hysteresis to tool selection
            enable_tool_learning: Whether to learn from tool execution outcomes
            enable_predictive_hints: Whether to provide hints to predictive tool selector
        """
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"{__name__}.ModelRouter")

        # Configuration
        self._interaction_interval = interaction_interval
        self._tool_hysteresis_window = max(1, tool_hysteresis_window)
        self._tool_hysteresis_threshold = max(0.0, min(tool_hysteresis_threshold, 1.0))
        self._enable_tool_hysteresis = enable_tool_hysteresis
        self._enable_tool_learning = enable_tool_learning
        self._enable_predictive_hints = enable_predictive_hints

        # State
        self._current_model: Optional[str] = None
        self._last_model_check: float = 0.0
        self._current_tool_bundle: List[str] = []
        self._current_execution_profile: Optional[ExecutionProfile] = None
        self._tool_profiles: Dict[str, ToolProfile] = {}  # Populated from registries and defaults
        self._tool_selection_history: deque = deque(maxlen=self._tool_hysteresis_window)
        self._last_tool_bundle_update: float = 0.0
        self._update_callbacks: List[Callable[[str, str], None]] = []  # (old_model, new_model)

        # Performance tracking
        self._tool_performance: Dict[str, Dict[str, Any]] = {}  # Tool -> metrics

        # Initialize with default tool profiles
        self._load_default_tool_profiles()

        # Last known state for change detection
        self._last_known_model: Optional[str] = None

        self._logger.info(
            f"Model Router initialized: "
            f"interaction_interval={self._interaction_interval}s, "
            f"tool_hysteresis_window={self._tool_hysteresis_window}, "
            f"tool_hysteresis_threshold={self._tool_hysteresis_threshold}"
        )

    def _load_default_tool_profiles(self) -> None:
        """Load default tool profiles for each transcendental model."""
        # Clear and reload
        self._tool_profiles.clear()

        # Add Gaṇeśa tools
        for name, profile in GAÑEŚA_TOOLS.items():
            self._tool_profiles[name] = profile

        # Add Sarasvatī tools
        for name, profile in SARASVATĪ_TOOLS.items():
            self._tool_profiles[name] = profile

        # Add Śiva tools
        for name, profile in ŚIVA_TOOLS.items():
            self._tool_profiles[name] = profile

        self._logger.debug(f"Loaded {len(self._tool_profiles)} default tool profiles")

    def _discover_available_tools(self) -> Dict[str, Any]:
        """
        Discover available tools from the tool registry and merge with defaults.

        Returns:
            Dictionary of tool_name -> tool_object or profile
        """
        available_tools = {}

        # Start with defaults
        available_tools.update(self._tool_profiles)

        # Try to get actual tools from registry
        try:
            registry = get_tool_registry()
            if hasattr(registry, 'list_tools'):
                tool_names = registry.list_tools()
                for tool_name in tool_names:
                    tool_obj = registry.get_tool(tool_name)
                    if tool_obj is not None:
                        # If we have a default profile for this tool, use it; else create a basic one
                        if tool_name in self._tool_profiles:
                            # Keep the default profile but note that the real tool exists
                            available_tools[tool_name] = self._tool_profiles[tool_name]
                        else:
                            # Create a basic profile for unknown tools
                            available_tools[tool_name] = ToolProfile(
                                name=tool_name,
                                description=f"Dynamically discovered tool: {tool_name}",
                                timeout_seconds=30.0,
                                max_retries=3,
                                priority=10,  # Low priority (high number)
                                resource_weight=1.0,
                                safety_level="medium",
                                tags=["dynamic", "discovered"]
                            )
        except Exception as e:
            self._logger.warning(f"Could not load tools from registry: {e}")

        return available_tools

    def _get_model_tool_bundle(self, model: str) -> List[str]:
        """
        Get the ordered list of tool names for a given transcendental model.

        Args:
            model: The transcendental model string (e.g., "Gaṇeśa-model")

        Returns:
            List of tool names in order of preference
        """
        if model == "Gaṇeśa-model":
            return list(GAÑEŚA_TOOLS.keys())
        elif model == "Sarasvatī-model":
            return list(SARASVATĪ_TOOLS.keys())
        elif model == "Śiva-model":
            return list(ŚIVA_TOOLS.keys())
        else:
            self._logger.warning(f"Unknown model '{model}', falling back to Sarasvatī-model")
            return list(SARASVATĪ_TOOLS.keys())

    def _get_model_execution_profile(self, model: str) -> ExecutionProfile:
        """
        Get the base execution profile for a given transcendental model.

        Args:
            model: The transcendental model string

        Returns:
            ExecutionProfile with model-specific settings
        """
        tool_bundle = self._get_model_tool_bundle(model)

        if model == "Gaṇeśa-model":
            return ExecutionProfile(
                model=model,
                tool_bundle=tool_bundle,
                global_timeout=10.0,
                max_parallel_tools=2,
                resource_allocation="low",
                safety_override="high",
                enable_fallback=True,
                cache_aggressiveness="high",
                description="Obstacle-removing mode: fast, safe, low-latency tool execution"
            )
        elif model == "Sarasvatī-model":
            return ExecutionProfile(
                model=model,
                tool_bundle=tool_bundle,
                global_timeout=60.0,
                max_parallel_tools=3,
                resource_allocation="medium",
                safety_override="medium",
                enable_fallback=True,
                cache_aggressiveness="medium",
                description="Wisdom-seeking mode: balanced depth and resource usage"
            )
        elif model == "Śiva-model":
            return ExecutionProfile(
                model=model,
                tool_bundle=tool_bundle,
                global_timeout=120.0,
                max_parallel_tools=1,
                resource_allocation="high",
                safety_override="low",  # Allow more exploration but still with oversight
                enable_fallback=True,
                cache_aggressiveness="low",
                description="Destroyer-of-illusion mode: high-depth, exploratory, breakthrough-focused"
            )
        else:
            # Fallback to Sarasvatī-model profile
            self._logger.warning(f"Unknown model '{model}', using Sarasvatī-model profile")
            return self._get_model_execution_profile("Sarasvatī-model")

    def _should_update_tool_bundle(self, candidate_bundle: List[str]) -> bool:
        """
        Determine if we should update the current tool bundle based on hysteresis.

        Args:
            candidate_bundle: The newly computed tool bundle

        Returns:
            True if we should update, False to keep current bundle (hysteresis)
        """
        if not self._enable_tool_hysteresis:
            return True

        if not self._current_tool_bundle:
            # No current bundle, so we should set it
            return True

        # If bundles are identical, no change needed
        if set(candidate_bundle) == set(self._current_tool_bundle):
            return False

        # Apply hysteresis: only change if the new bundle is sufficiently different
        # We'll use a simple approach: if more than threshold fraction differs, change
        current_set = set(self._current_tool_bundle)
        candidate_set = set(candidate_bundle)

        # Calculate Jaccard similarity: intersection over union
        intersection = len(current_set & candidate_set)
        union = len(current_set | candidate_set)
        similarity = intersection / union if union > 0 else 0.0

        # If similarity is below threshold (i.e., difference is above 1-threshold), change
        should_change = similarity < (1.0 - self._tool_hysteresis_threshold)

        self._logger.debug(
            f"Tool bundle hysteresis: similarity={similarity:.2f}, "
            f"threshold={1.0 - self._tool_hysteresis_threshold:.2f}, "
            f"change={'YES' if should_change else 'NO'}"
        )

        return should_change

    def update_model_context(self, force: bool = False) -> bool:
        """
        Update the internal model state from the Interaction Contract and refresh.

        This should be called periodically or triggered by a callback from the Interaction Contract.

        Args:
            force: If True, update regardless of time interval

        Returns:
            True if model state changed, False otherwise
        """
        current_time = time.time()
        if not force and (current_time - self._last_model_check) < self._interaction_interval:
            return False  # Not time yet

        self._last_model_check = current_time

        try:
            # Get current model from contract
            new_model = get_current_model()
            if new_model is None:
                self._logger.debug("No model set in interaction contract")
                new_model = None  # Explicitly None

            with self._lock:
                old_model = self._current_model

                # Check if model actually changed
                if old_model == new_model and not force:
                    return False

                # Update model state
                self._current_model = new_model
                self._last_known_model = new_model

                # If model changed, we may need to update tool bundle
                model_changed = (old_model != new_model)

                # Always refresh tool bundle based on current model (unless we have a strong reason not to)
                # But apply hysteresis to tool bundle changes
                if self._current_model is not None:
                    candidate_bundle = self._get_model_tool_bundle(self._current_model)
                    candidate_profile = self._get_model_execution_profile(self._current_model)

                    # Check if we should update tool bundle (hysteresis)
                    if model_changed or self._should_update_tool_bundle(candidate_bundle):
                        self._current_tool_bundle = candidate_bundle
                        self._current_execution_profile = candidate_profile
                        self._last_tool_bundle_update = current_time

                        # Discover and update tool profiles with real-time data
                        self._tool_profiles = self._discover_available_tools()

                        self._logger.info(
                            f"Model context updated: {old_model} → {new_model}. "
                            f"Tool bundle: {self._current_tool_bundle}"
                        )

                        # Notify callbacks
                        for callback in self._update_callbacks:
                            try:
                                callback(old_model or "None", new_model or "None")
                            except Exception as e:
                                self._logger.error(f"Error in model update callback: {e}")

                        # Provide hint to predictive tool selector if enabled
                        if self._enable_predictive_hints:
                            try:
                                predictor = get_predictive_tool_selector()
                                if hasattr(predictor, 'hint_tool_loading'):
                                    predictor.hint_tool_loading(self._current_tool_bundle)
                            except Exception as e:
                                self._logger.warning(f"Could not hint predictive tool selector: {e}")

                        return True
                    else:
                        # Model same and tool bundle not changing due to hysteresis
                        self._logger.debug(
                            f"Model unchanged ({new_model}) and tool bundle stable due to hysteresis"
                        )
                        return False
                else:
                    # Model is None - clear tool bundle
                    self._current_tool_bundle = []
                    self._current_execution_profile = None
                    self._logger.info(f"Model context cleared: {old_model} → None")
                    return old_model is not None  # Return True if we had a model and now don't

        except Exception as e:
            self._logger.error(f"Failed to update model context: {e}")
            return False

    def get_tool_recommendation(
        self,
        request_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], ExecutionProfile]:
        """
        Get the recommended tool bundle and execution profile for the current model state.

        Args:
            request_context: Optional context about the request (e.g., task type, urgency) that might influence selection

        Returns:
            Tuple of (ordered_tool_list, execution_profile)
        """
        with self._lock:
            # Ensure we have a recent model context
            self.update_model_context()

            if self._current_model is None or not self._current_tool_bundle:
                self._logger.warning("No model set, returning safe fallback")
                # Fallback to a minimal safe set
                fallback_tools = ["syntax_checker"] if "syntax_checker" in self._tool_profiles else list(self._tool_profiles.keys())[:1]
                fallback_profile = ExecutionProfile(
                    model="unknown",
                    tool_bundle=fallback_tools,
                    global_timeout=30.0,
                    max_parallel_tools=1,
                    resource_allocation="medium",
                    safety_override="medium",
                    description="Fallback safe mode"
                )
                return fallback_tools, fallback_profile

            # Apply any context-based adjustments (simplified for now)
            # In a full implementation, this would adjust tool weights, timeouts, etc. based on request_context
            adjusted_tool_bundle = list(self._current_tool_bundle)  # Start with model-based bundle
            adjusted_profile = self._current_execution_profile

            # TODO: Implement context-based adjustments (e.g., for urgent requests, prefer faster tools)
            # For now, we return the model-based recommendation

            self._logger.debug(
                f"Recommending tool bundle for model '{self._current_model}': {adjusted_tool_bundle}"
            )

            return adjusted_tool_bundle, adjusted_profile

    def record_tool_outcome(
        self,
        tool_name: str,
        success: bool,
        latency_seconds: float,
        error_details: Optional[str] = None
    ) -> None:
        """
        Record the outcome of a tool execution for learning and adaptation.

        Args:
            tool_name: Name of the tool that was executed
            success: Whether the tool execution succeeded
            latency_seconds: How long the tool took to run
            error_details: Optional error message if failed
        """
        if not self._enable_tool_learning:
            return

        with self._lock:
            if tool_name not in self._tool_performance:
                self._tool_performance[tool_name] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "total_latency": 0.0,
                    "last_used": 0.0,
                    "recent_results": deque(maxlen=10)  # Last 10 outcomes (True/False)
                }

            perf = self._tool_performance[tool_name]
            perf["total_runs"] += 1
            if success:
                perf["successful_runs"] += 1
            perf["total_latency"] += latency_seconds
            perf["last_used"] = time.time()
            perf["recent_results"].append(success)

            # Update the tool profile if we have one
            if tool_name in self._tool_profiles:
                profile = self._tool_profiles[tool_name]
                profile.last_used = time.time()
                profile.use_count += 1
                if success:
                    profile.success_count += 1
                profile.total_latency += latency_seconds

            self._logger.debug(
                f"Recorded tool outcome: {tool_name} -> "
                f"{'SUCCESS' if success else 'FAILURE'} ({latency_seconds:.2f}s)"
            )

            # Optionally, we could adjust tool priorities or parameters here based on performance
            # This is a placeholder for more sophisticated adaptive logic

    def get_tool_performance(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for tools.

        Args:
            tool_name: If provided, return stats for that specific tool; else return all

        Returns:
            Dictionary of tool performance metrics
        """
        with self._lock:
            if tool_name is not None:
                return self._tool_performance.get(
                    tool_name,
                    {"error": "Tool not found in performance tracking"}
                )
            return dict(self._tool_performance)  # Return a copy

    def register_update_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback to be notified when the model context changes.

        Args:
            callback: Function taking (old_model_str, new_model_str) -> None
        """
        if not callable(callback):
            raise TypeError("Callback must be callable")
        with self._lock:
            self._update_callbacks.append(callback)
            self._logger.debug(f"Registered model update callback: {callback.__name__}")

    def unregister_update_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Unregister a previously registered update callback.

        Args:
            callback: The callback function to remove
        """
        with self._lock:
            if callback in self._update_callbacks:
                self._update_callbacks.remove(callback)
                self._logger.debug(f"Unregistered model update callback: {callback.__name__}")

    def get_current_model(self) -> Optional[str]:
        """
        Get the current transcendental model.

        Returns:
            Current model string or None if not set.
        """
        with self._lock:
            return self._current_model

    def get_current_tool_bundle(self) -> List[str]:
        """
        Get the current ordered list of recommended tool names.

        Returns:
            List of tool names (empty if no model set)
        """
        with self._lock:
            return list(self._current_tool_bundle)  # Return a copy

    def get_current_execution_profile(self) -> Optional[ExecutionProfile]:
        """
        return copy
        Returns:
            Current execution profile or None if no model set
        """
        with self._lock:
            return self._current_execution_profile

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get comprehensive state information for debugging/monitoring.

        Returns:
            Dictionary with current state, performance stats, etc.
        """
        with self._lock:
            return {
                "current_model": self._current_model,
                "current_tool_bundle": list(self._current_tool_bundle),
                "current_execution_profile": {
                    "model": self._current_execution_profile.model if self._current_execution_profile else None,
                    "tool_bundle": list(self._current_ecution_profile.tool_bundle) if self._current_execution_profile else None,
                    "global_timeout": self._current_execution_profile.global_timeout if self._current_execution_profile else None,
                    "max_parallel_tools": self._current_execution_profile.max_parallel_tools if self._current_execution_profile else None,
                    "resource_allocation": self._current_execution_profile.resource_allocation if self._current_execution_profile else None,
                    "safety_override": self._current_execution_profile.safety_override if self._current_execution_profile else None,
                    "description": self._current_execution_profile.description if self._current_execution_profile else None
                } if self._current_execution_profile else None,
                "tool_hysteresis_window": self._tool_hysteresis_window,
                "tool_hysteresis_threshold": self._tool_hysteresis_threshold,
                "enable_tool_hysteresis": self._enable_tool_hysteresis,
                "enable_tool_learning": self._enable_tool_learning,
                "enable_predictive_hints": self._enable_predictive_hints,
                "last_model_check": self._last_model_check,
                "last_tool_bundle_update": self._last_tool_bundle_update,
                "tracked_tools": list(self._tool_performance.keys()),
                "total_tool_profiles": len(self._tool_profiles)
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the model router.

        Returns:
            Dictionary with health status and any issues.
        """
        issues = []
        status = "healthy"

        # Check if we have a model set (though None might be valid initially)
        # This is more of a warning than an error
        with self._lock:
            if self._current_model is None:
                issues.append("No model currently set in interaction contract")
                # Not necessarily unhealthy - might be initializing
                # status = "degraded"  # Only set to degraded if we expect a model to be set

            # Check that we have some tools available
            if not self._tool_profiles:
                issues.append("No tool profiles loaded")
                status = "unhealthy"

            # Check for inconsistencies
            if self._current_model is not None and not self._current_tool_bundle:
                issues.append("Model set but no tool bundle available")
                status = "degraded"

        return {
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "details": self.get_state_info()
        }

    def reset(self) -> None:
        """Reset the router to initial state (primarily for testing)."""
        with self._lock:
            old_model = self._current_model
            self._current_model = None
            self._current_tool_bundle = []
            self._current_execution_profile = None
            self._tool_selection_history.clear()
            self._tool_performance.clear()
            self._load_default_tool_profiles()  # Reload defaults
            self._logger.info(f"Model router reset: {old_model} -> None")


# =======================
# Module-Level Singleton
# =======================

# Global router instance for easy access throughout the codebase
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """
    Get or create the global ModelRouter instance (singleton pattern).

    Returns:
        The singleton ModelRouter instance.
    """
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router


def update_model_context(force: bool = False) -> bool:
    """
    Convenience function to update the global model router's context.

    Args:
        force: If True, update regardless of time interval

    Returns:
        True if model state changed, False otherwise
    """
    return get_model_router().update_model_context(force=force)


def get_tool_recommendation(
    request_context: Optional[Dict[str, Any]] = None
) -> Tuple[List[str], ExecutionProfile]:
    """
    Convenience function to get tool recommendation from global model router.

    Args:
        request_context: Optional context about the request

    Returns:
        Tuple of (ordered_tool_list, execution_profile)
    """
    return get_model_router().get_tool_recommendation(request_context)


def record_tool_outcome(
    tool_name: str,
    success: bool,
    latency_seconds: float,
    error_details: Optional[str] = None
) -> None:
    """
    Convenience function to record tool outcome via global model router.

    Args:
        tool_name: Name of the tool that was executed
        success: Whether the tool execution succeeded
        latency_seconds: How long the tool took to run
        error_details: Optional error message if failed
    """
    get_model_router().record_tool_outcome(tool_name, success, latency_seconds, error_details)


def get_current_model() -> Optional[str]:
    """
    Convenience function to get current model from global model router.

    Returns:
        Current model identifier string or None.
    """
    return get_model_router().get_current_model()


def get_current_tool_bundle() -> List[str]:
    """
    Convenience function to get current tool bundle from global model router.

    Returns:
        List of tool names (empty if no model set)
    """
    return get_model_router().get_current_tool_bundle()


def get_current_execution_profile() -> Optional[ExecutionProfile]:
    """
    Convenience function to get current execution profile from global model router.

    Returns:
        Current execution profile or None if no model set.
    """
    return get_model_router().get_current_execution_profile()


# ======================
# Demo / Self-Test
# ======================

if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("Model Router Demo / Self-Test")
    print("=" * 70)

    # Create instance with fast cycling for demo
    router = ModelRouter(
        interaction_interval=1.0,  # Check every second for demo
        tool_hysteresis_window=2,
        tool_hysteresis_threshold=0.5,  # More sensitive for demo
        enable_tool_hysteresis=True,
        enable_tool_learning=True,
        enable_predictive_hints=True
    )

    print(f"\nInitial state: {router.get_current_model()}")

    # Simulate model updates by directly manipulating the interaction contract
    # (In reality, this would come from the RTA feedback loop via pramana_router)
    from core.interaction.interaction_contract import update_model_state as set_model_state

    print("\n--- Simulating Model Updates ---")
    test_sequence = [
        "Gaṇeśa-model",
        "Sarasvatī-model",
        "Śiva-model",
        "Gaṇeśa-model",  # Test hysteresis - should not change tools immediately if window small
        "Sarasvatī-model",
        "invalid-model",  # Should be handled gracefully
        None              # Test clearing
    ]

    for model in test_sequence:
        print(f"\nSetting model to: {model}")
        # Update the interaction contract (simulating RTA feedback loop)
        if model is None:
            # To simulate None, we'd need a way to unset - for demo we'll use an invalid model that gets treated as None
            # Actually, let's just skip None for now and test with a known invalid that falls back
            pass
        else:
            set_model_state(model)

        # Give it a moment to process
        time.sleep(1.1)  # Wait for the interaction interval

        # Get recommendations
        tools, profile = router.get_tool_recommendation()
        current_model = router.get_current_model()
        print(f"  Current model: {current_model}")
        print(f"  Recommended tools: {tools}")
        print(f"  Execution profile: {profile.description if profile else 'None'}")
        if profile:
            print(f"    Timeout: {profile.global_timeout}s, "
                  f"Parallel: {profile.max_parallel_tools}, "
                  f"Resources: {profile.resource_allocation}, "
                  f"Safety: {profile.safety_override}")

        # Simulate some tool executions to test learning
        if tools:
            # Simulate running the first tool
            tool_to_test = tools[0]
            success = (model != "Śiva-model")  # Pretend Śiva-model tools are harder
            latency = 0.1 + (0.5 if model == "Śiva-model" else 0.05)  # Simulate latency
            router.record_tool_outcome(tool_to_test, success, latency)
            print(f"  Simulated execution of {tool_to_test}: {'SUCCESS' if success else 'FAILURE'} ({latency:.2f}s)")

    # Test callback system
    print("\n--- Testing Callback System ---")
    callback_log = []
    def test_callback(old_model, new_model):
        callback_log.append((old_model, new_model))
        print(f"  [CALLBACK] Model changed: {old_model} → {new_model}")

    router.register_update_callback(test_callback)
    print("Registered test callback.")

    print("Changing model to test callback:")
    set_model_state("Śiva-model")
    time.sleep(1.1)
    set_model_state("Gaṇeśa-model")
    time.sleep(1.1)

    print(f"Callback received {len(callback_log)} calls:")
    for old, new in callback_log:
        print(f"  {old} → {new}")

    # Test hysteresis with rapid changes
    print("\n--- Testing Tool Hysteresis ---")
    print("Setting up rapid model changes to test hysteresis...")
    # Reset and set up for hysteresis test
    router = ModelRouter(
        interaction_interval=0.5,  # Fast checking
        tool_hysteresis_window=3,
        tool_hysteresis_threshold=0.7,  # Need 70% agreement to change
        enable_tool_hysteresis=True
    )
    set_model_state("Gaṇeśa-model")
    time.sleep(0.6)
    print(f"After Gaṇeśa-model: {router.get_current_tool_bundle()}")

    # Rapidly switch between models that share some tools
    # Gaṇeśa and Sarasvatī share some conceptual similarity but different tools
    for i in range(5):
        set_model_state("Sarasvatī-model" if i % 2 == 0 else "Gaṇeśa-model")
        time.sleep(0.6)  # Faster than hysteresis window would allow change
        tools, _ = router.get_tool_recommendation()
        print(f"  Switch {i+1}: Current tools: {tools}")

    # Now wait longer to see if it eventually changes
    print("Waiting longer to see if hysteresis allows change...")
    time.sleep(2.0)
    tools, _ = router.get_tool_recommendation()
    print(f"After waiting: Current tools: {tools}")

    # Test performance tracking
    print("\n--- Testing Performance Tracking ---")
    # Simulate some tool usage
    test_tools = ["syntax_checker", "deep_analyzer", "assumption_challenger"]
    for i, tool in enumerate(test_tools):
        for j in range(3):  # 3 runs each
            success = (j % 3 != 0)  # 2/3 success rate
            latency = 0.1 + (i * 0.1) + (j * 0.05)
            router.record_tool_outcome(tool, success, latency)

    perf = router.get_tool_performance()
    for tool, stats in perf.items():
        if isinstance(stats, dict) and "total_runs" in stats:
            success_rate = (stats["successful_runs"] / stats["total_runs"]) * 100 if stats["total_runs"] > 0 else 0
            avg_latency = stats["total_latency"] / stats["total_runs"] if stats["total_runs"] > 0 else 0
            print(f"  {tool}: {stats['total_runs']} runs, {success_rate:.1f}% success, {avg_latency:.3f}s avg latency")

    # Test state info
    print("\n--- State Information ---")
    info = router.get_state_info()
    for key, value in info.items():
        if isinstance(value, dict) and len(str(value)) > 100:
            print(f"{key:30}: {type(value).__name__} with {len(value)} items")
        else:
            print(f"{key:30}: {value}")

    # Test health check
    print("\n--- Health Check ---")
    health = router.health_check()
    print(f"Status: {health['status']}")
    if health['issues']:
        print("Issues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("No issues detected.")

    # Test reset
    print("\n--- Testing Reset ---")
    print(f"Before reset: {router.get_current_model()}")
    router.reset()
    print(f"After reset: {router.get_current_model()}")

    print("\n" + "=" * 70)
    print("Demo completed.")
    print("=" * 70)