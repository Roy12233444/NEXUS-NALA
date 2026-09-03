# JIRA-009: NALA UI Future Roadmap & Telemetry Integration Plan

## 📌 Goal
Create a structured task plan for Phase 4 (LaTeX Math & Advanced Renderers) and the frontend integration of NALA's active backend telemetry features.

---

## 🛠️ Phase 4: LaTeX Math & Advanced Renderers
*   [ ] **Math Formula Parser**:
    *   Integrate KaTeX parser wrapper (`lazy-katex.ts`) to render math equations in block and inline formats.
*   [ ] **Premium Layouts & Inline Artifacts**:
    *   Natively render tables, system-generated image assets, diff blocks, and code logs.

---

## 📊 Phase 5: Telemetry Panel Integration
Connect the React UI to the active metrics emitted by NALA's Socket.IO backend:
*   [ ] **Pramāṇa Reasoning Indicator**:
    *   Display active Pramāṇas (Intuition, Logic, Intellect) with their real-time confidence scores.
    *   Add a warning badge for active reasoning obstacles (e.g., "Limited perspectival diversity").
*   [ ] **RTA Safety Governor**:
    *   Render a live safety gauge showing the active Ṛta-score.
    *   Add a historical line chart tracking RTA score updates over time.
*   [ ] **Resource Monitor Widget**:
    *   Build a dial widget displaying real-time CPU %, Memory MB, Disk IO, and Network throughput of the agent session.
*   [ ] **Transcendent State Dashboard**:
    *   Visualize cognitive metrics (Awareness, Coherence, Insight Depth, and Pattern Recognition) via a progress grid.

---

## 🔬 Verification Plan
*   [ ] Verify KaTeX math renders correctly in chat bubbles.
*   [ ] Confirm WebSocket event hooks receive and render telemetry payloads without crashing the main shell.
