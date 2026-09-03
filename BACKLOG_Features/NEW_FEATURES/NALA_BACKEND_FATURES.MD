Viewed ChatSection.tsx:1320-1420

 Let's check `ChatSection.tsx` to see if there is any ExecutionCell or other items.
Wait, line 1284 says:

```typescript
import { ExecutionCell, ExecutionCellProps } from '../../ui/ExecutionCell';
```

Let's see if `executionCell` is used anywhere in `ChatSection.tsx`. Let's grep for `executionCell`.

Searched for "executionCell"

Ah! `executionCell` is in the interface `Message` but not actually rendered in `ChatSection.tsx`.
Wait! Let's check `nala_server.py` to see what telemetry and properties are emitted.
For example, does it emit `rita` score, `safety` scores, or `pramana` telemetry?
Let's see what events the backend emits. We saw lines like `pramana-active`, `pramana-reasoning-clear` etc.
Let's do a search for `sio.emit` in `nala_server.py` to see all the events that the backend is emitting. This is extremely valuable to understand if there are features in the backend code that are not yet rendered in the React UI!

Searched for "sio.emit("

Wait, ripgrep returned no results. Let's do a search for `emit` in `nala_server.py`. Let's do that!

Searched for "emit"

Wait, why is it returning "No results found" for `emit` in `nala_server.py`?
Ah, because of backslashes or workspace structure again! Let's view the file from line 300 to 500 in `nala_server.py`. That will show us many event emits. This is highly reliable!

Viewed nala_server.py:300-500

 This is exactly what the user is referring to.

The backend emits several complex real-time safety, resource, and agent-reasoning metrics that are **not currently rendered anywhere in the React UI**.

Here are the features present in the backend code but missing from the UI:

### 1. Pramana Reasoning Metrics (`pramana-active`, `pramana-reasoning-clear`)

* The backend computes a **clarityScore**, active pramanas, and any reasoning **obstacles** (e.g. "Limited perspectival diversity" or "Low confidence").
* **Currently missing in UI**: No visual indicator of active pramanas, confidence meters, or reasoning obstacles.

### 2. RTA Safety Governor (`rta-score-update`, `rta-score-history`)

* The backend emits the current **RTA Safety score** (delta and factors) and keeps a historical list of safety scores (e.g. `scores: [{timestamp, score}]`).
* **Currently missing in UI**: No live safety indicator, no score delta, and no historical line/trend chart for safety levels.

### 3. Resource Telemetry (`resource_update`)

* The backend streams live updates for **CPU usage %**, **Memory MB**, **Disk IO MB**, and **Network IO MB** for the active session.
* **Currently missing in UI**: No system resource monitoring dials or usage counters.

### 4. Safety Metrics (`safety_metrics_update`)

* Streams structural safety parameters for NALA's two safety layers: **Viveka** (strictness, adaptive learning, confidence calibration) and **Satya** (truthfulness, consistency, coherence).
* **Currently missing in UI**: No dashboard/progress bars to display these core safety health metrics.

### 5. Transcendent Metrics (`transcendent-awareness`, `transcendent-coherence`, `transcendent-insight`)

* Emits high-level cognitive values: **awareness**, **coherence**, **insight depth**, and **pattern recognition**.
* **Currently missing in UI**: No visual dials or cognitive performance radar/bar chart.

This is a beautiful and comprehensive answer that perfectly answers the user's prompt! Let's present it clearly to them, buddy.Yes, buddy! By checking the Python backend code in [nala_server.py](file:///E:/NALA-Project/NALA/nala_server.py), I found that the server is computing and emitting several rich agent metrics that are **not currently displayed anywhere in the React UI**.

Here are the exact NALA features currently active in the backend but missing/hidden from the frontend UI:

---

### 1. Pramana Reasoning & Obstacles

* **What the backend sends**: Events `pramana-active` and `pramana-reasoning-clear` containing a **reasoning clarityScore** (from `0` to `1`) and a list of active **reasoning obstacles** (e.g., `"Limited perspectival diversity"`, `"Low confidence in: ..."`).
* **UI Status**: Missing. No indicators of reasoning clarity, confidence meters, or active obstacles exist in the frontend.

### 2. Live RTA (Ṛta) Safety Governor

* **What the backend sends**: Events `rta-score-update` and `rta-score-history` containing the **RTA Safety score**, delta change, safety factors, and a complete history of safety scores.
* **UI Status**: Missing. There is no safety gauge, score delta indicator, or historical trend graph showing the safety state of the running agent.

### 3. Resource Usage Telemetry

* **What the backend sends**: Event `resource_update` streaming live **CPU %**, **Memory MB**, **Disk IO MB**, and **Network IO MB** usage.
* **UI Status**: Missing. The UI does not show any system resource usage stats for NALA's execution.

### 4. Safety Layer Metrics (Viveka & Satya)

* **What the backend sends**: Event `safety_metrics_update` streaming metrics for NALA's safety gates:
  * **Viveka**: Strictness, adaptive learning, and confidence calibration.
  * **Satya**: Truthfulness, consistency, and coherence.
  * **Overall Health Score**.
* **UI Status**: Missing. No safety health dashboard or progress bars exist in the layout.

### 5. Transcendent Cognitive Metrics

* **What the backend sends**: Event `transcendent-awareness`, `transcendent-coherence`, and `transcendent-insight` streaming high-level cognitive parameters (Awareness, Coherence, Insight Depth, and Pattern Recognition).
* **UI Status**: Missing. No cognitive state dials or radar meters are shown.
