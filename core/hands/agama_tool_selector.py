"""
Āgama‑Compliant Tool Selector for NALA Transcendent Reasoning Engine
==================================================================

Implements Layer 2: Āgama‑Compliant Tool Orchestration from the Transcendent Dual‑Mode Framework.
Wraps the existing ToolRegistry with dharmic governance logic for mode‑aware tool selection
based on Śruti, Smṛti, Śiṣṭa, and Ātmasantuṣṭi classifications.

Integrates with:
- Tool Registry (core/hands/tool_registry.py) - for base tool discovery and metadata
- Model Router (core/hands/model_router.py) - to provide dharmically filtered tool recommendations
- RTA Feedback Loop (core/safety/rta_feedback_loop.py) - to obtain current Ṛta‑Score
- Interaction Contract (core/interaction/interaction_contract.py) - to get current operational mode
"""

import logging
import threading
import time
from typing import Optional, Dict, List, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

# Import core NALA components with fallbacks
try:
    from .tool_registry import ToolRegistry, ToolMetadata, get_tool_registry
except ImportError:
    # Fallback for development/testing
    class ToolMetadata:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ToolRegistry:
        def __init__(self, *args, **kwargs):
            self._tools = {}
        def get_tool(self, name: str) -> Optional[Any]:
            return None
        def get_all_tools(self) -> List[str]:
            return []

    def get_tool_registry():
        return ToolRegistry()

try:
    from ..interaction.interaction_contract import get_current_model as get_operational_mode, TranscendentalModel
except ImportError:
    # Fallback for development/testing
    def get_operational_mode() -> Optional[str]:
        return None

    class TranscendentalModel:
        GANESHA = auto()
        SARASVATI = auto()
        SHIVA = auto()

try:
    from ..safety.rta_feedback_loop import get_default_rta_loop
except ImportError:
    # Fallback for development/testing
    def get_default_rta_loop():
        class DummyLoop:
            def get_latest(self):
                return 0.5, {"viveka": 0.5, "satya": 0.5, "dustara": 0.5, "ananda": 0.5}
        return DummyLoop()

logger = logging.getLogger(__name__)


# ======================
# DHARMIC CLASSIFICATIONS
# ======================

class DharmicClassification(Enum):
    """
    Dharmic classifications for tools based on Indian epistemological traditions.

    Based on Nyaya-Vaiśeṣika and related darśanas:
    - SHRUTI: Revealed/divine origin knowledge (highest authority, apauruṣeya)
    - SMRTI: Remembered/traditional knowledge (secondary authority, human origin)
    - SHISTA: Exemplary practice/validated by wise practitioners (smṛti with ācārābhyasa)
    - ATMA_SANTUSHTI: Self-satisfied/self-validated through direct experience (ātmanaḥ pramāṇam)
    """
    SHRUTI = auto()        # Revealed/divine origin - foundational algorithms, axioms
    SMRTI = auto()         # Remembered/traditional - established heuristics, best practices
    SHISTA = auto()        # Exemplary practice - expert-validated, peer-reviewed techniques
    ATMA_SANTUSHTI = auto() # Self-satisfied - experimental, novel, self-validated approaches


class OperationalMode(Enum):
    """Operational modes from the transcendent dual-mode framework."""
    PRATYAKSHA = "PRATYAKSHA"   # Direct perception - human-in-the-loop, collaborative
    PAROKSHA = "PAROKSHA"       # Transcendent inference - autonomous, council-directed
    ATHAPRAPTI = "ATHAPRAPTI"   # Direct attainment - meditative, zero-I/O, self-reflective


@dataclass
class DharmicToolMetadata:
    """
    Extended tool metadata with dharmic governance properties.
    Wraps/enhances the base ToolMetadata with dharmic classifications.
    """
    # Core tool identity (inherited from ToolMetadata)
    name: str
    description: str
    version: str = "1.0.0"

    # Functional categorization
    tags: List[str] = field(default_factory=list)
    category: str = "general"

    # Execution characteristics
    timeout_seconds: float = 30.0
    max_retries: int = 3
    priority: int = 1
    resource_weight: float = 1.0

    # Safety and reliability
    safety_level: str = "medium"
    requires_sandbox: bool = False
    side_effects: bool = False
    deterministic: bool = True

    # Performance and usage (updated dynamically)
    avg_latency: float = 0.0
    success_rate: float = 1.0
    total_invocations: int = 0
    last_used: float = 0.0

    # Dependencies and requirements
    dependencies: List[str] = field(default_factory=list)
    min_python_version: tuple = (3, 8)
    environment_vars: Dict[str, str] = field(default_factory=dict)

    # Capabilities and constraints
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    max_input_size: int = 10_000_000
    supports_async: bool = False

    # Custom properties for extensibility
    config: Dict[str, Any] = field(default_factory=dict)

    # DHARMIC EXTENSIONS - NEW FIELDS FOR ĀGAMA COMPLIANCE
    dharmic_classification: DharmicClassification = DharmicClassification.SMRTI
    authority_weight: float = 0.5                  # 0.0-1.0 influence in tool selection
    mode_restrictions: Set[OperationalMode] = field(default_factory=set)  # Modes where tool is prohibited
    requires_purification: bool = False            # Pre/post-execution rituals needed
    dharmic_purity_score: float = 0.5              # Internal consistency measure (0.0-1.0)
    last_validated: Optional[float] = None         # Timestamp of last dharmic check
    validation_count: int = 0                      # Number of times validated


class AgamaToolSelector:
    """
    Āgama‑Compliant Tool Orchestrator - Layer 2 of Transcendent Dual‑Mode Framework.
    Wraps ToolRegistry with dharmic governance logic for mode‑aware tool selection.
    """

    def __init__(self, base_tool_registry: Optional[ToolRegistry] = None):
        self._base_registry = base_tool_registry or get_tool_registry()
        self._dharmic_metadata: Dict[str, DharmicToolMetadata] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"{__name__}.AgamaToolSelector")
        self._mode_subscription = None
        self._rta_subscription = None
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 5.0  # Cache validity in seconds

        # Initialize dharmic classifications for known tools
        self._initialize_dharmic_classifications()
        self._logger.info("Āgama‑Compliant Tool Selector initialized")

    def _initialize_dharmic_classifications(self):
        """Initialize dharmic classifications for discovered tools."""
        try:
            # Get all tools from base registry
            tool_names = self._base_registry.get_all_tools()

            for tool_name in tool_names:
                # Get base metadata
                base_metadata = self._base_registry.get_tool(tool_name)
                if base_metadata is None:
                    continue

                # Create dharmic metadata by extending base metadata
                dharmic_meta = self._create_dharmic_metadata_from_base(base_metadata)
                self._dharmic_metadata[tool_name] = dharmic_meta

                self._logger.debug(f"Initialized dharmic metadata for tool: {tool_name}")

        except Exception as e:
            self._logger.warning(f"Could not initialize dharmic classifications: {e}")

    def _create_dharmic_metadata_from_base(self, base_metadata: ToolMetadata) -> DharmicToolMetadata:
        """Create DharmicToolMetadata from base ToolMetadata with intelligent defaults."""
        # Heuristic-based initial classification based on tool properties
        classification = self._infer_dharmic_classification(base_metadata)

        # Determine authority weight based on classification
        weight_map = {
            DharmicClassification.SHRUTI: 0.9,
            DharmicClassification.SMRTI: 0.7,
            DharmicClassification.SHISTA: 0.6,
            DharmicClassification.ATMA_SANTUSHTI: 0.4
        }
        authority_weight = weight_map.get(classification, 0.5)

        # Determine mode restrictions based on classification and properties
        mode_restrictions = self._infer_mode_restrictions(classification, base_metadata)

        # Determine if purification is needed
        requires_purification = self._needs_purification(classification, base_metadata)

        # Calculate initial purity score
        purity_score = self._calculate_initial_purity(classification, base_metadata)

        return DharmicToolMetadata(
            # Copy all base metadata fields
            name=base_metadata.name,
            description=base_metadata.description,
            version=getattr(base_metadata, 'version', "1.0.0"),
            tags=getattr(base_metadata, 'tags', []),
            category=getattr(base_metadata, 'category', "general"),
            timeout_seconds=getattr(base_metadata, 'timeout_seconds', 30.0),
            max_retries=getattr(base_metadata, 'max_retries', 3),
            priority=getattr(base_metadata, 'priority', 1),
            resource_weight=getattr(base_metadata, 'resource_weight', 1.0),
            safety_level=getattr(base_metadata, 'safety_level', "medium"),
            requires_sandbox=getattr(base_metadata, 'requires_sandbox', False),
            side_effects=getattr(base_metadata, 'side_effects', False),
            deterministic=getattr(base_metadata, 'deterministic', True),
            avg_latency=getattr(base_metadata, 'avg_latency', 0.0),
            success_rate=getattr(base_metadata, 'success_rate', 1.0),
            total_invocations=getattr(base_metadata, 'total_invocations', 0),
            last_used=getattr(base_metadata, 'last_used', 0.0),
            dependencies=getattr(base_metadata, 'dependencies', []),
            min_python_version=getattr(base_metadata, 'min_python_version', (3, 8)),
            environment_vars=getattr(base_metadata, 'environment_vars', {}),
            input_types=getattr(base_metadata, 'input_types', []),
            output_types=getattr(base_metadata, 'output_types', []),
            max_input_size=getattr(base_metadata, 'max_input_size', 10_000_000),
            supports_async=getattr(base_metadata, 'supports_async', False),
            config=getattr(base_metadata, 'config', {}),

            # Dharmic extensions
            dharmic_classification=classification,
            authority_weight=authority_weight,
            mode_restrictions=mode_restrictions,
            requires_purification=requires_purification,
            dharmic_purity_score=purity_score
        )

    def _infer_dharmic_classification(self, metadata: ToolMetadata) -> DharmicClassification:
        """Infer dharmic classification from tool metadata using heuristics."""
        name_lower = metadata.name.lower()
        tags = [tag.lower() for tag in metadata.tags]
        description_lower = (metadata.description or "").lower()
        safety_level = getattr(metadata, 'safety_level', 'medium').lower()

        # SHRUTI: Foundational, axiomatic, high safety, low-level operations
        shruti_indicators = [
            'foundation', 'axiom', 'principle', 'law', 'rule', 'core', 'basic',
            'syntax', 'parse', 'validate', 'check', 'type', 'logic', 'math',
            'found', 'essential', 'fundamental'
        ]
        shruti_score = sum(1 for indicator in shruti_indicators
                          if indicator in name_lower or indicator in description_lower)

        # Check high safety and determinism as SHRUTI indicators
        if (safety_level in ['high', 'critical'] and
            metadata.deterministic and
            metadata.side_effects == False):
            shruti_score += 2

        # SMRTI: Established, traditional, widely accepted practices
        smrti_indicators = [
            'standard', 'conventional', 'traditional', 'established', 'common',
            'best practice', 'guideline', 'recommended', 'widely used', 'popular',
            'lint', 'format', 'style', 'convention'
        ]
        smrti_score = sum(1 for indicator in smrti_indicators
                         if indicator in name_lower or indicator in description_lower)

        # SHISTA: Expert-validated, peer-reviewed, high-performance
        shista_indicators = [
            'optimized', 'efficient', 'high-performance', 'advanced', 'expert',
            'professional', 'certified', 'validated', 'verified', 'proven',
            'benchmark', 'optimized', 'efficient'
        ]
        shista_score = sum(1 for indicator in shista_indicators
                          if indicator in name_lower or indicator in description_lower)

        # Check for success rate and performance as SHISTA indicators
        if (metadata.success_rate >= 0.95 and
            metadata.avg_latency > 0 and
            metadata.avg_latency < 5.0):  # Reasonable performance
            shista_score += 1

        # ATMA_SANTUSHTI: Experimental, novel, research-oriented, self-validated
        atma_santushti_indicators = [
            'experimental', 'research', 'novel', 'innovative', 'prototype',
            'exploratory', 'hypothesis', 'theory', 'conceptual', 'emerging',
            'ml', 'ai', 'neural', 'deep learning', 'reinforcement', 'evolutionary',
            'genetic', 'swarm', 'quantum', 'experimental'
        ]
        atma_santushti_score = sum(1 for indicator in atma_santushti_indicators
                                  if indicator in name_lower or indicator in description_lower)

        # Check for learning/adaptation as ATMA_SANTUSHTI indicator
        if (not metadata.deterministic or
            metadata.supports_async or
            'learning' in description_lower or
            'adaptive' in description_lower):
            atma_santushti_score += 1

        # Determine classification based on scores
        scores = {
            DharmicClassification.SHRUTI: shruti_score,
            DharmicClassification.SMRTI: smrti_score,
            DharmicClassification.SHISTA: shista_score,
            DharmicClassification.ATMA_SANTUSHTI: atma_santushti_score
        }

        # Return classification with highest score, default to SMRTI if tie or zero
        max_score = max(scores.values())
        if max_score == 0:
            return DharmicClassification.SMRTI  # Default fallback

        for classification, score in scores.items():
            if score == max_score:
                return classification

    def _infer_mode_restrictions(self, classification: DharmicClassification,
                                metadata: ToolMetadata) -> Set[OperationalMode]:
        """Infer operational mode restrictions based on dharmic classification."""
        restrictions = set()

        # Based on framework documentation:
        # PRATYAKSHA mode should deny Śruti-tools (too authoritative for direct perception)
        if classification == DharmicClassification.SHRUTI:
            restrictions.add(OperationalMode.PRATYAKSHA)

        # ATHAPRAPTI mode should be restricted to validated, non-revelatory tools
        # to avoid ego inflation in meditative state
        if classification == DharmicClassification.SHRUTI:
            # Śruti tools might be too revelatory for ATHAPRAPTI
            restrictions.add(OperationalMode.ATHAPRAPTI)

        # Additional restrictions based on tool properties
        if metadata.side_effects:
            # Tools with side effects may not be suitable for ATHAPRAPTI (zero-I/O)
            restrictions.add(OperationalMode.ATHAPRAPTI)

        if not metadata.deterministic:
            # Non-deterministic tools may be problematic for PRATYAKSHA (needs predictability)
            restrictions.add(OperationalMode.PRATYAKSHA)

        if metadata.requires_sandbox and safety_level in ['low', 'medium']:
            # High-risk sandboxed tools may need restrictions
            if classification == DharmicClassification.SHRUTI:
                restrictions.add(OperationalMode.PRATYAKSHA)

        return restrictions

    def _needs_purification(self, classification: DharmicClassification,
                           metadata: ToolMetadata) -> bool:
        """Determine if tool requires pre/post-execution purification."""
        # Śruti tools may need purification due to their high authority
        if classification == DharmicClassification.SHRUTI:
            return True

        # Experimental tools may need validation/cleansing
        if classification == DharmicClassification.ATMA_SANTUSHTI:
            return True

        # Tools with side effects may need energetic cleansing
        if metadata.side_effects:
            return True

        # Low safety tools may need purification before use
        if metadata.safety_level in ['low', 'medium']:
            return True

        return False

    def _calculate_initial_purity(self, classification: DharmicClassification,
                                 metadata: ToolMetadata) -> float:
        """Calculate initial dharmic purity score."""
        # Base purity from classification
        base_purity = {
            DharmicClassification.SHRUTI: 0.9,   # High but needs contextual checking
            DharmicClassification.SMRTI: 0.7,    # Solid traditional basis
            DharmicClassification.SHISTA: 0.8,   # Expert validated
            DharmicClassification.ATMA_SANTUSHTI: 0.5  # Self-validated, variable
        }.get(classification, 0.5)

        # Adjust based on safety and reliability
        safety_bonus = 0.0
        if metadata.safety_level == 'high':
            safety_bonus = 0.1
        elif metadata.safety_level == 'critical':
            safety_bonus = 0.2
        elif metadata.safety_level == 'low':
            safety_bonus = -0.1

        reliability_bonus = (metadata.success_rate - 0.5) * 0.2  # -0.1 to +0.1

        # Deterministic bonus for predictability
        deterministic_bonus = 0.1 if metadata.deterministic else -0.1

        # Side effect penalty
        side_effect_penalty = -0.1 if metadata.side_effects else 0.0

        purity = base_purity + safety_bonus + reliability_bonus + deterministic_bonus + side_effect_penalty

        # Clamp to valid range
        return max(0.1, min(0.95, purity))

    # ======================
    # PUBLIC API METHODS
    # ======================

    def get_dharmic_classification(self, tool_name: str) -> Optional[DharmicClassification]:
        """Get the dharmic classification for a tool."""
        with self._lock:
            metadata = self._dharmic_metadata.get(tool_name)
            return metadata.dharmic_classification if metadata else None

    def get_tool_dharmic_metadata(self, tool_name: str) -> Optional[DharmicToolMetadata]:
        """Get the complete dharmic metadata for a tool."""
        with self._lock:
            return self._dharmic_metadata.get(tool_name)

    def is_tool_allowed_in_mode(self, tool_name: str, mode: OperationalMode) -> bool:
        """Check if a tool is allowed in the specified operational mode."""
        with self._lock:
            metadata = self._dharmic_metadata.get(tool_name)
            if metadata is None:
                # Unknown tool - apply conservative default
                return mode != OperationalMode.PRATYAKSHA  # Allow except in PRATYAKSHA for safety

            return mode not in metadata.mode_restrictions

    def get_allowed_tools(self, mode: Optional[OperationalMode] = None,
                         rta_score: Optional[float] = None) -> List[str]:
        """
        Get list of tools allowed in the specified mode, optionally filtered by Ṛta‑Score.

        Args:
            mode: Operational mode (if None, uses current mode from interaction contract)
            rta_score: Current Ṛta‑Score (if None, fetches from RTA feedback loop)

        Returns:
            List of tool names permitted under the given conditions
        """
        # Get current mode if not specified
        if mode is None:
            mode_str = get_operational_mode()
            mode = self._string_to_operational_mode(mode_str) if mode_str else OperationalMode.PAROKSHA

        # Get current Rta‑Score if not specified
        if rta_score is None:
            try:
                rta_score, _ = get_default_rta_loop().get_latest()
            except Exception:
                rta_score = 0.5  # Neutral fallback

        # Check cache validity
        cache_key = f"{mode.value}_{rta_score:.3f}"
        current_time = time.time()
        if (self._cache.get('_last_key') == cache_key and
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._cache.get('allowed_tools', []).copy()

        allowed_tools = []

        try:
            # Get all tools from base registry
            all_tool_names = self._base_registry.get_all_tools()

            for tool_name in all_tool_names:
                # Check mode allowance
                if not self.is_tool_allowed_in_mode(tool_name, mode):
                    continue

                # Get dharmic metadata
                dharmic_meta = self._get_tool_dharmic_metadata_cached(tool_name)
                if dharmic_meta is None:
                    continue

                # Apply Ṛta‑Score based weighting/filtering
                if self._is_tool_suitable_for_rta_score(dharmic_meta, rta_score, mode):
                    allowed_tools.append(tool_name)

            # Sort by dharmic suitability (higher purity and authority weight first)
            allowed_tools.sort(
                key=lambda name: (
                    self._dharmic_metadata[name].dharmic_purity_score,
                    self._dharmic_metadata[name].authority_weight
                ),
                reverse=True
            )

            # Update cache
            self._cache['allowed_tools'] = allowed_tools.copy()
            self._cache['_last_key'] = cache_key
            self._cache_timestamp = current_time

            self._logger.debug(
                f"Found {len(allowed_tools)} allowed tools for mode={mode.value}, "
                f"Ṛta‑Score={rta_score:.3f}"
            )

        except Exception as e:
            self._logger.error(f"Error getting allowed tools: {e}")
            # Fallback to all tools if error occurs
            try:
                allowed_tools = self._base_registry.get_all_tools()
            except Exception:
                allowed_tools = []

        return allowed_tools

    def get_tool_weights(self, tool_name: str,
                        rta_score: Optional[float] = None) -> Dict[str, float]:
        """
        Get weight factors for a tool based on dharmic properties and current context.

        Returns:
            Dictionary with keys: 'dharmic', 'authority', 'purity', 'combined'
        """
        if rta_score is None:
            try:
                rta_score, _ = get_default_rta_loop().get_latest()
            except Exception:
                rta_score = 0.5

        with self._lock:
            dharmic_meta = self._dharmic_metadata.get(tool_name)
            if dharmic_meta is None:
                # Return neutral weights for unknown tools
                return {
                    'dharmic': 0.5,
                    'authority': 0.5,
                    'purity': 0.5,
                    'combined': 0.5
                }

            # Base weights from dharmic properties
            dharmic_weight = dharmic_meta.dharmic_purity_score
            authority_weight = dharmic_meta.authority_weight

            # Adjust based on Ṛta‑Score and operational mode
            mode_str = get_operational_mode()
            mode = self._string_to_operational_mode(mode_str) if mode_str else OperationalMode.PAROKSHA

            # Apply mode‑specific adjustments
            if mode == OperationalMode.PRATYAKSHA:
                # In direct perception mode, favor smṛti and śiṣṭa, reduce śruti weight
                if dharmic_meta.dharmic_classification == DharmicClassification.SHRUTI:
                    dharmic_weight *= 0.5  # Reduce śruti influence
                    authority_weight *= 0.5
                elif dharmic_meta.dharmic_classification in [
                        DharmicClassification.SMRTI,
                        DharmicClassification.SHISTA]:
                    dharmic_weight *= 1.2  # Boost traditional/validated tools
                    authority_weight *= 1.2

            elif mode == OperationalMode.ATHAPRAPTI:
                # In direct attainment mode, favor validated, non‑revelatory tools
                if dharmic_meta.dharmic_classification == DharmicClassification.SHRUTI:
                    dharmic_weight *= 0.3  # Strongly reduce śruti
                    authority_weight *= 0.3
                elif dharmic_meta.dharmic_classification == DharmicClassification.ATMA_SANTUSHTI:
                    dharmic_weight *= 0.8  # Slightly reduce experimental
                    # Note: śiṣṭa gets boosted below

            # Apply Ṛta‑Score based adjustments
            # Higher Ṛta‑Score (more transcendental) favors śruti and profound tools
            if rta_score > 0.8:  # High Ṛta‑Score - transcendental inference/attainment
                if dharmic_meta.dharmic_classification == DharmicClassification.SHRUTI:
                    dharmic_weight *= (1.0 + (rta_score - 0.8) * 0.5)  # Boost up to 1.5x
                elif dharmic_meta.dharmic_classification == DharmicClassification.SHISTA:
                    dharmic_weight *= (1.0 + (rta_score - 0.8) * 0.3)  # Moderate boost

            elif rta_score < 0.4:  # Low Ṛta‑Score - more grounded, perceptual
                if dharmic_meta.dharmic_classification == DharmicClassification.ATMA_SANTUSHTI:
                    dharmic_weight *= (0.5 + rta_score * 1.0)  # Reduce experimental at low Ṛta
                elif dharmic_meta.dharmic_classification == DharmicClassification.SMRTI:
                    dharmic_weight *= (1.0 + (0.4 - rta_score) * 0.5)  # Boost traditional

            # Ensure weights stay in reasonable bounds
            dharmic_weight = max(0.1, min(1.0, dharmic_weight))
            authority_weight = max(0.1, min(1.0, authority_weight))

            # Combined weight (geometric mean for balance)
            combined_weight = (dharmic_weight * authority_weight) ** 0.5

            return {
                'dharmic': round(dharmic_weight, 3),
                'authority': round(authority_weight, 3),
                'purity': round(dharmic_meta.dharmic_purity_score, 3),
                'combined': round(combined_weight, 3)
            }

    def _is_tool_suitable_for_rta_score(self, dharmic_meta: DharmicToolMetadata,
                                       rta_score: float, mode: OperationalMode) -> bool:
        """Determine if tool is suitable given current Ṛta‑Score and mode."""
        # First, check basic mode allowance (already done in caller, but double-check)
        mode_allowed = self.is_tool_allowed_in_mode(dharmic_meta.name, mode)
        if not mode_allowed:
            return False

        # Get dynamic weights for this context
        weights = self.get_tool_weights(dharmic_meta.name, rta_score)

        # Apply threshold based on combined weight
        # Higher threshold means more selective
        base_threshold = 0.3

        # Adjust threshold based on mode
        if mode == OperationalMode.PRATYAKSHA:
            threshold = base_threshold * 0.8  # More permissive in collaborative mode
        elif mode == OperationalMode.ATHAPRAPTI:
            threshold = base_threshold * 1.2  # More selective in meditative mode
        else:  # PAROKSHA
            threshold = base_threshold

        return weights['combined'] >= threshold

    def get_dharmic_recommendation(self, request_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get dharmically informed tool recommendation for current context.

        Returns:
            Dictionary with recommended tools, classifications, and reasoning
        """
        try:
            # Get current context
            mode_str = get_operational_mode()
            mode = self._string_to_operational_mode(mode_str) if mode_str else OperationalMode.PAROKSHA

            rta_score, rta_components = get_default_rta_loop().get_latest()

            # Get allowed and recommended tools
            allowed_tools = self.get_allowed_tools(mode, rta_score)

            # Get detailed information for top recommendations
            recommendations = []
            for tool_name in allowed_tools[:10]:  # Top 10 recommendations
                dharmic_meta = self._get_tool_dharmic_metadata_cached(tool_name)
                if dharmic_meta is None:
                    continue

                weights = self.get_tool_weights(tool_name, rta_score)

                recommendations.append({
                    'tool': tool_name,
                    'classification': dharmic_meta.dharmic_classification.name,
                    'authority_weight': weights['authority'],
                    'purity_score': weights['purity'],
                    'combined_weight': weights['combined'],
                    'description': dharmic_meta.description,
                    'tags': dharmic_meta.tags[:3]  # First 3 tags for brevity
                })

            # Sort by combined weight descending
            recommendations.sort(key=lambda x: x['combined_weight'], reverse=True)

            return {
                'operational_mode': mode.value if mode else 'UNKNOWN',
                'rta_score': round(rta_score, 3),
                'rta_components': {k: round(v, 3) for k, v in rta_components.items()},
                'total_allowed_tools': len(allowed_tools),
                'top_recommendations': recommendations[:5],  # Top 5 for brevity
                'all_recommendations': recommendations,
                'dharmic_distribution': self._get_dharmic_distribution(allowed_tools)
            }

        except Exception as e:
            self._logger.error(f"Error generating dharmic recommendation: {e}")
            return {
                'error': str(e),
                'fallback_available': True
            }

    def _get_dharmic_distribution(self, tool_list: List[str]) -> Dict[str, int]:
        """Get distribution of dharmic classifications in a tool list."""
        distribution = {
            'SHRUTI': 0,
            'SMRTI': 0,
            'SHISTA': 0,
            'ATMA_SANTUSHTI': 0
        }

        for tool_name in tool_list:
            dharmic_meta = self._dharmic_metadata.get(tool_name)
            if dharmic_meta:
                classification = dharmic_meta.dharmic_classification.name
                if classification in distribution:
                    distribution[classification] += 1

        return distribution

    def validate_tool_usage(self, tool_name: str,
                           mode: Optional[OperationalMode] = None) -> tuple[bool, str]:
        """
        Validate if a tool can be used in the current/mode context.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if mode is None:
            mode_str = get_operational_mode()
            mode = self._string_to_operational_mode(mode_str) if mode_str else OperationalMode.PAROKSHA

        # Check if tool exists
        if tool_name not in self._dharmic_metadata:
            return False, f"Tool '{tool_name}' not found in dharmic registry"

        dharmic_meta = self._dharmic_metadata[tool_name]

        # Check mode restrictions
        if mode in dharmic_meta.mode_restrictions:
            return False, (
                f"Tool '{tool_name}' is prohibited in {mode.value} mode "
                f"(classification: {dharmic_meta.dharmic_classification.name})"
            )

        # Check purification requirements
        if dharmic_meta.requires_purification:
            # In a real implementation, this would check if purification was performed
            # For now, we log a warning but allow usage
            self._logger.warning(
                f"Tool '{tool_name}' requires purification before use in {mode.value} mode"
            )

        # Check if validation is stale (older than 24 hours)
        if dharmic_meta.last_validated:
            age_hours = (time.time() - dharmic_meta.last_validated) / 3600.0
            if age_hours > 24:
                return False, (
                    f"Tool '{tool_name}' dharmic validation is stale "
                    f"({age_hours:.1f} hours old)"
                )

        return True, "Tool usage validated"

    def record_tool_validation(self, tool_name: str, validator: str = "system") -> bool:
        """Record that a tool has been dharmically validated."""
        with self._lock:
            if tool_name not in self._dharmic_metadata:
                self._logger.warning(f"Cannot validate unknown tool: {tool_name}")
                return False

            metadata = self._dharmic_metadata[tool_name]
            metadata.last_validated = time.time()
            metadata.validation_count += 1

            # Optionally update purity score based on validation
            # In a full implementation, this might involve more complex logic
            self._logger.info(
                f"Tool '{tool_name}' dharmic validation recorded by {validator} "
                f"(count: {metadata.validation_count})"
            )
            return True

    # ======================
    # HELPER METHODS
    # ======================

    def _string_to_operational_mode(self, mode_str: Optional[str]) -> Optional[OperationalMode]:
        """Convert mode string to OperationalMode enum."""
        if not mode_str:
            return None

        try:
            return OperationalMode(mode_str)
        except ValueError:
            # Try case-insensitive match
            for mode in OperationalMode:
                if mode.value.lower() == mode_str.lower():
                    return mode
            self._logger.warning(f"Unknown operational mode: {mode_str}")
            return None

    def _get_tool_dharmic_metadata_cached(self, tool_name: str) -> Optional[DharmicToolMetadata]:
        """Get dharmic metadata with internal caching."""
        # Simple cache - in practice might want more sophisticated invalidation
        current_time = time.time()
        if (hasattr(self, '_meta_cache') and
            tool_name in self._meta_cache and
            current_time - self._meta_cache.get(f'{tool_name}_timestamp', 0) < 60.0):
            return self._meta_cache[tool_name]

        # Fetch and cache
        metadata = self._dharmic_metadata.get(tool_name)
        if not hasattr(self, '_meta_cache'):
            self._meta_cache = {}
        self._meta_cache[tool_name] = metadata
        self._meta_cache[f'{token_name}_timestamp'] = current_time

        return metadata

    def purge_caches(self):
        """Clear all internal caches."""
        self._cache.clear()
        if hasattr(self, '_meta_cache'):
            self._meta_cache.clear()
        self._logger.debug("Internal caches purged")

    def get_statistics(self) -> Dict[str, Any]:
        """Get selector statistics for monitoring/debugging."""
        with self._lock:
            total_tools = len(self._dharmic_metadata)
            if total_tools == 0:
                return {'total_tools': 0}

            # Count by classification
            classification_counts = {
                'SHRUTI': 0,
                'SMRTI': 0,
                'SHISTA': 0,
                'ATMA_SANTUSHTI': 0
            }

            # Count by restriction patterns
            pratyaksha_restricted = 0
            paroksha_restricted = 0
            athaprapti_restricted = 0

            total_purity = 0.0
            total_authority = 0.0
            validation_count = 0

            for metadata in self._dharmic_metadata.values():
                # Classification counts
                classification_counts[metadata.dharmic_classification.name] += 1

                # Restriction counts
                if OperationalMode.PRATYAKSHA in metadata.mode_restrictions:
                    pratyaksha_restricted += 1
                if OperationalMode.PAROKSHA in metadata.mode_restrictions:
                    paroksha_restricted += 1
                if OperationalMode.ATHAPRAPTI in metadata.mode_restrictions:
                    athaprapti_restricted += 1

                # Sums for averages
                total_purity += metrics.dharmic_purity_score
                total_authority += metrics.authority_weight
                validation_count += metrics.validation_count

            return {
                'total_tools': total_tools,
                'classification_distribution': classification_counts,
                'mode_restrictions': {
                    'PRATYAKSHA': pratyaksha_restricted,
                    'PAROKSHA': paroksha_restricted,
                    'ATHAPRAPTI': athaprapti_restricted
                },
                'average_purity': round(total_purity / total_tools, 3) if total_tools > 0 else 0.0,
                'average_authority': round(total_authority / total_tools, 3) if total_tools > 0 else 0.0,
                'total_validations': validation_count,
                'average_validations_per_tool': round(validation_count / total_tools, 1) if total_tools > 0 else 0.0,
                'cache_size': len(getattr(self, '_cache', {})),
                'meta_cache_size': len(getattr(self, '_meta_cache', {}))
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the dharmic tool selector."""
        issues = []
        status = "healthy"

        try:
            stats = self.get_statistics()

            # Check if we have any tools
            if stats.get('total_tools', 0) == 0:
                issues.append("No tools loaded in dharmic selector")
                status = "unhealthy"

            # Check for excessive restrictions
            total_restrictions = (
                stats.get('mode_restrictions', {}).get('PRATYAKSHA', 0) +
                stats.get('mode_restrictions', {}).get('PAROKSHA', 0) +
                stats.get('mode_restrictions', {}).get('ATHAPRAPTI', 0)
            )
            if total_restrictions > stats.get('total_tools', 1) * 0.5:  # More than 50% restricted
                issues.append("High number of mode restrictions detected")
                if status == "healthy":
                    status = "degraded"

            # Check average purity
            avg_purity = stats.get('average_purity', 0.0)
            if avg_purity < 0.3:
                issues.append(f"Low average dharmic purity: {avg_purity:.3f}")
                if status == "healthy":
                    status = "degraded"

            # Check if we can access dependencies
            try:
                get_operational_mode()
                get_default_rta_loop().get_latest()
            except Exception as e:
                issues.append(f"Dependency access failed: {e}")
                status = "degraded"

        except Exception as e:
            issues.append(f"Health check failed: {e}")
            status = "unhealthy"

        return {
            'status': status,
            'issues': issues,
            'timestamp': time.time(),
            'statistics': self.get_statistics()
        }

    # ======================
    # CALLBACK SYSTEM
    # ======================

    def register_dharmic_update_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> Callable[[], None]:
        """
        Register a callback for dharmic updates (e.g., when classifications change).

        Returns an unsubscribe function.
        """
        if not hasattr(self, '_dharmic_callbacks'):
            self._dharmic_callbacks = []

        if not callable(callback):
            raise TypeError("Callback must be callable")

        self._dharmic_callbacks.append(callback)
        self._logger.debug(f"Registered dharmic update callback: {callback.__name__}")

        def unsubscribe():
            if hasattr(self, '_dharmic_callbacks') and callback in self._dharmic_callbacks:
                self._dharmic_callbacks.remove(callback)
                self._logger.debug(f"Unregistered dharmic update callback: {callback.__name__}")

        return unsubscribe

    def _notify_dharmic_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify all registered dharmic callbacks."""
        if not hasattr(self, '_dharmic_callbacks'):
            return

        callbacks = list(self._dharmic_callbacks)  # Copy for safety
        for callback in callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                self._logger.error(f"Error in dharmic callback {callback.__name__}: {e}")


# =======================
# Module-Level Singleton
# =======================

# Global selector instance for easy access throughout the codebase
_agama_tool_selector: Optional[AgamaToolSelector] = None
_agama_selector_lock = threading.Lock()


def get_agama_tool_selector() -> AgamaToolSelector:
    """
    Get or create the global Āgama‑Compliant Tool Selector instance (singleton pattern).

    Returns:
        The singleton AgamaToolSelector instance.
    """
    global _agama_tool_selector
    if _agama_tool_selector is None:
        with _agama_selector_lock:
            if _agama_tool_selector is None:  # Double-check locking
                _agama_tool_selector = AgamaToolSelector()
    return _agama_tool_selector


def get_dharmic_classification(tool_name: str) -> Optional[DharmicClassification]:
    """
    Convenience function to get dharmic classification for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        DharmicClassification or None if tool not found
    """
    return get_agama_tool_selector().get_dharmic_classification(tool_name)


def is_tool_allowed(tool_name: str, mode: Optional[str] = None) -> bool:
    """
    Convenience function to check if tool is allowed in specified mode.

    Args:
        tool_name: Name of the tool
        mode: Operational mode string (optional, uses current mode if not provided)

    Returns:
        True if tool is allowed, False otherwise
    """
    selector = get_agama_tool_selector()
    mode_enum = selector._string_to_operational_mode(mode) if mode else None
    return selector.is_tool_allowed_in_mode(tool_name, mode_enum)


def get_dharmic_recommendation() -> Dict[str, Any]:
    """
    Convenience function to get current dharmic tool recommendation.

    Returns:
        Dictionary with recommendation details
    """
    return get_agama_tool_selector().get_dharmic_recommendation()


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
    print("Āgama‑Compliant Tool Selector Demo / Self-Test")
    print("=" * 70)

    # Create selector instance
    selector = get_agama_tool_selector()

    print(f"\nInitial state: {selector.get_statistics()['total_tools']} tools loaded")

    # Show some tool classifications if any exist
    stats = selector.get_statistics()
    if stats.get('total_tools', 0) > 0:
        print(f"\nClassification distribution: {stats['classification_distribution']}")
        print(f"Mode restrictions: {stats['mode_restrictions']}")
        print(f"Average purity: {stats['average_purity']}")
        print(f"Average authority: {stats['average_authority']}")
    else:
        print("\nNo tools loaded (expected in fresh environment)")
        print("To test with real tools, ensure tool registry has discovered tools")

    # Demo mode-based filtering
    print("\n--- Mode-Based Filtering Demo ---")
    for mode in OperationalMode:
        allowed = selector.get_allowed_tools(mode=mode)
        print(f"{mode.value}: {len(allowed)} allowed tools")
        if allowed and len(allowed) <= 5:
            print(f"  Tools: {', '.join(allowed)}")
        elif allowed:
            print(f"  Sample: {', '.join(allowed[:3])}... ({len(allowed)} total)")

    # Demo dharmic recommendations
    print("\n--- Dharmic Recommendation Demo ---")
    try:
        recommendation = selector.get_dharmic_recommendation()
        if 'error' not in recommendation:
            print(f"Current mode: {recommendation['operational_mode']}")
            print(f"Ṛta‑Score: {recommendation['rta_score']}")
            print(f"Total allowed tools: {recommendation['total_allowed_tools']}")
            print("Top recommendations:")
            for rec in recommendation['top_recommendations']:
                print(
                    f"  - {rec['tool']} "
                    f"[{rec['classification']}] "
                    f"(purity: {rec['purity_score']}, "
                    f"authority: {rec['authority_weight']}, "
                    f"combined: {rec['combined_weight']})"
                )
        else:
            print(f"Recommendation error: {recommendation['error']}")
    except Exception as e:
        print(f"Recommendation demo failed: {e}")

    # Demo validation
    print("\n--- Validation Demo ---")
    all_tools = selector.get_allowed_tools()  # Get any available tools
    if all_tools:
        test_tool = all_tools[0]
        is_valid, reason = selector.validate_tool_usage(test_tool)
        print(f"Tool '{test_tool}' validation: {'PASS' if is_valid else 'FAIL'} - {reason}")

        # Test invalid mode
        is_valid_pra, reason_pra = selector.validate_tool_usage(
            test_tool,
            mode=OperationalMode.PRATYAKSHA
        )
        print(f"Tool '{test_tool}' in PRATYAKSHA: {'PASS' if is_valid_pra else 'FAIL'} - {reason_pra}")
    else:
        print("No tools available for validation demo")

    # Demo health check
    print("\n--- Health Check ---")
    health = selector.health_check()
    print(f"Status: {health['status']}")
    if health['issues']:
        print("Issues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("No issues detected.")

    print("\n" + "=" * 70)
    print("Demo completed.")
    print("=" * 70)