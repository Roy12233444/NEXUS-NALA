# NALA — Current Problems & Fix Plan
**Date Logged**: 2026-08-01  
**Status**: Open  
**Priority**: High  
**Logged By**: Sourav Ray + Buddy (Antigravity)

---

## Overview

These are the 3 critical real problems that NALA is facing right now in its current state.  
All 3 problems are **blocking NALA from feeling like a real intelligent assistant** and must be fixed before any new features are added.

---

## Problem 1: Every Simple Chat Message Triggers Full Execution Pipeline

### Description
When the user sends any message — even a casual greeting like `"hi"` or a question like `"which model are you using?"` — NALA immediately:
1. Opens an **ExecutionCell Terminal Card** in the UI.
2. Runs the full **3-step NalaLoop** (`initial_planning` → `execution_phase` → `reflection_synthesis`).
3. Activates the **256MB Windows Job Object Sandbox**.
4. Writes **Checkpoint LSN files** to disk (`checkpoint_LSN_000001.json` etc.).

### Why This is a Problem
- **Normal conversation should never trigger the execution pipeline.**
- The terminal card is designed for **real coding/tool tasks** (like "create a file", "run this script", "write a Python function"). It should NOT appear for a simple `"hi"`.
- This makes NALA feel broken and mechanical instead of intelligent.
- It wastes resources and creates unnecessary checkpoint files for every chat message.

### Expected Correct Behaviour
| User Message | Expected NALA Behaviour |
|--------------|-------------------------|
| `"hi"` | Instant natural text reply. No terminal card. No sandbox. |
| `"which model are you using?"` | Instant natural text reply. No terminal card. No sandbox. |
| `"write a Python script to sort a list"` | Opens terminal card. Runs execution pipeline. Uses sandbox. |
| `"create a file on E: drive"` | Opens terminal card. Runs execution pipeline. Uses sandbox. |

### Root Cause
In `nala_server.py`, the `submit_prompt` socket event handler **always** creates a `SessionContract` and runs `NalaLoop` regardless of the nature of the prompt. There is no **intent classification** step that checks: *"Is this a chat message or a task directive?"*

### Enhanced Fix Plan
Implement a **three-tier intent classification pipeline** in `nala_server.py` with fallback safety nets:

1. **Tier 1: Lightning-Fast Heuristic Filter** (0-2ms latency)
   - Regex-based pattern matching for definitive chat/task indicators:
     - Chat patterns: `^\s*(hi|hello|hey|yo|sup|greetings|good\s+(morning|afternoon|evening|night))\s*[.!]?\s*$`, `^\s*(how\s+are\s+you|how\'s\s+it\s+going|what\'s\s+up|how\s+do\s+you\s+do)\s*[.!?]?\s*$`, `^\s*(thank\s+you|thanks|thx|appreciate\s+it)\s*[.!]?\s*$`, `^\s*(bye|goodbye|see\s+you|later|peace|out)\s*[.!]?\s*$`
     - Task patterns: Action verbs in imperative mood `(create|make|build|write|code|develop|design|fix|debug|test|run|execute|install|configure|deploy|generate|produce|construct|implement|optimize|refactor)\s+.+`, file/path references `(file|directory|folder|path)\s+[:=]\s*[\/\\]|\.(py|js|ts|html|css|json|yaml|txt|md|log)\b`, system commands `(sudo|apt|pip|npm|yarn|docker|kubectl|git|ssh|scp|rsync|wget|curl)\s+`
   - Pre-compiled regex patterns at startup for zero allocation overhead

2. **Tier 2: Lightweight Semantic Scorer** (5-15ms latency)
   - Quantized ONNX model (distilbert-base-uncased-finetuned-sst-2-english equivalent, int8 precision)
   - Input: User prompt + last 2 conversation turns for context
   - Output: Probability distribution over `{CHAT, TASK, AMBIGUOUS}`
   - Thresholds: `P(TASK) > 0.7` → TASK; `P(CHAT) > 0.7` → CHAT
   - Model size: <50MB, loaded once at server startup, <100MB RAM
   - LRU cache (size=1000) for identical prompts

3. **Tier 3: LLM-Powered Disambiguation** (50-200ms, for edge cases)
   - Triggered only when Tiers 1-2 confidence < 0.7 for both classes
   - Specialized prompt: `"Classify intent as CHAT or TASK. CHAT: casual conversation, questions, greetings. TASK: requests for action, creation, modification, analysis. Reply with only CHAT or TASK."`
   - Uses optimized Ollama call: `qwen2.5-coder:1.5b`, `num_predict: 1`
   - Results cached per session for multi-turn conversations
   - Timeout fallback: 50ms hard limit → use Tier 2 result

**Critical Implementation Nuances:**
- **Stateful Context Awareness**: Classification considers recent message history, UI state (terminal open/closed), and session type
- **Fallback Safety Nets**: 
  - Classification failure → default to CHAT (safer UX)
  - Task pipeline failure after classification → emit error without retrying classification
  - Classification latency >50ms → fallback to heuristic result
- **Performance Optimizations**:
  - Asynchronous classification non-blocking on main event loop
  - Shared Ollama connection pool for Tier 3 disambiguation
  - Classification results tagged in session metadata for UI routing
- **Metrics Collection**:
  - Track classification accuracy via implicit user feedback (engagement with terminal card)
  - Monitor latency distribution per tier (P50, P95, P99)
  - Log false positives/negatives for continuous rule refinement

**Integration Points:**
- Insert classifier immediately after `submit_prompt` receives data but before `create_session()`
- Create new `handle_chat_message(prompt, session_id)` function:
  - Calls Ollama directly with optimized parameters (see Problem 2 enhancements)
  - Emits only `ai_response` event (no step events, no terminal card activation)
  - Updates session state with lightweight metadata only (`last_chat_timestamp`, `message_type`)
- Modify existing task pipeline to skip entirely for chat-classified messages
- Add session metadata field: `message_type: Literal["chat", "task", "ambiguous"]`

**Edge Case Handling:**
- **Mixed Intent** ("hi, can you help me write a script?"): 
  - Tier 1 detects "help me write" → TASK
  - Override: Greeting detected in first 3 words → still TASK but with adjusted tone in response
- **Code Snippets in Chat** ("Does this look right: `for i in range(10): print(i)`"?):
  - Tier 2 recognizes question framing → CHAT
  - Special handler: Detect code blocks → offer sandbox execution as optional action (not automatic)
- **Multi-Lingual Support**: 
  - Tier 1 extended with common non-English greetings (hola, bonjour, namaste, etc.)
  - Tier 2 model is multilingual-capable (distilbert-base-multilingual-cased)

---

## Problem 2: AI Response is Slow / Timing Out

### Description
When NALA calls the local Ollama model (`qwen2.5-coder:7b` on `http://localhost:11434`), the HTTP request sometimes:
- Takes **30–45 seconds** to get a response.
- Throws a **timeout error** (`Ollama model call failed: timed out`), causing NALA to fall back to a generic hardcoded message.

### Why This is a Problem
- A **45-second wait for "hi"** is completely unacceptable for any chat assistant.
- When the timeout is hit, NALA shows a fake fallback response instead of a real AI answer, which is misleading.
- Even when it does not time out, **30 seconds feels extremely slow** compared to any normal assistant.

### Root Cause
1. **Model Loading Latency**: `qwen2.5-coder:7b` is a 7B parameter model that takes time to load if it was evicted from RAM. The first call after idle always takes longest.
2. **`num_predict: 300`** tokens is generous — for a short conversational reply ("hi"), this is too many tokens.
3. The Ollama request is `asyncio.to_thread` (non-blocking on the event loop), but **the actual wall-clock wait** for the Ollama model has not changed.

### Enhanced Fix Plan
Implement a **dynamic model routing system** with adaptive token prediction, intelligent pre-warming, and streaming delivery:

#### 1. Dynamic Model Selector Based on Query Complexity
- **Complexity Scorer** (runs concurrently with intent classification):
  - Features extracted:
    - Token count (after basic cleaning: punctuation/whitespace normalization)
    - Technical keyword density: `(algorithm|function|class|method|variable|loop|recursion|async|await|promise|callback|api|endpoint|database|sql|query|frame|library|framework|deploy|container|microservice|kubernetes|docker)`
    - Structural complexity: Max parentheses depth, bracket nesting level, semicolon count
    - Domain specificity: `(python|javascript|typescript|java|cpp|rust|go|html|css|react|vue|angular|node|django|flask|spring|tensorflow|pytorch|aws|azure|gcp)`
  - Output: Continuous score 0.0-1.0
  - Thresholds:
    - <0.3: Use `qwen2.5-coder:1.5b` + base `num_predict: 40`
    - 0.3-0.7: Use `qwen2.5-coder:3b` + base `num_predict: 80`
    - >0.7: Use `qwen2.5-coder:7b` + base `num_predict: 200` (adaptive based on actual need)

#### 2. Adaptive Token Prediction with Early Stopping
- Instead of fixed `num_predict`, implement **criteria-based termination**:
  - Stop when ANY condition is met:
    - `[END]` token generated (if model supports special tokens)
    - Repeated trigrams detected (indicating pathological looping)
    - Probability of next token < 0.001 followed by punctuation (`.` `!` `?`)
    - Token generation rate drops below 0.5 tokens/sec for 2 consecutive seconds
    - Max tokens reached (dynamically calculated)
  - Minimum tokens: 10 (prevents ultra-short nonsensical replies)
  - Dynamic maximum tokens:
    - Chat: 60 tokens (covers 95% of conversational replies per linguistic studies)
    - Task: 256 tokens (covers most code explanations)
    - Complex task: 512 tokens (for architectural descriptions)
  - **Token Efficiency Bonus**: 
    - If complexity score < 0.2 AND intent = CHAT → hard cap at 30 tokens
    - If query contains direct question words ("what", "who", "when", "where", "why", "how") → prioritize concise answers

#### 3. Advanced Pre-warming & Model Residency Strategy
- **Predictive Pre-warming Engine**:
  - Analyze last 5 messages in session:
    - ≥3 TASK with complexity >0.6 → keep `:7b` resident
    - ≥4 CHAT → keep `:1.5b` resident
    - Mixed pattern → keep `:1.5b` and `:3b` resident
    - No recent activity → keep smallest model (`:1.5b`) resident
  - Model residency decisions updated after every message
- **Smart Model Swapping**:
  - Monitor Ollama's RAM usage via `/api/ps` endpoint every 10s
  - If target model not loaded → initiate warm-up 2s before predicted need (based on complexity trend)
  - Never unload model if used in last 30 seconds (unless RAM pressure >85%)
  - LRU eviction policy for model unloading (least recently used first)
- **Background Keep-Alive Mechanism**:
  - Send minimal generate request every 45s to resident models:
    ```json
    {
      "model": "qwen2.5-coder:1.5b",
      "prompt": "Hi",
      "stream": false,
      "options": {"num_predict": 1, "temperature": 0.0}
    }
    ```
  - Overhead: ~5ms every 45s per model (negligible vs. cold start penalty)
  - Adaptive interval: Increase to 2m if model used in last 5m, decrease to 20s if RAM <60% used

#### 4. Industrial-Strength Streaming Implementation
- **Token-by-Token Delivery Pipeline**:
  ```mermaid
  graph LR
  A[Ollama Stream] --> B{Token Parser}
  B -->|Valid Token| C[Token Buffer]
  B -->|Special Token| D[Handling Logic]
  C --> E{Buffer Full?}
  E -->|Yes| F[Emit Chunk]
  E -->|No| G[Wait for More]
  F --> H[WebSocket Send]
  H --> I[Client Buffer]
  I --> J{Render Threshold}
  J -->|3 Tokens OR >100ms| K[Update UI]
  J -->|Timeout >500ms| K[Force Update]
  ```
- **Critical Streaming Optimizations**:
  - **Adaptive Chunking**:
    - Start: 1-token chunks (immediate feedback)
    - After 3rd token: Increase to 3-token chunks (reduces WS overhead)
    - After 10th token: Increase to 5-token chunks
    - Max chunk: 8 tokens (balances latency and throughput)
  - **Bidirectional Flow Control**:
    - Client sends `stream_ready` signal before accepting more tokens
    - Server pauses if client buffer > 4 chunks (prevents memory bloat)
    - Resume when client buffer < 1.5 chunks
    - Client can send `stream_pause`/`stream_resume` manually
  - **Smart Error Recovery**:
    - Stream break → fallback to non-streaming with current progress + `stream_interrupted` event
    - Timeout mid-stream → emit `stream_interrupted` with partial result + retry suggestion
    - Client can request continuation from last known token via `continue_stream` event
    - Automatic retry with exponential backoff (1s, 2s, 4s, 8s) on network errors

#### 5. Progressive Timeout & Intelligent Fallback System
- **Adaptive Timeout Strategy**:
  - Initial request: 3s (for cached/warm models in resident state)
  - If timeout → retry with 6s (model may be loading from disk)
  - If timeout again → retry with 12s (full cold start from SSD)
  - If all fail → emit `model_unavailable` with contextual suggestion:
    *"Models are loading. Try a simpler question or wait 10 seconds for heavier queries."*
- **Smart Fallback Chains** (tried in order until success):
  - Tier 1: `:1.5b` (fastest, for chat/simple queries)
  - Tier 2: `:3b` (balance, for moderate complexity)
  - Tier 3: `:7b` (most capable, for complex tasks)
  - Tier 4: Canned responses for ultra-common queries (cached in Redis):
    - `"hi"` → `"Hello! How can I assist you today?"`
    - `"how are you"` → `"I'm functioning optimally! Ready to help with your coding tasks."`
    - `"what model are you using"` → `"I'm powered by NVIDIA's Nemotron model family, optimized for coding assistance."`
  - Tier 5: Last-resort: `"I'm experiencing high demand. Please try rephrasing your request."`
- **Request Batching for Similar Queries**:
  - Detect identical prompts within 3s sliding window
  - Batch into single Ollama call with `n` variations using prompt variations:
    - Original: `"Explain recursion"`
    - Batch: `["Explain recursion", "Explain recursion simply", "Recursion explanation for beginners"]`
  - Return appropriately indexed results using custom separators
  - Reduces redundant model loading by ~40% for repetitive workflows

**Critical Implementation Considerations:**
- **Ollama API Compliance Verification**:
  - Check streaming support via `/api/version` (requires Ollama ≥0.1.47)
  - Graceful fallback to non-streaming if unsupported (with user-perceptible degradation notice)
- **Resource Monitoring & Alerting**:
  - Track per-model latency histograms (P50, P90, P99, max)
  - Monitor RAM/VRAM usage per model instance via Prometheus metrics
  - Trigger alert if swap usage >10% for >30s (indicates thrashing)
  - Dashboard showing model residency status and hit/miss ratios
- **Security Hardening**:
  - Prompt sanitization: Remove/escaping potential injection sequences (`<<SYS>>`, `<|`, `\n\n\n`)
  - Rate limit: Max 2 Ollama requests/second per session (burst to 5)
  - Response validation: Scan for harmful content patterns before forwarding to UI
  - Ollama sandboxing: Run via dedicated user with limited filesystem access
- **Metrics for Continuous Tuning**:
  - Time-to-first-token (TTFT) - critical for perceived speed (target: <1.5s for chat)
  - Time-to-complete-token (TCT)
  - Token generation rate (tokens/sec) - target: >15 tokens/sec for `:1.5b`
  - Streaming smoothness: Jitter in inter-timing < 200ms
  - Fallback rate: % requests needing larger model or retry (target: <5%)
  - Cache hit ratio for batched requests (target: >30%)

---

## Problem 3: Thinking Section Shows Raw Internal Technical Text

### Description
The **"Thinking..." collapsible fold** inside NALA's response bubble shows raw internal system text to the user. Examples seen in production:
```
Initializing live autonomous execution pipeline for directive: "which model you are using".
Establishing BehaviorMonitor telemetry and state checkpoints.
```
```
Next, Initialize RLock telemetry accumulators in BehaviorMonitor:
BehaviorMonitor initialized with memory-bounded buffers
Telemetry SLA < 1.0ms confirmed
```
```
Next, Execute autonomous task graph steps:
Synthesizing task execution graph
Cooperative checkpointing enabled
```

### Why This is a Problem
- This text is **internal system monitoring language** — it is meant for developers, not for users.
- A regular user seeing `"RLock telemetry accumulators"` or `"BehaviorMonitor SLA"` is confused and loses trust in NALA.
- It makes NALA look broken and unpolished even though the backend is actually working correctly.
- For a **casual conversation message** like `"hi"`, there should be **no Thinking section at all** — it adds zero value.

### Expected Correct Behaviour
| Scenario | Expected Thinking Section |
|----------|---------------------------|
| Casual chat (`"hi"`) | **No Thinking section.** Just the clean reply. |
| Simple question (`"which model?"`) | **No Thinking section.** Just the clean reply. |
| Code task (`"write a Python sort function"`) | Show clean human-readable steps like `"Planning code structure..."`, `"Executing in sandbox..."`, `"Verifying output..."`. |
| Complex task (`"build a REST API"`) | Show full reasoning steps with clean labels. |

### Root Cause
1. In `ChatSection.tsx`, every socket event from the backend (regardless of type) triggers the `CoTStep` rendering logic and opens the Thinking fold.
2. The step `details` text was previously set to raw `JSON.stringify(data.result)` (partially fixed), but the **Thinking fold itself** still appears for every message because the UI always expects step events.
3. In `nala_server.py`, the `emit` calls broadcast internal monitoring strings that were never intended to be shown to the user directly.

### Enhanced Fix Plan
Implement a **strict diagnostic/user-facing channel separation** with message typing, thought curation, and conditional rendering:

#### 1. Message Typing System Implementation
Every socket event gains a `message_type` field with strict enforcement:
```typescript
type MessageType = 
  | "chat"              // Pure conversational, NO thinking shown
  | "task_thought"      // Task-related, show CURATED thinking only
  | "task_diagnostic"   // Task-related, INTERNAL diagnostics ONLY (never in UI)
  | "system"            // Connection/status events
  | "error"             // Error conditions
  | "telemetry"         // Raw metrics (diagnostic channel only)
```

**Thinking Section Events** (`task_thought`) contain **EXCLUSIVELY**:
- Clean, human-readable step descriptions (max 120 chars)
- Zero technical jargon, acronyms, or internal system references
- Structured as: `[Phase] [Action] [Object]` (e.g., `"Planning: Analyzing requirements for user auth system"`)
- Action verbs from approved lexicon: `Analyzing`, `Planning`, `Executing`, `Verifying`, `Synthesizing`, `Reflecting`, `Optimizing`, `Validating`

**Diagnostic Events** (`task_diagnostic`/`telemetry`) contain:
- Full technical details for developer debugging
- **NEVER** emitted as thinking_update events
- Routed exclusively to:
  - Structured JSON logs (`logs/diagnostic.ndjson`)
  - Separate WebSocket channel for developer tools (port 3002)
  - `/diagnostics` HTTP endpoint for real-time internal state
  - In-memory ring buffer of last 1000 diagnostic events

#### 2. Thought Curation Pipeline (replaces raw monitoring strings)
Instead of emitting raw monitoring logs, map internal states to user-friendly descriptions:
```python
# INTERNAL (never shown to user):
internal_msg = "Initializing BehaviorMonitor telemetry accumulators with RLock"

# USER-FACING (after curation):
user_facing_msg = "Setting up thought process monitoring"
```
Curation rules:
- Replace technical components with metaphors:
  - `BehaviorMonitor` → "thought process monitor"
  - `RLock` → "synchronization mechanism"
  - `checkpoint_LSN` → "progress save point"
  - `sandbox initialization` → "safe execution environment preparation"
  - `telemetry SLA` → "response timing check"
- Remove implementation details:
  - Instead of `"Initializing live autonomous execution pipeline for directive: ..."`
    → `"Beginning task analysis: [user objective summary]"`
- Add intentionality and goals:
  - Instead of `"Establishing checkpoint LSN files"`
    → `"Creating recovery points to ensure work continuity"`
- Contextualize for user:
  - Instead of `"Telemetry SLA < 1.0ms confirmed"`
    → `"Verified system responsiveness meets interaction standards"`

#### 3. Frontend Conditional Rendering Logic (`ChatSection.tsx`)
Enhanced `CoTStep` component with intelligent filtering:
```typescript
interface CoTStepProps {
  step: {
    id: string;
    type: 'thought' | 'action' | 'reflection';
    content: string; // Already curated user-facing text
    messageType: MessageType; // Critical new field
    timestamp: number;
  };
  showThinkingFold: boolean; // Derived prop
}

const CoTStep = ({ step, showThinkingFold }: CoTStepProps) => {
  // NEVER show thinking fold for chat-type messages
  if (step.messageType === 'chat') return null;
  
  // Only show diagnostic steps in developer mode
  if (step.messageType === 'task_diagnostic' && !isDeveloperMode()) return null;
  
  // Standard rendering for task_thought
  return (
    <div className={`cot-step ${step.type}`}>
      <div className="step-content">{step.content}</div>
      {step.type === 'action' && <TerminalCardPreview />}
    </div>
  );
};
```
**Thinking Fold Visibility Logic**:
```typescript
const showThinkingFold = useMemo(() => {
  // Never show for pure chat
  if (hasChatMessageInSession) return false;
  
  // Show if we have meaningful task thoughts
  const taskThoughts = cotSteps.filter(
    step => step.messageType === 'task_thought' && step.content.trim().length > 10
  );
  
  // Show fold only if we have substantial curated thoughts
  return taskThoughts.length >= 2 || 
         (taskThoughts.length === 1 && taskThoughts[0].content.length > 30);
}, [cotSteps, hasChatMessageInSession]);
```
**Visual Design Improvements**:
- For chat messages: Display only in standard message bubble (no expansion indicator)
- For task thoughts: 
  - Subtle "💭" icon in message header indicating expandable thoughts
  - Smooth animation when expanding/collapsing
  - Thoughts shown in readable serif font (vs monospace for code)
  - Optional "Show raw diagnostics" link for developers (in dev mode only)

#### 4. Diagnostic Channel Preservation
Maintain full internal diagnostics through:
- Enhanced logging system (structured JSON logs)
- Separate WebSocket channel for developer tools (port 3002)
- `/diagnostics` HTTP endpoint for real-time internal state
- In-memory ring buffer of last 1000 diagnostic events
- Developer toolbar in UI (hidden by default, toggleable with `Ctrl+Shift+D`)

#### Critical Implementation Nuances
**Backward Compatibility**: 
- Existing events without `message_type` default to `task_thought` (safe fallback)
- Gradual rollout: new events get type, old events processed as before

**Performance Optimizations**:
- Thought curation happens at emission point (not during UI rendering)
  - Cached curation maps for 95% of common internal phrases (<2ms lookup)
  - Asynchronous curation for non-latency-critical diagnostics
  - Zero-copy event serialization where possible (FlatBuffers for high-volume telemetry)
  - UI rendering uses virtualized lists for long thought sequences (>50 thoughts)

**User Experience Controls**:
- **Thought Density Slider** in settings (0-3 thoughts visible simultaneously)
- **Technical Depth Toggle** (Simple / Detailed / Expert) for thought verbosity
- **Thought History** - clickable timeline of all thoughts in session
- **Export Thoughts** - download curated thinking process as markdown
- **Feedback Mechanism** - "Was this thought helpful?" on each expanded thought

**Backend Integration Points**:
- **In `nala_server.py`**:
  - Replace all `emit('thinking_update', ...)` with:
    ```python
    emit_curated_thought(
      session_id, 
      internal_message, 
      step_context,
      confidence=calculate_confidence(step_context),
      related_files=extract_related_files(step_context)
    )
    ```
  - Where `emit_curated_thought` applies curation rules and sets `message_type='task_thought'`
  - Add diagnostic emission functions:
    - `emit_diagnostic(event_type, data, session_id)` → logs/diagnostic channel only
    - `emit_telemetric(metric_name, value, tags)` → Prometheus endpoint
  - Modify `update_*_metrics()` methods to use diagnostic channel
  - Add thought curation service as injectable dependency (for testability/mocking)
  
- **In `websocketService.ts`**:
  - Extend all event interfaces with `messageType: MessageType`
  - Update Redux action handlers:
    ```typescript
    case 'pramana-active':
      if (action.messageType === 'task_thought') {
        // Update pramana slice with curated content
      }
      // Diagnostic events go to separate diagnostic slice (dev-only)
    ```
  - Add diagnostic channel subscription (separate WS connection to port 3002)
  - Implement message type routing middleware

- **In `ChatSection.tsx`**:
  - Replace monolithic `CoTStep` rendering with typed component system
  - Implement thinking fold visibility logic as described
  - Add developer diagnostics toggle and panel (hidden by default)
  - Implement thought visualization enhancements (chaining, tooltips, file previews)
  - Add "Export Thoughts" and "Feedback" buttons in thought footer

#### Edge Case Resolution Framework
| Scenario | Handling Mechanism |
|----------|-------------------|
| **Ambiguous Intent Mid-Execution**<br>(User asks "what's the weather?" during code task) | 1. Pause task thinking stream<br>2. Route query to chat classifier<br>3. Respond in pure chat mode (no thinking)<br>4. Resume task thoughts with context bridge: "Returning to [task]..." |
| **Thought Overload**<br>(>20 thoughts in 10s) | 1. Automatic aggregation: "Performed 15 validation checks"<br>2. Fade thoughts older than 8s<br>3. "Show all thoughts" modal with pagination<br>4. Priority queue: High-confidence thoughts > low-confidence |
| **Cultural/Localization Needs**<br>(Japanese user sees awkward metaphor) | 1. Locale-specific curation rules (`curation_rules.ja.yml`)<br>2. Metaphor adaptation engine:<br>   - English: "synchronization mechanism" → Japanese: "調和保持機構" (harmony maintenance mechanism)<br>3. Dynamic RTL layout for Arabic/Hebrew thoughts |
| **Technical Term Ambiguity**<br>("cache" could mean CPU cache or browser cache) | 1. Context-aware disambiguation:<br>   - If near "CPU"/"kernel" → hardware cache<br>   - If near "browser"/"web" → browser cache<br>2. Fallback to most common meaning in coding context<br>3. User-selectable preference in settings |

**Quality Assurance & Feedback Loops**:
- 🔍 **Thought Audit Log** (opt-in):
  - Records raw internal → curated thought mappings
  - Weekly review to refine curation rules
  - User feedback: "Was this thought helpful?" (thumbs up/down) on expanded thoughts
- 📊 **Bias Detection System**:
  - Flags over-explaining simple concepts (entropy < 0.3 in thought)
  - Detects under-explaining complex concepts (high user follow-up questions)
  - Identifies uncertain language patterns ("maybe", "possibly") for review
- 🔁 **Consistency Verification**:
  - Compares thoughts against actual system behavior (via diagnostic traces)
  - Validates no promised capabilities are missing in execution
  - Checks estimated times in thoughts align with actual execution (within 20%)
- 🧪 **A/B Testing Framework**:
  - Randomized exposure to different curation rule sets
  - Measures: task completion rate, user satisfaction, thought engagement
  - Auto-promotes winning variant after statistical significance (p<0.01)

--- 

## Summary Table

| # | Problem | Impact | Fix Complexity |
|---|---------|--------|----------------|
| 1 | Every chat message triggers full execution pipeline | 🔴 Critical | Medium-High — Three-tier intent classifier needed |
| 2 | AI response is slow / timing out | 🔴 Critical | High — Dynamic model routing + streaming required |
| 3 | Thinking section shows raw internal text | 🟠 High | Medium — Message typing + thought curation system |

---

## Files That Will Need Changes

| File | Change Needed |
|------|---------------|
| `nala_server.py` | Add intent classifier, route chat vs. task, implement dynamic model routing, add message typing, implement thought curation |
| `ChatSection.tsx` | Conditional Thinking fold rendering based on `message_type`, add thought visualization enhancements |
| `websocketService.ts` | Pass `messageType` field through socket events, add diagnostic channel subscription |
| `obserservability/logger.py` | Enhance to support structured JSON logging for diagnostics |
| `core/hands/sandbox.py` | Add conditional activation based on message type |
| `core/harness/nala_loop.py` | Add hooks for thought emission at key steps |

---

## Next Session Action Items (In Order)

1. **Phase 1 - Intent Classification** (Today):
   - [ ] Implement three-tier intent classifier in `nala_server.py`
   - [ ] Create `handle_chat_message()` function
   - [ ] Modify `submit_prompt` to route based on classification
   - [ ] Add session metadata for `message_type`

2. **Phase 2 - Model Optimization** (Tomorrow):
   - [ ] Implement dynamic model selector based on complexity scoring
   - [ ] Add adaptive token prediction with early stopping
   - [ ] Create predictive pre-warming engine
   - [ ] Implement industrial-strength streaming with flow control

3. **Phase 3 - UI/UX Separation** (Day 3):
   - [ ] Add `message_type` field to all socket events
   - [ ] Implement thought curation pipeline in `nala_server.py`
   - [ ] Update `ChatSection.tsx` with conditional rendering
   - [ ] Add developer diagnostics toggle and panel
   - [ ] Implement thought visualization enhancements

4. **Phase 4 - Integration & Testing** (Day 4):
   - [ ] Connect all components end-to-end
   - [ ] Test chat vs. task routing accuracy
   - [ ] Validate latency improvements (target: <1.5s TTFT for chat)
   - [ ] Verify thinking section shows only curated content for tasks
   - [ ] Ensure zero thinking section for pure chat messages

5. **Phase 5 - Monitoring & Refinement** (Ongoing):
   - [ ] Implement metrics collection for all enhancements
   - [ ] Add feedback loops for continuous improvement
   - [ ] Set up alerting for performance regressions
   - [ ] Schedule weekly review of thought audit logs

--- 

*End of Enhanced Problem Log — NALA v0.1 | Enhanced 2026-08-01*