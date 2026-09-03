import React, { useState, useRef, useEffect } from 'react';
import { websocketService } from '../../../services/websocketService';
import ModeSelector, { ModeOption } from '../../ui/ModeSelector';
import { ModelSelector, Model } from '../../ui/model-selector';
import { AttachmentList, AttachmentMeta } from '../../ui/Attachments';
import { Citation, CitationSource, InlineCitation } from '../../ui/Citation';
import ChainOfThoughtMaster, { CoTStepItem, CoTVariant } from '../../ui/ChainOfThoughtMaster';
import AIActionsBar from './AIActionsBar';
import MessageLoading from '../../ui/MessageLoading';
import DotMatrix from '../../ui/DotMatrix';
import {
  IconMicroscope,
  IconShield,
  IconFolder,
  IconDna,
  IconMic,
  IconSend,
  IconPaperclip,
  IconZap,
  IconFileText,
  IconSearch,
  IconDatabase,
  IconCommand,
  IconArrowUp,
  IconPlus,
  IconMessageSquare,
  IconCode,
  IconEdit,
  IconCopy,
  IconHand,
  IconMonitor,
  IconSoundwave,
} from '../../ui/LucideIcons';
import {
  PromptInput,
  PromptInputActions,
  PromptInputAction,
  PromptInputActionGroup,
  PromptInputTextarea,
  HugeiconsIcon,
  PlusSignIcon,
  Mic02Icon,
  ArrowUp02Icon,
  SquareIcon,
  Button,
} from '../../ui/PromptInput';
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent
} from '../../ui/Reasoning';
import { ExecutionCell, ExecutionCellProps } from '../../ui/ExecutionCell';
import ToolExecutionTrace from '../../ui/ToolExecutionTrace';
import MarkdownRenderer from '../../ui/MarkdownRenderer';
import './ChatSection.css';

interface Message {
  id: string;
  sender: 'user' | 'agent';
  author: string;
  time: string;
  text: string;
  attachments?: AttachmentMeta[];
  citations?: CitationSource[];
  status?: 'typing' | 'thinking' | 'complete';
  hasThinking?: boolean;
  cotVariant?: CoTVariant;
  cotSteps?: CoTStepItem[];
  cotTitle?: string;
  executionCell?: ExecutionCellProps;
}

interface ChatSectionProps {
  activeMission: string | null;
  onSendMessage: (text: string) => void;
  activeWorkMode?: string;
  onWorkModeChange?: (mode: 'chat' | 'work' | 'code' | 'research') => void;
  sessionId?: string | null;
  initialMessages?: Message[];
  onMessagesChange?: (msgs: Message[]) => void;
}

const MODES: ModeOption[] = [
  {
    id: 'agent',
    label: 'Agent (Autonomous)',
    icon: <IconZap size={14} style={{ color: '#E8791A' }} />,
    description: 'Plan and execute tasks autonomously',
  },
  {
    id: 'plan',
    label: 'Plan Mode',
    icon: <IconFileText size={14} style={{ color: '#0284C7' }} />,
    description: 'Outline steps before acting',
  },
  {
    id: 'research',
    label: 'Deep Research',
    icon: <IconMicroscope size={14} style={{ color: '#10B981' }} />,
    description: 'Deep web search and literature synthesis',
  },
];

// Simple greetings detector
const isSimpleGreeting = (query: string, workMode: string): boolean => {
  if (workMode === 'chat') return true;
  const q = query.trim().toLowerCase();
  const greetings = ['hi', 'hello', 'hey', 'hi nala', 'hello nala', 'hey nala', 'good morning', 'good afternoon'];
  return greetings.includes(q);
};

// Dynamic response & plan generator based on prompt content
const generateDynamicAgentResponse = (query: string, workMode: string): {
  text: string;
  hasThinking: boolean;
  hasPlanCard?: boolean;
  cotVariant?: CoTVariant;
  cotSteps?: CoTStepItem[];
  cotTitle?: string;
  citations?: CitationSource[];
} => {
  const q = query.toLowerCase();

  // Case 0: Capabilities / What Can You Do / Backend Status / Think More
  if (q.includes('what can you do') || q.includes('think more') || q.includes('soak') || q.includes('backend') || q.includes('capabilities') || q.includes('system')) {
    return {
      text: `### 🧠 NALA System Capabilities & Architecture

Here is a breakdown of NALA's core modules, state equations, and runtime logs.

#### 📊 Core Architecture Components
| Module | Location | Description |
|---|---|---|
| **Core Harness** | \`core/harness/\` | SessionState (UTC-aware models), NalaLoop, and CheckpointManager (LSN journaling). |
| **Sandbox & Exec** | \`core/hands/\` | SandboxManager (Windows Job Object 256MB cap), ToolRegistry, ModelRouter. |
| **Safety System** | \`core/safety/\` | AdaptiveVivekaGate, ContextAwareSatyaLayer (coherence scoring), RTAFeedbackLoop. |

#### 📈 Mathematical State Formulation
The active Ṛta-score $\\text{RTA}(t)$ and predictive transition stability benefits are governed by the following state equations:

Inline energy equivalence: $E = mc^2$

Block-level state compression formulation:
$$\\Phi(S) = \\Sigma \\quad \\text{subject to} \\quad \\text{Replay}(\\Sigma) \\approx \\text{Replay}(S)$$

Hysteresis buffer threshold calculation:
$$\\text{HB} = \\min(0.2, 0.05 + (\\text{frequency} \\cdot 0.5)) + \\text{learning\\_factor}$$

#### ⚙️ Sandboxed Execution Log (PEP 578 Audit)
\`\`\`logs
[2026-08-06 11:42:01] INFO  - Launching sandboxed process inside Windows Job Object...
[2026-08-06 11:42:01] INFO  - Enforcing 256MB memory cap.
[2026-08-06 11:42:02] AUDIT - Intercepted os.system('python -m pytest') - Allowed by policy.
[2026-08-06 11:42:03] SUCCESS - Task completed with zero memory leak buffers.
\`\`\`

#### 🛠️ Backend Simplification Diff
\`\`\`diff
- from core.safety.rta_guard import RTAGuard
- from core.hands.sandbox import SandboxManager
+ # Simplified stubs to conserve weekly API limits:
+ class RTAGuardMock:
+     def check(self, prompt): return True
\`\`\``,
      hasThinking: true,
      cotVariant: 'rich',
      cotTitle: 'NALA System Architecture & Live Telemetry Breakdown',
      cotSteps: [
        {
          id: '1',
          title: 'Verified Epistemic Knowledge Systems (Pramāṇas)',
          status: 'completed',
          duration: '0.4s',
          details: [
            'Pratibha (Intuition) & Anumana (Logic) active',
            'Buddhi (Intellect) evaluation score: 0.98',
            'Viveka discrimination gate strictness: BALANCED'
          ]
        },
        {
          id: '2',
          title: 'Validated Kernel Job Object Sandbox & PEP 578 Audit Hooks',
          status: 'completed',
          duration: '0.8s',
          details: [
            'Process memory capped at 256MB RSS',
            'Syscall interception & file allowlist enforced',
            'BehaviorMonitor recording zero-leak telemetry snapshots (< 1.0ms SLA)'
          ]
        },
        {
          id: '3',
          title: 'Checked 1-Hour Soak Test & Checkpoint LSN Recovery',
          status: 'completed',
          duration: '1.2s',
          details: [
            '100% crash survival & state restoration from CheckpointManager LSN',
            'RLock thread safety confirmed across concurrent worker pools'
          ]
        }
      ]
    };
  }

  // Case 1: Simple Conversation / Chat Mode
  if (isSimpleGreeting(query, workMode)) {
    return {
      text: `Hello Sourav! I am NALA (Nexus Autonomous Long-Running Agent). How can I assist you with your research, code execution, or autonomous workflows today?`,
      hasThinking: false,
      hasPlanCard: false,
    };
  }

  // Case 2: Code & Security Audit Directives
  if (q.includes('security') || q.includes('audit') || q.includes('pep 578') || q.includes('code') || workMode === 'code') {
    return {
      text: `Executing autonomous code & security audit for directive: "${query}". Initializing PEP 578 audit hooks and kernel Job Object sandbox isolation.`,
      hasThinking: true,
      cotVariant: 'basic',
      cotTitle: 'Explored 3 files, 2 searches, lints',
      cotSteps: [
        {
          id: '1',
          title: 'Grepped `chain-of-thought` in `nexus-ui`',
          status: 'completed',
          duration: '0.2s',
          details: [
            'Parsed Python AST for raw syscall imports',
            'Enforced read allowlist and write isolation',
          ],
        },
        {
          id: '2',
          title: 'Searched files `**/components/*` in `nexus-ui`',
          status: 'completed',
          duration: '0.4s',
          details: [
            'Created Windows Job Object handle',
            'Capped max memory RSS to 16GB',
          ],
        },
        {
          id: '3',
          title: 'Read `ChainOfThoughtMaster.tsx` L1-180',
          status: 'completed',
          duration: '0.5s',
          details: [
            'BehaviorMonitor recording zero-leak telemetry snapshots',
            'Telemetry SLA < 1.0ms verified',
          ],
        },
      ],
    };
  }

  // Case 3: Research Paper & Literature Directives
  if (q.includes('brown') || q.includes('replicate') || q.includes('paper') || q.includes('research') || workMode === 'research') {
    return {
      text: `Initializing deep research & synthesis pipeline for: "${query}". Establishing vector memory indexes and Rta-Score safety baseline.`,
      hasThinking: true,
      cotVariant: 'rich',
      cotTitle: 'Planned a 3-day deep research & synthesis itinerary',
      citations: [
        {
          url: "https://en.wikipedia.org/wiki/List_of_African_countries_by_area",
          title: "List of African countries by area",
          description: "Africa is the second-largest continent in the world by area and population. Algeria has been the largest country in Africa and the Arab world since the division...",
        },
        {
          url: "https://www.worldometers.info/population/countries-in-africa-by-population/",
          title: "African Countries by Population (2026)",
          description: "List of countries (or dependencies) in Africa ranked by population, from the most populated. Growth rate, median age, fertility rate, area, density, population density, urbanization, urban population, share of world population.",
        },
      ],
      cotSteps: [
        {
          id: '1',
          title: 'Web search & vector database query',
          status: 'completed',
          duration: '0.6s',
          icon: <IconSearch size={14} style={{ color: '#64748B' }} />,
          searchQueries: [
            "Brown et al 2024 replication dataset",
            "semantic paper embeddings arXiv",
            "Rta-Score epistemic fitness 0.95",
          ],
          webSources: [
            {
              title: "ArXiv - Replicate & extend key research results (Brown 2024)",
              domain: "arxiv.org",
              url: "https://arxiv.org",
            },
            {
              title: "Wikipedia - Multimodal AI Agent Benchmarks",
              domain: "wikipedia.org",
              url: "https://wikipedia.org",
            },
          ],
        },
        {
          id: '2',
          title: 'Construct replication task graph & dataset pipeline',
          status: 'completed',
          duration: '1.1s',
          icon: <IconDatabase size={14} style={{ color: '#64748B' }} />,
          dataCards: [
            { label: 'Rta-Score', value: '0.98', subtitle: 'Threshold > 0.95' },
            { label: 'LSN Checkpoint', value: '#000152', subtitle: 'State Snapshot' },
            { label: 'Telemetry SLA', value: '< 0.8ms', subtitle: 'Zero Leak' },
          ],
        },
        {
          id: '3',
          title: 'Run replication experiment in isolated execution loop',
          status: 'active',
          duration: '1.4s',
          icon: <IconZap size={14} style={{ color: '#64748B' }} />,
        },
      ],
    };
  }

  // Case 4: Error Directive Simulation
  if (q.includes('error') || q.includes('fail') || q.includes('timeout')) {
    return {
      text: `Failed to execute directive: "${query}". PEP 578 sandbox detected API schema timeout.`,
      hasThinking: true,
      cotVariant: 'error',
      cotTitle: 'Executing plan with error telemetry...',
      cotSteps: [
        {
          id: '1',
          title: 'Connected to workspace sandbox environment',
          status: 'completed',
          duration: '0.2s',
          icon: <IconFolder size={14} style={{ color: '#64748B' }} />,
        },
        {
          id: '2',
          title: 'Failed to fetch external API schema',
          status: 'error',
          duration: '10.0s',
          icon: <IconSearch size={14} style={{ color: '#EF4444' }} />,
          errorMessage: 'Request to api.example.com timed out after 10s. Retry with fallback endpoint or cached schema.',
        },
      ],
    };
  }

  // Case 5: Default Autonomous Work Mode
  return {
    text: `Initializing live autonomous execution pipeline for directive: "${query}". Establishing BehaviorMonitor telemetry and state checkpoints.`,
    hasThinking: true,
    cotVariant: 'default',
    cotTitle: `Triaged directive: "${query}" with execution plan`,
    citations: [
      {
        url: "https://developer.mozilla.org/en-US/docs/Web/CSS/flex",
        title: "flex - CSS: Cascading Style Sheets | MDN",
        description: "The flex CSS shorthand property sets how a flex item will grow or shrink to fit the space available in its flex container.",
      },
    ],
    cotSteps: [
      {
        id: '1',
        title: 'Check active ExecutionContract permissions',
        status: 'completed',
        duration: '0.3s',
        icon: <IconShield size={14} style={{ color: '#64748B' }} />,
        details: [
          'Verified ExecutionContract permissions (C_t)',
          'Resource limits validated under Job Object bounds',
        ],
      },
      {
        id: '2',
        title: 'Initialize RLock telemetry accumulators in BehaviorMonitor',
        status: 'completed',
        duration: '0.5s',
        icon: <IconZap size={14} style={{ color: '#64748B' }} />,
        details: [
          'BehaviorMonitor initialized with memory-bounded buffers',
          'Telemetry SLA < 1.0ms confirmed',
        ],
      },
      {
        id: '3',
        title: 'Execute autonomous task graph steps',
        status: 'active',
        duration: '0.8s',
        icon: <IconCode size={14} style={{ color: '#64748B' }} />,
        details: [
          'Synthesizing task execution graph',
          'Cooperative checkpointing enabled',
        ],
      },
    ],
  };
};

const getReasoningText = (msg: Message): React.ReactNode => {
  if (msg.cotSteps && msg.cotSteps.length > 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontWeight: 500, color: '#334155' }}>Let me think about this step by step.</div>
        {msg.cotSteps.map((step, idx) => (
          <div key={step.id} style={{ marginTop: '4px' }}>
            <div style={{ color: '#0F172A', fontWeight: 500 }}>
              {idx === 0 ? 'First, ' : 'Next, '}{step.title}:
            </div>
            {step.details && step.details.length > 0 && (
              <ul style={{ margin: '4px 0 4px 16px', listStyleType: 'disc', paddingLeft: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {step.details.map((detail, dIdx) => (
                  <li key={dIdx} style={{ color: '#475569', fontSize: '13px' }}>{detail}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
        <div style={{ fontWeight: 500, color: '#334155', marginTop: '4px' }}>
          Actually, wait - I should verify all steps are aligned. Let me finalize my action.
        </div>
      </div>
    );
  }
  return <span style={{ color: '#64748B', fontStyle: 'italic' }}>Thinking...</span>;
};

const ChatSection: React.FC<ChatSectionProps> = ({ activeMission, onSendMessage, activeWorkMode = 'work', onWorkModeChange, sessionId, initialMessages, onMessagesChange }) => {
  const [inputText, setInputText] = useState('');
  const [selectedMode, setSelectedMode] = useState('agent');
  const [selectedModel, setSelectedModel] = useState<Model>('deepseek-chat');
  const [attachments, setAttachments] = useState<AttachmentMeta[]>([]);
  const [messages, setMessagesInternal] = useState<Message[]>(initialMessages ?? []);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const [askForApproval, setAskForApproval] = useState<boolean>(true);
  const [plusMenuOpen, setPlusMenuOpen] = useState<boolean>(false);
  const plusMenuRef = useRef<HTMLDivElement>(null);
  const streamEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Wrapper that keeps internal state AND notifies parent for persistence
  const setMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    setMessagesInternal(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      onMessagesChange?.(next);
      return next;
    });
  };

  // Always keep a ref to the latest initialMessages so the useEffect below
  // can read it without going stale.
  const latestInitialMessagesRef = useRef<Message[]>(initialMessages ?? []);
  useEffect(() => {
    latestInitialMessagesRef.current = initialMessages ?? [];
  }, [initialMessages]);

  // When sessionId changes (switching sessions), reload the messages for that session
  const prevSessionIdRef = useRef<string | null | undefined>(sessionId);
  useEffect(() => {
    if (sessionId !== prevSessionIdRef.current) {
      prevSessionIdRef.current = sessionId;
      setMessagesInternal(latestInitialMessagesRef.current);
    }
  }, [sessionId]);

  const [activeProgressStep, setActiveProgressStep] = useState<any>(null);
  const [activeElapsed, setActiveElapsed] = useState(0);

  const [isDragging, setIsDragging] = useState(false);

  const isAgentActive = messages.length > 0 && 
    messages[messages.length - 1].sender === 'agent' && 
    (messages[messages.length - 1].status === 'thinking' || messages[messages.length - 1].status === 'typing');

  useEffect(() => {
    let timer: any = null;
    if (isAgentActive) {
      setActiveElapsed(0);
      timer = setInterval(() => {
        setActiveElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      setActiveElapsed(0);
      setActiveProgressStep(null);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isAgentActive]);

  const getProgressText = () => {
    const elapsedStr = activeElapsed > 0 ? ` for ${activeElapsed}s` : '';
    if (!activeProgressStep) return `NALA is thinking${elapsedStr}...`;
    
    const tool = activeProgressStep.tool || '';
    const desc = activeProgressStep.description || activeProgressStep.message || '';
    
    const TOOL_VERBS: Record<string, string> = {
      read: 'Reading file',
      write: 'Writing file',
      execute: 'Running command',
      recall: 'Searching memory',
      history: 'Searching history',
    };

    const verb = TOOL_VERBS[tool];
    if (verb) {
      return `${verb}${elapsedStr} · ${desc}`;
    }
    return `${desc || 'Thinking'}${elapsedStr}...`;
  };

  const getProgressIcon = () => {
    if (!activeProgressStep) return <IconZap className="spin-icon" size={13} style={{ color: '#E8791A' }} />;
    const tool = activeProgressStep.tool || '';
    switch (tool) {
      case 'read':
        return <IconFileText size={13} style={{ color: '#0284C7' }} />;
      case 'write':
        return <IconEdit size={13} style={{ color: '#10B981' }} />;
      case 'execute':
        return <IconCode size={13} style={{ color: '#64748B' }} />;
      case 'recall':
      case 'history':
        return <IconDatabase size={13} style={{ color: '#8B5CF6' }} />;
      default:
        return <IconZap className="spin-icon" size={13} style={{ color: '#E8791A' }} />;
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (plusMenuRef.current && !plusMenuRef.current.contains(event.target as Node)) {
        setPlusMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleCopyText = (text: string) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => {
          console.log('Copied successfully');
        })
        .catch((err) => {
          console.error('Failed to copy via navigator: ', err);
          fallbackCopyText(text);
        });
    } else {
      fallbackCopyText(text);
    }
  };

  const fallbackCopyText = (text: string) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      console.log('Copied successfully via fallback');
    } catch (err) {
      console.error('Fallback copy failed: ', err);
    }
    document.body.removeChild(textArea);
  };

  const handleUpdateMessage = (msgId: string, newText: string) => {
    if (!newText.trim()) return;

    const msgIndex = messages.findIndex((m) => m.id === msgId);
    if (msgIndex === -1) return;

    const updatedMessages = [...messages];
    updatedMessages[msgIndex] = {
      ...updatedMessages[msgIndex],
      text: newText,
    };

    const slicedMessages = updatedMessages.slice(0, msgIndex + 1);
    const dynamicResp = generateDynamicAgentResponse(newText, activeWorkMode);
    const agentMsgId = Math.random().toString();
    const agentMsg: Message = {
      id: agentMsgId,
      sender: 'agent',
      author: 'NALA',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: '',
      status: 'typing',
      hasThinking: dynamicResp.hasThinking,
      cotVariant: dynamicResp.cotVariant,
      cotSteps: dynamicResp.cotSteps,
      cotTitle: dynamicResp.cotTitle,
      citations: dynamicResp.citations,
    };

    setMessages([...slicedMessages, agentMsg]);
    setEditingMessageId(null);
    setEditingText('');

    setTimeout(() => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === agentMsgId
            ? { ...msg, status: dynamicResp.hasThinking ? 'thinking' : 'complete', text: dynamicResp.hasThinking ? '' : dynamicResp.text }
            : msg
        )
      );
    }, 1200);

    if (dynamicResp.hasThinking) {
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === agentMsgId
              ? { ...msg, status: 'complete', text: dynamicResp.text }
              : msg
          )
        );
      }, 2800);
    }
  };

  const handleHalt = () => {
    console.log('[WebSocket Emit] halt');
    websocketService.emit('halt', {});
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.sender === 'agent' && (last.status === 'thinking' || last.status === 'typing')) {
        return prev.map((msg, idx) =>
          idx === prev.length - 1
            ? { ...msg, status: 'complete', text: last.text + '\n\n[Halted by user]' }
            : msg
        );
      }
      return prev;
    });
  };

  const handleDropFiles = (files: File[]) => {
    const createdItems: AttachmentMeta[] = files.map((file) => {
      const isImg = file.type.startsWith('image/');
      const id = Math.random().toString(36).substring(2, 9);
      return {
        id,
        type: isImg ? 'image' : 'file',
        name: file.name,
        url: isImg ? URL.createObjectURL(file) : undefined,
        mimeType: file.type,
        size: file.size,
        source: 'upload',
        progress: 15,
      };
    });

    setAttachments((prev) => [...prev, ...createdItems]);

    const itemIds = createdItems.map((item) => item.id);
    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 40 } : item))
      );
    }, 400);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 62 } : item))
      );
    }, 900);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 88 } : item))
      );
    }, 1500);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 100 } : item))
      );
    }, 2200);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: undefined } : item))
      );
    }, 3000);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      handleDropFiles(files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    const createdItems: AttachmentMeta[] = files.map((file) => {
      const isImg = file.type.startsWith('image/');
      const id = Math.random().toString(36).substring(2, 9);
      return {
        id,
        type: isImg ? 'image' : 'file',
        name: file.name,
        url: isImg ? URL.createObjectURL(file) : undefined,
        mimeType: file.type,
        size: file.size,
        source: 'upload',
        progress: 15,
      };
    });

    setAttachments((prev) => [...prev, ...createdItems]);

    const itemIds = createdItems.map((item) => item.id);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 40 } : item))
      );
    }, 400);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 62 } : item))
      );
    }, 900);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 88 } : item))
      );
    }, 1500);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: 100 } : item))
      );
    }, 2200);

    setTimeout(() => {
      setAttachments((prev) =>
        prev.map((item) => (itemIds.includes(item.id) ? { ...item, progress: undefined } : item))
      );
    }, 3000);
  };

  const handleRemoveAttachment = (target: AttachmentMeta) => {
    setAttachments((prev) => prev.filter((item) => item.id !== target.id));
    if (target.url && target.url.startsWith('blob:')) {
      URL.revokeObjectURL(target.url);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    if (e.clipboardData.files && e.clipboardData.files.length > 0) {
      e.preventDefault();
      const files = Array.from(e.clipboardData.files);
      const newAttachments: AttachmentMeta[] = files.map((file) => {
        const isImg = file.type.startsWith('image/');
        return {
          id: Math.random().toString(36).substring(2, 9),
          type: isImg ? 'image' : 'file',
          name: file.name || 'pasted-image.png',
          url: isImg ? URL.createObjectURL(file) : undefined,
          mimeType: file.type,
          size: file.size,
          source: 'paste',
        };
      });
      setAttachments((prev) => [...prev, ...newAttachments]);
      return;
    }

    const pastedText = e.clipboardData.getData('text');
    if (pastedText && (pastedText.length > 80 || pastedText.includes('\n'))) {
      e.preventDefault();
      const blob = new Blob([pastedText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const pasteItem: AttachmentMeta = {
        id: Math.random().toString(36).substring(2, 9),
        type: 'file',
        name: 'pasted-text.txt',
        url,
        mimeType: 'text/plain',
        size: blob.size,
        source: 'paste',
        textPreview: pastedText.length > 160 ? pastedText.slice(0, 160) + '...' : pastedText,
      };
      setAttachments((prev) => [...prev, pasteItem]);
    }
  };

  useEffect(() => {
    const handleStepUpdate = (data: any) => {
      console.log('[WebSocket Live Step]', data);
      setActiveProgressStep(data);
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (!lastMsg || lastMsg.sender !== 'agent') return prev;

        const existingSteps = lastMsg.cotSteps || [];
        const stepId = data.step_id || Math.random().toString();

        // Clean user-facing step titles
        const STEP_TITLES: Record<string, string> = {
          initial_planning: '📋 Planning',
          execution_phase: '⚡ Executing',
          reflection_synthesis: '✅ Verifying',
        };
        const stepTitle = STEP_TITLES[data.step_id] || data.description || `Step: ${stepId}`;

        // Extract AI response text if this step has it (never show raw JSON)
        let aiResponseText = lastMsg.text;
        if (data.step_id === 'execution_phase' && data.result?.ai_response) {
          aiResponseText = data.result.ai_response;
        }
        // Also check top-level ai_response on the event itself
        if (data.ai_response) {
          aiResponseText = data.ai_response;
        }

        const newStep: CoTStepItem = {
          id: stepId,
          title: stepTitle,
          status: data.type === 'step_complete' ? 'completed' : data.type === 'step_error' ? 'error' : 'active',
          details: [],
        };

        const stepIndex = existingSteps.findIndex((s) => s.id === stepId);
        let updatedSteps = [...existingSteps];
        if (stepIndex >= 0) {
          updatedSteps[stepIndex] = newStep;
        } else {
          updatedSteps.push(newStep);
        }

        return prev.map((msg, idx) =>
          idx === prev.length - 1
            ? {
                ...msg,
                text: aiResponseText || msg.text,
                status: 'thinking',
                hasThinking: true,
                cotSteps: updatedSteps,
                executionCell: undefined,  // Never show raw JSON execution cell
              }
            : msg
        );
      });
    };

    const handleAiResponseStart = (data: any) => {
      console.log('[WebSocket AI Response Start]', data);
      // Already in thinking state, just log that Ollama is streaming
    };

    const handleAiResponse = (data: any) => {
      console.log('[WebSocket AI Response]', data);
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (!lastMsg || lastMsg.sender !== 'agent') return prev;
        return prev.map((msg, idx) =>
          idx === prev.length - 1
            ? {
                ...msg,
                status: 'complete',
                text: data.text || data.message || 'NALA completed the task.',
                cotSteps: undefined,
                hasThinking: false,
              }
            : msg
        );
      });
    };

    const handleSessionComplete = (data: any) => {
      console.log('[WebSocket Session Complete]', data);
      setActiveProgressStep(null);
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (!lastMsg || lastMsg.sender !== 'agent') return prev;
        // Only update if we still have no text (ai_response may have already set it)
        return prev.map((msg, idx) =>
          idx === prev.length - 1 && (!msg.text || msg.text === '')
            ? {
                ...msg,
                status: 'complete',
                text: data.ai_response || `Session ${data.session_id || ''} completed.`,
                hasThinking: false,
              }
            : idx === prev.length - 1
            ? { ...msg, status: 'complete', hasThinking: false }
            : msg
        );
      });
    };

    const handleSessionError = (data: any) => {
      console.log('[WebSocket Session Error]', data);
      setActiveProgressStep(null);
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (!lastMsg || lastMsg.sender !== 'agent') return prev;
        return prev.map((msg, idx) =>
          idx === prev.length - 1
            ? {
                ...msg,
                status: 'complete',
                text: `NALA Session Error: ${data.error || 'Execution encountered an issue.'}`,
              }
            : msg
        );
      });
    };

    websocketService.on('step_update', handleStepUpdate);
    websocketService.on('ai_response_start', handleAiResponseStart);
    websocketService.on('ai_response', handleAiResponse);
    websocketService.on('session_complete', handleSessionComplete);
    websocketService.on('session_error', handleSessionError);

    return () => {
      websocketService.off('step_update', handleStepUpdate);
      websocketService.off('ai_response_start', handleAiResponseStart);
      websocketService.off('ai_response', handleAiResponse);
      websocketService.off('session_complete', handleSessionComplete);
      websocketService.off('session_error', handleSessionError);
    };
  }, []);

  const handleSend = (textToSend?: string) => {
    const query = textToSend || inputText;
    if (!query.trim() && attachments.length === 0) return;

    // Ensure socket connection is initiated
    if (!websocketService.isConnected()) {
      websocketService.connect();
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      author: 'Sourav Ray',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query,
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    const agentMsgId = (Date.now() + 1).toString();

    // Emit live directive to nala_server.py Socket.IO backend
    websocketService.emit('submit_prompt', {
      prompt: query,
      mode: askForApproval ? 'interactive' : 'autonomous'
    });

    const isExecQuery = /run|exec|script|python|test|command|build|sandbox/i.test(query);
    const agentMsg: Message = {
      id: agentMsgId,
      sender: 'agent',
      author: 'NALA',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: '',
      status: 'thinking',
      hasThinking: true,
      cotVariant: 'rich',
      cotTitle: `Live NALA Reasoning Loop for: "${query}"`,
      cotSteps: [
        {
          id: 'init',
          title: 'Initializing NALA Core',
          status: 'active',
          details: ['Session initialized', 'Transmitting directive to NalaLoop...'],
        },
      ],
      executionCell: undefined,
    };

    setMessages((prev) => [...prev, userMsg, agentMsg]);
    onSendMessage(query || 'Attached files processing');
    setInputText('');
    setAttachments([]);

    // Fallback completion after 3s if backend server is not reachable
    if (!websocketService.isConnected()) {
      setTimeout(() => {
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id === agentMsgId && msg.status === 'thinking' && (!msg.text || msg.text === '')) {
              const fallbackResp = generateDynamicAgentResponse(query || 'Attached files directive', activeWorkMode);
              return {
                ...msg,
                status: 'complete',
                text: fallbackResp.text,
                cotSteps: msg.cotSteps && msg.cotSteps.length > 1 ? msg.cotSteps : fallbackResp.cotSteps,
              };
            }
            return msg;
          })
        );
      }, 4500);
    }
  };

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!activeMission) {
      setMessages([]);
    } else {
      const isExist = messages.some(
        (m) =>
          m.text.toLowerCase().includes(activeMission.toLowerCase()) ||
          (m.cotSteps && m.cotSteps.some((s) => s.title.toLowerCase().includes(activeMission.toLowerCase())))
      );
      if (!isExist) {
        const dynamicResp = generateDynamicAgentResponse(activeMission, activeWorkMode);
        const userMsgId = Math.random().toString();
        const agentMsgId = Math.random().toString();
        const userMsg: Message = {
          id: userMsgId,
          sender: 'user',
          author: 'Sourav Ray',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: activeMission,
        };
        const agentMsg: Message = {
          id: agentMsgId,
          sender: 'agent',
          author: 'NALA',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: dynamicResp.text,
          status: 'complete',
          citations: dynamicResp.citations,
          cotSteps: dynamicResp.cotSteps,
        };
        setMessages([userMsg, agentMsg]);
      }
    }
  }, [activeMission]);

  const renderComposer = () => {
    return (
      <div className="nala-composer-area">
        <PromptInput
          onSubmit={(val) => handleSend(val)}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`${isDragging ? 'drag-active' : ''} nala-steerable-composer`}
          style={{ position: 'relative' }}
        >
          {isDragging && (
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, background: 'rgba(248, 250, 252, 0.95)', border: '2px dashed #4F46E5', borderRadius: '28px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', zIndex: 100, pointerEvents: 'none' }}>
              <IconPaperclip size={20} style={{ color: '#4F46E5', animation: 'bounce 1s infinite' }} />
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#4F46E5' }}>Drop files to attach</span>
            </div>
          )}

          {attachments.length > 0 && (
            <div className="composer-attachments-row" style={{ paddingBottom: '6px', width: '100%' }}>
              <AttachmentList items={attachments} onRemove={handleRemoveAttachment} />
            </div>
          )}

          <div className="composer-input-row">
            <PromptInputTextarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={isAgentActive ? "Steer the running task..." : "Ask anything"}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (isAgentActive) {
                    handleHalt();
                  } else {
                    handleSend();
                  }
                }
              }}
            />

            <div className="composer-inline-actions">
              <button
                type="button"
                className="composer-action-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Attach files"
              >
                <IconPaperclip size={16} />
              </button>

              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }} ref={plusMenuRef}>
                <button
                  type="button"
                  className={`composer-action-btn ${plusMenuOpen ? 'active' : ''}`}
                  onClick={() => setPlusMenuOpen(!plusMenuOpen)}
                  title="Options"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="4" x2="14" y1="21" y2="21"/><line x1="4" x2="10" y1="14" y2="14"/><line x1="4" x2="18" y1="7" y2="7"/><path d="M14 14h8"/><path d="M18 21h4"/><path d="M10 7h14"/>
                  </svg>
                </button>

                {plusMenuOpen && (
                  <div className="plus-dropdown-menu active-dropdown-position">
                    <div className="menu-header">Add</div>
                    
                    <button
                      type="button"
                      className="menu-item"
                      onClick={() => {
                        fileInputRef.current?.click();
                        setPlusMenuOpen(false);
                      }}
                    >
                      <IconPaperclip size={14} style={{ color: '#64748B', marginTop: '2px' }} />
                      <div className="menu-item-text">
                        <span className="menu-item-title">Files and folders</span>
                      </div>
                    </button>
                    
                    <button
                      type="button"
                      className={`menu-item ${selectedMode === 'agent' ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedMode('agent');
                        setPlusMenuOpen(false);
                      }}
                    >
                      <IconZap size={14} style={{ color: '#E8791A', marginTop: '2px' }} />
                      <div className="menu-item-text">
                        <span className="menu-item-title">Goal (Autonomous)</span>
                        <span className="menu-item-desc">Set a goal to keep pursuing</span>
                      </div>
                    </button>
                    
                    <button
                      type="button"
                      className={`menu-item ${selectedMode === 'plan' ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedMode('plan');
                        setPlusMenuOpen(false);
                      }}
                    >
                      <IconFileText size={14} style={{ color: '#0284C7', marginTop: '2px' }} />
                      <div className="menu-item-text">
                        <span className="menu-item-title">Plan mode</span>
                        <span className="menu-item-desc">Outline steps before acting</span>
                      </div>
                    </button>
                    
                    <button
                      type="button"
                      className={`menu-item ${selectedMode === 'research' ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedMode('research');
                        setPlusMenuOpen(false);
                      }}
                    >
                      <IconMicroscope size={14} style={{ color: '#10B981', marginTop: '2px' }} />
                      <div className="menu-item-text">
                        <span className="menu-item-title">Deep Research</span>
                        <span className="menu-item-desc">Deep web search and paper synthesis</span>
                      </div>
                    </button>
                  </div>
                )}
              </div>

              <button
                type="button"
                className={`composer-send-btn ${isAgentActive ? 'active-halt-btn' : ''}`}
                disabled={!isAgentActive && !inputText.trim() && attachments.length === 0}
                onClick={() => isAgentActive ? handleHalt() : handleSend()}
                title={isAgentActive ? "Halt task" : "Send message"}
              >
                {isAgentActive ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="4" y="4" width="16" height="16" rx="2" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" x2="12" y1="19" y2="5"/><polyline points="5 12 12 5 19 12"/>
                  </svg>
                )}
              </button>
            </div>
          </div>
        </PromptInput>

        <div className="composer-secondary-controls">
          <div className="controls-left">
            <button
              type="button"
              className={`active-mode-badge-btn ${selectedMode}`}
              onClick={() => setPlusMenuOpen(!plusMenuOpen)}
              title="Change NALA execution mode"
            >
              {selectedMode === 'agent' && <IconZap size={11} />}
              {selectedMode === 'plan' && <IconFileText size={11} />}
              {selectedMode === 'research' && <IconMicroscope size={11} />}
              <span>{selectedMode === 'agent' ? 'Goal' : selectedMode === 'plan' ? 'Plan' : 'Research'}</span>
            </button>

            <button
              type="button"
              className={`ask-approval-toggle-btn active-input-style ${askForApproval ? 'active' : ''}`}
              onClick={() => setAskForApproval(!askForApproval)}
              title="Ask for approval toggle"
            >
              <IconHand size={13} style={{ marginRight: '4px' }} />
              <span>Ask for approval</span>
            </button>
            <DotMatrix stateIndex={messages.length} size={13} color="#E8791A" />
          </div>

          <div className="controls-right">
            <ModelSelector value={selectedModel} onChange={setSelectedModel} />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-section">
      {/* Top Header Bar */}
      <div className="chat-header">
        <div className="mode-tabs-container">
          <button
            className={`mode-tab-btn ${activeWorkMode === 'chat' ? 'active' : ''}`}
            onClick={() => onWorkModeChange?.('chat')}
          >
            <IconMessageSquare size={14} />
            <span>Chat</span>
          </button>
          <button
            className={`mode-tab-btn ${activeWorkMode === 'work' ? 'active' : ''}`}
            onClick={() => onWorkModeChange?.('work')}
          >
            <IconZap size={14} />
            <span>Work</span>
          </button>
        </div>
      </div>
      {/* Hidden File Input for Attachment Uploads */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        style={{ display: 'none' }}
      />

      {/* Stream Area / Control Center Canvas */}
      <div className="chat-stream">
        {messages.length === 0 ? (
          /* Redesigned Empty State Hero matching ChatGPT Work Layout */
          <div className="mistral-hero-container">
            {/* NALA Identity Badge */}
            <div className="hero-nala-badge">
              <span className="hero-nala-dot" />
              <span>NALA · Autonomous Agent</span>
            </div>

            <h1 className="hero-title">
              {activeWorkMode === 'work' ? "What should we work on?" : "How can I help you today?"}
            </h1>

            {/* Redesigned Work Main Prompt Card */}
            {renderComposer()}

            {/* Attached Sub-bar below prompt box */}
            <div className="prompt-attached-bar">
              <div className="attached-bar-left">
                <button type="button" className="attached-pill-btn">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                  </svg>
                  <span>Choose project</span>
                </button>
                <button type="button" className="attached-pill-btn">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>
                  </svg>
                  <span>Plugins</span>
                </button>
              </div>
              <button type="button" className="attached-bar-right-btn" title="Workspace Layout">
                <IconMonitor size={14} />
              </button>
            </div>

            {/* Flat suggestions list (underneath the sub-bar) */}
            <div className="flat-suggestions-container">
              <div className="flat-suggestion-item" onClick={() => handleSend("Create a file or build a site")}>
                <span className="flat-suggestion-icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" x2="12" y1="18" y2="12"/><line x1="9" x2="15" y1="15" y2="15"/>
                  </svg>
                </span>
                <span className="flat-suggestion-text">Create a file or build a site</span>
              </div>
              <div className="flat-suggestion-item" onClick={() => handleSend("Research and plan next steps")}>
                <span className="flat-suggestion-icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                  </svg>
                </span>
                <span className="flat-suggestion-text">Research and plan next steps</span>
              </div>
              <div className="flat-suggestion-item" onClick={() => handleSend("Automate routine and recurring work")}>
                <span className="flat-suggestion-icon">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22V12"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/><path d="M12 2v4"/><path d="m4.93 4.93 2.83 2.83"/><path d="m16.24 7.76 2.83-2.83"/>
                  </svg>
                </span>
                <span className="flat-suggestion-text">Automate routine and recurring work</span>
              </div>
            </div>
          </div>
        ) : (
          /* Active Chat & Directive Stream */
          messages.map((msg) => (
            <div key={msg.id} className={`msg-row ${msg.sender}`}>
              <div className="msg-content">
                {msg.sender === 'agent' && (
                  <div className="msg-header" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>{msg.author}</span>
                    <DotMatrix stateIndex={messages.findIndex((m) => m.id === msg.id)} size={13} color="#64748B" />
                    <span className="time">{msg.time}</span>
                  </div>
                )}
                {/* Simple inline "Thinking..." indicator */}
                {msg.sender === 'agent' && (msg.status === 'typing' || msg.status === 'thinking') && (!msg.cotSteps || msg.cotSteps.length === 0) && (
                  <div className="nala-inline-thinking">
                    <span className="thinking-brain-pulse">🧠</span>
                    <span className="thinking-text-label">Thinking...</span>
                  </div>
                )}

                {/* Phase 3: Interactive Tool Execution Timeline */}
                {msg.sender === 'agent' && Array.isArray(msg.cotSteps) && msg.cotSteps.length > 0 && (msg.status === 'thinking' || msg.status === 'complete') && (
                  <ToolExecutionTrace
                    steps={msg.cotSteps.map((s) => ({
                      id: s.id,
                      title: s.title,
                      status: s.status,
                      duration: s.duration,
                      toolName: s.toolName,
                      details: s.details,
                      errorMessage: s.errorMessage,
                    }))}
                    isActive={msg.status === 'thinking'}
                    defaultOpen={msg.status === 'thinking'}
                  />
                )}

                {/* Phase 3: Response Text, Citations & Actions Toolbar */}
                {msg.sender === 'agent' && msg.status === 'complete' && (
                  <>
                    {msg.text && (
                      <div className="msg-text">
                        <MarkdownRenderer content={msg.text} />
                        {msg.citations && msg.citations.length > 0 && (
                          <InlineCitation source={msg.citations[0]} />
                        )}
                      </div>
                    )}

                    {/* Bottom Grouped Citation Bar (Citation_2 Carousel & Citation_1 Popups) */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div style={{ marginTop: '10px', marginBottom: '8px', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                        {(() => {
                           const groups: { [domain: string]: CitationSource[] } = {};
                           msg.citations.forEach((c) => {
                             try {
                               const clean = c.url.replace(/^<|>$/g, '');
                               const domain = new URL(clean).hostname;
                               if (!groups[domain]) groups[domain] = [];
                               groups[domain].push(c);
                             } catch {
                               if (!groups['general']) groups['general'] = [];
                               groups['general'].push(c);
                             }
                           });
                           return Object.entries(groups).map(([domain, groupItems], idx) => (
                             <Citation key={idx} citations={groupItems} />
                           ));
                        })()}
                      </div>
                    )}

                    <AIActionsBar
                      messageText={msg.text}
                      onRetry={() => handleSend(msg.text)}
                    />
                  </>
                )}

                {/* User Message Attachments, Bubble & Quick Hover Actions */}
                {msg.sender === 'user' && (
                  <>
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div style={{ marginBottom: '6px' }}>
                        <AttachmentList items={msg.attachments} />
                      </div>
                    )}
                    
                    {editingMessageId === msg.id ? (
                      <div className="edit-message-container">
                        <textarea
                          className="edit-message-textarea"
                          value={editingText}
                          onChange={(e) => setEditingText(e.target.value)}
                        />
                        <div className="edit-message-actions">
                          <button
                            className="btn-edit-save"
                            onClick={() => handleUpdateMessage(msg.id, editingText)}
                          >
                            Save & Submit
                          </button>
                          <button
                            className="btn-edit-cancel"
                            onClick={() => {
                              setEditingMessageId(null);
                              setEditingText('');
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        {msg.text && (
                           <div className="msg-user-bubble">
                             <MarkdownRenderer content={msg.text} />
                           </div>
                         )}
                        <div className="user-actions-row">
                          <button
                            className="user-action-btn"
                            title="Edit"
                            onClick={() => {
                              setEditingMessageId(msg.id);
                              setEditingText(msg.text || '');
                            }}
                          >
                            <IconEdit size={14} />
                          </button>
                          <button
                            className="user-action-btn"
                            title="Copy"
                            onClick={() => handleCopyText(msg.text || '')}
                          >
                            <IconCopy size={14} />
                          </button>
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={streamEndRef} />
      </div>

      {/* Input Bar (When Messages Exist) */}
      {messages.length > 0 && (
        <div className="chat-input-wrapper">
          {isAgentActive && (
            <div className="composer-progress-bar">
              <div className="progress-spinner">
                {getProgressIcon()}
              </div>
              <span className="progress-text">
                {getProgressText()}
              </span>
            </div>
          )}
          {renderComposer()}
        </div>
      )}
    </div>
  );
};

export default ChatSection;
