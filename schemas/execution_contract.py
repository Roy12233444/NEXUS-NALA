"""
Execution Contract Schema for NALA Adaptive Contract Protocol (ACP)
===================================================================

Defines the core Pydantic v2 data models for the Adaptive Contract Protocol (ACP)
and Runtime Constitution Layer (RCL). These schemas enable the dynamic evolution
of the execution contract $C_t = (P_t, R_t, B_t)$ based on runtime observations
$O_t$: $C_{t+1} = f(C_t, O_t)$.

This module provides:
- Standardized data contracts between ACP/RCL components
- Validation and serialization for execution contracts
- Behavior snapshots for risk estimation
- Change events for execution ledger and deterministic replay
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


# ======================
# Enumerations
# ======================

class ContractStatus(str, Enum):
    """Lifecycle states of an execution contract."""
    ACTIVE = "ACTIVE"          # Normal execution, permissions evolving normally
    RESTRICTED = "RESTRICTED"  # Risk thresholds exceeded, permissions reduced
    EVALUATING = "EVALUATING"  # Policy evaluation in progress
    PAUSED = "PAUSED"          # Execution halted awaiting manual intervention
    TERMINATED = "TERMINATED"  # Execution completed or forcefully stopped


class RiskLevel(str, Enum):
    """Risk severity levels for alerting and policy triggers."""
    LOW = "LOW"        # 0.0 - 0.3: Normal operation
    MODERATE = "MODERATE" # 0.3 - 0.6: Increased monitoring
    HIGH = "HIGH"      # 0.6 - 0.8: Restricted permissions
    CRITICAL = "CRITICAL" # 0.8 - 1.0: Pause execution, require approval


# ======================
# Core Models
# ======================

class PermissionSet(BaseModel):
    """Dynamic permissions governing tool and resource access."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Tool-level permissions
    allowed_tools: List[str] = Field(
        default_factory=list,
        description="Explicitly permitted tool names (empty list = deny all)",
        examples=[["file_read", "web_search", "calculator"]]
    )
    blocked_tools: List[str] = Field(
        default_factory=list,
        description="Explicitly forbidden tool names (takes precedence over allowed)",
        examples=[["file_write", "system_shell", "network_raw"]]
    )

    # File system permissions
    file_read_allowlist: List[str] = Field(
        default_factory=list,
        description="Glob patterns for permitted read paths",
        examples=[["/tmp/*", "/user/data/*.txt"]]
    )
    file_write_allowlist: List[str] = Field(
        default_factory=list,
        description="Glob patterns for permitted write paths",
        examples=[["/tmp/output/*"]]
    )

    # Network permissions
    network_domain_allowlist: List[str] = Field(
        default_factory=list,
        description="Permitted domains for outbound connections",
        examples=[["api.example.com", "*.github.com"]]
    )

    # Process permissions
    allow_subprocess_spawn: bool = Field(
        default=False,
        description="Whether spawning child processes is permitted"
    )
    allow_code_execution: bool = Field(
        default=False,
        description="Whether arbitrary code execution (eval, exec, etc.) is permitted"
    )

    @field_validator('blocked_tools')
    @classmethod
    def validate_blocked_superset(cls, v: List[str], info) -> List[str]:
        """Ensure blocked tools don't conflict with allowed tools."""
        allowed = info.data.get('allowed_tools', [])
        conflicts = set(v) & set(allowed)
        if conflicts:
            raise ValueError(f"Tools cannot be both allowed and blocked: {conflicts}")
        return v


class ResourceBudget(BaseModel):
    """Dynamic resource allocation limits that scale with risk."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    max_memory_mb: int = Field(
        default=16384,  # 16GB
        ge=256,
        le=131072,  # 128GB max
        description="Maximum memory allocation in megabytes"
    )
    max_cpu_percent: float = Field(
        default=80.0,
        ge=10.0,
        le=100.0,
        description="Maximum CPU utilization percentage"
    )
    max_execution_time_sec: int = Field(
        default=3600,  # 1 hour
        ge=30,
        le=86400,  # 24 hours max
        description="Maximum wall-clock execution time in seconds"
    )
    max_step_time_sec: int = Field(
        default=30,  # 30 seconds per step
        ge=5,
        le=300,  # 5 minutes max per step
        description="Maximum time allowed for a single tool execution step"
    )
    token_budget: int = Field(
        default=100000,
        ge=1000,
        le=1000000,
        description="Maximum LLM token consumption for planning/reasoning"
    )
    tool_call_budget: int = Field(
        default=1000,
        ge=10,
        le=10000,
        description="Maximum number of tool invocations allowed"
    )
    retry_budget: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Maximum total retries allowed across all tool executions"
    )
    disk_io_mb_per_sec: float = Field(
        default=100.0,
        ge=1.0,
        le=1000.0,
        description="Maximum disk I/O throughput in MB/s"
    )
    network_bandwidth_mbps: float = Field(
        default=100.0,
        ge=1.0,
        le=1000.0,
        description="Maximum network bandwidth in Mbps"
    )


class BehavioralConstraints(BaseModel):
    """Dynamic constraints governing agent behavior and cognition."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    max_planning_depth: int = Field(
        default=10,
        ge=0,
        le=20,
        description="Maximum depth of recursive planning/reasoning chains"
    )
    strictness_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        default="HIGH",
        description="Behavioral constraint strictness (maps to Viveka-Clarity threshold)"
    )
    require_step_approval: bool = Field(
        default=False,
        description="Whether each tool execution requires explicit human approval"
    )
    enforce_deterministic_seed: bool = Field(
        default=True,
        description="Whether to enforce deterministic random seeds for replay fidelity"
    )
    max_concurrent_tools: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum number of tools that can execute simultaneously"
    )
    max_step_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries per failed tool execution before marking as failed"
    )
    allowed_modalities: List[Literal["text", "code", "data", "image", "audio"]] = Field(
        default=["text", "code", "data"],
        description="Permitted interaction/modalities for tool inputs/outputs"
    )
    max_tool_chain_length: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum length of sequential tool executions without planner intervention"
    )
    policy_violation_threshold: int = Field(
        default=3,
        ge=0,
        description="Number of policy violations before triggering contract restriction"
    )


class BehaviorSnapshot(BaseModel):
    """Immutable telemetry sample captured at point-in-time for risk analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        frozen=True  # Make immutable for safety
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when snapshot was captured"
    )

    # Planner metrics
    planner_depth: int = Field(
        ge=0,
        description="Current depth of recursive planning stack"
    )
    planner_branching_factor: float = Field(
        ge=0.0,
        description="Average number of planning branches explored per step"
    )
    planner_time_ms: float = Field(
        ge=0.0,
        description="Time spent in planning phase (milliseconds)"
    )

    # Tool execution metrics
    tool_calls_count: int = Field(
        ge=0,
        description="Number of tool invocations in this measurement window"
    )
    tool_success_count: int = Field(
        ge=0,
        description="Number of successful tool executions"
    )
    tool_retry_count: int = Field(
        ge=0,
        description="Number of tool executions that required retries"
    )
    tool_latency_ms: float = Field(
        ge=0.0,
        description="Average tool execution latency (milliseconds)"
    )
    anomalous_tool_requests: List[str] = Field(
        default_factory=list,
        description="Tool requests that violated current permission set"
    )
    blocked_tool_attempts: List[str] = Field(
        default_factory=list,
        description="Attempts to use explicitly blocked tools"
    )

    # Resource metrics
    memory_usage_mb: float = Field(
        ge=0.0,
        description="Current memory consumption in megabytes"
    )
    memory_growth_mb: float = Field(
        description="Memory delta since previous snapshot (can be negative)"
    )
    cpu_percent: float = Field(
        ge=0.0,
        le=100.0,
        description="Current CPU utilization percentage"
    )
    disk_io_mb: float = Field(
        ge=0.0,
        description="Disk I/O consumed since last snapshot (MB)"
    )
    network_mb: float = Field(
        ge=0.0,
        description="Network data transferred since last snapshot (MB)"
    )

    # Safety and policy metrics
    policy_violations: int = Field(
        ge=0,
        description="Count of Satya/Viveka policy violations detected"
    )
    safety_layer_triggers: Dict[str, int] = Field(
        default_factory=dict,
        description="Triggers from each safety layer (e.g., {'viveka_gate': 2, 'satya_layer': 1})"
    )
    rta_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Current Ṛta-Score from RTA feedback loop (epistemic fitness)"
    )
    viveka_clarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Current Viveka-Clarity metric (internal coherence)"
    )
    satya_truthfulness: float = Field(
        ge=0.0,
        le=1.0,
        description="Current Satya-Truthfulness score (factual consistency)"
    )

    # Behavioral anomaly indicators
    planning_oscillation: bool = Field(
        default=False,
        description="Detected oscillation in planning depth (possible loop)"
    )
    tool_choice_entropy: float = Field(
        ge=0.0,
        le=1.0,
        description="Shannon entropy of tool selection distribution (0=deterministic, 1=random)"
    )
    repetition_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Measure of repetitive tool/argument patterns (potential stuck state)"
    )


class ExecutionContract(BaseModel):
    """The dynamic execution contract that evolves as $C_{t+1} = f(C_t, O_t)$."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    # Identity and versioning
    contract_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this contract instance (ULID recommended)"
    )
    goal_id: str = Field(
        description="Identifier of the user goal this contract serves"
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Monotonically increasing version number for this contract lineage"
    )
    parent_contract_id: Optional[str] = Field(
        default=None,
        description="ID of parent contract if this is a derivative (for fork/merge tracking)"
    )

    # Core components (the $C_t = (P_t, R_t, B_t)$ tuple)
    permissions: PermissionSet = Field(
        default_factory=PermissionSet,
        description="Current tool and resource permissions"
    )
    resource_budget: ResourceBudget = Field(
        default_factory=ResourceBudget,
        description="Current resource allocation limits"
    )
    constraints: BehavioralConstraints = Field(
        default_factory=BehavioralConstraints,
        description="Current behavioral and cognitive constraints"
    )

    # Risk and confidence metrics
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite risk score (0.0=safe, 1.0=critical risk)"
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Discrete risk level derived from risk_score for alerting"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in current risk assessment (0.0=untrusted, 1.0=certain)"
    )
    risk_factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual risk factor contributions (e.g., {'behavioral': 0.3, 'resource': 0.1})"
    )

    # State and metadata
    status: ContractStatus = Field(
        default=ContractStatus.ACTIVE,
        description="Current lifecycle state of the contract"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when contract was last modified"
    )
    updated_by: Literal["behavior_monitor", "risk_estimator", "policy_evaluator", "manual"] = Field(
        default="behavior_monitor",
        description="Component responsible for last contract update"
    )
    update_reason: str = Field(
        default="initial_creation",
        description="Reason for last contract change (for audit trail)"
    )

    # Audit and provenance
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when contract was initially created"
    )
    created_by: Literal["planner", "manual", "handoff", "recovery"] = Field(
        default="planner",
        description="Entity that created the initial contract"
    )
    tags: Set[str] = Field(
        default_factory=set,
        description="User-defined tags for contract categorization and filtering"
    )

    # Computed properties (not stored)
    @computed_field
    @property
    def is_active(self) -> bool:
        """Whether contract is currently active and permitting execution."""
        return self.status in (ContractStatus.ACTIVE, ContractStatus.EVALUATING)

    @computed_field
    @property
    def is_restricted(self) -> bool:
        """Whether contract has entered restricted mode due to risk."""
        return self.status == ContractStatus.RESTRICTED

    @computed_field
    @property
    def requires_human_intervention(self) -> bool:
        """Whether contract requires manual approval to proceed."""
        return self.status in (ContractStatus.PAUSED, ContractStatus.TERMINATED) or \
               (self.risk_score >= 0.8 and self.confidence > 0.7)

    @field_validator('blocked_tools', mode='after', check_fields=False)
    @classmethod
    def _validate_blocked_tools(cls, v: List[str], info) -> List[str]:
        """Ensure blocked tools don't conflict with allowed tools (redundant with PermissionSet validator but safe)."""
        # This is handled in PermissionSet, but we keep for completeness
        return v

    @model_validator(mode='after')
    def _validate_risk_confidence_consistency(self) -> 'ExecutionContract':
        """Warn when high risk is reported with low confidence (logged elsewhere)."""
        # In a real implementation, we would log a warning here
        # For now, we just return the object unchanged
        if self.risk_score > 0.7 and self.confidence < 0.4:
            pass  # Would log warning: "High risk score with low confidence"
        return self

    def to_ledger_entry(self) -> Dict[str, Any]:
        """Convert ExecutionContract to flat dictionary for storage inary for storage in = {
        "contract_id": self.contract_id in execution ledger."""
        data = self.model_dump()
        # Convert datetime objects to ISO strings for JSON serialization
        if isinstance(data.get("last_updated"), datetime):
            data["last_updated"] = data["last_updated"].isoformat()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        # Convert set to list for JSON serialization
        if isinstance(data.get("tags"), set):
            data["tags"] = list(data["tags"])
        return data

    @classmethod
    def from_ledger_entry(cls, data: Dict[str, Any]) -> 'ExecutionContract':
        """Reconstruct ExecutionContract from ledger entry."""
        # Convert ISO strings back to datetime objects
        if isinstance(data.get("last_updated"), str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        # Convert list back to set for tags
        if isinstance(data.get("tags"), list):
            data["tags"] = set(data["tags"])
        return cls(**data)


class ContractChangeEvent(BaseModel):
    """Immutable record of a contract modification for execution ledger."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        frozen=True  # Make immutable for ledger integrity
    )

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this change event (ULID recommended)"
    )
    contract_id: str = Field(
        description="ID of the contract that was modified"
    )
    previous_version: int = Field(
        ge=1,
        description="Contract version number before this change"
    )
    new_version: int = Field(
        ge=1,
        description="Contract version number after this change"
    )
    trigger_reason: str = Field(
        description="What triggered this change (e.g., 'high_risk_score', 'policy_violation')"
    )
    risk_score_before: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk score prior to this change"
    )
    risk_score_after: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk score after this change"
    )
    confidence_before: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence prior to this change"
    )
    confidence_after: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence after this change"
    )

    # Detailed permission changes
    permissions_added: List[str] = Field(
        default_factory=list,
        description="Tool names newly permitted in this change"
    )
    permissions_revoked: List[str] = Field(
        default_factory=list,
        description="Tool names newly forbidden in this change"
    )
    file_read_added: List[str] = Field(
        default_factory=list,
        description="File read paths newly permitted"
    )
    file_read_revoked: List[str] = Field(
        default_factory=list,
        description="File read paths newly forbidden"
    )
    file_write_added: List[str] = Field(
        default_factory=list,
        description="File write paths newly permitted"
    )
    file_write_revoked: List[str] = Field(
        default_factory=list,
        description="File write paths newly forbidden"
    )

    # Resource budget deltas
    memory_mb_delta: int = Field(
        default=0,
        description="Change in max_memory_mb (positive=increase, negative=decrease)"
    )
    cpu_percent_delta: float = Field(
        default=0.0,
        description="Change in max_cpu_percent"
    )
    execution_time_sec_delta: int = Field(
        default=0,
        description="Change in max_execution_time_sec"
    )
    token_budget_delta: int = Field(
        default=0,
        description="Change in token_budget"
    )

    # Behavioral constraints changes
    planning_depth_delta: int = Field(
        default=0,
        description="Change in max_planning_depth"
    )
    strictness_level_changed: bool = Field(
        default=False,
        description="Whether strictness_level was modified"
    )
    step_approval_changed: bool = Field(
        default=False,
        description="Whether require_step_approval was modified"
    )

    # Audit fields
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this change event was recorded"
    )
    recorded_by: Literal["contract_engine", "manual", "system"] = Field(
        default="contract_engine",
        description="Component that recorded this change"
    )
    update_latency_ms: float = Field(
        ge=0.0,
        description="Time taken to compute and apply this change (milliseconds)"
    )

    # Provenance
    triggering_snapshot_id: Optional[str] = Field(
        default=None,
        description="ID of BehaviorSnapshot that triggered this change (if applicable)"
    )
    policy_rules_violated: List[str] = Field(
        default_factory=list,
        description="Specific policy rules that were violated (if policy trigger)"
    )


# ======================
# Helper Functions
# ======================

def calculate_risk_factors(snapshot: BehaviorSnapshot) -> Dict[str, float]:
    """Helper function to compute risk factor breakdown from behavior snapshot."""
    factors = {}

    # Behavioral risk factors
    if snapshot.planner_depth > 10:
        factors["planning_depth"] = min(1.0, (snapshot.planner_depth - 10) / 10)
    if snapshot.tool_calls_count > 0:
        retry_ratio = snapshot.tool_retry_count / snapshot.tool_calls_count
        if retry_ratio > 0.3:
            factors["high_retry_rate"] = min(1.0, retry_ratio / 0.3)  # Cap at 1.0 when ratio >= 0.3*3.33
    if snapshot.anomalous_tool_requests:
        factors["anomalous_requests"] = min(1.0, len(snapshot.anomalous_tool_requests) / 5)
    if snapshot.policy_violations > 0:
        factors["policy_violations"] = min(1.0, snapshot.policy_violations / 3)

    # Resource risk factors (assuming 16GB baseline)
    memory_usage_ratio = snapshot.memory_usage_mb / 16384
    if memory_usage_ratio > 0.7:
        factors["high_memory_usage"] = min(1.0, (memory_usage_ratio - 0.7) / 0.3)
    if snapshot.cpu_percent > 80:
        factors["high_cpu_usage"] = min(1.0, (snapshot.cpu_percent - 80) / 20)

    # Safety layer factors (inverse because lower score = higher risk)
    factors["low_rta_score"] = 1.0 - snapshot.rta_score
    factors["low_viveka_clarity"] = 1.0 - snapshot.viveka_clarity
    factors["low_satya_truthfulness"] = 1.0 - snapshot.satya_truthfulness

    # Behavioral anomaly factors
    factors["tool_choice_entropy"] = snapshot.tool_choice_entropy
    factors["repetition_score"] = snapshot.repetition_score
    if snapshot.planning_oscillation:
        factors["planning_oscillation"] = 1.0

    return factors


# ======================
# Module-Level Constants
# ======================

# Default risk factor weights for combine_risk_factors function
DEFAULT_RISK_FACTOR_WEIGHTS = {
    "planning_depth": 0.15,
    "high_retry_rate": 0.2,
    "anomalous_requests": 0.15,
    "policy_violations": 0.15,
    "high_memory_usage": 0.1,
    "high_cpu_usage": 0.1,
    "low_rta_score": 0.05,
    "low_viveka_clarity": 0.05,
    "low_satya_truthfulness": 0.05,
    "tool_choice_entropy": 0.025,
    "repetition_score": 0.025,
    "planning_oscillation": 0.0
}

def combine_risk_factors(factors: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    """Combine individual risk factors into a single risk score using weighted average."""
    if weights is None:
        weights = DEFAULT_RISK_FACTOR_WEIGHTS

    total_weight = 0.0
    weighted_sum = 0.0

    for factor, value in factors.items():
        weight = weights.get(factor, 0.0)
        weighted_sum += value * weight
        total_weight += weight

    # Avoid division by zero
    if total_weight == 0:
        return 0.0

    # Normalize to [0, 1] range
    raw_score = weighted_sum / total_weight
    return min(1.0, max(0.0, raw_score))


__all__ = [
    "ContractStatus",
    "RiskLevel",
    "PermissionSet",
    "ResourceBudget",
    "BehavioralConstraints",
    "BehaviorSnapshot",
    "ExecutionContract",
    "ContractChangeEvent",
    "calculate_risk_factors",
    "combine_risk_factors"
]