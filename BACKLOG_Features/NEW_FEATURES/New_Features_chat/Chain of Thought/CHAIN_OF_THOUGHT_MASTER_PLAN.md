# 🧠 Unified Master Chain-of-Thought (Tree of Thought) Component Plan

## 🎯 Executive Overview & Objective
This implementation plan defines the architectural blueprint for **`ChainOfThoughtMaster`** — a unified, multi-variant Tree of Thought reasoning accordion designed for NALA and the Nexus LAB AI Control Center (`nexus-ui.dev`).

`ChainOfThoughtMaster` will **unify and cleanly replace** both the old top `Thought Process` text box and the bottom `NALA Execution Plan & Task Graph` card into a single, interactive, prop-driven component supporting **all 5 CoT variants** dynamically based on the active mission directive.

---

## 🏛️ 5 Variant Specifications

| Variant Prop Mode | Design Specification | Iconography / Visual Elements | Target NALA Use Case |
| :--- | :--- | :--- | :--- |
| `variant="default"` | **Standard Icon Accordion** | Trigger header (`🧠 Triaged support ticket...`), step-specific icons (`FileSearch`, `Analytics`, `Idea`), green completion badge (`✓ Task complete`). | **Standard Autonomous Directives** (General prompt execution, task graph execution, code refactoring). |
| `variant="basic"` | **Minimalist Search & Lint** | Compact header (`Explored 3 files, 2 searches`), text-only steps, simple text label (`No linter errors`). | **Workspace Exploration & File Grepping** (File scanning, sidebar code checks). |
| `variant="rich"` | **Deep Research (DEQ Mode)** | Expandable steps with nested search pills (`🌐 3 days in lisbon...`), domain favicon links (`visitlisboa.com`), tool result cards. | **Deep Research & Multi-Tool Directives** (arXiv papers, web search queries, biomedical database searches). |
| `variant="error"` | **Sandbox & SLA Failure Alert** | Completed steps + highlighted **Red Destructive Error Step** (`status="error"`) + error callout box. | **Sandbox Execution & SLA Timeouts** (PEP 578 sandbox errors, Ṛta-Score safety threshold blockages). |
| `variant="no-header"` | **Embedded Accordion** | Frameless, header-less, open-by-default step list (`defaultOpen`). | **Embedded Sidebars & Sub-Agent Modals** (Control room side panels, sub-agent dialog cards). |

---

## 🛠️ Component Architecture & Props Interface

### 📄 Component Location
* Core Component: `src/components/ui/ChainOfThoughtMaster.tsx`
* CSS Styling: `src/components/ui/ChainOfThoughtMaster.css`

### 💻 TypeScript Interface

```typescript
export type CoTVariant = 'default' | 'basic' | 'rich' | 'error' | 'no-header';
export type CoTStepStatus = 'completed' | 'active' | 'pending' | 'error';

export interface CoTWebSource {
  title: string;
  domain: string;
  url: string;
}

export interface CoTDataCard {
  label: string;
  value: string;
  subtitle?: string;
}

export interface CoTStepItem {
  id: string;
  title: string;
  status: CoTStepStatus;
  duration?: string;
  icon?: React.ReactNode;
  toolName?: string;
  details?: string[];
  searchQueries?: string[];
  webSources?: CoTWebSource[];
  dataCards?: CoTDataCard[];
  errorMessage?: string;
}

export interface ChainOfThoughtMasterProps {
  variant?: CoTVariant;
  triggerTitle?: string;
  triggerIcon?: React.ReactNode;
  steps: CoTStepItem[];
  completionLabel?: string;
  defaultOpen?: boolean;
  autoCloseOnAllComplete?: boolean;
}
```

---

## ⚡ Integration Plan into `ChatSection.tsx`

1. **Clean Replacement:** Remove redundant `AIThinkingBlock` and `AgentPlanningBlock` calls in assistant messages.
2. **Dynamic Variant Selector:** 
   * If directive contains error $\rightarrow$ render `variant="error"`.
   * If directive is research/paper search $\rightarrow$ render `variant="rich"`.
   * If workspace grep/file read $\rightarrow$ render `variant="basic"`.
   * Default directive $\rightarrow$ render `variant="default"`.
3. **Smooth Slide & Fade Animations:** Full dark/light mode compatibility matching NALA's glassmorphism theme.

---

## 🚀 Execution & Verification Plan

1. **Phase 1:** Build `src/components/ui/ChainOfThoughtMaster.tsx` and `ChainOfThoughtMaster.css`.
2. **Phase 2:** Integrate into `ChatSection.tsx`.
3. **Phase 3:** Verify in browser at `http://localhost:3000` across all 5 directive types!
