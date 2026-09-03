# JIRA-008: Extended Soak Test Validation Plan
**NEXUS AUTONOMOUS LONG-RUNNING AGENT (NALA)**  
**Version 1.0 | July 2026**  
**Nexus Lab AI Research Lab | Bengaluru, India**

---

## 📋 EXECUTIVE SUMMARY

This plan establishes a rigorous methodology for validating NALA's capability to perform **true sustained long-duration operation** (target: 1+ hours continuous productive work), distinct from chaotic engineering validation runs. It builds upon preliminary chaos testing results to verify core architectural promises: long-term stability, memory integrity, context management efficacy, and graceful degradation/recovery under nominal operating conditions.

**Key Distinction**:  
- *Chaos Engineering Validation*: Frequent fault injection (SIGKILL, checkpoint corruption) to test recovery mechanisms  
- *Sustained Operation Validation*: Nominal operation over extended periods to validate stability, resource management, and progressive work completion  

This plan focuses exclusively on the latter, providing a blueprint for configuring, executing, and validating NALA's performance during extended soak tests.

---

## 🎯 OBJECTIVES

1. **Validate Sustained Productive Work**: Demonstrate NALA can complete ≥80% of the 1,236-step task graph (≥989 steps) in a single continuous run without fatal errors.
2. **Confirm Context Management Efficacy**: Observe and document at least one successful context exhaustion handoff (`spawn_reason`: "handoff") triggered by `DronagiriCompactor` when context thresholds are approached.
3. **Verify Memory Stability**: Prove no memory leaks exist via heap profiling and RSS monitoring showing predictable, bounded growth.
4. **Ensure Recovery Integrity**: Validate that crash recovery mechanisms (when chaos testing is selectively enabled) correctly restore state and continue work progression.
5. **Establish Baseline Performance Metrics**: Capture telemetry for cost-per-step, step-completion-rate, and context utilization for future regression analysis.

---

## 🔧 METHODOLOGY

### **1. Test Configuration Optimization**

#### **Critical Adjustments to `run_soak.py`**
Modify these parameters in `E:\NALA-Project\NALA\run_soak.py` to prioritize sustained validation over chaos injection:

```python
# SOAK DURATION - Set target validation period (seconds)
SOAK_DURATION_S = int(os.environ.get("SOAK_DURATION", 3600))  # 1 hour default

# DISABLE FREQUENT CHAOS INJECTION FOR BASELINE VALIDATION
# Comment out or adjust these windows to minimal/no chaos during primary validation
KILL_WINDOW_START = int(SOAK_DURATION_S * 0.33)   # Start chaos injection late in test
KILL_WINDOW_END   = int(SOAK_DURATION_S * 0.75)   # End chaos injection before completion
CHAOS_WINDOW_START = int(SOAK_DURATION_S * 0.20)  # Minimal chaos window
CHAOS_WINDOW_END   = int(SOAK_DURATION_S * 0.25)  # Very short chaos exposure

# Alternative: For pure chaos-free validation, set:
# SOAK_DURATION_S = 3600  # 1 hour
# KILL_WINDOW_START = SOAK_DURATION_S  # Disable injection entirely
# KILL_WINDOW_END   = SOAK_DURATION_S
# CHAOS_WINDOW_START = SOAK_DURATION_S
# CHAOS_WINDOW_END   = SOAK_DURATION_S
```

#### **Environment Preparation**
```bash
# Ensure clean state before extended run
cd E:\NALA-Project\NALA
rm -rf soak_runs/*          # Clear previous run artifacts (optional: keep for comparison)
rm -rf tests/long_running/.soak_history/soak_history.jsonl  # Reset history if regression tracking not needed
```

### **2. Execution Protocol**

#### **Launch Command**
```bash
# For 1-hour sustained validation (minimal chaos)
SOAK_DURATION=3600 python run_soak.py --no-heartbeat  # Disable heartbeat if causing overhead

# For monitoring with heartbeat (recommended)
SOAK_DURATION=3600 python run_soak.py
```

#### **Real-Time Monitoring Setup**
In a separate terminal, establish live monitoring:
```bash
# Navigate to latest run directory (auto-updating alias)
alias latest_run='ls -dt soak_runs/*/ | head -1'

# Monitor key metrics in real-time
watch -n 5 '
  echo "=== SOAK TEST PROGRESS ==="
  echo "Latest run: $(ls -dt soak_runs/*/ | head -1 | xargs basename)"
  echo ""
  echo "--- soak_status.json ---"
  cat $(latest_run)soak_status.json 2>/dev/null | jq -r ". | {session_id, .generation_index, .steps_completed, .steps_total, .context_status, .total_cost_usd" 2>/dev/null || echo "Waiting for status..."
  echo ""
  echo "--- Recent Metrics (last 5 events) ---"
  tail -5 $(latest_run)soak_metrics.jsonl 2>/dev/null | jq -c "." || echo "Waiting for metrics..."
  echo ""
  echo "--- Heap Leak Check (if available) ---"
  if [ -f $(latest_run)/*/heap_leaks.jsonl ]; then
    tail -3 $(latest_run)/*/heap_leaks.jsonl 2>/dev/null | jq -r ".step_index, .current_mb, .peak_mb" 2>/dev/null || echo "No heap leaks yet"
  else
    echo "Heap leak monitoring not active"
  fi
'
```

### **3. Validation Metrics & Success Criteria**

#### **Primary Success Indicators**
| **Metric** | **Target** | **Measurement Tool** | **Validation Method** |
|------------|------------|----------------------|------------------------|
| **Step Completion Rate** | ≥80% (989/1,236 steps) | `soak_status.json` | `steps_completed / steps_total ≥ 0.8` at test end or checkpoint |
| **Generational Progress** | ≥2 complete generations | `soak_metrics.jsonl` | Count of `"event": "generation_complete"` with `normalized_exit` ∈ {0, 10} |
| **Context Handling** | ≥1 handoff event | `soak_metrics.jsonl` | Presence of `"spawn_reason": "handoff"` preceded by `"context_status": "EXHAUSTED"` |
| **Memory Stability** | No heap leak trend | `*/heap_leaks.jsonl` | Linear regression slope of `current_mb` vs `step_index` ≈ 0 (MB/step) |
| **Cost Efficiency** | Predictable cost accumulation | `soak_status.json` | `total_cost_usd` correlates with `steps_completed` (no spikes without progress) |
| **Exit Status** | Clean termination | Final process exit | Exit code 0 (success) or 10 (handoff/paused) - NOT 1, 2, 3 unless chaos testing enabled |

#### **Secondary Validation Checks**
- **Phase Progression**: Verify work advances through all three workload phases (Steps 0-400, 401-800, 801-1236)
- **Checkpoint Integrity**: Confirm periodic checkpoints are written without failure (check supervisor logs for `[Bootstrap:...]` messages)
- **Telemetry Continuity**: Ensure `StateMatrix` metrics (cost, error count) update monotonically or reset appropriately on handoff
- **Spore Validation**: For handoff events, verify `handoff.spore.json` is written and contains valid SessionState

### **4. Risk Mitigation & Troubleshooting**

#### **Common Failure Modes & Responses**
| **Symptom** | **Likely Cause** | **Diagnostic Action** | **Corrective Measure** |
|-------------|------------------|------------------------|------------------------|
| `steps_completed` stalls <20% | Early infinite loop or deadlock | Check supervisor logs for repeated same step ID | Increase `max_retries_per_step`; verify task graph validity |
| Frequent `spawn_reason`: "crash_recovery" (>50%) | Undetected exceptions or instability | Search logs for exceptions before process exit | Enable core dumps; add try/catch around step execution |
| Context status stuck at "EXHAUSTED" | Handoff mechanism failure | Verify `handoff.py` and `recovery.py` functionality | Check file permissions in `data/sessions/`; validate spore write/read |
| RSS memory sawtooth pattern | Memory leak in Python heap | Analyze `heap_leaks.jsonl` for growing allocation traces | Use `objgraph` or `guppy` to identify leaking objects; fix in core harness |
| Cost accumulation with no step progress | Busy-wait or ineffective polling | Correlate `total_cost_usd` timestamps with step completion times | Review `model_router.py` and LLM call efficiency; add idle detection |
| Generation durations consistently <60s | Unintended chaos injection or early termination | Verify `sigkill_injected` frequency in metrics | Adjust chaos windows; ensure `SOAK_DURATION` is respected |

#### **Emergency Procedures**
1. **Unresponsive Loop**:  
   - Check for deadlock via `ps aux | grep python`  
   - Send `SIGTERM` for graceful stop if cooperative mechanism fails  
   - Analyze last checkpoint for state reconstruction

2. **Disk Space Exhaustion**:  
   - Monitor `du -sh soak_runs/` periodically  
   - Implement log rotation if running beyond 1 hour  
   - Archive old runs to external storage

3. **Metric Collection Failure**:  
   - Verify `soak_metrics.jsonl` is being appended to  
   - Check logging configuration in `observability/logger.py`  
   - Ensure sufficient file descriptors (`ulimit -n`)

### **5. Post-Run Analysis Procedure**

#### **Automated Validation Script**
Create `validate_soak_run.py` in `tests/long_running/`:
```python
#!/usr/bin/env python3
"""
Extended soak test validation script.
Analyzes run artifacts to confirm sustained operation success criteria.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_run(run_path: Path) -> Dict[str, bool]:
    """Analyze a soak run directory and return validation results."""
    results = {
        "step_completion_adequate": False,
        "sufficient_generations": False,
        "context_handling_observed": False,
        "memory_stable": False,
        "clean_termination": False,
        "cost_efficient": False
    }
    
    # Load final status
    status_path = run_path / "soak_status.json"
    if status_path.exists():
        with open(status_path) as f:
            status = json.load(f)
        
        # Check step completion
        steps_done = status.get("steps_completed", 0)
        steps_total = status.get("steps_total", 1236)
        results["step_completion_adequate"] = (steps_done / steps_total) >= 0.8
        
        # Check termination status
        exit_code = status.get("normalized_exit", 1)  # Default to failure
        results["clean_termination"] = exit_code in [0, 10]  # Success or handoff/paused
    
    # Analyze metrics for generations and context
    metrics_path = run_path / "soak_metrics.jsonl"
    if metrics_path.exists():
        generations = 0
        handoffs = 0
        context_exhausted_before_handoff = False
        
        with open(metrics_path) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get("event") == "generation_complete":
                        generations += 1
                        if event.get("normalized_exit") in [0, 10]:
                            pass  # Counted in generations
                    elif event.get("spawn_reason") == "handoff":
                        handoffs += 1
                    # Check for context exhaustion precedent to handoff
                    # (Would need more complex state tracking in practice)
                except json.JSONDecodeError:
                    continue
        
        results["sufficient_generations"] = generations >= 2
        results["context_handling_observed"] = handoffs >= 1
    
    # Heap leak analysis (simplified)
    heap_leaks = list(run_path.glob("*/heap_leaks.jsonl"))
    if heap_leaks:
        # In practice, would perform linear regression on current_mb vs step_index
        # For now, flag if any leak file exists with concerning growth
        latest_leak = max(heap_leaks, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_leak) as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    first = json.loads(lines[0].strip())
                    last = json.loads(lines[-1].strip())
                    mb_growth = last.get("current_mb", 0) - first.get("current_mb", 0)
                    steps_diff = last.get("step_index", 0) - first.get("step_index", 0)
                    if steps_diff > 0:
                        leak_rate = mb_growth / steps_diff  # MB per step
                        results["memory_stable"] = abs(leak_rate) < 0.01  # <0.01 MB/step
        except (json.JSONDecodeError, IndexError):
            results["memory_stable"] = False  # Unable to analyze
    
    # Cost efficiency check
    if status_path.exists():
        with open(status_path) as f:
            status = json.load(f)
        cost = status.get("total_cost_usd", 0)
        steps = status.get("steps_completed", 0)
        if steps > 0:
            cost_per_step = cost / steps
            results["cost_efficient"] = cost_per_step < 0.0001  # <$0.0001 per step (adjust based on actual)
    
    return results

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validate_soak_run.py <run_directory>")
        sys.exit(1)
    
    run_path = Path(sys.argv[1])
    if not run_path.exists():
        print(f"Error: Run directory {run_path} does not exist")
        sys.exit(1)
    
    results = analyze_run(run_path)
    
    print(f"\n=== VALIDATION RESULTS FOR {run_path.name} ===")
    for criterion, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{criterion.replace('_', ' ').title():<25} {status}")
    
    overall_pass = all(results.values())
    print(f"\nOVERALL VALIDATION: {'✅ PASS' if overall_pass else '❌ FAIL'}")
    print("To be considered successful, ALL criteria must pass.")
    
    return 0 if overall_pass else 1

if __name__ == "__main__":
    sys.exit(main())
```

#### **Manual Analysis Checklist**
After run completion, manually verify:
1. **soak_metrics.jsonl**:
   - Sequential `generation_index` increases (1,2,3,...)
   - `steps_completed` shows steady, monotonic increase
   - Presence of `"event": "generation_complete"` with `normalized_exit`: 0 or 10
   - Occasional `"spawn_reason": "handoff"` events
   - Absence of frequent `"sigkill_injected"` during work periods (if chaos disabled)

2. **Final soak_status.json**:
   - High `steps_completed` value (≥989 for 80%)
   - `context_status`: "NORMAL" or "EXHAUSTED" (if halted at limit)
   - Reasonable `total_cost_usd` proportional to work done
   - `rss_mb` showing gradual increase (not sawtooth)

3. **Supervisor Logs** (`soak_runs/<run>/supervisor_logs/`):
   - Regular `[LoopStart]`, `[LoopEnd]` entries showing productive work
   - `[HeapProfile]` entries indicating stable memory growth
   - `[Bootstrap:...]` messages confirming successful checkpoints/recoveries
   - Minimal `[StepFailure]` or `[Entrypoint] Unhandled exception` entries

4. **Heap Leak Files** (`soak_runs/<run>/session_id/heap_leaks.jsonl`):
   - Linear regression of `current_mb` vs `step_index` shows negligible slope
   - No exponential or step-like growth patterns
   - Peak memory remains within expected bounds for workload

---

## 📂 FILES & DIRECTORY STRUCTURE

### **Key Artifacts Generated**
```
soak_runs/
├- <run_id>/
│  ├- soak_metrics.jsonl          # Primary event timeline (JSONL)
│  ├- soak_status.json            # Final state snapshot
│  ├- soak_success_bundle_*.zip   # Complete artefact on success
│  ├- supervisor_logs/            # Detailed process logs per generation
│  │   ├- <session_id>__gen01__*.log
│  │   └- <session_id>__genNN__*.log
│  └- <session_id>/               # Per-session data
│       ├- checkpoints/           # Session checkpoints (LSN sequenced)
│       └- heap_leaks.jsonl       # Heap profiling data (if tracemalloc enabled)
```

### **Critical Configuration Files**
- `E:\NALA-Project\NALA\run_soak.py` - Main test orchestrator (adjust SOAK_DURATION, chaos windows)
- `E:\NALA-Project\NALA\tests\long_running\_soak_supervisor.py` - Chaos injection timing
- `E:\NALA-Project\NALA\tests\long_running\_soak_workload.py` - Phase boundaries and step timing
- `E:\NALA-Project\NALA\tests\long_running\_soak_subprocess_entrypoint.py` - Exit code mapping and leak checks

### **Validation Outputs**
- `E:\NALA-Project\NALA\tests\long_running\.soak_history\soak_history.jsonl` - Historical run data for regression
- Custom validation script outputs (if using `validate_soak_run.py`)

---

## ⏱️ EXPECTED TIMELINE & PROGRESSION

### **For 1-Hour (3600s) Sustained Validation**
| **Phase** | **Step Range** | **Time Allocation** | **Expected Generations** | **Key Events** |
|-----------|----------------|---------------------|--------------------------|----------------|
| **Phase 1** | 0-400 | ~25% (900s) | Gen 1 (partial/complete) | Initial bootstrap, early context filling |
| **Phase 2** | 401-800 | ~35% (1260s) | Gen 1-2 | Mid-workload, potential first handoff |
| **Phase 3** | 801-1236 | ~40% (1440s) | Gen 2-3 | Late workload, likely context exhaustion handoff |
| **Overhead** | — | ~15% (540s) | — | Checkpointing, recovery cycles, telemetry updates |

**Typical Generation Pattern:**
- **Gen 1**: Completes Steps 0-450 (~1000s) → Checkpoint → Possible handoff if context fills early
- **Gen 2**: Continues from Step 451 → Completes Steps 451-900 (~1200s) → Handoff (context exhaustion)
- **Gen 3**: Recovers from spore → Completes Steps 901-1236 → Success (exit code 0) or paused at limit

**Note**: Actual timing varies based on:
- Step complexity (mock vs real LLM calls)
- System performance (CPU, I/O)
- Context threshold settings in `SOAK_TRACKER_CONFIG`
- Checkpoint frequency settings

---

## 🛡️ ASSUMPTIONS & CONSTRAINTS

### **Assumptions**
1. **Base System Stability**: NALA core components (`nala_loop.py`, `session_contract.py`, `checkpoint.py`) are functioning correctly (validated via prior chaos testing).
2. **Deterministic Workload**: The `_soak_workload.mock_step_executor` provides predictable step execution timing.
3. **Adequate Resources**: Test execution environment has sufficient CPU, memory (>512MB RAM), and disk space (>2GB free).
4. **Configuration Integrity**: No unintended modifications to core NALA components during validation period.

### **Constraints**
- **Maximum Validation Duration**: Practical limit of 4-6 hours due to checkpoint file accumulation and log growth (beyond this, implement log rotation).
- **Chaos Testing Interference**: Freffective chaos injection intervals (<60s) will invalidate sustained operation metrics; disable for pure stability validation.
- **Metric Overhead**: Monitoring tools (especially `psutil` in supervisor) add minimal overhead (<5% CPU) but should be accounted for in baseline measurements.
- **Determinism Requirement**: For true regression validation, use identical `run_start_ts` and workload configuration across runs.

---

## 📈 REGRESSION TRACKING & BASELINE ESTABLISHMENT

### **Establishing Performance Baselines**
After 3-5 successful sustained runs, record:
1. **Average Step Completion Rate**: Steps per minute
2. **Mean Generation Duration**: Time per productive generation
3. **Context Exhaustion Frequency**: Occurrences per hour
4. **Memory Growth Rate**: MB/hour RSS increase
5. **Cost Efficiency**: USD per 1000 steps
6. **Failure Rate**: % of generations requiring recovery

### **Regression Detection Thresholds**
Flag for investigation if any metric deviates beyond:
- Step completion rate: ±20% from baseline
- Generation duration: ±30% from baseline  
- Memory growth rate: ±50% from baseline (absolute increase)
- Cost per step: ±25% from baseline
- Handoff frequency: Absent when expected (>2hrs without handoff in 4hr run)

---

## ✅ SUCCESS CRITERIA SUMMARY

A soak test run is deemed **validated for sustained operation** when **ALL** of the following are true:

1. **Work Completion**: ≥989 steps completed (80% of 1,236) in a single continuous execution sequence
2. **Generational Progress**: Demonstrated ≥2 complete generations with productive work (exit codes 0 or 10)
3. **Context Management**: At least one verified context exhaustion handoff event (`spawn_reason`: "handoff" preceded by context approaching limits)
4. **Memory Stability**: Heap profiling shows no statistically significant memory leak (leak rate < 0.01 MB/step)
5. **Cost Efficiency**: Resource consumption scales predictably with work done (no cost accumulation without progress)
6. **Clean Termination**: Process exits with code 0 (success) or 10 (handoff/paused) - **NOT** 1, 2, or 3 unless chaos testing was explicitly enabled and expected
7. **Artifact Integrity**: Generates `soak_success_bundle_*.zip` containing complete, verifiable execution traces

### **Partial Success Indicators**
- **Promising**: 70-79% step completion with stable metrics → indicates core functionality working, needs minor tuning
- **Needs Investigation**: <70% completion OR frequent crashes OR memory leaks → requires root cause analysis before extended testing
- **Chaos Validation Only**: High step completion but only with frequent chaos injection → validates recovery but not sustained stability

---

## 🚀 IMPLEMENTATION ROADMAP

### **Phase 1: Preparation (Immediate)**
- [ ] Backup current `run_soak.py` and test configuration files
- [ ] Create `validate_soak_run.py` in `tests/long_running/`
- [ ] Document baseline configuration for reproducibility
- [ ] Clear or archive previous soak run data (if desired clean slate)

### **Phase 2: Configuration Tuning (Day 1)**
- [ ] Adjust `SOAK_DURATION_S` in `run_soak.py` to target validation period (e.g. 3600s)
- [ ] Set chaos windows to minimal/no injection for baseline validation:
  ```python
  # Example: Pure 1-hour validation with no chaos
  SOAK_DURATION_S = 3600
  KILL_WINDOW_START = SOAK_DURATION_S   # Effectively disabled
  KILL_WINDOW_END = SOAK_DURATION_S
  CHAOS_WINDOW_START = SOAK_DURATION_S
  CHAOS_WINDOW_END = SOAK_DURATION_S
  ```
- [ ] Verify `SOAK_TRACKER_CONFIG` in `_soak_workload.py` matches desired context thresholds
- [ ] Ensure sufficient disk space (>5GB free recommended for multiple runs)

### **Phase 3: Execution & Monitoring (Day 2-3)**
- [ ] Launch validation run: `SOAK_DURATION=3600 python run_soak.py`
- [ ] Establish real-time monitoring using the `watch` command template provided
- [ ] Monitor for:
   - Steady `steps_completed` increase
   - Generation durations in expected range (600-1800s)
   - Absence of frequent crash recoveries
   - Context exhaustion events triggering handoffs
- [ ] Intervene only if:
   - Process appears truly hung (>30min with no step progress)
   - Disk space critically low (<1GB free)
   - Repeated unrecoverable exceptions in logs

### **Phase 4: Post-Run Analysis (After Completion)**
- [ ] Execute validation script:  
      `python tests/long_running/validate_soak_run.py soak_runs/<latest_run_id>/`
- [ ] Manually review:
   - Final `soak_status.json` for completion metrics
   - `soak_metrics.jsonl` for generational and context patterns
   - Supervisor logs for errors and performance indicators
   - Heap leak files (if any) for memory trends
- [ ] Archive successful runs for baseline establishment
- [ ] Document any anomalies for root cause analysis

### **Phase 5: Regression Setup (Ongoing)**
- [ ] After 3-5 successful baseline runs, commit configuration as "known good"
- [ ] Use `.soak_history` for automated regression detection in future runs
- [ ] Integrate validation criteria into CI/CD pipeline for pre-release testing
- [ ] Plan periodic re-validation (weekly/bimonthly) to detect degradation

---

## 📚 REFERENCES & RELATED DOCUMENTATION

### **Internal NALA Documents**
- [NALA Project Structure](../NALA_Project_Structure.md) - Core architecture overview
- [NALA Advanced Plan](../NALA_Advanced_Plan.md) - Master architecture and build order
- [Future Enhancements](../future_enhancements.md) - Planned improvements affecting long-term stability
- [JIRA-007 1Hour Soak Test Plan](../JIRA_007_1Hour_Soak_Test_Plan.md) - Original test specification
- [JIRA-007-B Advanced Soak Orchestrator Plan](../BACKLOG_Features/JIRA_007_B_Advanced_Soak_Orchestrator_Plan.md) - Enhanced orchestration details

### **Key Source Files**
- `core/harness/nala_loop.py` - Main execution loop (validates stepwise progression)
- `core/harness/context_tracker.py` - Context management and compaction triggers
- `core/harness/recovery.py` - Session restoration mechanics
- `tests/long_running/_soak_supervisor.py` - Chaos injection timing and process management
- `tests/long_running/_soak_workload.py` - Step timing, phase boundaries, and workload definition
- `tests/long_running/_soak_subprocess_entrypoint.py` - Exit code mapping and leak detection

### **Validation Artifacts**
- `soak_success_bundle_*.zip` - Complete forensic package for successful runs
  - Contains all logs, checkpoints, metrics, and session states
  - Enables deep post-mortem analysis of any anomalies
- `soak_metrics.jsonl` - Primary timeline of events (JSON Lines format)
- `soak_status.json` - Final state snapshot for quick health assessment

---

## 🙏 CLOSING NOTE

*Jai Bajrang Bali 🙏*

This plan transforms NALA from a system validated for **failure recovery** into one proven for **sustained productive operation**. By rigorously distinguishing chaos engineering validation from true stability testing, we establish a foundation for trusting NALA in production-long-running agent scenarios where continuous, reliable work completion is paramount.

The methodologies outlined herein provide not just a test procedure, but a framework for ongoing quality assurance—enabling the team to detect regressions, validate improvements, and confidently extend NALA's operational horizons beyond the initial 1-hour target.

**Next Step**: Execute this plan, document the results, and iterate toward ever-greater durations of stable autonomous operation.

---
*Document Version: 1.0 | Prepared: 2026-07-08 | Validated Against: NALA Core v1.0.0*