# NALA Server Implementation Plan
## Addressing Current Limitations and Next Steps

### Overview
This document outlines the plan to complete the nala_server.py Socket.IO server implementation to fully bridge the React UI with NALA's Python backend as requested. The current implementation has several limitations that need to be addressed to achieve full functionality.

### Current Limitations to deliver real-time updates from NALA's reasoning loop to the UI.

---

## Limitation 1: Execution Phase Simulation
**Issue**: The execution phase currently simulates tool use rather than calling actual sandbox.py for tool execution.

**Solution**:
1. Replace the `execute_cognitive_cycle` simulation with actual tool execution flow:
   - UI prompt → Socket.IO server → NalaLoop step handler → SandboxManager.execute_in_sandbox()
   - Implement proper tool selection via ToolRegistry based on task requirements
   - Execute tools within appropriate sandbox security levels (NONE/BASIC/RESTRICTED/ISOLATED)
   - Capture tool execution results, stdout/stderr, and side effects

2. Implementation steps:
   - Modify `custom_step_handler` in `process_nala_session` to:
     - For "execution_phase" steps: 
       a. Determine required tools from planner output or task requirements
       b. Select appropriate sandbox level based on tool risk assessment
       c. Execute tools via `sandbox_manager.execute_in_sandbox(tool_call, context)`
       d. Capture execution results, logs, and side effects
       e. Return structured results to NalaLoop step handler
   - Integrate with existing ToolRegistry for tool discovery and selection
   - Implement proper error handling for sandbox violations and execution failures

---

## Limitation 2: Variable Name Fixes
**Issue**: Variable name `caste_breaker` should be `circuit_breaker`.

**Solution**:
1. Search and replace all instances of `caste_breaker` with `circuit_breaker`
2. Specifically fix in:
   - `process_nala_session()` function where components are initialized
   - `execute_cognitive_cycle()` function parameter list
   - `perform_safety_checks()` function call
3. Verify no other similar typos exist in the codebase

---

## Limitation 3: Checkpoint Manager Initialization Syntax Error
**Issue**: Incomplete line in checkpoint manager initialization (`checkpoint` without assignment).

**Solution**:
1. Locate the incomplete line in `create_session()` method:
   ```python
   # Create checkpoint manager
   checkpoint_dir = f"./sessions/{session_id}"
   os.makedirs(checkpoint_dir, exist_ok=True)
   checkpoint_manager = CheckpointManager(base_dir=checkpoint_dir)
   
   checkpoint  # <-- THIS LINE IS INCOMPLETE
   ```
2. Fix by either:
   - Removing the incomplete line (if it was accidental)
   - Or completing the assignment if it was intended to be:
     ```python
     checkpoint = checkpoint_manager  # or similar
     ```
3. Based on code context, the line appears to be accidental - it should be removed as `checkpoint_manager` is already properly assigned on the previous line

---

## Limitation 4: Missing Tool Execution Flow
**Issue**: Need to implement actual tool execution flow from UI → server → sandbox → nala_loop.

**Solution**:
1. **UI → Server Layer** (already partially implemented):
   - `submit_prompt` Socket.IO handler creates session and starts processing
   - Ensure proper session ID mapping to client socket rooms

2. **Server → NALA Loop Layer**:
   - Enhance `custom_step_handler` to interface with actual NalaLoop
   - Instead of simulating execution, call:
     ```python
     # In execution_phase step handler:
     tool_result = nala_loop.execute_step_with_tools(step, session_state)
     ```
   - Implement `execute_step_with_tools` method in NalaLoop wrapper or extend existing loop

3. **NALALoop → Sandbox Layer**:
   - Modify NalaLoop step execution to use SandboxManager for tool calls
   - Implement tool selection logic based on:
     - Task requirements from planner
     - Safety assessments from Viveka/RTA systems
     - Resource requirements
   - Execute tools via `sandbox_manager.execute_in_sandbox(tool_spec, execution_context)`
   - Capture and return:
     - Tool execution results (stdout/stderr)
     - Side effects (file changes, network calls, etc.)
     - Sandbox violation reports
     - Execution timing and resource usage

4. **Sandbox → Server Telemetry Layer**:
   - Implement real-time telemetry capture during sandbox execution:
     - CPU/Memory usage via sandbox monitoring hooks
     - System call tracing (via audit hooks/seccomp)
     - File system access logs
     - Network activity monitoring
   - Stream telemetry data back to server for UI consumption

---

## Next Steps: Real-Time Telemetry Streaming Implementation

### 1. Pramāṇa Activation Status Streaming
**Implementation**:
- Integrate with NALA's cognitive systems (Planner, Saptacore Council, etc.) to detect active Pramāṇas
- Map cognitive processes to Pramāṇa types:
  - Pratibha (Intuition) → Intuitive insights generation
  - Anumana (Inference) -> Logical deduction processes
  - Upamana (Comparison) -> Analogical reasoning
  - Arthapatti (Postulation) -> Presumptive reasoning
  - Anupalabdhi (Non-apprehension) -> Negative evidence handling
  - Shabda (Testimony) -> External knowledge/input processing
- Emit `pramana-active` and `pramana-reasoning-clear` events with:
  - Active Pramāṇa list
  - Confidence levels
  - Reasoning clarity metrics

### 2. Ṛta-Score Changes Streaming
**Implementation**:
- Integrate with RTA Validator and RTAGuard components
- Track Ṛta-score (cosmic order/righteousness measure) changes during reasoning
- Emit `rita-score-update` events with:
  - Current Ṛta-score value (0-1 scale)
  - Delta change since last update
  - Contributing factors (truthfulness, consistency, ethical alignment)
  - Historical trend data (for `rta-score-history` event)

### 3. CPU/Memory Metrics Streaming
**Implementation**:
- Enhance SandboxManager to capture resource usage:
  - CPU utilization percentage
  - Memory consumption (RSS/VMS)
  - Disk I/O operations
  - Network bandwidth usage
- Use sandbox monitoring hooks (audit hooks, job objects, namespace stats)
- Emit periodic resource metrics via:
  - Custom resource events or integrate with existing telemetry
  - Map to websocketService.ts expectations for system metrics

### 4. Safety System Evaluations (Viveka/Satya)
**Implementation**:
- **Viveka Gate** (Discrimination/Validation):
  - Integrate with viveka_discriminate logic and related systems
  - Track discrimination accuracy, bias detection, assumption validation
  - Emit `viveka-strictness`, `viveka-adaptive-learning`, `viveka-confidence-calibration` events
  - Include `viveka-transition-outcome` for decision validation results
  
- **Satya Layer** (Truthfulness/Consistency):
  - Integrate with Satya truthfulness checking systems
  - Track factual consistency, logical coherence, evidence alignment
  - Emit `satya-scores`, `satya-latency`, `satya-truthfulness-level` events
  - Include overall health metrics in `safety-metrics-update`

### 5. Tool Usage and Predictions Streaming
**Implementation**:
- Integrate with ToolRegistry and ModelRouter for tool predictions
- Track:
  - Tool prediction confidence scores
  - Tool warm-up/cooldown states
  - Actual tool usage frequency and success rates
  - Tool execution timing and resource usage
- Emit events matching websocketService.ts expectations:
  - `tool-predictions`: Upcoming tool suggestions with confidence
  - `tool-warmed`: Tools prepared for imminent use
  - `tool-cooled`: Tools recently used, cooling down
  - `tool-ready`: Tools available for immediate use
  - `tool-usage-update`: Actual tool execution statistics

---

## Event Mapping Alignment with websocketService.ts
**Requirement**: Ensure all emitted events match the exact event names and data structures expected by `src/services/websocketService.ts`.

**Events to Implement** (based on websocketService.ts listeners):
1. Connection/status events:
   - `connection_status` → `{status: 'connected'|'disconnected'}`

2. Session management:
   - `session_created` → `{session_id: string, message: string}`
   - `joined_room` / `left_room` → `{session_id: string}`
   - `session_status` → `{session_id: string, status: string, timestamp: string}`
   - `session_complete` → `{session_id: string, status: string, timestamp: string}`
   - `session_error` → `{session_id: string, error: string, timestamp: string}`

3. Step execution events:
   - `step_update` → Matches NalaLoop step events with:
     - `type`: 'step_start'|'step_complete'|'step_error'
     - `step_id`: string
     - `description`: string (for start)
     - `result`: object (for complete)
     - `error`: string (for error)
     - `execution_time`: number
     - `timestamp`: ISO string

4. Safety and metrics events (matching websocketService.ts exactly):
   - `safety-metrics-update` → `{viveka: object, satya: object, overallHealth: number}`
   - `rita-score-update` → `{score: number, delta: number, factors: array}`
   - `viveka-strictness` → `{level: number, confidence: number}`
   - `viveka-adaptive-learning` → `{rate: number, adaptation: object}`
   - `viveka-confidence-calibration` → `{calibration: number, reliability: number}`
   - `viveka-transition-outcome` → `{valid: boolean, confidence: number, reasoning: string}`
   - `satya-scores` → `{truthfulness: number, consistency: number, coherence: number}`
   - `satya-latency` → `{processingTime: number, validationTime: number}`
   - `satya-truthfulness-level` → `{level: string, confidence: number}`

5. Tool system events:
   - `tool-predictions` → `{predictions: Array<{tool: string, confidence: number, reasoning: string}>}` 
   - `tool-warmed` → `{tools: Array<string>}`
   - `tool-cooled` → `{tools: Array<string>}`
   - `tool-ready` → `{tools: Array<string>}`
   - `tool-usage-update` → `{usage: Array<{tool: string, count: number, successRate: number, avgTime: number}>}`

6. Transcendent and Pramāṇa events:
   - `pramana-active` → `{activePramanas: Array<string>, confidence: Map<string, number>}`
   - `pramana-reasoning-clear` → `{clarityScore: number, obstacles: Array<string>}`
   - `rta-score-history` → `{scores: Array<{timestamp: string, score: number}>}`

7. Transcendent layer events (from observability systems):
   - `transcendent-awareness` → `{level: float, trend: string}`
   - `transcendent-coherence` → `{score: float, stability: float}`
   - `transcendent-insight-depth` → `{depth: float, novelty: float}`
   - `transcendent-pattern-recognition` → `{patterns: Array<string>, confidence: float}`

8. Heartbeat for connection health:
   - `heartbeat` → `{timestamp: ISO string}`

9. Error handling:
   - `error` → `{message: string}`

---

## Implementation Phases

### Phase 1: Foundation Fixes (Immediate)
- [ ] Fix variable name: `caste_breaker` → `circuit_breaker`
- [ ] Fix checkpoint manager initialization syntax error
- [ ] Validate basic Socket.IO connection and session creation flow
- [ ] Ensure basic event streaming works (heartbeat, session events)

### Phase 2: Tool Execution Integration (Short-term)
- [ ] Implement actual sandbox-based tool execution in execution_phase
- [ ] Connect NalaLoop step handler to SandboxManager
- [ ] Implement tool selection logic based on task requirements
- [ ] Capture and return tool execution results properly
- [ ] Add error handling for sandbox violations and execution failures

### Phase 3: Telemetry Streaming Implementation (Mid-term)
- [ ] Implement Pramāṇa activation tracking and streaming
- [ ] Implement Ṛta-score tracking and history streaming
- [ ] Implement CPU/memory metrics collection from sandbox
- [ ] Implement Viveka gate metrics streaming
- [ ] Implement Satya layer metrics streaming
- [ ] Implement tool usage and predictions streaming

### Phase 4: Event Mapping Validation (Final)
- [ ] Verify all emitted events match websocketService.ts expectations exactly
- [ ] Test event data structures and timing
- [ ] Validate real-time update flow from UI → server → sandbox → NALA → UI
- [ ] Performance testing for low-latency telemetry streaming

### Phase 5: Integration Testing
- [ ] End-to-end testing with React UI websocketService.ts
- [ ] Validate all expected UI updates receive correct data
- [ ] Test error scenarios and recovery
- [ ] Benchmark performance under load

---

## Success Criteria
1. UI receives real-time updates for all specified metrics and events
2. Tool execution flows correctly: UI prompt → server → sandbox → NALA → results → UI
3. All safety systems (Viveka/Satya) provide continuous feedback to UI
4. Transcendent metrics (Pramāṇa, Ṛta-score) update in real-time during reasoning
5. Resource usage (CPU/memory) monitoring visible in UI
6. Tool prediction and usage statistics accurately reflect actual execution
7. Event names and data structures match websocketService.ts exactly
8. System handles errors gracefully with appropriate error events to UI
9. Performance maintains <100ms latency for critical telemetry updates
10. Memory usage remains stable during extended sessions

---

## Files to Modify
Primary file: `E:\NALA-Project\NALA\nala_server.py`

Potential supporting modifications (if needed):
- `core/hands/sandbox.py` - Enhanced monitoring hooks
- `core/harness/nala_loop.py` - Better step execution instrumentation
- `core/observability/logger.py` - Structured logging for telemetry
- `core/observability/metrics.py` - Metrics collection enhancements

Note: Prefer to implement telemetry gathering within nala_server.py where possible to avoid modifying core NALA components unless absolutely necessary.

---

## Risks and Mitigations
1. **Performance overhead from telemetry collection**
   - Mitigation: Implement sampling, batch non-critical metrics, use efficient data structures

2. **Complexity of integrating with existing NALA components**
   - Mitigation: Use existing extension points (hooks, callbacks) rather than modifying core logic

3. **Event flooding overwhelming WebSocket connection**
   - Mitigation: Implement rate limiting, delta-only updates, client-side buffering

4. **Sandbox security restrictions blocking necessary monitoring
Igate appropriately configured for monitoring (audit hooks are designed
 I'll create this plan file.