"""
Tool Registry for NALA Transcendent Reasoning Engine
===================================================

Discovers, manages, and provides metadata for tools available to the NALA system.
Enables model-aware tool selection by the Model Router based on tool characteristics
such as safety level, computational cost, latency, and functional tags.

Integrates with:
- Model Router (to provide tool recommendations based on transcendental model state)
- Predictive Tool Selector (to hint which tools should be preloaded)
- Executor (to provide tool instances and metadata for execution)
"""

import logging
import threading
import importlib
import inspect
import os
import json
import sys
import time
from typing import Optional, Dict, List, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata describing a tool's capabilities, requirements, and characteristics."""
    # Basic identification
    name: str
    description: str
    version: str = "1.0.0"

    # Functional categorization
    tags: List[str] = field(default_factory=list)  # e.g., ["validation", "fast", "repair"]
    category: str = "general"  # e.g., "validation", "analysis", "repair", "generation"

    # Execution characteristics
    timeout_seconds: float = 30.0
    max_retries: int = 3
    priority: int = 1  # Lower number = higher priority
    resource_weight: float = 1.0  # Relative CPU/memory usage (1.0 = baseline)

    # Safety and reliability
    safety_level: str = "medium"  # low, medium, high, critical
    requires_sandbox": "medium"  # low, medium, high, critical
    requires_sandbox: bool = False
    side_effects: bool = False  # Whether tool modifies external state
    deterministic: bool = True  # Whether tool produces same output for same input

    # Performance and usage (updated dynamically)
    avg_latency: float = 0.0
    success_rate: float = 1.0
    total_invocations: int = 0
    last_used: float = 0.0

    # Dependencies and requirements
    dependencies: List[str] = field(default_factory=list)  # Python package names
    min_python_version: Tuple[int, int] = (3, 8)
    environment_vars: Dict[str, str] = field(default_factory=dict)

    # Capabilities and constraints
    input_types: List[str] = field(default_factory=list)  # e.g., ["code", "text", "data"]
    output_types: List[str] = field(default_factory=list)
    max_input_size: int = 10_000_000  # bytes
    supports_async: bool = False

    # Custom properties for extensibility
    config: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Discovers and manages tools available to the NALA system.

    Features:
    - Automatic discovery of tools in designated directories
    - Rich metadata support for intelligent tool selection
    - Thread-safe concurrent access
    - Health monitoring and validation
    - Dynamic loading/unloading of tool instances
    - Usage statistics and performance tracking
    - Integration with model-aware selection via tags and safety levels
    """

    def __init__(self,
                 tool_directories: Optional[List[str]] = None,
                 enable_auto_discovery: bool = True,
                 enable_usage_tracking: bool = True,
                 validation_level: str = "standard"):  # none, basic, strict
        """
        Initialize the Tool Registry.

        Args:
            tool_directories: List of directories to scan for tools.
                             If None, uses default: [core/hands/tools]
            enable_auto_discovery: Whether to automatically discover tools on init
            enable_usage_tracking: Whether to track tool invocation statistics
            validation_level: How strictly to validate discovered tools
        """
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"{__name__}.ToolRegistry")

        # Configuration
        self._tool_directories = tool_directories or [
            os.path.join(os.path.dirname(__file__), "tools")
        ]
        self._enable_auto_discovery = enable_auto_discovery
        self._enable_usage_tracking = enable_usage_tracking
        self._validation_level = validation_level

        # State
        self._tools: Dict[str, ToolMetadata] = {}  # name -> metadata
        self._tool_modules: Dict[str, Any] = {}   # name -> loaded module (for instantiation)
        self._tool_instances: Dict[str, Any] = {}  # name -> singleton instance (if applicable)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> set of tool names
        self._category_index: Dict[str, Set[str]] = defaultdict(set)  # category -> set of tool names
        self._safety_index: Dict[str, Set[str]] = defaultdict(set)  # safety_level -> set of tool names

        # Statistics
        self._discovery_errors: List[str] = []
        self._last_discovery_time: float = 0.0

        # Initialize
        self._ensure_directories()
        if self._enable_auto_discovery:
            self.discover_tools()

        self._logger.info(
            f"Tool Registry initialized: {len(self._tools)} tools discovered "
            f"from {len(self._tool_directories)} directories"
        )

    def _ensure_directories(self) -> None:
        """Ensure all tool directories exist."""
        for directory in self._tool_directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    self._logger.info(f"Created tool directory: {directory}")
                except Exception as e:
                    self._logger.error(f"Failed to create tool directory {directory}: {e}")

    def discover_tools(self, force: bool = False) -> int:
        """
        Discover and load tools from configured directories.

        Args:
            force: If True, rediscover even if recently discovered

        Returns:
            Number of newly discovered tools
        """
        current_time = time.time()
        if not force and (current_time - self._last_discovery_time) < 60.0 and self._tools:
            self._logger.debug("Skipping discovery - recently completed")
            return 0

        self._logger.info("Starting tool discovery...")
        initial_count = len(self._tools)
        errors_before = len(self._discovery_errors)

        # Clear indices for rebuilding (but keep existing tools if not forcing)
        if force:
            self._tools.clear()
            self._tool_modules.clear()
            self._tool_instances.clear()
            self._tag_index.clear()
            self._category_index.clear()
            self._safety_index.clear()
            self._discovery_errors.clear()

        # Discover in each directory
        for directory in self._tool_directories:
            if not os.path.isdir(directory):
                self._logger.warning(f"Tool directory does not exist: {directory}")
                continue

            self._discover_in_directory(directory)

        self._last_discovery_time = time.time()
        newly_discovered = len(self._tools) - initial_count
        new_errors = len(self._discovery_errors) - errors_before

        self._logger.info(
            f"Discovery complete: {newly_discovered} new tools, "
            f"{len(self._tools)} total tools, {new_errors} new errors"
        )
        return newly_discovered

    def _discover_in_directory(self, directory: str) -> None:
        """Discover tools in a specific directory."""
        try:
            entries = os.listdir(directory)
        except OSError as e:
            self._logger.error(f"Cannot list directory {directory}: {e}")
            self._discovery_errors.append(f"Directory listing failed: {directory} - {e}")
            return

        for entry in entries:
            # Skip hidden files and directories
            if entry.startswith('.') or entry.startswith('_'):
                continue

            full_path = os.path.join(directory, entry)

            # Check for Python files
            if entry.endswith('.py') and os.path.isfile(full_path):
                module_name = entry[:-3]  # Remove .py
                self._discover_python_tool(directory, module_name, full_path)
            # Check for directories that might be packages
            elif os.path.isdir(full_path):
                # Check if it's a Python package (has __init__.py)
                init_file = os.path.join(full_path, '__init__.py')
                if os.path.isfile(init_file):
                    package_name = entry
                    self._discover_python_tool(directory, package_name, full_path, is_package=True)
                # Also check for JSON/YAML tool definitions
                elif entry.endswith('.json') or entry.endswith('.yaml') or entry.endswith('.yml'):
                    self._discover_config_tool(directory, entry, full_path)

    def _discover_python_tool(self, directory: str, module_name: str,
                            file_path: str, is_package: bool = False) -> None:
        """Discover a tool from a Python module or package."""
        try:
            # Add directory to sys.path if not already there
            if directory not in sys.path:
                sys.path.insert(0, directory)

            # Import the module
            if is_package:
                module = importlib.import_module(module_name)
            else:
                module = importlib.import_module(module_name)

            # Remove from sys.path if we added it (to avoid pollution)
            if directory in sys.path:
                sys.path.remove(directory)

            # Extract metadata
            metadata = self._extract_tool_metadata(module, module_name)
            if metadata:
                self._register_tool(metadata, module)
            else:
                self._logger.warning(f"No valid tool metadata found in {module_name}")

        except ImportError as e:
            self._logger.warning(f"Failed to import module {module_name} from {directory}: {e}")
            self._discovery_errors.append(f"Import failed: {module_name} - {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error discovering {module_name}: {e}")
            self._discovery_errors.append(f"Discovery error: {module_name} - {e}")
        finally:
            # Clean up sys.path if we added it
            if directory in sys.path:
                try:
                    sys.path.remove(directory)
                except ValueError:
                    pass  # Already removed

    def _discover_config_tool(self, directory: str, filename: str, file_path: str) -> None:
        """Discover a tool from a JSON/YAML configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if filename.endswith('.json'):
                    config = json.load(f)
                else:  # YAML
                    try:
                        import yaml
                        config = yaml.safe_load(f)
                    except ImportError:
                        self._logger.warning(f"YAML support not available for {filename}")
                        return

            # Expect config to have at least a 'name' field
            if not isinstance(config, dict) or 'name' not in config:
                self._logger.warning(f"Invalid tool config in {filename}: missing name")
                return

            # Create metadata from config
            metadata = self._metadata_from_config(config, filename[:-5])  # Remove extension
            if metadata:
                self._register_tool(metadata, None)  # No module for config-based tools
            else:
                self._logger.warning(f"Failed to create metadata from config in {filename}")

        except Exception as e:
            self._logger.error(f"Failed to load tool config {filename}: {e}")
            self._discovery_errors.append(f"Config load failed: {filename} - {e}")

    def _extract_tool_metadata(self, module: Any, module_name: str) -> Optional[ToolMetadata]:
        """Extract tool metadata from a module."""
        # Look for TOOL_METADATA attribute
        if hasattr(module, 'TOOL_METADATA'):
            metadata_attr = getattr(module, 'TOOL_METADATA')
            if isinstance(metadata_attr, dict):
                return self._metadata_from_dict(metadata_attr, module_name)
            elif isinstance(metadata_attr, ToolMetadata):
                return metadata_attr
            else:
                self._logger.warning(f"TOOL_METADATA in {module_name} is not dict or ToolMetadata")

        # Look for a class that might be a tool
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.endswith('Tool') and hasattr(obj, 'TOOL_METADATA'):
                metadata_attr = getattr(obj, 'TOOL_METADATA')
                if isinstance(metadata_attr, dict):
                    return self._metadata_from_dict(metadata_attr, f"{module_name}.{name}")
                elif isinstance(metadata_attr, ToolMetadata):
                    return metadata_attr

        # Fallback: try to infer from module attributes
        return self._infer_tool_metadata(module, module_name)

    def _metadata_from_dict(self, data: Dict[str, Any], name: str) -> Optional[ToolMetadata]:
        """Create ToolMetadata from a dictionary."""
        try:
            # Handle nested dataclasses or special types
            # We'll do a simple conversion for now
            if 'metadata' in data and isinstance(data['metadata'], dict):
                # Some tools might nest metadata
                data = {**data, **data.pop('metadata')}

            # Convert list fields if they're strings
            for field in ['tags', 'dependencies', 'input_types', 'output_types']:
                if field in data and isinstance(data[field], str):
                    data[field] = [data[field]]

            # Create the metadata object
            metadata = ToolMetadata(name=name, **{
                k: v for k, v in data.items()
                if k in ToolMetadata.__dataclass_fields__
            })
            return metadata
        except Exception as e:
            self._logger.warning(f"Failed to create ToolMetadata from dict in {name}: {e}")
            return None

    def _metadata_from_config(self, config: Dict[str, Any], name: str) -> Optional[ToolMetadata]:
        """Create ToolMetadata from a configuration dictionary."""
        # Map config keys to ToolMetadata fields
        field_mapping = {
            'name': 'name',
            'description': 'description',
            'version': 'version',
            'tags': 'tags',
            'category': 'category',
            'timeout': 'timeout_seconds',
            'timeout_seconds': 'timeout_seconds',
            'max_retries': 'max_retries',
            'priority': 'priority',
            'resource_weight': 'resource_weight',
            'safety_level': 'safety_level',
            'requires_sandbox': 'requires_sandbox',
            'side_effects': 'side_effects',
            'deterministic': 'deterministic',
            'avg_latency': 'avg_latency',
            'success_rate': 'success_rate',
            'dependencies': 'dependencies',
            'environment_vars': 'environment_vars',
            'input_types': 'input_types',
            'output_types': 'output_types',
            'max_input_size': 'max_input_size',
            'supports_async': 'supports_async'
        }

        mapped_data = {}
        for key, value in config.items():
            if key in field_mapping:
                mapped_data[field_mapping[key]] = value
            else:
                # Put unknown keys in config
                if 'config' not in mapped_data:
                    mapped_data['config'] = {}
                mapped_data['config'][key] = value

        # Ensure name is set
        if 'name' not in mapped_data:
            mapped_data['name'] = name

        return self._metadata_from_dict(mapped_data, name)

    def _infer_tool_metadata(self, module: Any, module_name: str) -> Optional[ToolMetadata]:
        """Try to infer tool metadata from module attributes."""
        # This is a basic fallback - in practice, tools should provide explicit metadata
        name = getattr(module, '__tool_name__', module_name)
        description = getattr(module, '__doc__', '').strip() or f"Tool: {name}"

        # Basic heuristics based on module name
        tags = []
        if 'lint' in name.lower() or 'check' in name.lower():
            tags.append('validation')
        if 'fix' in name.lower() or 'repair' in name.lower():
            tags.append('repair')
        if 'analyze' in name.lower() or 'deep' in name.lower():
            tags.append('analysis')
        if 'generate' in name.lower() or 'create' in name.lower():
            tags.append('generation')
        if 'research' in name.lower():
            tags.append('research')
        if 'test' in name.lower():
            tags.append('testing')

        if not tags:
            tags = ['general']

        try:
            return ToolMetadata(
                name=name,
                description=description,
                tags=tags
            )
        except Exception as e:
            self._logger.warning(f"Failed to infer metadata for {module_name}: {e}")
            return None

    def _register_tool(self, metadata: ToolMetadata, module: Optional[Any]) -> None:
        """Register a tool with the registry."""
        with self._lock:
            tool_name = metadata.name

            # Validate based on validation level
            if self._validation_level != "none":
                is_valid, errors = self._validate_tool(metadata)
                if not is_valid:
                    self._logger.warning(
                        f"Tool {tool_name} failed validation: {'; '.join(errors)}"
                    )
                    if self._validation_level == "strict":
                        return  # Don't register invalid tools in strict mode
                    # In basic mode, we log but still register

            # Store the tool
            self._tools[tool_name] = metadata
            if module is not None:
                self._tool_modules[tool_name] = module

            # Update indices
            for tag in metadata.tags:
                self._tag_index[tag].add(tool_name)
            self._category_index[metadata.category].add(tool_name)
            self._safety_index[metadata.safety_level].add(tool_name)

            self._logger.debug(f"Registered tool: {tool_name} ({len(metadata.tags)} tags)")

    def _validate_tool(self, metadata: ToolMetadata) -> Tuple[bool, List[str]]:
        """Validate tool metadata."""
        errors = []

        # Required fields
        if not metadata.name or not isinstance(metadata.name, str):
            errors.append("Tool name must be a non-empty string")
        if not metadata.description or not isinstance(metadata.description, str):
            errors.append("Tool description must be a non-empty string")

        # Validate safety level
        valid_safety = {"low", "medium", "high", "critical"}
        if metadata.safety_level not in valid_safety:
            errors.append(f"Safety level must be one of {valid_safety}")

        # Validate numeric fields
        if metadata.timeout_seconds <= 0:
            errors.append("Timeout must be positive")
        if metadata.max_retries < 0:
            errors.append("Max retries cannot be negative")
        if metadata.priority < 0:
            errors.append("Priority cannot be negative")
        if metadata.resource_weight <= 0:
            errors.append("Resource weight must be positive")
        if not (0.0 <= metadata.success_rate <= 1.0):
            errors.append("Success rate must be between 0.0 and 1.0")
        if metadata.avg_latency < 0:
            errors.append("Average latency cannot be negative")

        # Validate lists
        for field_name in ['tags', 'dependencies', 'input_types', 'output_types']:
            field_value = getattr(metadata, field_name)
            if not isinstance(field_value, list):
                errors.append(f"{field_name} must be a list")
            else:
                for item in field_value:
                    if not isinstance(item, str):
                        errors.append(f"All items in {field_name} must be strings")

        # Validate version format (basic)
        if metadata.version and not isinstance(metadata.version, str):
            errors.append("Version must be a string")

        return len(errors) == 0, errors

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """
        Get metadata for a specific tool.

        Args:
            name: Name of the tool

        Returns:
            ToolMetadata if found, None otherwise
        """
        with self._lock:
            return self._tools.get(name)

    def get_tool_module(self, name: str) -> Optional[Any]:
        """
        Get the loaded module for a tool (if available).

        Args:
            name: Name of the tool

        Returns:
            Loaded module or None
        """
        with self._lock:
            return self._tool_modules.get(name)

    def get_tool_instance(self, name: str) -> Optional[Any]:
        """
        Get or create a singleton instance of a tool.

        Args:
            name: Name of the tool

        Returns:
            Tool instance or None if not available/instantiable
        """
        with self._lock:
            if name in self._tool_instances:
                return self._tool_instances[name]

            module = self._tool_modules.get(name)
            if module is None:
                return None

            # Try to instantiate a known class
            instance = None
            # Look for a class matching the tool name (with Tool suffix)
            class_name = f"{name.capitalize()}Tool"
            if hasattr(module, module, module, class_name):
                cls = getattr(module, class_name)
                try:
                    instance = cls()
                except Exception as e:
                    self._logger.warning(f"Failed to instantiate {class_name}: {e}")
            # Look for a class named exactly like the tool
            elif hasattr(module, name):
                cls = getattr(module, name)
                try:
                    instance = cls()
                except Exception as e:
                    self._logger.warning(f"Failed to instantiate {name}: {e}")
            # Fallback: look for any class that seems like a tool
            else:
                for attr_name in dir(module):
                    if attr_name.endswith('Tool') and not attr_name.startswith('_'):
                        attr = getattr(module, attr_name)
                        if inspect.isclass(attr):
                            try:
                                instance = attr()
                                break
                            except Exception:
                                continue

            if instance is not None:
                self._tool_instances[name] = instance
                return instance
            return None

    def find_tools_by_tag(self, tag: str) -> List[str]:
        """
        Find tools that have a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of tool names with the given tag
        """
        with self._lock:
            return list(self._tag_index.get(tag, set()))

    def find_tools_by_tags(self, tags: List[str], require_all: bool = False) -> List[str]:
        """
        Find tools that match tag criteria.

        Args:
            tags: List of tags to match
            require_all: If True, tool must have ALL tags; if False, tool needs ANY tag

        Returns:
            List of matching tool names
        """
        with self._lock:
            if not tags:
                return list(self._tools.keys())

            if require_all:
                # Intersection of all tag sets
                result_set = None
                for tag in tags:
                    tag_set = self._tag_index.get(tag, set())
                    if result_set is None:
                        result_set = set(tag_set)
                    else:
                        result_set &= tag_set
                return list(result_set) if result_set else []
            else:
                # Union of all tag sets
                result_set = set()
                for tag in tags:
                    result_set.update(self._tag_index.get(tag, set()))
                return list(result_set)

    def find_tools_by_category(self, category: str) -> List[str]:
        """
        Find tools in a specific category.

        Args:
            category: Category to search for

        Returns:
            List of tool names in the category
        """
        with self._lock:
            return list(self._category_index.get(category, set()))

    def find_tools_by_safety(self, safety_level: str) -> List[str]:
        """
        Find tools with a specific safety level.

        Args:
            safety_level: Safety level to filter by (low, medium, high, critical)

        Returns:
            List of tool names with the given safety level
        """
        with self._lock:
            return list(self._safety_index.get(safety_level, set()))

    def get_all_tools(self) -> List[str]:
        """
        Get names of all registered tools.

        Returns:
            List of all tool names
        """
        with self._lock:
            return list(self._tools.keys())

    def get_tool_count(self) -> int:
        """Get the number of registered tools."""
        with self._lock:
            return len(self._tools)

    def get_tools_for_model(self, model_name: str) -> List[str]:
        """
        Get recommended tools for a transcendental model based on predefined mappings.

        Args:
            model_name: Name of transcendental model (Gaṇeśa-model, Sarasvatī-model, Śiva-model)

        Returns:
            List of tool names recommended for the model
        """
        # Map transcendental models to preferred tags/categories
        model_preferences = {
            "Gaṇeśa-model": {
                "tags": ["validation", "fast", "repair", "obstacle-removal"],
                "safety_level": ["high", "critical"],
                "max_timeout": 10.0
            },
            "Sarasvatī-model": {
                "tags": ["analysis", "deep", "research", "synthesis", "wisdom-seeking"],
                "safety_level": ["medium", "high"],
                "min_resource_weight": 1.5
            },
            "Śiva-model": {
                "tags": ["breakthrough", "assumption", "perspective", "deconstruction", "radical"],
                "safety_level": ["low", "medium"],  # Allow exploration but with oversight
                "min_timeout": 30.0
            }
        }

        if model_name not in model_preferences:
            self._logger.warning(f"Unknown model {model_name}, returning all tools")
            return self.get_all_tools()

        prefs = model_preferences[model_name]
        candidates = set(self.get_all_tools())

        # Filter by tags (any match)
        if "tags" in prefs:
            tag_matches = set()
            for tag in prefs["tags"]:
                tag_matches.update(self.find_tools_by_tag(tag))
            candidates &= tag_matches

        # Filter by safety level
        if "safety_level" in prefs:
            safety_matches = set()
            for level in prefs["safety_level"]:
                safety_matches.update(self.find_tools_by_safety(level))
            candidates &= safety_matches

        # Additional filters could be added here (timeout, resource weight, etc.)
        # For simplicity, we'll just return what we have

        result = list(candidates)
        self._logger.debug(f"Model {model_name}: {len(result)} recommended tools")
        return result

    def update_tool_usage(self, tool_name: str, success: bool, latency: float) -> None:
        """
        Update usage statistics for a tool.

        Args:
            tool_name: Name of the tool
            success: Whether the tool execution succeeded
            latency: Latency of the execution in seconds
        """
        if not self._enable_usage_tracking:
            return
        with self._lock:
            if tool_name not in self._tools:
                self._logger.warning(f"Attempted to update unknown tool: {tool_name}")
                return
            metadata = self._tools[tool_name]
            metadata.total_invocations += 1
            metadata.last_used = time.time()
            self._logger.debug(
                f"Updated usage for {tool_name}: count={metadata.total_invocations}"
            )

    def get_tool_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary of statistics or None if tool not found
        """
        with self._lock:
            if tool_name not in self._tools:
                return None
            metadata = self._tools[tool_name]
            return {
                "name": tool_name,
                "total_invocations": metadata.total_invocations,
                "success_rate": metadata.success_rate,
                "avg_latency": metadata.avg_latency,
                "last_used": metadata.last_used,
                "tags": list(metadata.tags),
                "safety_level": metadata.safety_level
            }

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get overall registry statistics.

        Returns:
            Dictionary with registry-wide statistics
        """
        with self._lock:
            total_tools = len(self._tools)
            if total_tools == 0:
                return {"total_tools": 0}

            # Calculate averages
            total_invocations = sum(t.total_invocations for t in self._tools.values())
            avg_success_rate = (
                sum(t.success_rate for t in self._tools.values()) / total_tools
                if total_tools > 0 else 0.0
            )
            avg_latency = (
                sum(t.avg_latency for t in self._tools.values()) / total_tools
                if total_tools > 0 else 0.0
            )

            # Safety level distribution
            safety_dist = defaultdict(int)
            for t in self._tools.values():
                safety_dist[t.safety_level] += 1

            # Category distribution
            category_dist = defaultdict(int)
            for t in self._tools.values():  # Fixed: was self._tokens.values()
                category_dist[t.category] += 1

            # Tag frequency
            tag_freq = defaultdict(int)
            for t in self._tools.values():
                for tag in t.tags:
                    tag_freq[tag] += 1

            return {
                "total_tools": total_tools,
                "total_invocations": total_invocations,
                "average_success_rate": avg_success_rate,
                "average_latency": avg_latency,
                "safety_distribution": dict(safety_dist),
                "category_distribution": dict(category_dist),
                "top_tags": dict(sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]),
                "last_discovery": self._last_discovery_time,
                "discovery_errors": len(self._discovery_errors)
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the tool registry.

        Returns:
            Dictionary with health status and any issues
        """
        issues = []
        status = "healthy"

        # Check tool directories
        for directory in self._tool_directories:
            if not os.path.isdir(directory):
                issues.append(f"Tool directory does not exist: {directory}")
                status = "degraded"

        # Check for discovery errors
        if self._discovery_errors:
            issues.append(f"{len(self._discovery_errors)} discovery errors")
            if status == "healthy":
                status = "degraded"

        # Check that we have some tools
        if len(self._tools) == 0:
            issues.append("No tools discovered")
            status = "unhealthy"

        # Validate a sample of tools
        sample_size = min(10, len(self._tools))
        invalid_tools = 0
        for name, metadata in list(self._tools.items())[:sample_size]:
            is_valid, errors = self._validate_tool(metadata)
            if not is_valid:
                invalid_tools += 1
                if invalid_tools <= 3:  # Log first few errors
                    issues.append(f"Invalid tool {name}: {'; '.join(errors[:2])}")

        if invalid_tools > 0:
            issues.append(f"{invalid_tools} invalid tools in sample of {sample_size}")
            if status == "healthy":
                status = "degraded"

        return {
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": self.get_registry_stats()
        }

    def reset(self) -> None:
        """Reset the registry to initial state (primarily for testing)."""
        with self._lock:
            self._tools.clear()
            self._tool_modules.clear()
            self._tool_instances.clear()
            self._tag_index.clear()
            self._category_index.clear()
            self._safety_index.clear()
            self._discovery_errors.clear()
            self._last_discovery_time = 0.0
            self._logger.info("Tool registry reset")


# =======================
# Module-Level Singleton
# =======================

# Global registry instance for easy access throughout the codebase
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get or create the global ToolRegistry instance (singleton pattern).

    Returns:
        The singleton ToolRegistry instance.
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_tool(name: str) -> Optional[ToolMetadata]:
    """
    Convenience function to get tool metadata from global registry.

    Args:
        name: Name of the tool

    Returns:
        ToolMetadata if found, None otherwise
    """
    return get_tool_registry().get_tool(name)


def get_tool_module(name: str) -> Optional[Any]:
    """
    Convenience function to get tool module from global registry.

    Args:
        name: Name of the tool

    Returns:
        Loaded module or None
    """
    return get_tool_registry().get_tool_module(name)


def get_tool_instance(name: str) -> Optional[Any]:
    """
    Convenience function to get tool instance from global registry.

    Args:
        name: Name of the tool

    Returns:
        Tool instance or None
    """
    return get_tool_registry().get_tool_instance(name)


def find_tools_by_tag(tag: str) -> List[str]:
    """
    Convenience function to find tools by tag from global registry.

    Args:
        tag: Tag to search for

    Returns:
        List of tool names with the given tag
    """
    return get_tool_registry().find_tools_by_tag(tag)


def find_tools_by_tags(tags: List[str], require_all: bool = False) -> List[str]:
    """
    Convenience function to find tools by tags from global registry.

    Args:
        tags: List of tags to match
        require_all: If True, tool must have ALL tags; if False, needs ANY tag

    Returns:
        List of matching tool names
    """
    return get_tool_registry().find_tools_by_tags(tags, require_all)


def get_all_tools() -> List[str]:
    """
    Convenience function to get all tools from global registry.

    Returns:
        List of all tool names
    """
    return get_tool_registry().get_all_tools()


def get_tools_for_model(model_name: str) -> List[str]:
    """
    Convenience function to get tools for a transcendental model.

    Args:
        model_name: Name of transcendental model

    Returns:
        List of tool names recommended for the model
    """
    return get_tool_registry().get_tools_for_model(model_name)


def update_tool_usage(tool_name: str, success: bool, latency: float) -> None:
    """
    Convenience function to update tool usage statistics.

    Args:
        tool_name: Name of the tool
        success: Whether the tool execution succeeded
        latency: Latency of the execution in seconds
    """
    get_tool_registry().update_tool_usage(tool_name, success, latency)


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
    print("Tool Registry Demo / Self-Test")
    print("=" * 70)

    # Create registry with faster discovery for demo
    registry = ToolRegistry(
        tool_directories=[os.path.join(os.path.dirname(__file__), "tools")],
        enable_auto_discovery=True,
        enable_usage_tracking=True,
        validation_level="basic"
    )

    print(f"\nInitial state: {registry.get_tool_count()} tools discovered")

    # Show discovered tools
    all_tools = registry.get_all_tools()
    if all_tools:
        print(f"\nDiscovered tools ({len(all_tools)}):")
        for tool in sorted(all_tools)[:10]:  # Show first 10
            metadata = registry.get_tool(tool)
            if metadata:
                print(f"  - {tool}: {metadata.description[:50]}... "
                      f"(safety: {metadata.safety_level}, tags: {', '.join(metadata.tags[:3])})")
        if len(all_tools) > 10:
            print(f"  ... and {len(all_tools) - 10} more")
    else:
        print("\nNo tools discovered (this is expected in a fresh environment)")

    # Demonstrate manual tool registration for testing
    print("\n--- Registering Test Tools ---")
    test_tool_metadata = ToolMetadata(
        name="test_syntax_checker",
        description="A test syntax checker for demonstration",
        tags=["validation", "fast", "obstacle-removal"],
        category="validation",
        timeout_seconds=2.0,
        max_retries=1,
        priority=1,
        resource_weight=0.5,
        safety_level="high",
        requires_sandbox=False,
        side_effects=False,
        deterministic=True
    )
    registry._register_tool(test_tool_metadata, None)  # No module for this test tool

    test_tool2_metadata = ToolMetadata(
        name="test_deep_analyzer",
        description="A test deep analyzer for demonstration",
        tags=["analysis", "deep", "wisdom-seeking"],
        category="analysis",
        timeout_seconds=30.0,
        max_retries=3,
        priority=2,
        resource_weight=2.0,
        safety_level="medium",
        requires_sandbox=True,
        side_effects=False,
        deterministic=False
    )
    registry._register_tool(test_tool2_metadata, None)

    print(f"After manual registration: {registry.get_tool_count()} tools")

    # Demonstrate querying
    print("\n--- Querying Tools ---")
    validation_tools = registry.find_tools_by_tag("validation")
    print(f"Tools with 'validation' tag: {validation_tools}")

    analysis_tools = registry.find_tools_by_tag("analysis")
    print(f"Tools with 'analysis' tag: {analysis_tools}")

    high_safety_tools = registry.find_tools_by_safety("high")
    print(f"Tools with 'high' safety: {high_safety_tools}")

    # Demonstrate model-based tool selection
    print("\n--- Model-Based Tool Selection ---")
    for model in ["Gaṇeśa-model", "Sarasvatī-model", "Śiva-model"]:
        tools = registry.get_tools_for_model(model)
        print(f"{model}: {len(tools)} recommended tools")
        if tools:
            print(f"  Sample: {', '.join(tools[:5])}{'...' if len(tools) > 5 else ''}")

    # Demonstrate usage tracking
    print("\n--- Usage Tracking ---")
    registry.update_tool_usage("test_syntax_checker", True, 0.15)
    registry.update_tool_usage("test_syntax_checker", True, 0.12)
    registry.update_tool_usage("test_syntax_checker", False, 0.20)  # Simulate failure
    registry.update_tool_usage("test_deep_analyzer", True, 2.5)
    registry.update_tool_usage("test_deep_analyzer", True, 3.0)

    stats1 = registry.get_tool_stats("test_syntax_checker")
    stats2 = registry.get_tool_stats("test_deep_analyzer")
    if stats1:
        print(f"test_syntax_checker: {stats1['total_invocations']} calls, "
              f"{stats1['success_rate']*100:.1f}% success, "
              f"{stats1['avg_latency']:.3f}s avg latency")
    if stats2:
        print(f"test_deep_analyzer: {stats2['total_invocations']} calls, "
              f"{stats2['success_rate']*100:.1f}% success, "
              f"{stats2['avg_latency']:.3f}s avg latency")

    # Demonstrate registry statistics
    print("\n--- Registry Statistics ---")
    stats = registry.get_registry_stats()
    for key, value in stats.items():
        if isinstance(value, dict) and len(str(value)) > 100:
            print(f"{key:25}: {type(value).__name__} with {len(value)} items")
        else:
            print(f"{key:25}: {value}")

    # Demonstrate health check
    print("\n--- Health Check ---")
    health = registry.health_check()
    print(f"Status: {health['status']}")
    if health['issues']:
        print("Issues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("No issues detected.")

    # Test reset functionality
    print("\n--- Testing Reset ---")
    print(f"Before reset: {registry.get_tool_count()} tools")
    registry.reset()
    print(f"After reset: {registry.get_tool_count()} tools")

    print("\n" + "=" * 70)
    print("Demo completed.")
    print("=" * 70)