# 📋 Advanced Plan: Execution Contract Schema for NALA ACP/RCL
**Target File:** `schemas/execution_contract.py`  
**Related Ticket:** NLA-ACP-013  
**Phase:** 1 of 5 (Core Schemas & Data Models)  
**Status:** Ready for Implementation  
**Created:** 2026-07-23  

---

## 🎯 Objective
Define the foundational Pydantic v2 data models that enable the Adaptive Contract Protocol (ACP) to dynamically evolve the execution contract $C_t = (P_t, R_t, B_t)$ based on runtime observations $O_t$. This schema layer transforms NALA from static governance to dynamic, risk-adaptive execution governance by providing standardized, validated data contracts between all ACP/RCL components.

---

## 🔗 Dependencies & Integration Points
| Component | Dependency Type | Integration Point |
|-----------|----------------|-------------------|
| `core/hands/agama_tool_selector.py` | Input | Provides baseline dharmic tool classifications & weights for initial PermissionSet |
| `core/hands/model_router.py` | Input | Supplies transcendental model state for behavioral constraint initialization |
| `core/safety/rta_feedback_loop.py` | Input | Feeds Ṛta-Score into risk estimation algorithms |
| `core/safety/adaptive_viveka_gate.py` | Input | Contributes Viveka-Clarity metrics to risk scoring |
| `core/safety/context_aware_satya_layer.py` | Input | Provides Satya-Truthfulness validation for policy evaluation |
| `core/harness/nala_loop.py` | Output | Consumes ExecutionContract for pre/post-step permission checks |
| `core/harness/session_contract.py` | Output | Stores ExecutionContract + ContractChangeEvent history for persistence |
| `core/harness/checkpoint.py` | Output | Serializes/deserializes contract state for deterministic replay |
| Future ACP/RCL modules | Output | BehaviorMonitor, RiskEstimator, PolicyEvaluator, PermissionManager, ContractEngine all depend on these schemas |

---

## 📐 Detailed Schema Specification

### 1. Enumerations
```python
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
```

### 2. Core Models

#### PermissionSet
```python
class PermissionSet(BaseModel):
    """Dynamic permissions governing tool and resource access."""
    
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
        description="Whether arbitrary code execution (eval, including permissions('import', 'exec', 'eval'): # nose
    model constraints
        validationdepthretries": 3,  # Maximum planning recursion depth
    "strictness_level": "HIGH",  # CRITICAL, HIGH, MEDIUM, LOW - maps to Viveka gate sensitivity
    "require_step_approval": False,  # Require manual approval for each tool call (Satya enforcement)
    "enforce_deterministic_seed": True,  # Force deterministic execution for replay fidelity
    "max_concurrent_tools": 2,  # Maximum simultaneous tool executions
    "allowed_modalities": ["text", "code", "data"],  # Permitted interaction modes
}
)
class BehavioralConstraints(BaseModel):
    """Dynamic constraints governing agent behavior and cognition."""
    
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
```

#### ResourceBudget
```python 
class ResourceBudget(BaseModel):
    """Dynamic resource allocation limits that scale with risk."""
    
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
```

#### BehaviorSnapshot
```python
class BehaviorSnapshot(BaseModel):
    """Immutable telemetry sample captured at point-in-time for risk analysis."""
    
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
        description="Current Satya-Truthfulness score ( factual consistency)"
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
```

#### ExecutionContract
```python
class ExecutionContract(BaseModel):
    """The dynamic execution contract that evolves as $C_{t+1} = f(C_t, O_t)$."""
    
    # Identity and versioning
    contract_id: str = Field(
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
    @computed_field  # Pydantic v2 decorator
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
```

#### ContractChangeEvent
```python
class ContractChangeEvent(BaseModel):
    """Immutable record of a contract modification for execution ledger."""
    
    event_id: str = Field(
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
    )
    policy_rules_violated: List[str] = Field(
        default_factory=list,
        description="Specific policy rules that were violated (if policy trigger)"
    )
```

### 3. Validation Rules and Constraints
```python
# Model-level validators
@field_validator('blocked_tools')
@classmethod
def validate_blocked_superset(cls, v, info):
    """Ensure blocked tools don't conflict with allowed tools."""
    allowed = info.data.get('allowed_tools', [])
    conflicts = set(v) & set(allowed)
    if conflicts:
        raise ValueError(f"Tools cannot be both allowed and blocked: {conflicts}")
    return v

@field_validator('risk_score')
@classmethod
def validate_risk_confidence_consistency(cls, v, info):
    """Warn when high risk is reported with low confidence."""
    confidence = info.data.get('confidence', 1.0)
    if v > 0.7 and confidence < 0.4:
        # Warning only - don't fail validation
        pass  # In practice, log warning
    return v

@model_validator(mode='after')
def validate_resource_limits(self):
    """Ensure resource limits are reasonable for current constraints."""
    if self.constraints.max_planning_depth > 15 and self.resource_budget.max_cpu_percent < 50:
        # Warning: high planning depth with low CPU may cause timeouts
        pass
    return self
```

### 4. Serialization and Utility Methods
```python
def to_ledger_entry(self) -> Dict[str, Any]:
    """Convert ExecutionContract to flat dictionary for storage in execution ledger."""
    return {
        "contract_id": self.contract_id,
        "goal_id": self.goal_id,
        "version": self.version,
        "status": self.status.value,
        "risk_score": self.risk_score,
        "confidence": self.confidence,
        "last_updated": self.last_updated.isoformat(),
        "permissions": self.permissions.model_dump(),
        "resource_budget": self.resource_budget.model_dump(),
        "constraints": self.constraints.model_dump(),
        "tags": list(self.tags)
    }

@classmethod
def from_ledger_entry(cls, data: Dict[str, Any]) -> 'ExecutionContract':
    """Reconstruct ExecutionContract from ledger entry."""
    # Convert ISO strings back to datetime objects
    if isinstance(data.get("last_updated"), str):
        data["last_updated"] = datetime.fromisoformat(data["last_updated"])
    if isinstance(data.get("created_at"), str):
        data["created_at"] = datetime.fromisoformat(data["created_at"])
    
    return cls(**data)

def calculate_risk_factors(snapshot: BehaviorSnapshot) -> Dict[str, float]:
    """Helper function to compute risk factor breakdown from behavior snapshot."""
    factors = {}
    
    # Behavioral risk factors
    if snapshot.planner_depth > 10:
        factors["planning_depth"] = min(1.0, (snapshot.planner_depth - 10) / 10)
    if snapshot.tool_retry_count > snapshot.tool_calls_count * 0.3:
        factors["high_retry_rate"] = min(1.0, snapshot.tool_retry_count / max(1, snapshot.tool_calls_count))
    if snapshot.anomalous_tool_requests:
        factors["anomalous_requests"] = min(1.0, len(snapshot.anomalous_tool_requests) / 5)
    if snapshot.policy_violations > 0:
        factors["policy_violations"] = min(1.0, snapshot.policy_violations / 3)
    
    # Resource risk factors
    memory_usage_ratio = snapshot.memory_usage_mb / 16384  # Assuming 16GB baseline
    if memory_usage_ratio > 0.7:
        factors["high_memory_usage"] = min(1.0, (memory_usage_ratio - 0.7) / 0.3)
    if snapshot.cpu_percent > 80:
        factors["high_cpu_usage"] = min(1.0, (snapshot.cpu_percent - 80) / 20)
    
    # Safety layer factors
    factors["low_rta_score"] = 1.0 - snapshot.rta_score
    factors["low_viveka_clarity"] = 1.0 - snapshot.viveka_clarity
    factors["low_satya_truthfulness"] = 1.0 - snapshot.satya_truthfulness
    
    # Behavioral anomaly factors
    factors["tool_choice_entropy"] = snapshot.tool_choice_entropy
    factors["repetition_score"] = snapshot.repetition_score
    if snapshot.planning_oscillation:
        factors["planning_oscillation"] = 1.0
    
    return factors
```

---

## ⚙️ Implementation Considerations

### 1. Pydantic v2 Features to Leverage
- **`@field_validator`** and **`@model_validator`** for complex validation logic
- **`@computed_field`** for derived properties (is_active, is_restricted, requires_human_intervention)
- **`model_dump()`** and **`model_validate()`** for serialization/deserialization
- **Field constraints** (`ge`, `le`, `gt`, `lt`) for boundary validation
- **Literal types** for discrete enumerations (strictness_level, risk_level)
- **Set and List types** with default factories for mutable fields
- **Description and examples** for automatic documentation generation

### 2. Performance Optimizations
- Use **`frozen=True`** on BehaviorSnapshot and ContractChangeEvent for immutability (reduces copying overhead)
- Implement **`__slots__`** equivalence via Pydantic config for memory efficiency
- Pre-compile regex patterns for file path validation if needed (though using simple glob matching currently)
- Consider **`orm_mode=False`** since we're not using ORMs

### 3. Error Handling and Validation
- Validation errors should be **logged but not fatal** during runtime (system should degrade gracefully)
- Provide **meaningful error messages** for debugging configuration issues
- Implement **validation recovery strategies** (e.g., auto-correct obvious validation errors where safe)
- Distinguish between **user configuration errors** (should fail fast) vs **runtime telemetry anomalies** (should be handled gracefully)

### 4. Backwards Compatibility and Versioning
- Schema versions should be tracked via `ExecutionContract.version` field
- Migration strategies needed for contract history when schemas evolve
- Consider adding `schema_version: str = "1.0"` field to all models for explicit versioning
- Deprecation warnings for fields that will be removed in future versions

### 5. Security Considerations
- Ensure **no sensitive data** is logged via model __repr__ or __str__ methods
- Validate that **allowlists cannot be bypassed** through path traversal or other injection
- Consider **encryption at rest** for contract history in ledger (handled at persistence layer)
- Ensure **immutability** of BehaviorSnapshot and ContractChangeEvent to prevent tampering

### 6. Testing Strategy
- **Unit tests** for each model's validation logic
- **Property-based testing** using Hypothesis for edge cases
- **Serialization/deserialization round-trip tests**
- **Integration tests** with mocked ACP/RCL components
- **Performance benchmarks** for model instantiation (should be <1ms)
- **Contract evolution simulation** tests verifying $C_{t+1} = f(C_t, O_t)$ behavior

---

## 📈 Integration Roadmap with Existing NALA

### Immediate Integration (After this schema is implemented)
1. **Update `core/hands/agama_tool_selector.py`** to:
   - Export dharmic classifications as initial PermissionSet weights
   - Add method to convert dharmic weights to tool allow/block lists

2. **Enhance `core/hands/model_router.py`** to:
   - Provide transcendental state as input to initial BehavioralConstraints
   - Export model confidence for use in ExecutionContract.confidence initialization

3. **Extend `core/harness/session_contract.py`** to:
   ```python
   class SessionState(BaseModel):
       # Existing fields...
       active_contract: ExecutionContract
       contract_history: List[ContractChangeEvent] = Field(default_factory=list)
       schema_version: str = "1.0"
   ```

4. **Prepare `core/harness/checkpoint.py`** for:
   - Serializing/deserializing ExecutionContract + history
   - Verifying schema compatibility during restore

### Future Integration (Phases 2-5)
- **Behavior Monitor** will populate BehaviorSnapshot from nala_loop telemetry
- **Risk Estimator** will use calculate_risk_factors() and update ExecutionContract.risk_score
- **Policy Evaluator** will validate proposed ExecutionContract changes
- **Permission Manager** will apply PermissionSet to sandbox/tool registry
- **Contract Engine** will implement $C_{t+1} = f(C_t, O_t)$ using all above components

---

## ✅ Acceptance Criteria
1. **Schema Validity**: All models instantiate correctly with default values
2. **Serialization**: model_dump() → model_validate() round-trip preserves all data
3. **Validation**: Invalid inputs are properly rejected with meaningful messages
4. **Integration Ready**: Fields align with data expected by planned ACP/RCL components
5. **Performance**: Model instantiation < 1ms on typical hardware
6. **Documentation**: All fields have clear descriptions and examples
7. **Extensibility**: Design allows for future fields without breaking changes
8. **Type Safety**: Full mypy compliance with no ignored errors

---

## 📁 File Location
```
E:\NALA-Project\NALA\schemas\
└── execution_contract.py
```

**Note:** The `schemas/` directory must be created before implementing this file.

---

## 🔄 Relationship to NALA's Transcendent Dual-Mode Framework
This schema layer **complements rather than replaces** the existing transcendental architecture:

| Transcendental Layer | ACP/RCL Schema Layer | Integration Point |
|----------------------|----------------------|-------------------|
| Gaṇeśa-model (obstacle-removing) | Baseline PermissionSet for low-risk states | Initial permissions when Ṛta < 0.60 |
| Sarasvatī-model (wisdom-seeking) | Standard BehavioralConstraints for moderate risk | Default constraints when 0.60 ≤ Ṛta ≤ 0.95 |
| Śiva-model (destroyer-of-illusion) | Restricted PermissionSet + tight constraints for high risk | Applied when Ṛta > 0.95 or risk_score > 0.6 |
| Ṛta-Score | Direct input to risk_factors and risk_score calculation | Used by Risk Estimator |
| Viveka-Clarity | Component of behavioral risk factors | Used in calculate_risk_factors() |
| Satya-Truthfulness | Component of behavioral risk factors | Used in calculate_risk_factors() |
| Tool Registry | Source of allowed/blocked tool names | PermissionSet.allowed_tools/.blocked_tools |
| Model Router | Source of transcendental model recommendations | Initial BehavioralConstraints priors |

The ACP/RCL schema layer provides the **dynamic governance substrate** that allows the transcendental framework to evolve from static model-based decisions to continuous, observation-driven adaptation—essential for long-running autonomous agents operating in uncertain environments.

---
*This plan establishes the critical foundation for transforming NALA from a statically-governed research prototype into a dynamically-adaptive production-capable autonomous agent runtime. All subsequent ACP/RCL implementation phases depend on these data contracts being defined, validated, and integrated first.*