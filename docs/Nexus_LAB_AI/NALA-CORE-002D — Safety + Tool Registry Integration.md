# 🔥 NALA-CORE-002D — Safety + Tool Registry Integration

## Executive Summary

**NALA-CORE-002D** establishes the authoritative safety and capability enforcement spine of the NALA cognitive architecture. Prior to 002D, the runtime executed tools and file operations via ad-hoc regex handling and bypassed the central `ToolRegistry` and `AdaptiveVivekaGate`.

With 002D completed, all tool invocations are strictly routed through:
$$\text{User Goal} \longrightarrow \text{Planner} \longrightarrow \text{TaskGraph} \longrightarrow \text{ToolRegistry (Resolve)} \longrightarrow \text{ToolRequest} \longrightarrow \text{AdaptiveVivekaGate (Pre-flight Inspection)} \longrightarrow \begin{cases} \text{ALLOW} \implies \text{Sandbox Execution} \implies \text{Disk Readback / SHA-256} \\ \text{DENY} \implies \text{Execution Halted} \implies \text{Zero Filesystem Modification} \end{cases}$$

---

## 1. Architectural Components Implemented

### 1.1 Authoritative Tool Registry (`core/hands/tool_registry.py`)
- **Built-in Canonical Tools Registered on Startup**:
  - `file_writer`: Verified workspace file creation with hash integrity. (Safety: `medium`, side effects: `True`, requires sandbox: `True`).
  - `file_reader`: Readback and SHA-256 checksum empirical validation. (Safety: `low`, side effects: `False`).
  - `code_generator`: Algorithmic synthesis and program drafting. (Safety: `low`, side effects: `False`).
  - `security_auditor`: Vulnerability scanning and invariant auditing. (Safety: `low`, side effects: `False`).
  - `memory_tool`: Persistent long-term memory query and capture. (Safety: `low`, side effects: `True`).
  - `system_command`: Command line execution in sandboxed isolation. (Safety: `critical`, side effects: `True`, requires sandbox: `True`).
- **Canonical `ToolRequest` Dataclass**: Standard payload encapsulating `tool_name`, `action`, `arguments`, `session_id`, `task_id`, `provenance`, `requested_capabilities`.
- **Public API**: `register_tool()`, `resolve_tool(intent_or_action)`, `update_tool_usage()`, `get_tool()`.

### 1.2 Adaptive Viveka Gate (`core/safety/adaptive_viveka_gate.py`)
- **Tri-State Decision Enum (`VivekaDecision`)**:
  - `ALLOW`: Permitted within workspace bounds.
  - `APPROVAL_REQUIRED`: Privileged commands requiring explicit human approval.
  - `DENY`: Strictly prohibited hostile actions (path traversal, system deletion, fork bombs).
- **`VivekaEvaluationResult`**: Detailed evaluation record including policy identifier, risk level (`low`, `medium`, `high`, `critical`), justification reason, and timestamp.
- **Deterministic Policy Enforcement Rules**:
  - `WORKSPACE_BOUNDARY_ENFORCEMENT`: Intercepts and blocks path traversal attempts (`../..`, escaping workspace, accessing Windows/system paths, SSH keys, AWS credentials).
  - `SYSTEM_INTEGRITY_PROTECTION`: Intercepts destructive commands (`rm -rf /`, `rmdir /s /q c:\`, `format c:`, fork bombs, unauthorized reboot/shutdown).
  - `CORE_SUBSYSTEM_IMMUTABILITY`: Protects foundational engine code (`core/`, `nala_server.py`, `src/store/`) from unauthorized deletion or mutation.
  - `PRIVILEGED_ACTION_GOVERNANCE`: Traps privileged commands (`sudo`, `runas`, `chmod 777`).

### 1.3 Live Runtime Integration (`nala_server.py`)
- Connected `execute_tools_via_sandbox` and `custom_step_handler` directly to `ToolRegistry` and `AdaptiveVivekaGate`.
- **Physics Invariant Enforced**:
  - If Viveka evaluates `DENY`: Execution is halted immediately. `SandboxManager` is **NEVER** initialized, tools are **NEVER** executed, and the filesystem is **NEVER** modified.
  - Telemetry and step result clearly reflect the safety rejection banner with policy and risk metrics.
  - If Viveka evaluates `ALLOW`: Sandboxed execution executes the operation, updates tool usage metrics, and physically verifies the artifact on disk.

---

## 2. Test Verification Matrix

56 automated unit and integration tests passing:

```bash
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.0.3, pluggy-1.6.0
collecting ... collected 56 items

tests/unit/test_tool_registry.py::TestToolRegistry::test_builtin_tools_registered PASSED [  1%]
tests/unit/test_tool_registry.py::TestToolRegistry::test_custom_tool_registration PASSED [  3%]
tests/unit/test_tool_registry.py::TestToolRegistry::test_resolve_tool_by_intent_and_keywords PASSED [  5%]
tests/unit/test_tool_registry.py::TestToolRegistry::test_tool_request_dataclass PASSED [  7%]
tests/unit/test_tool_registry.py::TestToolRegistry::test_usage_tracking PASSED [  8%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_safe_workspace_operation_allowed PASSED [ 10%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_path_traversal_denied PASSED [ 12%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_destructive_command_denied PASSED [ 14%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_core_system_file_deletion_denied PASSED [ 16%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_privileged_command_requires_approval PASSED [ 17%]
tests/unit/test_adaptive_viveka_gate.py::TestAdaptiveVivekaGate::test_evaluation_determinism PASSED [ 19%]
tests/integration/test_safety_tool_registry_runtime.py::test_safe_task_tool_resolution_and_viveka_allow PASSED [ 21%]
tests/integration/test_safety_tool_registry_runtime.py::test_hostile_task_strictly_denied_with_zero_filesystem_modification PASSED [ 23%]
tests/integration/test_safety_tool_registry_runtime.py::test_hostile_destructive_command_blocked PASSED [ 25%]
tests/unit/test_planner.py (9 tests) PASSED
tests/unit/test_memory_service.py (7 tests) PASSED
tests/unit/test_pramana_router.py (17 tests) PASSED
tests/integration/test_dynamic_planner_runtime.py (3 tests) PASSED
tests/integration/test_memory_runtime_lifecycle.py (3 tests) PASSED
tests/integration/test_pramana_runtime_integration.py (3 tests) PASSED

============================= 56 passed in 2.26s ==============================
```

---

## 3. Empirical Live Browser Verification

### 3.1 Task 1: Safe Tool Execution (`ALLOW`)
- **Directive**: `Create a safe file named nala_002d_safe.txt containing: NALA 002D Safe Tool Execution Verified`
- **Tool Resolved**: `file_writer` (`ToolRegistry`)
- **Viveka Decision**: `ALLOW` (`STANDARD_WORKSPACE_EXECUTION`, Risk: `low`)
- **Physical Verification**: File created in `demo_files/nala_002d_safe.txt` (161 bytes), SHA-256 matched, readback confirmed.

### 3.2 Task 2: Hostile Tool Rejection (`DENY`)
- **Directive**: `Create file ../../windows/system32/exploit_002d.txt containing: evil_payload`
- **Tool Resolved**: `file_writer` (`ToolRegistry`)
- **Viveka Decision**: `DENY` (`WORKSPACE_BOUNDARY_ENFORCEMENT`, Risk: `critical`)
- **Safety Interception Banner**: Displayed `PROHIBITED ACTION DENIED & HALTED`.
- **Physical Verification**: Zero filesystem mutation. `exploit_002d.txt` was never written.
