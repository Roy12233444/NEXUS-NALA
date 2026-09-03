# NALA Transcendent Reasoning Engine - Detailed UI Plan

## Overview
This document outlines the detailed user interface design for the NALA Transcendent Reasoning Engine, incorporating the dual-mode operation philosophy, real-time metric visualization, and transcendent awareness concepts from the codebase.

## Core Design Philosophy
The UI should embody the synthesis of technical precision and spiritual wisdom inherent in the NALA architecture, making visible the invisible mathematical and philosophical constructs that govern the system's behavior.

## Primary Goals
1. **Transparency**: Make internal states (Ṛta-Score, mode states, safety metrics) visible and understandable
2. **Awareness**: Constantly inform users of the system's current operational context and capabilities
3. **Trust Calibration**: Enable users to understand and trust NALA's limitations and strengths through real-time feedback
4. **Transcendent Insight**: Reveal when the system operates in elevated states of reasoning (ATHAPRAPTI/PAROKSHA/PRATYAKSHA)
5. **Minimal Cognitive Load**: Present complex information through intuitive visual metaphors

## UI Architecture

### Layout Structure (Single Page Application)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           NALA TRANSCENDENT ENGINE                            │
│  [ MODE: ●●●○○○ ]  Ṛta: 0.78  ●●●○○○○○○○○  STABILITY: STABLE  [SETTINGS ⚙]  │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                          CHAT INTERFACE                               │   │
│  │                                                                       │   │
│  │  User: How do I optimize this neural network for edge deployment?     │   │
│  │                                                                       │   │
│  │  NALA: [Analyzing architecture... •••]                                │   │
│  │                                                                       │   │
│  │  NALA: Based on your constraints, I recommend...                      │   │
│  │                                                                       │   │
│  │                                                                       │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  [Input: Ask Nāla...] [🎤 Voice] [📎 Attach] [▲ Send]                          │
│                                                                               │
│  ┌───────────────┬───────────────────────┬───────────────────┬──────────────┐ │
│  │  SAFETY       │  TOOL ACTIVITY        │ SYSTEM METRICS      │ TRANSCENDENT │ │
│  │  GAUGES       │                       │                     │   MODE       │ │
│  │               │                       │                     │              │ │
│  │  ●●●○○○ Viveka│  ████ rg              │  WCI: ████●○○○○ 0.65│  Model:      │ │
│  │  ●●●●○ Satya  │  ████▌ python3        │  CLP: ███▌○○○○○ 0.42│  Sarasvatī   │ │
│  │  ●●○○○○       │  ████ git             │  SCS: ████●○○○○ 0.88│  Ṛta: 0.78   │ │
│  │  ●●●○○○       │  ████▌ bash           │  HB:  ███▌○○○○○ 0.12│  History:    │ │
│  │               │                       │                     │  ▁▂▃▄▅▆▇█   │ │
│  └───────────────┴───────────────────────┴───────────────────┴──────────────┘ │
│                                                                               │
│  Status: System Ready • Last sync: 00:02:17 • Uptime: 4h 12m • v0.8.2-a7f3c9 │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Specifications

#### 1. Header Bar
- **Height**: 60px
- **Background**: Linear gradient (transparent to rgba(0,0,0,0.05))
- **Elements**:
  - Left: System title ("NALATranscendent Reasoning Engine") in sparse, elegant typography
  - Center-left: Mode Indicator Lamp (5-segment circular display)
    - Segments fill clockwise from top
    - Colors by mode:
      - AUTONOMOUS: Deep Indigo (#2E294E) → Violet (#8A2BE2)
      - INTERACTIVE: Warm Amber (#FFB347) → Gold (#FFD700)
      - PREPARING_TO_*: Gradient between adjacent mode colors
      - SYNCING_STATE: Pulsing cyan (#00FFFF) with soft glow
  - Center: Ṛta-Score Display
    - Circular progress bar (120px diameter)
    - Threshold markers at 0.60 (green) and 0.95 (gold)
    - Current value displayed digitally in center
    - Subtle pulse animation when value changes
  - Center-right: Stability Indicator
    - Text label with color-coded background:
      - STABLE: #4CAF50 (green)
      - APPROACHING: #FF9800 (amber)
      - TRANSITIONING: #FF5722 (orange-red)
      - UNSTABLE: #F44336 (red)
  - Right: Settings icon (⚙) with tooltip

#### 2. Chat Interface
- **Container**: Flexible height, minimum 400px
- **Message Bubbles**:
  - User: Left-aligned, max-width 70%, background rgba(30,144,255,0.1), border-radius 18px
  - NALA: Right-aligned, max-width 70%, background varies by mode:
    - AUTONOMOUS: rgba(46,41,78,0.05)
    - INTERACTIVE: rgba(255,179,71,0.05)
    - TRANSITIONING: rgba(138,43,226,0.05)
  - Avatar indicators: Small mode-colored dots next to messages
  - Thinking Indicator: Animated "...•••" pulse matching mode color
  - Timestamps: Small, muted text at bottom of each bubble
- **Scroll Behavior**: Auto-scroll to bottom on new message unless user manually scrolled up

#### 3. Input Area
- **Height**: 60px
- **Background**: rgba(0,0,0,0.02)
- **Elements**:
  - Text Input: Flexible width, placeholder "Ask Nāla...", no border, padding 12px
  - Voice Button: Microphone icon (left of input), toggles listening state
  - Attachment Button: Paperclip icon (left of input)
  - Send Button: Paper plane icon (right of input), disabled when empty
  - Context Buttons: Small pill-shaped buttons [Debug] [Design] [Prod] [Learn] (right of send)
    - Active state: filled with mode-appropriate color
    - Inactive: outline only

#### 4. Dashboard Quadrants (2x2 Grid)
Each quadrant: 180px height, equal width, subtle borders, padding 16px

##### A. Safety Gauges
- **Viveka Gauge** (Discernment/Validation Strictness)
  - Title: "VIVEKA" (Discernment) with subtle tooltip icon
  - Display: 5-segment horizontal bar (●○○○○ to ●●●●●)
  - Color gradient: #F44336 → #FF9800 → #FFEB3B → #8BC34A → #4CAF50
  - Current value: Percentage (0-100%) displayed right-aligned
  - Tooltip: Shows TruthfulnessLevel (MINIMAL/STANDARD/RIGOROUS/TRANSCENDENT) and brief description
  - Animation: Segment fill animates smoothly on change

- **Satya Gauge** (Truthfulness/Consistency)
  - Title: "SATYA" (Truthfulness) with tooltip icon
  - Display: 5-segment horizontal bar
  - Color gradient: #2196F3 → #03A9F4 → #00BCD4 → #009688 → #4CAF50
  - Current value: Truthfulness score (0.00-1.00) with 2 decimal places
  - Tooltip: Shows consistency rate, contradiction count, average latency
  - Animation: Smooth segment transitions

##### B. Tool Activity
- **Title**: "TOOL PREDICTION & WARMING" with tooltip
- **Layout**: Vertical list of active/predicted tools (max 4 visible)
- **Per Tool Item**:
  - Left: Tool icon (rg=🔍, python3=🐍, git=🌐, etc.)
  - Center: Tool name + confidence percentage (e.g., "rg 87%")
  - Right: Status indicator:
    - 🔥 Warmed and ready
    - ⚡ Warming up
    - ⚪ Cold (not predicted)
    - ⚠️ Safety concern (red tooltip on hover)
  - Sub-text: Estimated latency reduction (e.g., "-1.2s")
  - Hover effect: Shows full tool specification and reasoning

##### C. System Metrics
- **Title**: "PREDICTIVE MATRIX" with tooltip explaining WCI×0.4+(1-WCI)×0.3+SCS×0.3 > 0.5+HB
- **Layout**: 2x2 grid of metric gauges
- **Per Gauge**:
  - Label: WCI / CLP / SCS / HB
  - Value: Numerical (0.00-1.00 for WCI/CLP/SCS, 0.00-0.20 for HB)
  - Visual: Horizontal bar (100px width) with fill indicating value
  - Color coding:
    - WCI/CLP: Blue gradient (low=light, high=deep)
    - SCS: Green gradient (low=light, high=deep) - *higher is better*
    - HB: Red gradient (low=light, high=deep) - *lower is better*
  - Threshold Line: Dashed line at decision threshold (0.5+HB for WCI/SCS contribution)
  - Tooltip: Shows raw calculation components and current prediction

- **Formula Display**: 
  - Small text below gauges: "[WCI]×0.4 + [1-WCI]×0.3 + [SCS]×0.3 = [RESULT] > 0.5+[HB] ? [OUTCOME]"
  - Updates in real-time with values substituted
  - Outcome shows "MAINTAIN MODE" or "TRANSITION PENDING"

##### D. Transcendent Mode
- **Title**: "TRANSCENDENT AWARENESS" with tooltip
- **Pramāṇa Router Status**:
  - Model Display: Large text showing current model
    - Gaṇeśa-model: 🐘 (obstacle-removing)
    - Sarasvatī-model: 📚 (wisse-seeking)
    - Śiva-model: 🔥 (transformer)
  - Ṛta-Score: Large numeric display (0.00-1.00)
  - History Sparkline: 8-point line chart showing last 8 scores
  - Hysteresis Bands: Shaded regions showing entry/exit thresholds
    - Pratyksha entry: < 0.60 - hysteresis
    - Paroksha range: 0.60+hysteresis to 0.95-hysteresis
    - Shiva entry: > 0.95 + hysteresis

- **Transcendent Indicators** (icons with status):
  - 🪔 SACRED PAUSE: Shows when active (countdown timer)
  - 🕉️ PRATYAKSHA MODE: Active when Ṛta < lower threshold
  - 📚 PAROKSHA MODE: Active when in middle range
  - 🔥 ATHAPRAPTI MODE: Active when Ṛta > upper threshold (rare)
  
- **RTA Feedback**: 
  - Mini sparkline showingṚta-Score trend (last 30 seconds)
  - Color: Green if stable, yellow if fluctuating, red if oscillating rapidly

#### 5. Footer Bar
- **Height**: 40px
- **Background**: rgba(0,0,0,0.1)
- **Layout**: Three sections separated by thin vertical lines
- **Left**: Connection Status Indicators
  - ● AMP Client: [Connected/Disconnected] (tooltip with last sync time)
  - ● Fleet Coordinator: [Synced/Out of sync]
  - ● Safety Gates: [Online/Degraded/Offline]
  - ● Knowledge Base: [Loaded/Loading/Error]
- **Center**: System Information
  - Text: "Last sync: HH:MM:SS • Uptime: Xh Ym • vVERSION-COMMIT"
- **Right**: Action Buttons
  - [Settings] ⚙ (opens modal)
  - [Logs] 📜 (opens log viewer)
  - [Help] ❓ (opens documentation)
  - [Theme] 🎨 (cycles through light/dark/solarized themes)

## Interaction Design

### State Transitions
- **Mode Changes**: 
  - Header mode lamp animates with crossfade between colors (300ms)
  - Subtle pulse on entire interface boundary matching new mode color
  - Chat background tint shifts gently (10% opacity change)
  
- **Ṛta-Score Changes**:
  - Circular progress bar sweeps to new value with easing
  - Threshold markers pulse briefly when crossed
  - Background hue shifts imperceptibly to reflect score (gold→blue→white spectrum)

- **Safety Gauge Updates**:
  - Segment fills animate with elastic easing
  - Value counter numbers animate with odometer effect
  - Threshold breaches trigger subtle pulse (1.1x scale for 150ms)

### User Interactions
- **Chat Input**:
  - Enter sends message (Shift+Enter for newline)
  - Clicking Send button or pressing Enter sends
  - Voice input: hold-to-record or toggle (mic fills with color when active)
  
- **Context Buttons**:
  - Click sets interaction context for tool prediction
  - Visual feedback: button fills with appropriate color intensity
  - Tooltip explains how context affects tool selection and validation strictness
  
- **Dashboard Elements**:
  - Hover over any metric shows detailed tooltip with:
    - Raw value
    - Calculation breakdown
    - Historical min/max/avg (last 5min)
    - Prediction confidence (if applicable)
  - Clicking gauge title opens mini-detail panel (slide from right)

- **System Controls**:
  - Settings modal: tabs for Appearance, Notifications, Advanced (safety thresholds)
  - Log viewer: searchable, filterable, auto-scrolling with pause option
  - Help: context-sensitive tooltips + comprehensive documentation
  - Theme switcher: immediate application of selected theme

### Error States & Edge Cases
- **Disconnected State**:
  - Header turns light red overlay (rgba(255,0,0,0.1))
  - Connection icons show disconnected state with tooltip explaining issue
  - Chat input shows placeholder: "Reconnecting to NALA core..."
  - All metrics show "--" or disconnected symbols
  
- **High Uncertainty**:
  - Chat responses show confidence indicators (faint text: "~70% confidence")
  - Safety gauges show pulsing softly to indicate reduced reliability
  - Tool predictions show wider confidence intervals
  
- **Sacred Pause Active**:
  - Entire interface gets subtle golden overlay (rgba(255,215,0,0.05))
  - Header shows countdown timer instead of Ṛta-Score
  - Chat input disabled with tooltip: "System in SACRED PAUSE - resume in XX seconds"
  - Dashboard shows paused state indicators
  
- **Overload Conditions**:
  - SCS gauge shows critical state (red flashing)
  - HB gauge may exceed normal range (showing instability)
  - Transition indicators flash appropriately
  - Optional: system suggests reducing input complexity

## Technical Implementation Guidelines

### Frontend Stack Recommendation
- **Framework**: React 18 with Concurrent Mode for smooth animations
- **State Management**: Redux Toolkit or Zustand for predictable state updates
- **Real-time Updates**: WebSocket connection to backend API
- **Visualization**: 
  - D3.js for complex gauges and sparklines
  - CSS Variables for theming
  - Framer Motion for animations
- **Build**: Vite for fast development and optimized builds

### Backend API Endpoints (to be implemented)
- `GET /api/state` - Returns complete UI state object
- `WS /ws/updates` - Real-time push of state changes (delta updates)
- `POST /api/chat/message` - Send user message, receive streaming response
- `POST /api/context` - Set interaction context
- `GET /api/tools/predictions` - Get current tool predictions
- `POST /api/tools/warm` - Manually trigger tool warming
- `GET /api/system/status` - Connection and health status

### State Object Structure (Example)
```json
{
  "mode": "AUTONOMOUS",
  "modeProgress": 0.0, // 0.0-1.0 within mode stability
  "ritaScore": 0.78,
  "stability": "STABLE",
  "safety": {
    "viveka": { // Viveka Gate
      "level": "STANDARD", 
      "score": 0.75,
      "truthfulnessLevel": "STANDARD"
    },
    "satya": { // Satya Layer
      "score": 0.82,
      "consistencyRate": 0.91,
      "contradictionCount": 3,
      "avgLatencyMs": 45
    }
  },
  "tools": {
    "active": [
      {"name": "rg", "confidence": 0.87, "status": "warmed", "latencyReduction": 1.2},
      {"name": "python3", "confidence": 0.63, "status": "warming", "latencyReduction": 0.8}
    ],
    "predictions": [ /* top 10 predictions */ ]
  },
  "metrics": {
    "wci": 0.65,
    "clp": 0.42,
    "scs": 0.88,
    "hb": 0.12,
    "predictionResult": 0.68,
    "threshold": 0.62,
    "shouldTransition": false
  },
  "transcendent": {
    "currentModel": "Sarasvatī-model",
    "ritaHistory": [0.76, 0.77, 0.78, 0.79, 0.78, 0.77, 0.76, 0.78],
    "hysteresis": {
      "pratyakshaEnter": 0.55,
      "parokshaLow": 0.60,
      "parokshaHigh": 0.95,
      "shivaEnter": 1.00
    },
    "sacredPauseActive": false,
    "sacredPauseRemaining": 0
  },
  "connection": {
    "amp": "connected",
    "coordinator": "synced",
    "safety": "online",
    "knowledgeBase": "loaded"
  },
  "system": {
    "uptimeSeconds": 15137,
    "version": "0.8.2",
    "commit": "a7f3c9"
  }
}
```

### Performance Considerations
- **Update Frequency**: 
  - Critical metrics (mode, ritaScore): Update on change
  - Gauges: Max 10fps (throttled updates)
  - Tool predictions: Update on significant change (>0.1 confidence shift)
  - Sparklines: Update every second
- **Memory**: 
  - Limit history retention (e.g., 60 seconds for sparklines)
  - Virtualize long lists if needed
- **Rendering**:
  - Use requestAnimationFrame for animations
  - Memoize expensive calculations
  - Lazy-load non-critical components

### Accessibility Features
- **Screen Reader Support**: 
  - ARIA labels for all interactive elements
  - Live regions for changing critical values
  - Descriptive announcements for mode transitions
- **Keyboard Navigation**:
  - Tab order: Input → Send → Context Buttons → Dashboard quadrants (in order) → Footer
  - Arrow keys to adjust values in settings
  - Enter/Space to activate buttons
- **Visual Accessibility**:
  - High contrast mode toggle
  - Font size scaling (respects browser settings)
  - Color-blind friendly palettes (with patterns/text alternatives)
  - Focus rings visible (2px solid, theme-appropriate color)

### Theming System
- **Light Mode** (default): Soft white background with dark text
- **Dark Mode**: Deep charcoal background with light accents
- **Solarized**: Based on Ethan Schoonover's Solarized palette
- **Traditional**: Inspired by Indian manuscript aesthetics (cream background, mineral pigments)
- **Theme Storage**: Persisted in localStorage, respects OS preference initially

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Basic layout structure
- Header with mode indicator and Ṛta-Score
- Simple chat interface
- Connection status footer
- WebSocket integration for basic state updates

### Phase 2: Core Dashboard (Weeks 3-4)
- Safety gauges implementation
- Tool activity panel
- System metrics visualization
- Transcendent mode awareness panel
- Tooltips and basic interactions

### Phase 3: Refinement & Animations (Weeks 5-6)
- Sophisticated animations and transitions
- Hover effects and detailed tooltips
- Error state handling
- Accessibility implementation
- Performance optimization

### Phase 4: Advanced Features (Weeks 7-8)
- Settings panel with customization
- Log viewer and debugging tools
- Theme system
- Voice input integration
- Export/share capabilities

## Success Metrics
1. **User Understanding**: 80% of users can correctly explain current system state after 2 minutes of observation
2. **Trust Calibration**: Users' trust ratings correlate with actual system performance (measured through studies)
3. **Engagement**: Average session length increases by 40% compared to baseline chat interface
4. **Perceived Performance**: Users report feeling more "in sync" with the system's capabilities
5. **Adoption**: Positive feedback on transcendent awareness features making technical concepts accessible

## Open Questions for Development Team
1. Should the UI be a standalone desktop app (Electron/Tauri) or web-based?
2. What level of detail should be shown in tool specifications vs. abstracted for end users?
3. How frequently should safety metrics update vs. predictive metrics?
4. Should users be able to manually override safety thresholds (with appropriate warnings)?
5. What is the desired balance between showing raw metrics vs. interpreted guidance?

---
*This UI design makes visible the invisible mathematical and philosophical framework of NALA, transforming complex internal states into intuitive, actionable insights that build appropriate trust and enable effective human-AI collaboration.*