# NALA Server Fix Implementation Plan
## Phased Approach to Complete websocketService.ts Integration

### Overview
This plan outlines the phased implementation needed to complete the nala_server.py Socket.IO server to fully integrate with the React UI's websocketService.ts expectations. Each phase builds upon the previous one, focusing on critical telemetry and integration points.

### Current Status
Foundational fixes completed:
- ✅ Checkpoint manager initialization syntax error fixed
- ✅ Variable name correction: `caste_breaker` → `circuit_breaker`
- ✅ Basic Socket.IO connection and session management implemented
- ✅ Event streaming infrastructure in place (heartbeat, session events)
- ✅ Framework for tool execution via sandbox established

---

## Phase 1: Telemetry Event Infrastructure (Immediate Priority)
**Goal**: Establish reliable emission of all telemetry events matching websocketService.ts exactly

### Tasks:
1. **Pramāṇa Event System**
   - Implement `update_pramana_state()` to track active Pramāṇas per session
   - Create `emit_pramana_events()` function to send:
     - `pramana-active`: `{activePramanas: string[], confidence: Map<string, number>}`
     - `pramana-reasoning-clear`: `{clarityScore: number, obstacles: string[]}`

2. **Ṛta-Score Tracking System**
   - Implement `update_rita_score()` to maintain score history per session
   - Create `emit_rita_events()` function to send:
     - `rta-score-update`: `{score: number, delta: number, factors: string[]}`
     - `rta-score-history`: `{scores: [{timestamp: string, score: number}]}`

3. **Safety Metrics System**
   - Implement `update_safety_metrics()` to track Viveka and Satya systems
   - Create `emit_safety_events()` function to send:
     - `safety-metrics-update`: `{viveka: {...}, satya: {...}, overallHealth: number}`
     - Individual events: `viveka-strictness`, `viveka-adaptive-learning`, etc.
     - Individual events: `satya-scores`, `satya-latency`, `satya-truthfulness-level`

4. **Tool System Tracking**
   - Implement `update_tool_predictions()`, `update_tool_usage()` functions
   - Create `emit_tool_events()` function to send:
     - `tool-predictions`: `{predictions: [{tool: string, confidence: number, reasoning: string}]}`
     - `tool-warmed`: `{tools: string[]}`
     - `tool-cooled`: `{tools: string[]}`
     - `tool-ready`: `{tools: string[]}`
     - `tool-usage-update`: `{usage: [{tool: string, count: number, successRate: number, avgTime: number}]}`

5. **Transcendent Metrics System**
   - Implement tracking for awareness, coherence, insight depth, pattern recognition
   - Create `emit_transcendent_events()` function to send:
     - `transcendent-awareness`: `{level: float, trend: string}`
     - `transcendent-coherence`: `{score: float, stability: float}`
     - `transcendent-insight-depth`: `{depth: float, novelty: float}`
     - `transcendent-pattern-recognition`: `{patterns: string[], confidence: float}`

### Success Criteria:
- All events emit with exact naming and structure matching websocketService.ts
- Events fire at appropriate points in NALA lifecycle (planning, execution, reflection)
- No duplicate or missing events
- Event data accurately reflects NALA's internal state

---

## Phase 2: Actual Tool Execution Integration (High Priority)
**Goal**: Replace simulated tool execution with real sandbox-based tool invocation

### Tasks:
1. **Tool Registry Integration**
   - Modify `execute_tools_via_sandbox()` to properly retrieve tool instances from `ToolRegistry.get_tool_instance()`
   - Handle both module-based tools and instance-based tools correctly
   - Implement proper error handling for missing/unavailable tools

2. **Sandbox Execution Enhancement**
   - Ensure tools execute with appropriate safety levels based on ToolMetadata
   - Capture and return actual tool results (not simulations)
   - Implement proper timeout handling using sandbox resource limits
   - Capture stdout/stderr from tool execution for telemetry

3. **Tool Requirement Determination**
   - Enhance `determine_tool_requirements()` to use actual planner analysis
   - Base tool selection on:
     - Planner's identified task type
     - Required safety level from tool metadata
     - Available tools in registry matching the need
   - Implement fallback to general assistant when no specific match

4. **Tool Usage Statistics**
   - Integrate with ToolRegistry's usage tracking automatically:
   - Update tool usage statistics (success/failure, latency) post-execution
   - Ensure statistics feed into tool prediction system
   - Implement tool warming/cooling logic based on usage patterns

### Success Criteria:
- Tools execute in actual sandboxes (not simulations)
- Tool results are accurate and usable by NALA's reasoning systems
- Safety levels correctly applied to tool execution
- Tool usage statistics accurately tracked and reflected in telemetry
- Fallback mechanisms work when specific tools unavailable

---

## Phase 3: Safety System Enhancement (Medium Priority)
**Goal**: Replace simplified safety checks with actual NALA safety system integration

### Tasks:
1. **Viveka Integration**
   - Replace `viveka_discriminate()` with actual Viveka gate logic
   - Implement proper discrimination scoring, bias detection, assumption validation
   - Connect to viveka_discriminate function from core systems (if available)
   - Emit detailed viveka events with discriminatory factors

2. **Satya Layer Integration**
   - Replace `perform_safety_checks()` with actual Satya truthfulness validation
   - Implement fact-checking, logical consistency verification, coherence scoring
   - Connect to usha and rta_validator systems where applicable
   - Emit detailed satya scores with truthfulness, consistency, coherence metrics

3. **RTA Guard Integration**
   - Implement actual RTAGuard and RTAValidator checks
   - Track Ṛta-score based on cosmic order/righteousness measures
   - Provide detailed breakdown of Ṛta-score contributing factors
   - Implement proper safety approval/rejection logic

4. **Circuit Breaker Utilization**
   - Properly integrate CircuitBreaker for fault tolerance
   - Track circuit state (closed/open/half-open) per service/tool type
   - Emit circuit breaker status in safety metrics when relevant

### Success Criteria:
- Safety systems provide meaningful, accurate assessments
- Safety decisions properly influence tool execution approval
- Detailed safety metrics available for UI consumption
- Fallback to safe defaults when safety systems unavailable
- No false positives/negatives in safety assessments

---

## Phase 4: Resource Monitoring & System Metrics (Medium Priority)
**Goal**: Implement actual CPU/memory/disk/network monitoring during execution

### Tasks:
1. **Resource Tracking System**
   - Implement `update_resource_usage()` to capture:
     - CPU usage percentage (per core and total)
     - Memory consumption (RSS/VMS in MB)
     - Disk I/O (read/write MB/s)
     - Network activity (sent/received KB/s)
   - Use psutil or similar for cross-platform monitoring
   - Sample at appropriate intervals during tool execution

2. **Resource Event Emission**
   - Create `emit_resource_events()` function to send:
     - Custom resource events or integrate with existing telemetry
     - Format to be determined based on websocketService.ts expectations
     - Consider efficiency - batch or delta-only updates when possible

3. **Sandbox Resource Integration**
   - Enhance SandboxManager to provide resource usage data
   - Hook into existing sandbox monitoring mechanisms (audit hooks, job objects, etc.)
   - Ensure resource limits are properly enforced and reported

4. **Performance Optimization**
   - Implement efficient data collection to minimize overhead
   - Consider sampling strategies for high-frequency metrics
   - Ensure monitoring doesn't significantly impact execution performance

### Success Criteria:
- Accurate, real-time resource usage data available
- Resource monitoring adds minimal overhead (<5% performance impact)
- Data correctly attributed to specific tool executions/sessions
- Resource limits properly enforced and violations reported
- Information presented in UI-usable format

---

## Phase 5: Validation, Testing & Refinement (Ongoing)
**Goal**: Ensure complete compatibility with websocketService.ts and robust operation

### Tasks:
1. **Event Structure Validation**
   - Create validation tests for each event type against websocketService.ts expectations
   - Verify exact field names, types, and nesting structures
   - Test edge cases (null values, empty arrays, boundary conditions)

2. **Timing & Frequency Testing**
   - Ensure events fire at appropriate moments in NALA lifecycle
   - Prevent event flooding (implement debouncing/throttling where needed)
   - Verify critical events (errors, completion) are not delayed

3. **Integration Testing**
   - Test end-to-end flow: UI prompt → server → sandbox → tool execution → telemetry → UI update
   - Verify error handling propagates correctly to UI
   - Test session isolation (multiple concurrent users don't interfere)

4. **Performance Benchmarking**
   - Measure latency from tool completion to UI update
   - Ensure real-time feel (<100ms for critical updates)
   - Test under load (multiple concurrent sessions)

5. **Documentation & Comments**
   - Add clear comments explaining telemetry systems
   - Document event structures and emission conditions
   - Create troubleshooting guide for common issues

### Success Criteria:
- 100% event structure compliance with websocketService.ts
- Reliable end-to-end operation under various conditions
- Acceptable performance characteristics
- Clear maintenance and extension pathways
- Comprehensive error handling and recovery

---

## Dependencies & Prerequisites
1. **Completed Foundation Work**: Socket.IO connection, session management, basic event streaming
2. **Available NALA Components**: ToolRegistry, SandboxManager, NalaLoop (with working checkpoint/telemetry)
3. **Development Environment**: Python 3.8+, required NALA dependencies installed
4. **UI Compatibility**: websocketService.ts expectations clearly defined and stable

## Risk Mitigation
- **Telemetry Overhead**: Implement efficient data structures, consider sampling for high-frequency metrics
- **Integration Complexity**: Use adapter patterns to isolate NALA core changes
- **Backward Compatibility**: Maintain fallback simulation modes during development
- **Testing Coverage**: Create unit tests for each telemetry component before integration

## Success Metrics
1. All required by UI are emitted with correct structure and timing
2 Tool execution works reliably in sandboxes with proper safety levels
3 Safety systems provide meaningful, accurate assessments
4 Resource monitoring provides useful operational insights
5 System maintains <100ms latency for critical telemetry updates
6 Zero regressions in existing NALA core functionality

## Next Immediate Action
Begin Phase 1 implementation by adding the telemetry tracking infrastructure to nala_server.py, starting with Pramāṇa and Ṛta-Score systems since they form the foundation for other telemetry.