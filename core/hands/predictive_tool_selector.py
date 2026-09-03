"""
Predictive Tool Selector - Layer 4: Intelligent Tool Routing for NALA Predictive Dual-Mode Operation.
Implements predictive tool anticipation, container warming, and safety-compliant tool selection
based on workload patterns, cognitive load forecasts, and contextual awareness.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import hashlib
import json

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Tool classifications based on Āgama principles."""
    SRUTI = "sruti"      # Revealed knowledge: File system, database access (requires PAROKSHA/ATHAPRAPTI)
    SMRITI = "smriti"    # Remembered knowledge: Web search, APIs (available in all modes)
    ANUBHAVA = "anubhava" # Direct experience: Debuggers, profilers (requires PRATYAKSHA)


@dataclass(frozen=True)
class ToolSpec:
    """Specification for a tool including its capabilities and security constraints."""
    name: str                           # e.g., "ripgrep", "python3", "bash"
    tool_type: ToolType
    allowed_read_paths: Set[str]        # Glob patterns, e.g., {"/tmp/**", "/var/log/*"}
    allowed_write_paths: Set[str]       # Usually empty for safe tools
    allowed_network_endpoints: Set[str] # e.g., {"api.github.com", "pypi.org"}
    spawns_processes: bool              # Does it fork/exec subprocesses?
    requires_root: bool
    is_deterministic: bool              # For verification, prefer deterministic tools
    estimated_init_time: float          # Seconds to warm up/initialize (cold start)
    resource_profile: Dict[str, float]  # CPU, memory, disk estimates (normalized 0-1)
    description: str = ""               # Human-readable description
    tags: Set[str] = field(default_factory=set)  # e.g., {"search", "compile", "debug"}


@dataclass
class PredictionContext:
    """Context information for tool prediction."""
    workload_complexity_index: float = 0.5  # WCI: [0,1] - task graph complexity
    cognitive_load_predictive: float = 0.5   # CLP: [0,1] - predicted human interaction intensity
    state_cohesion_score: float = 0.9       # SCS: [0,1] - AMP state integrity measure
    hysteresis_buffer: float = 0.1          # HB: [0,0.2] - dynamic threshold for stability
    interaction_context: str = "general"    # e.g., "debugging", "design", "production"
    recent_tools: List[str] = field(default_factory=list)  # Recently used tools
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolPrediction:
    """A prediction for tool need with confidence score."""
    tool_name: str
    confidence: float  # 0.0 to 1.0
    reasoning: List[str]  # Explanation for the prediction
    estimated_latency_reduction: float  # Expected seconds saved by pre-warming
    safety_checked: bool = True  # Whether policy validation passed


class PredictiveToolSelector:
    """
    Predictive tool selector that anticipates tool needs based on:
    - Workload complexity patterns
    - Cognitive load forecasts
    - Historical usage and context
    - Safety and policy constraints
    """

    def __init__(self, history_size: int = 100):
        """Initialize the predictive tool selector."""
        self._tool_registry: Dict[str, ToolSpec] = {}
        self._warm_tool_pool: Dict[str, List[Any]] = defaultdict(list)  # tool_name -> [instances]
        self._prediction_history: deque = deque(maxlen=history_size)
        self._tool_usage_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "last_used": 0.0, "total_latency": 0.0}
        )
        self._context_policy_mapper = ContextPolicyMapper()
        self._initialize_default_tool_registry()

        logger.info("Predictive Tool Selector initialized")

    def _initialize_default_tool_registry(self):
        """Initialize with a default set of common development tools."""
        # Ripgrep - fast search tool
        self.register_tool(ToolSpec(
            name="rg",
            tool_type=ToolType.SMRITI,
            allowed_read_paths={"/tmp/**", "/home/user/projects/**", "/usr/local/**"},
            allowed_write_paths=set(),
            allowed_network_endpoints=set(),
            spawns_processes=False,
            requires_root=False,
            is_deterministic=True,
            estimated_init_time=0.1,
            resource_profile={"cpu": 0.2, "memory": 0.1, "disk": 0.05},
            description="Fast recursive search tool with regex support",
            tags={"search", "text-processing"}
        ))

        # Python3 - versatile scripting language
        self.register_tool(ToolSpec(
            name="python3",
            tool_type=ToolType.SMRITI,
            allowed_read_paths={"/tmp/**", "/usr/local/lib/python3.9/**", "/home/user/**"},
            allowed_write_paths={"/tmp/**"},
            allowed_network_endpoints={"pypi.org", "github.com", "gitlab.com"},
            spawns_processes=True,   # Can subprocess
            requires_root=False,
            is_deterministic=False,  # General purpose → not deterministic
            estimated_init_time=1.5,
            resource_profile={"cpu": 0.6, "memory": 0.4, "disk": 0.2},
            description="Python 3 interpreter with standard library",
            tags={"scripting", "data-processing", "automation"}
        ))

        # Git - version control
        self.register_tool(ToolSpec(
            name="git",
            tool_type=ToolType.SMRITI,
            allowed_read_paths={"/tmp/**", "/home/user/**", "/usr/local/**"},
            allowed_write_paths={"/tmp/**", "/home/user/**"},
            allowed_network_endpoints={"github.com", "gitlab.com", "bitbucket.org"},
            spawns_processes=True,
            requires_root=False,
            is_deterministic=True,
            estimated_init_time=0.3,
            resource_profile={"cpu": 0.3, "memory": 0.2, "disk": 0.1},
            description="Distributed version control system",
            tags={"version-control", "collaboration"}
        ))

        # Bash - shell interpreter
        self.register_tool(ToolSpec(
            name="bash",
            tool_type=ToolType.SMRITI,
            allowed_read_paths={"/tmp/**", "/usr/**", "/bin/**"},
            allowed_write_paths={"/tmp/**"},
            allowed_network_endpoints=set(),
            spawns_processes=True,
            requires_root=False,
            is_deterministic=False,  # Can run arbitrary commands
            estimated_init_time=0.05,
            resource_profile={"cpu": 0.1, "memory": 0.05, "disk": 0.01},
            description="Bourne Again SHell",
            tags={"shell", "scripting", "system"}
        ))

        # SQLite - embedded database
        self.register_tool(ToolSpec(
            name="sqlite3",
            tool_type=ToolType.SRUTI,  # Database access requires higher privilege
            allowed_read_paths={"/tmp/**", "/home/user/**"},
            allowed_write_paths={"/tmp/**"},
            allowed_network_endpoints=set(),
            spawns_processes=False,
            requires_root=False,
            is_deterministic=True,
            estimated_init_time=0.2,
            resource_profile={"cpu": 0.2, "memory": 0.1, "disk": 0.1},
            description="Embedded SQL database engine",
            tags={"database", "storage", "query"}
        ))

        # Docker - container platform (requires more scrutiny)
        self.register_tool(ToolSpec(
            name="docker",
            tool_type=ToolType.SRUTI,  # Container access = system-level
            allowed_read_paths={"/tmp/**", "/var/run/docker.sock"},
            allowed_write_paths={"/tmp/**"},
            allowed_network_endpoints={"index.docker.io"},
            spawns_processes=True,
            requires_root=True,        # Typically requires root/sudo
            is_deterministic=False,
            estimated_init_time=2.0,
            resource_profile={"cpu": 0.5, "memory": 0.3, "disk": 0.2},
            description="Container platform for application isolation",
            tags={"containerization", "deployment", "virtualization"}
        ))

        # Strace - system call tracer (debugging tool)
        self.register_tool(ToolSpec(
            name="strace",
            tool_type=ToolType.ANUBHAVA,  # Direct experience: debugging/profile
            allowed_read_paths={"/tmp/**", "/proc/**", "/sys/**"},
            allowed_write_paths={"/tmp/**"},
            allowed_network_endpoints=set(),
            spawns_processes=True,
            requires_root=False,
            is_deterministic=True,
            estimated_init_time=0.1,
            resource_profile={"cpu": 0.3, "memory": 0.1, "disk": 0.05},
            description="Diagnostic, debugging and instructional userspace utility",
            tags={"debugging", "tracing", "system-analysis"}
        ))

        logger.debug(f"Initialized tool registry with {len(self._tool_registry)} tools")

    def register_tool(self, tool_spec: ToolSpec):
        """Register a new tool in the selector's registry."""
        self._tool_registry[tool_spec.name] = tool_spec
        logger.debug(f"Registered tool: {tool_spec.name} ({tool_spec.tool_type.value})")

    def unregister_tool(self, tool_name: str) -> bool:
        """Remove a tool from the registry."""
        if tool_name in self._tool_registry:
            del self._tool_registry[tool_name]
            logger.debug(f"Unregistered tool: {tool_name}")
            return True
        return False

    def get_tool_spec(self, tool_name: str) -> Optional[ToolSpec]:
        """Get the specification for a registered tool."""
        return self._tool_registry.get(tool_name)

    def predict_tool_needs(
        self,
        predictive_signals: Any,  # Expects PredictiveSignals from fleet/coordinator
        current_context: Optional[Dict[str, Any]] = None,
        recent_interactions: Optional[List[Dict[str, Any]]] = None
    ) -> List[ToolPrediction]:
        """
        Predict tools needed based on predictive signals and context.

        Args:
            predictive_signals: Object with WCI, CLP, SCS, HB attributes
            current_context: Additional context (interaction type, user intent, etc.)
            recent_interactions: Recent tool usage patterns

        Returns:
            List of ToolPrediction objects sorted by confidence (highest first)
        """
        if current_context is None:
            current_context = {}
        if recent_interactions is None:
            recent_interactions = []

        # Extract signals with fallback defaults
        wci = getattr(predictive_signals, 'workload_complexity_index', 0.5)
        clp = getattr(predictive_signals, 'cognitive_load_predictive', 0.5)
        scs = getattr(predictive_signals, 'state_cohesion_score', 0.9)
        hb = getattr(predictive_signals, 'hysteresis_buffer', 0.1)

        prediction_context = PredictionContext(
            workload_complexity_index=wci,
            cognitive_load_predictive=clp,
            state_cohesion_score=scs,
            hysteresis_buffer=hb,
            interaction_context=current_context.get("interaction_context", "general"),
            recent_tools=current_context.get("recent_tools", [])
        )

        predictions = []

        # Analyze usage patterns from recent interactions
        usage_patterns = self._analyze_usage_patterns(recent_interactions)

        # Evaluate context suitability for each tool type
        context_suitability = self._evaluate_context_suitability(prediction_context)

        # Generate predictions for each registered tool
        for tool_name, tool_spec in self._tool_registry.items():
            confidence, reasoning, latency_reduction = self._calculate_tool_prediction(
                tool_name, tool_spec, prediction_context, usage_patterns, context_suitability
            )

            # Only include predictions with meaningful confidence
            if confidence >= 0.1:
                safety_checked = self._context_policy_mapper.validate_tool_safety(
                    tool_name, tool_spec, prediction_context
                )

                predictions.append(ToolPrediction(
                    tool_name=tool_name,
                    confidence=confidence,
                    reasoning=reasoning,
                    estimated_latency_reduction=latency_reduction,
                    safety_checked=safety_checked
                ))

        # Sort by confidence (descending) and then by latency reduction
        predictions.sort(key=lambda p: (p.confidence, p.estimated_latency_reduction), reverse=True)

        # Record prediction for learning
        self._prediction_history.append({
            "timestamp": time.time(),
            "context": prediction_context,
            "predictions": [(p.tool_name, p.confidence) for p in predictions[:5]]  # Top 5
        })

        logger.debug(f"Generated {len(predictions)} tool predictions")
        return predictions

    def _analyze_usage_patterns(self, recent_interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Analyze recent tool usage to identify patterns.
        Returns a dict mapping tool names to pattern strength scores.
        """
        patterns = defaultdict(float)

        if not recent_interactions:
            return patterns

        # Weight recent interactions more heavily
        now = time.time()
        for interaction in recent_interactions:
            timestamp = interaction.get("timestamp", now)
            age_hours = (now - timestamp) / 3600.0
            # Exponential decay: more recent = higher weight
            weight = max(0.1, math.exp(-age_hours / 24.0))  # Half-life of ~1 day

            tool_name = interaction.get("tool_name")
            if tool_name:
                patterns[tool_name] += weight

                # Also look for patterns in tool sequences
                prev_tool = interaction.get("previous_tool")
                if prev_tool:
                    # Boost likelihood of tools that often follow each other
                    pattern_key = f"{prev_tool}->{tool_name}"
                    patterns[pattern_key] += weight * 0.5

        # Normalize pattern scores
        if patterns:
            max_score = max(patterns.values())
            if max_score > 0:
                for tool in patterns:
                    patterns[tool] /= max_score

        return dict(patterns)

    def _evaluate_context_suitability(self, context: PredictionContext) -> Dict[str, float]:
        """
        Evaluate how suitable each tool type is for the current context.
        Returns dict mapping tool types to suitability scores [0,1].
        """
        suitability = {
            ToolType.SRUTI: 0.0,
            ToolType.SMRITI: 0.0,
            ToolType.ANUBHAVA: 0.0
        }

        interaction_context = context.interaction_context.lower()

        # Context-based suitability mapping
        if interaction_context in ["debugging", "troubleshooting", "analysis"]:
            suitability[ToolType.ANUBHAVA] = 0.9  # Debugging tools highly suitable
            suitability[ToolType.SMRITI] = 0.6    # Research/search still useful
            suitability[ToolType.SRUTI] = 0.3     # File access less critical

        elif interaction_context in ["design", "architecture", "planning"]:
            suitability[ToolType.SMRITI] = 0.8    # Research, docs, APIs
            suitability[ToolType.ANUBHAVA] = 0.4  # Some analysis tools
            suitability[ToolType.SRUTI] = 0.5     # File/document access

        elif interaction_context in ["production", "deployment", "release"]:
            suitability[ToolType.SRUTI] = 0.8     # File/system access critical
            suitability[ToolType.SMRITI] = 0.6    # APIs, configuration
            suitability[ToolType.ANUBHAVA] = 0.2  # Less debugging in prod

        elif interaction_context in ["learning", "education", "exploration"]:
            suitability[ToolType.SMRITI] = 0.9    # Research, tutorials, docs
            suitability[ToolType.SRUTI] = 0.5     # File access for examples
            suitability[ToolType.ANUBHAVA] = 0.3  # Some debugging for learning

        else:  # general/default context
            suitability[ToolType.SMRITI] = 0.7    # Default to research/search
            suitability[ToolType.SRUTI] = 0.5     # Moderate file access
            suitability[ToolType.ANUBHAVA] = 0.3  # Some debugging capability

        # Adjust based on cognitive load prediction
        # High cognitive load → prefer simpler, more deterministic tools
        if context.cognitive_load_predictive > 0.7:
            # Boost deterministic tools when user is under high load
            suitability[ToolType.SRUTI] *= 1.2  # File ops often deterministic
            suitability[ToolType.SMRITI] *= 0.9  # Network tools less predictable
            suitability[ToolType.ANUBHAVA] *= 0.8 # Debugging can be complex

        # Adjust based on workload complexity
        # High workload complexity → need more powerful/tools
        if context.workload_complexity_index > 0.7:
            suitability[ToolType.SMRITI] *= 1.3  # Need research/automation
            suitability[ToolType.SRUTI] *= 1.1   # Need file processing
            suitability[ToolType.ANUBHAVA] *= 1.2 # Might need debugging complex systems

        # Normalize to [0,1] range
        for tool_type in suitability:
            suitability[tool_type] = min(1.0, max(0.0, suitability[tool_type]))

        return suitability

    def _calculate_tool_prediction(
        self,
        tool_name: str,
        tool_spec: ToolSpec,
        context: PredictionContext,
        usage_patterns: Dict[str, float],
        context_suitability: Dict[ToolType, float]
    ) -> Tuple[float, List[str], float]:
        """
        Calculate prediction confidence for a specific tool.
        Returns: (confidence_score, reasoning_list, latency_reduction_estimate)
        """
        confidence = 0.0
        reasoning = []

        # Base suitability from tool type
        type_suitability = context_suitability.get(tool_spec.tool_type, 0.0)
        if type_suitability > 0:
            confidence += type_suitability * 0.3
            reasoning.append(f"Tool type {tool_spec.tool_type.value} suitability: {type_suitability:.2f}")

        # Workload complexity factor
        wci = context.workload_complexity_index
        if tool_spec.tool_type == ToolType.SMRITI and wci > 0.5:
            # Complex workloads benefit from research/automation tools
            wci_factor = min(1.0, (wci - 0.5) * 2.0)  # 0.5-1.0 maps to 0.0-1.0
            confidence += wci_factor * 0.2
            reasoning.append(f"High workload complexity benefit: {wci_factor:.2f}")
        elif tool_spec.tool_type == ToolType.SRUTI and wci > 0.6:
            # Very complex workloads need file/system access
            wci_factor = min(1.0, (wci - 0.6) * 2.5)  # 0.6-1.0 maps to 0.0-1.0
            confidence += wci_factor * 0.2
            reasoning.append(f"Complex workload file access need: {wci_factor:.2f}")

        # Cognitive load predictive factor
        clp = context.cognitive_load_predictive
        if tool_spec.tool_type == ToolType.ANUBHAVA and clp > 0.6:
            # High predicted interaction → likely debugging needed
            clp_factor = min(1.0, (clp - 0.6) * 2.5)  # 0.6-1.0 maps to 0.0-1.0
            confidence += clp_factor * 0.25
            reasoning.append(f"High cognitive load suggests debugging: {clp_factor:.2f}")
        elif tool_spec.is_deterministic and clp > 0.7:
            # Under high load, prefer deterministic tools
            det_bonus = 0.15 if tool_spec.is_deterministic else 0.0
            confidence += det_bonus
            if det_bonus > 0:
                reasoning.append(f"Deterministic tool preferred under high load: +{det_bonus:.2f}")

        # State cohesion factor (higher cohesion → more predictable tool needs)
        scs = context.state_cohesion_score
        if scs > 0.8:
            # High cohesion allows better prediction
            cohesion_bonus = (scs - 0.8) * 0.5  # 0.8-1.0 maps to 0.0-0.1
            confidence += cohesion_bonus
            reasoning.append(f"High state cohesion improves prediction: +{cohesion_bonus:.2f}")

        # Usage pattern factor
        usage_score = usage_patterns.get(tool_name, 0.0)
        if usage_score > 0:
            confidence += usage_score * 0.2
            reasoning.append(f"Recent usage pattern suggests need: {usage_score:.2f}")

        # Check for tool sequencing patterns
        recent_tools = context.recent_tools
        if len(recent_tools) >= 2:
            # Look for patterns like "python3" -> "git" or "rg" -> "python3"
            for i in range(len(recent_tools) - 1):
                pattern = f"{recent_tools[i]}->{tool_name}"
                pattern_score = usage_patterns.get(pattern, 0.0)
                if pattern_score > 0:
                    confidence += pattern_score * 0.15
                    reasoning.append(f"Sequential pattern '{pattern}' detected: +{pattern_score:.2f}")
                    break  # Only count strongest pattern

        # Resource availability factor (simplified)
        # In a real implementation, this would check current system resources
        resource_factor = 0.1  # Assume moderate resource availability
        confidence += resource_factor
        reasoning.append(f"Assumed resource availability: +{resource_factor:.2f}")

        # Apply hysteresis buffer to prevent rapid toggling
        hb = context.hysteresis_buffer
        if len(self._prediction_history) > 0:
            # Get last prediction for this tool
            last_pred = None
            for hist in reversed(self._prediction_history):
                for tool, conf in hist["predictions"]:
                    if tool == tool_name:
                        last_pred = conf
                        break
                if last_pred is not None:
                    break

            if last_pred is not None:
                # Reduce confidence if prediction is changing rapidly (hysteresis)
                change = abs(confidence - last_pred)
                if change > hb:
                    # Apply damping
                    damping_factor = max(0.0, 1.0 - (change - hb))
                    confidence *= damping_factor
                    reasoning.append(f"Hysteresis damping applied: *{damping_factor:.2f}")

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        # Estimate latency reduction from pre-warming
        # Base estimate: tool init time * confidence
        latency_reduction = tool_spec.estimated_init_time * confidence * 0.8  # 80% efficiency

        return confidence, reasoning, latency_reduction

    def warm_up_tools(self, predictions: List[ToolPrediction], threshold: float = 0.3) -> List[str]:
        """
        Warm up tools that exceed the confidence threshold.

        Args:
            predictions: List of ToolPrediction objects
            threshold: Minimum confidence to trigger warming (default 0.3)

        Returns:
            List of tool names that were warmed up
        """
        warmed_tools = []

        # Filter predictions above threshold that passed safety check
        tools_to_warm = [
            p for p in predictions
            if p.confidence >= threshold and p.safety_checked
        ]

        logger.info(f"Warming up {len(tools_to_warm)} tools (threshold={threshold})")

        for prediction in tools_to_warm:
            tool_name = prediction.tool_name
            try:
                warmed_instance = self._warm_tool_instance(tool_name)
                if warmed_instance is not None:
                    self._warm_tool_pool[tool_name].append(warmed_instance)
                    warmed_tools.append(tool_name)

                    # Update usage stats
                    stats = self._tool_usage_stats[tool_name]
                    stats["last_warmed"] = time.time()

                    logger.debug(
                        f"Warmed tool '{tool_name}' (confidence: {prediction.confidence:.2f}, "
                        f"expected latency reduction: {prediction.estimated_latency_reduction:.2f}s)"
                    )
                else:
                    logger.warning(f"Failed to warm up tool: {tool_name}")
            except Exception as e:
                logger.error(f"Error warming up tool {tool_name}: {e}")

        return warmed_tools

    def _warm_tool_instance(self, tool_name: str) -> Any:
        """
        Create a warmed instance of a tool.
        Implementation varies by tool type - in practice this might:
        - Pre-import modules for interpreters
        - Start paused containers
        - Establish database connections
        - Warm up JIT caches

        Returns the warmed tool instance or None if failed.
        """
        tool_spec = self.get_tool_spec(tool_name)
        if tool_spec is None:
            logger.error(f"Cannot warm unknown tool: {tool_name}")
            return None

        logger.debug(f"Warming up tool: {tool_name}")

        # Tool-specific warming strategies
        if tool_name == "python3":
            # For Python, we could pre-import common modules
            try:
                import sys
                # Simulate warming by importing commonly used modules
                # In reality, we'd do this in a subprocess or isolated context
                warmed_state = {
                    "tool": "python3",
                    "warmed_at": time.time(),
                    "preloaded_modules": ["sys", "os", "json", "math"],
                    "ready": True
                }
                return warmed_state
            except Exception as e:
                logger.error(f"Failed to warm Python3: {e}")
                return None

        elif tool_name == "rg" or tool_name == "ripgrep":
            # For ripgrep, ensure it's available and test basic functionality
            try:
                warmed_state = {
                    "tool": "rg",
                    "warmed_at": time.time(),
                    "version_checked": True,
                    "ready": True
                }
                return warmed_state
            except Exception as e:
                logger.error(f"Failed to warm ripgrep: {e}")
                return None

        elif tool_name == "git":
            # For git, we could warm up by checking version and preparing config
            try:
                warmed_state = {
                    "tool": "git",
                    "warmed_at": time.time(),
                    "config_ready": True,
                    "ready": True
                }
                return warmed_state
            except Exception as e:
                logger.error(f"Failed to warm Git: {e}")
                return None

        elif tool_name == "bash":
            # Shell is usually ready, but we can prepare environment
            try:
                warmed_state = {
                    "tool": "bash",
                    "warmed_at": time.time(),
                    "environment_prepared": True,
                    "ready": True
                }
                return warmed_state
            except Exception as e:
                logger.error(f"Failed to warm Bash: {e}")
                return None

        else:
            # Generic warming - just mark as ready
            try:
                warmed_state = {
                    "tool": tool_name,
                    "warmed_at": time.time(),
                    "ready": True
                }
                return warmed_state
            except Exception as e:
                logger.error(f"Failed to warm {tool_name}: {e}")
                return None

    def get_tool(self, tool_name: str) -> Any:
        """
        Get a warmed tool instance if available, otherwise create a new one.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance (warmed or newly created)
        """
        # Try to get a warmed instance first
        if self._warm_tool_pool[tool_name]:
            instance = self._warm_tool_pool[tool_name].pop()
            logger.debug(f"Retrieved warmed instance of {tool_name}")
            return instance

        # Otherwise create a new instance
        logger.debug(f"Creating new instance of {tool_name}")
        return self._create_tool_instance(tool_name)

    def _create_tool_instance(self, tool_name: str) -> Any:
        """Create a new tool instance (placeholder for actual implementation)."""
        tool_spec = self.get_tool_spec(tool_name)
        if tool_spec is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        # In a real implementation, this would:
        # 1. For language runtimes: start a subprocess with appropriate environment
        # 2. For containers: start a container instance
        # 3. For utilities: ensure they're available in PATH
        # 4. For complex tools: initialize with appropriate configuration

        # For now, return a placeholder indicating the tool is ready to use
        return {
            "tool": tool_name,
            "created_at": time.time(),
            "spec": tool_spec,
            "ready": True,
            "instance_type": "new"
        }

    def return_tool(self, tool_name: str, instance: Any):
        """
        Return a tool instance to the warm pool for potential reuse.

        Args:
            tool_name: Name of the tool
            instance: The tool instance to return
        """
        # Basic validation - in practice would check instance health
        if isinstance(instance, dict) and instance.get("tool") == tool_name:
            # Check if it's still valid (not expired)
            age = time.time() - instance.get("warmed_at", instance.get("created_at", 0))
            max_age = 300.0  # 5 minutes max for warmed instances

            if age < max_age:
                self._warm_tool_pool[tool_name].append(instance)
                logger.debug(f"Returned {tool_name} to warm pool (age: {age:.1f}s)")
            else:
                logger.debug(f"Tool instance too old ({age:.1f}s), discarding")
        else:
            logger.warning(f"Attempted to return invalid instance for {tool_name}")

    def get_tool_stats(self) -> Dict[str, Any]:
        """Get statistics about tool usage and warming."""
        stats = {
            "registered_tools": len(self._tool_registry),
            "warmed_pools": {name: len(instances) for name, instances in self._warm_tool_pool.items()},
            "usage_stats": dict(self._tool_usage_stats),
            "prediction_history_size": len(self._prediction_history)
        }
        return stats

    def cleanup_expired_instances(self, max_age_seconds: float = 300.0):
        """Remove expired instances from warm pools."""
        now = time.time()
        cleaned_count = 0

        for tool_name in list(self._warm_tool_pool.keys()):
            instances = self._warm_tool_pool[tool_name]
            valid_instances = []

            for instance in instances:
                if isinstance(instance, dict):
                    timestamp = instance.get("warmed_at", instance.get("created_at", 0))
                    age = now - timestamp
                    if age < max_age_seconds:
                        valid_instances.append(instance)
                    else:
                        logger.debug(f"Removing expired {tool_name} instance (age: {age:.1f}s)")
                        cleaned_count += 1
                else:
                    # Non-dict instances - assume they need special handling
                    valid_instances.append(instance)  # Keep for now

            self._warm_tool_pool[tool_name] = valid_instances

            # Remove empty pools
            if not self._warm_tool_pool[tool_name]:
                del self._warm_tool_pool[tool_name]

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired tool instances")

        return cleaned_count


class ContextPolicyMapper:
    """
    Maps interaction contexts to tool policies and validates tool safety.
    Implements the policy engine mentioned in NALASafetyResearchOpportunities.md
    """

    def __init__(self):
        """Initialize the context-policy mapper."""
        self._context_policies = self._initialize_context_policies()
        logger.debug("Context Policy Mapper initialized")

    def _initialize_context_policies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize security policies for different interaction contexts."""
        return {
            "debugging": {
                "max_read_paths": {"/tmp/**", "/home/user/projects/**", "/proc/**", "/sys/**"},
                "max_write_paths": {"/tmp/**"},
                "allowed_network": set(),  # Usually no network in debugging
                "allow_process_spawning": True,
                "allow_root_tools": False,
                "require_deterministic": False,
                "blocked_tools": {"docker", "rm", "dd", "mkfs", "fdisk"}  # Dangerous in debugging
            },

            "design": {
                "max_read_paths": {"/tmp/**", "/home/user/**", "/usr/local/share/**"},
                "max_write_paths": {"/tmp/**", "/home/user/designs/**"},
                "allowed_network": {"api.github.com", "raw.githubusercontent.com", "pypi.org"},
                "allow_process_spawning": True,
                "allow_root_tools": False,
                "require_deterministic": False,
                "blocked_tools": {"docker", "rm -rf", "dd", "mkfs", "format"}
            },

            "production": {
                "max_read_paths": {"/tmp/**", "/var/www/**", "/opt/**", "/usr/local/**"},
                "max_write_paths": {"/tmp/**", "/var/log/**"},
                "allowed_network": {"api.github.com", "pypi.org", "npmjs.com"},
                "allow_process_spawning": True,
                "allow_root_tools": True,  # Sometimes needed in prod
                "require_deterministic": True,  # Prefer predictable tools in prod
                "blocked_tools": {"rm -rf /", "dd if=/dev/zero", "mkfs", "format c:"}
            },

            "learning": {
                "max_read_paths": {"/tmp/**", "/home/user/**", "/usr/local/share/**", "/usr/share/doc/**"},
                "max_write_paths": {"/tmp/**", "/home/user/learn/**"},
                "allowed_network": {"api.github.com", "raw.githubusercontent.com", "pypi.org", "stackoverflow.com"},
                "allow_process_spawning": True,
                "allow_root_tools": False,
                "require_deterministic": False,
                "blocked_tools": {"docker", "rm -rf", "dd", "mkfs", "fdisk", "format"}
            },

            "general": {
                "max_read_paths": {"/tmp/**", "/home/user/**"},
                "max_write_paths": {"/tmp/**"},
                "allowed_network": {"api.github.com", "pypi.org"},
                "allow_process_spawning": True,
                "allow_root_tools": False,
                "require_deterministic": False,
                "blocked_tools": {"docker", "rm -rf", "dd", "mkfs", "fdisk"}
            }
        }

    def validate_tool_safety(
        self,
        tool_name: str,
        tool_spec: ToolSpec,
        context: PredictionContext
    ) -> bool:
        """
        Validate whether a tool is safe to use in the given context.

        Args:
            tool_name: Name of the tool to validate
            tool_spec: Specification of the tool
            context: Prediction context including interaction context

        Returns:
            True if tool is safe to use in context, False otherwise
        """
        interaction_context = context.interaction_context.lower()

        # Get policy for this context (fallback to general)
        policy = self._context_policies.get(
            interaction_context,
            self._context_policies["general"]
        )

        # Check if tool is explicitly blocked
        blocked_tools = policy.get("blocked_tools", set())
        if tool_name in blocked_tools:
            logger.debug(f"Tool {tool_name} blocked in {interaction_context} context")
            return False

        # Check path permissions
        read_paths = tool_spec.allowed_read_paths
        write_paths = tool_spec.allowed_write_paths

        max_read = policy.get("max_read_paths", set())
        max_write = policy.get("max_write_paths", set())

        # For simplicity, we'll do a basic check - in reality would use glob matching
        if read_paths and not read_paths.issubset(max_read):
            logger.debug(f"Tool {tool_name} requests read paths exceeding policy: {read_paths - max_read}")
            return False

        if write_paths and not write_paths.issubset(max_write):
            logger.debug(f"Tool {tool_name} requests write paths exceeding policy: {write_paths - max_write}")
            return False

        # Check network endpoints
        network_endpoints = tool_spec.allowed_network_endpoints
        allowed_network = policy.get("allowed_network", set())

        if network_endpoints and not network_endpoints.issubset(allowed_network):
            logger.debug(f"Tool {tool_name} requests network endpoints exceeding policy: {network_endpoints - allowed_network}")
            return False

        # Check process spawning
        allow_spawning = policy.get("allow_process_spawning", True)
        if not allow_spawning and tool_spec.spawns_processes:
            logger.debug(f"Tool {tool_name} spawns processes but not allowed in {interaction_context}")
            return False

        # Check root requirement
        allow_root = policy.get("allow_root_tools", False)
        if not allow_root and tool_spec.requires_root:
            logger.debug(f"Tool {tool_name} requires root but not allowed in {interaction_context}")
            return False

        # Check determinism requirement
        require_det = policy.get("require_deterministic", False)
        if require_det and not tool_spec.is_deterministic:
            logger.debug(f"Tool {tool_name} is not deterministic but required in {interaction_context}")
            return False

        logger.debug(f"Tool {tool_name} validated as safe for {interaction_context} context")
        return True

    def get_context_policy(self, context: str) -> Dict[str, Any]:
        """Get the policy for a given context."""
        return self._context_policies.get(context.lower(), self._context_policies["general"])

    def add_context_policy(self, context: str, policy: Dict[str, Any]):
        """Add or update a policy for a context."""
        self._context_policies[context.lower()] = policy
        logger.debug(f"Added/updated policy for context: {context}")


# Factory function for easy instantiation
def make_predictive_tool_selector() -> PredictiveToolSelector:
    """Factory function to create a predictive tool selector with default configuration."""
    return PredictiveToolSelector()


if __name__ == "__main__":
    # Simple demo/test when run directly
    logging.basicConfig(level=logging.INFO)

    selector = make_predictive_tool_selector()

    # Mock predictive signals (would come from fleet/coordinator in practice)
    class MockSignals:
        def __init__(self):
            self.workload_complexity_index = 0.7
            self.cognitive_load_predictive = 0.6
            self.state_cohesion_score = 0.85
            self.hysteresis_buffer = 0.1

    signals = MockSignals()

    # Mock context
    context = {
        "interaction_context": "debugging",
        "recent_tools": ["python3", "git"],
        "timestamp": time.time()
    }

    # Mock recent interactions
    recent_interactions = [
        {"tool_name": "python3", "timestamp": time.time() - 10},
        {"tool_name": "git", "timestamp": time.time() - 20},
        {"tool_name": "rg", "timestamp": time.time() - 30}
    ]

    # Generate predictions
    predictions = selector.predict_tool_needs(signals, context, recent_interactions)

    print("\n=== Tool Predictions ===")
    for pred in predictions[:5]:  # Top 5
        print(f"Tool: {pred.tool_name}")
        print(f"  Confidence: {pred.confidence:.2f}")
        print(f"  Reasoning: {', '.join(pred.reasoning)}")
        print(f"  Expected latency reduction: {pred.estimated_latency_reduction:.2f}s")
        print(f"  Safety checked: {pred.safety_checked}")
        print()

    # Warm up tools
    warmed = selector.warm_up_tools(predictions, threshold=0.3)
    print(f"Warmed up tools: {warmed}")

    # Show stats
    stats = selector.get_tool_stats()
    print(f"\n=== Selector Stats ===")
    print(f"Registered tools: {stats['registered_tools']}")
    print(f"Warmed pools: {stats['warmed_pools']}")