import React, { useEffect, useRef, useState } from 'react';
import ShiningText from '../../ui/ShiningText';
import { IconBrain, IconRefreshCcw } from '../../ui/LucideIcons';

interface AIThinkingBlockProps {
  thinkingText?: string;
  isCompleted?: boolean;
}

export const AIThinkingBlock: React.FC<AIThinkingBlockProps> = ({
  thinkingText,
  isCompleted = false,
}) => {
  const [timer, setTimer] = useState(0);
  const contentRef = useRef<HTMLDivElement>(null);

  const defaultThinking = `Analyzing mission directive and extracting execution constraints...
Checking active ExecutionContract (C_t) and Ṛta-Score safety thresholds.
Initializing RLock telemetry accumulators in BehaviorMonitor (runtime/behavior_monitor.py).
Querying vector memory and checking local project dependencies.
Evaluating tool permissions: [vector_search, python_sandbox, web_search].
Executing task step within isolated Python audit hook (PEP 578) sandbox.
Synthesizing response and validating factual consistency against Satya-Truthfulness layer.`;

  const textToDisplay = thinkingText || defaultThinking;

  useEffect(() => {
    if (isCompleted) return;
    const interval = setInterval(() => {
      setTimer((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isCompleted]);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [textToDisplay]);

  return (
    <div
      style={{
        margin: '12px 0',
        borderRadius: '10px',
        border: '1px solid #E2E8F0',
        backgroundColor: '#F8FAFC',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: '1px solid #EEF2F6',
          backgroundColor: '#F1F5F9',
          fontSize: '12px',
          fontWeight: 600,
          color: '#334155',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {!isCompleted ? (
            <IconRefreshCcw size={14} style={{ color: '#E8791A', animation: 'spin 1.5s linear infinite' }} />
          ) : (
            <IconBrain size={14} style={{ color: '#E8791A' }} />
          )}
          {isCompleted ? (
            <span>Thought Process</span>
          ) : (
            <ShiningText text="NALA is thinking..." />
          )}
        </div>
        <div style={{ fontSize: '11px', color: '#64748B', fontFamily: 'monospace' }}>
          ({timer}s)
        </div>
      </div>

      {/* Auto-scrolling Reasoning Box */}
      <div
        ref={contentRef}
        style={{
          maxHeight: '140px',
          overflowY: 'auto',
          padding: '10px 12px',
          fontSize: '12px',
          lineHeight: '1.6',
          fontFamily: 'monospace',
          color: '#475569',
          whiteSpace: 'pre-wrap',
        }}
      >
        {textToDisplay}
      </div>
    </div>
  );
};

export default AIThinkingBlock;
