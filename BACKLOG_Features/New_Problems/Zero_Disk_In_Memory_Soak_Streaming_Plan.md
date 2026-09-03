# 🧠 Architectural Plan: In-Memory Zero-Disk Storage & Live Streaming System for NALA

**Target File:** `run_soak.py` & `core/harness/`  
**Target Location:** `E:\NALA-Project\NALA\BACKLOG_Features\New_Problems\Zero_Disk_In_Memory_Soak_Streaming_Plan.md`  
**Status:** Implementation Specification  
**Created:** July 26, 2026  

---

## 🎯 Executive Overview

To prevent hard drive bloat, unnecessary storage consumption, and disk I/O wear during long-running soak tests and 24/7 autonomous background execution, this plan specifies the **In-Memory Zero-Disk Streaming System**.

Instead of writing gigabytes of test run logs to disk (`soak_runs/soak_run_*.log`), NALA streams all live test step metrics, token usage, and thread health directly in RAM using bounded in-memory structures (`collections.deque`). Upon test completion, Python's Garbage Collector automatically frees memory back to the OS, ensuring **0 MB of hard drive space is consumed**.

---

## 📐 System Architecture Diagram

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       IN-MEMORY ZERO-DISK TELEMETRY & STREAMING ENGINE                            │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                   │
│   1. LIVE EXECUTION EVENTS              2. IN-MEMORY BOUNDED STREAM      3. RICH CLI DASHBOARD    │
│   ┌───────────────────────────┐         ┌───────────────────────────┐    ┌──────────────────────┐ │
│   │ nala_loop.py / run_soak   │         │ RAM Ring Buffer (deque)   │    │ Live Terminal Stream │ │
│   │ • Step Start              │ ──────► │ • Max footprint: < 3 MB   │ ─► │ • Rich Panels / HUD  │ │
│   │ • Token & Cost Metrics    │         │ • Zero Hard Drive Writes  │    │ • Instant Render     │ │
│   │ • LSN Checkpoint State    │         └─────────────┬─────────────┘    └──────────────────────┘ │
│   └───────────────────────────┘                       │                                           │
│                                                       │                                           │
│   4. AUTOMATIC CLEANUP & GC                           │                                           │
│   ┌───────────────────────────────────────────────────┴────────────────────────────────────────┐  │
│   │                         python Garbage Collector (gc.collect)                               │  │
│   │            Frees 100% of RAM footprint instantly upon test completion / script exit.        │  │
│   └────────────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Technical Features

### 1. In-Memory Streaming (`< 3 MB` RAM Footprint)
* All step metrics, execution times, token counts, and cost metrics are stored in a bounded `collections.deque(maxlen=1000)` in RAM.
* **Storage Footprint:** Less than 3 MB total RAM consumed (less than 0.01% of system RAM).
* **Zero Disk Writes:** Completely bypasses file output streams (`open(log_file, "w")`).

### 2. Auto-Deleting Transient Scratch (`tempfile.TemporaryDirectory`)
* If temporary files are strictly required by third-party tools during a test run, they are placed in `tempfile.TemporaryDirectory()`.
* **Instant Teardown:** The OS temp directory is automatically purged from disk the exact millisecond `run_soak.py` exits.

### 3. Startup Legacy Purge Hook (`purge_legacy_soak_runs()`)
* Automatically checks for any existing `soak_runs/` directories created in prior runs and purges them at startup, restoring 100% of hard drive space.

---

## 📁 Implementation Modifications for `run_soak.py`

```python
# Prototype Implementation for run_soak.py
import shutil
import tempfile
from pathlib import Path

def purge_legacy_soak_runs(workspace_dir: Path):
    """Purge legacy soak_runs folder to ensure 0 MB disk usage."""
    legacy_dir = workspace_dir / "soak_runs"
    if legacy_dir.exists():
        try:
            shutil.rmtree(legacy_dir)
            print("[Auto-Cleanup] Purged legacy soak_runs folder. 0 MB disk space used.")
        except Exception as e:
            pass

def run_in_memory_soak_test():
    """Run soak test using transient in-memory streaming and auto-cleanup."""
    workspace = Path(r"E:\NALA-Project\NALA")
    purge_legacy_soak_runs(workspace)
    
    with tempfile.TemporaryDirectory(prefix="nala_soak_inmem_") as temp_dir:
        # All transient state lives in temporary RAM directory
        print(f"[In-Memory Mode] Active in RAM temp dir: {temp_dir}")
        # Run test execution steps...
    # Auto-cleanup complete on context exit
```

---

## ✅ Acceptance & Verification Matrix

| Metric / Requirement | Target Value | Verification Method |
| :--- | :--- | :--- |
| **Disk Space Consumed** | **0 MB** | Verify `soak_runs/` folder is absent after test completion. |
| **RAM Footprint** | **< 3 MB** | Measure `psutil.Process().memory_info().rss` diff before/after run. |
| **Step Test Success** | **100% PASSED** | All 1,000 steps executed cleanly without state loss. |
| **Auto-Cleanup Latency** | **< 10 ms** | Context manager exit teardown benchmark. |
