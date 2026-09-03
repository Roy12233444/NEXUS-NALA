# 🖥️ Architectural Plan: NALA 24/7 Autonomous Personal Computer System

**Target Location:** `E:\NALA-Project\NALA\BACKLOG_Features\NEW_FEATURES\24_7_Autonomous_Personal_Computer_Plan.md`  
**Inspired By:** Perplexity Personal Computer & Sovereign Agent Infrastructure  
**Status:** Advanced Architecture Specification  
**Created:** July 26, 2026  

---

## 🎯 Executive Overview

To transform **NALA** into the ultimate **24/7 Personal Autonomous Computer**, this plan specifies four high-impact architectural features. These features enable NALA to run continuously in the background on your local machine, monitor file dropboxes, provide remote mobile telemetry control, enforce emergency safety overrides, and dynamically balance local versus frontier LLM compute.

Unlike proprietary cloud platforms (such as Perplexity Personal Computer) that charge $200/month and store data on external servers, **NALA operates 100% locally, private, and sovereign** on your own hardware.

---

## 📐 System Architecture Diagram

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           NALA 24/7 AUTONOMOUS COMPUTER CONTROL PLANE                             │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                   │
│   ┌───────────────────────────┐                        ┌───────────────────────────────┐          │
│   │   Local Folder Watcher    │                        │    Remote Mobile / Web App    │          │
│   │  (inbox_watcher.py)       │                        │ (remote_telemetry_bridge.py)  │          │
│   │  E:\NALA-Project\inbox\   │                        │ WebSocket / REST API Stream   │          │
│   └─────────────┬─────────────┘                        └───────────────┬───────────────┘          │
│                 │                                                      │                          │
│                 └──────────────────────────┬───────────────────────────┘                          │
│                                            ▼                                                      │
│                                ┌───────────────────────┐                                          │
│                                │  Smart Model Router   │                                          │
│                                │(smart_model_router.py)│                                          │
│                                └───────────┬───────────┘                                          │
│                                            │                                                      │
│                    ┌───────────────────────┴───────────────────────┐                              │
│                    ▼                                               ▼                              │
│       ┌──────────────────────────┐                    ┌──────────────────────────┐                │
│       │    Fast Local Model      │                    │  Frontier Reasoning Model│                │
│       │ (Ollama / LLaMA / Qwen)  │                    │(Claude 3.5 / GPT-4o/ DEQ)│                │
│       └────────────┬─────────────┘                    └────────────┬─────────────┘                │
│                    │                                               │                              │
│                    └───────────────────────┬───────────────────────┘                              │
│                                            ▼                                                      │
│                                ┌───────────────────────┐                                          │
│                                │   NALA Execution Loop │                                          │
│                                │    (nala_loop.py)     │                                          │
│                                └───────────┬───────────┘                                          │
│                                            │                                                      │
│                                            ▼                                                      │
│                 ┌─────────────────────────────────────────────────────┐                           │
│                 │        Emergency Kill Switch & Safety Layer         │                           │
│                 │ (emergency_kill_switch.py / Job Objects Lockdown)   │                           │
│                 └─────────────────────────────────────────────────────┘                           │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 The 4 Core Feature Specifications

---

### 📂 Feature 1: Autonomous Folder Watcher / Trigger System (`/inbox` Monitor)

#### 1. Objective & Description
Continuously monitors a dedicated local directory (`E:\NALA-Project\inbox\`) using OS-level file system event hooks (`watchdog`). As soon as a file (PDF, Python script, CSV, markdown paper, dataset) is dropped into the folder, NALA automatically detects it, classifies the document intent, spawns an autonomous task in the background, and generates a structured summary report in `E:\NALA-Project\output\`.

#### 2. Architecture & File Location
* **File Location:** `core/harness/inbox_watcher.py`

#### 3. Key Technical Capabilities
* **OS Event Hooks:** Uses `watchdog.observers.Observer` for zero-CPU file system event listening.
* **File Type Classifiers:**
  * `.pdf` / `.md` / `.txt`: Auto-summarize research papers, extract technical formulas, and update vector memory.
  * `.py` / `.ts` / `.json`: Run security audit, linting, and sandbox execution tests.
  * `.csv` / `.parquet`: Execute automated exploratory data analysis (EDA).
* **De-duplication & Debouncing:** Ensures partially copied files do not trigger premature execution loops.

```python
# Prototype Interface: core/harness/inbox_watcher.py
class InboxWatcher:
    def __init__(self, watch_dir: str = r"E:\NALA-Project\inbox"):
        self.watch_dir = watch_dir
        self.observer = Observer()

    def start(self):
        handler = InboxFileEventHandler(on_new_file=self.trigger_nala_task)
        self.observer.schedule(handler, self.watch_dir, recursive=False)
        self.observer.start()

    def trigger_nala_task(self, file_path: str):
        # Spawns async task in NALA execution loop
        ...
```

---

### 📱 Feature 2: Remote Mobile Control & Telemetry (Web Dashboard)

#### 1. Objective & Description
Provides a secure WebSocket and REST API bridge that allows you to monitor NALA's 24/7 background execution live from your mobile phone, tablet, or secondary laptop while away from your primary workstation.

#### 2. Architecture & File Location
* **File Location:** `core/harness/remote_telemetry_bridge.py`

#### 3. Key Technical Capabilities
* **Live Telemetry Stream:** Streams real-time `TaskGraph` step transitions, terminal logs, and `Ṛta-Score` metrics via WebSockets (`socket.io`).
* **Remote Directive Submission:** Allows submitting new prompt directives or modifying active runs remotely.
* **Mobile-Responsive Control Room UI:** Renders a lightweight, high-contrast mobile dashboard accessible over secure local network or encrypted tunnel (Tailscale/Cloudflare Tunnel).

```python
# Prototype Interface: core/harness/remote_telemetry_bridge.py
class RemoteTelemetryBridge:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = FastAPI()
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

    async def broadcast_step_update(self, step_id: str, status: str, telemetry: dict):
        await self.sio.emit("telemetry_update", {
            "step_id": step_id,
            "status": status,
            "telemetry": telemetry,
            "timestamp": datetime.utcnow().isoformat()
        })
```

---

### 🛑 Feature 3: One-Click Emergency "Kill Switch" & Pause Button

#### 1. Objective & Description
A high-priority, zero-latency safety mechanism accessible from both the UI header and command-line. When pressed, it immediately freezes all active Python sandbox threads, suspends Windows Job Objects, freezes the current LSN checkpoint state in `session_contract.py`, and revokes all tool permissions.

#### 2. Architecture & File Location
* **File Location:** `core/safety/emergency_kill_switch.py`

#### 3. Key Technical Capabilities
* **Thread & Process Lockdown:** Sends `SIGSTOP` / `SuspendThread` calls to active sandbox workers using Windows Job Objects (`sandbox_windows.py`).
* **Checkpoint Freeze:** Writes a emergency `LSN_FREEZE` record to `checkpoint.py` so the task can be safely resumed later without state corruption.
* **UI Integration:** Prominent red **"🛑 EMERGENCY KILL SWITCH"** button prominently placed in the Cowork workspace header bar.

```python
# Prototype Interface: core/safety/emergency_kill_switch.py
class EmergencyKillSwitch:
    @staticmethod
    def trigger_emergency_stop(reason: str = "User manual override"):
        # 1. Freeze active sandbox Job Objects
        SandboxManager().lockdown_all_sandboxes()
        
        # 2. Update active ExecutionContract status to PAUSED
        ContractEngine().force_status(ContractStatus.PAUSED)
        
        # 3. Create emergency LSN checkpoint
        CheckpointManager().save_emergency_checkpoint(reason)
        
        print(f"[KILL SWITCH TRIGGERED] {reason}")
```

---

### 𔠀 Feature 4: Smart Multi-Model Router (Local vs. Frontier AI)

#### 1. Objective & Description
An intelligent cost-and-performance optimizer that dynamically routes task steps to the appropriate AI model. Simple administrative tasks (file sorting, syntax formatting, simple summaries) are routed to fast, free local LLMs (Ollama / LLaMA / Qwen), while complex multi-step reasoning (architecture design, code synthesis, mathematical proofs) is routed to frontier models (Claude 3.5 / GPT-4o / DEQ).

#### 2. Architecture & File Location
* **File Location:** `core/hands/smart_model_router.py`

#### 3. Key Technical Capabilities
* **Complexity Classifier:** Evaluates step prompt complexity, required context size, and tool requirements.
* **Cost & Speed Optimization:** Saves 80% of API token costs by handling routine tasks locally on your PC.
* **Seamless Fallback:** Automatically escalates a task to a frontier model if the local model fails a task step twice.

```python
# Prototype Interface: core/hands/smart_model_router.py
class SmartModelRouter:
    def select_model(self, task_type: str, prompt: str) -> str:
        complexity_score = self.assess_complexity(prompt)
        
        if task_type in ["file_organize", "syntax_check", "simple_summary"] or complexity_score < 0.3:
            return "ollama/llama3"
        elif complexity_score < 0.7:
            return "claude-3-5-haiku"
        else:
            return "claude-3-5-sonnet"
```

---

## 📁 File Creation & Integration Index

| Target File Path | Feature Module | Purpose |
| :--- | :--- | :--- |
| `core/harness/inbox_watcher.py` | Feature 1 | File system watcher monitoring `E:\NALA-Project\inbox\`. |
| `core/harness/remote_telemetry_bridge.py` | Feature 2 | WebSocket/REST bridge for mobile telemetry & control. |
| `core/safety/emergency_kill_switch.py` | Feature 3 | Immediate process freezer, Job Object lockdown & checkpoint freeze. |
| `core/hands/smart_model_router.py` | Feature 4 | Dynamic task router between local LLMs & frontier models. |
| `src/components/features/chat/KillSwitchButton.tsx` | Feature 3 UI | Red visual override button in NALA workspace header. |

---

## 🗓️ Implementation Steps

1. **Step 1:** Implement `emergency_kill_switch.py` and add the kill button to the NALA Cowork header bar.
2. **Step 2:** Build `smart_model_router.py` to route local tasks vs. frontier reasoning.
3. **Step 3:** Implement `inbox_watcher.py` for automated background file processing in `E:\NALA-Project\inbox\`.
4. **Step 4:** Build `remote_telemetry_bridge.py` to enable mobile dashboard streaming and remote control.
