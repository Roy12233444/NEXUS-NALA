import React, { useState } from 'react';
import {
  IconSparkles,
  IconSearch,
  IconDatabase,
  IconZap,
  IconCheck,
  IconRefreshCcw,
} from '../../ui/LucideIcons';

export type PlanStepStatus = 'pending' | 'active' | 'success' | 'error';

export interface PlanStep {
  id: string;
  title: string;
  status: PlanStepStatus;
  duration?: string;
  icon?: React.ReactNode;
  details?: string[];
  toolName?: string;
}

export interface AgentPlanningProps {
  title?: string;
  steps?: PlanStep[];
}

const DEFAULT_STEPS: PlanStep[] = [
  {
    id: '1',
    title: 'Analyze mission directive & extract constraints',
    status: 'success',
    duration: '0.4s',
    icon: <IconSearch size={14} style={{ color: '#0284C7' }} />,
    toolName: 'context_tracker',
    details: [
      'Parsed user intent & target parameters',
      'Checked ExecutionContract (C_t) permissions',
      'Enforced PEP 578 audit hook isolation',
    ],
  },
  {
    id: '2',
    title: 'Query vector memory & knowledge base',
    status: 'success',
    duration: '1.2s',
    icon: <IconDatabase size={14} style={{ color: '#7C3AED' }} />,
    toolName: 'vector_search',
    details: [
      'Retrieved semantic embedding matches from index',
      'Verified Rta-Score safety baseline (0.98)',
      'Loaded relevant context files',
    ],
  },
  {
    id: '3',
    title: 'Execute sandbox tool in isolated kernel context',
    status: 'active',
    duration: '0.8s',
    icon: <IconZap size={14} style={{ color: '#E8791A' }} />,
    toolName: 'python_sandbox',
    details: [
      'Kernel Job Object caps applied (RSS: 16GB, CPU: 80%)',
      'Executing task steps under BehaviorMonitor observation',
      'Telemetry snapshot capture SLA < 1.0ms verified',
    ],
  },
];

export const AgentPlanningBlock: React.FC<AgentPlanningProps> = ({
  title = 'NALA Execution Plan & Task Graph',
  steps = DEFAULT_STEPS,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>('3');

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const getStatusIcon = (status: PlanStepStatus) => {
    switch (status) {
      case 'success':
        return <IconCheck size={14} style={{ color: '#10B981', fontWeight: 700 }} />;
      case 'active':
        return <IconRefreshCcw size={14} style={{ color: '#6366F1', animation: 'spin 1.5s linear infinite' }} />;
      case 'error':
        return <span style={{ color: '#EF4444', fontWeight: 700 }}>✕</span>;
      default:
        return <span style={{ color: '#94A3B8' }}>○</span>;
    }
  };

  return (
    <div
      style={{
        margin: '12px 0',
        borderRadius: '10px',
        border: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      {/* Plan Title Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderBottom: '1px solid #F1F5F9',
          backgroundColor: '#F8FAFC',
          fontSize: '12px',
          fontWeight: 700,
          color: '#1E293B',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <IconSparkles size={14} style={{ color: '#E8791A' }} />
          <span>{title}</span>
        </div>
        <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>
          {steps.filter((s) => s.status === 'success').length}/{steps.length} Completed
        </span>
      </div>

      {/* Step Timeline List */}
      <div style={{ padding: '8px 12px' }}>
        {steps.map((step, idx) => {
          const isExpanded = expandedId === step.id;
          return (
            <div
              key={step.id}
              style={{
                borderBottom: idx === steps.length - 1 ? 'none' : '1px solid #F1F5F9',
                padding: '8px 0',
              }}
            >
              {/* Row */}
              <div
                onClick={() => toggleExpand(step.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
                  <span>{getStatusIcon(step.status)}</span>
                  <span>{step.icon || <IconZap size={14} style={{ color: '#E8791A' }} />}</span>
                  <span
                    style={{
                      fontWeight: step.status === 'active' ? 700 : 500,
                      color: step.status === 'active' ? '#0F172A' : '#334155',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {step.title}
                  </span>
                  {step.toolName && (
                    <span
                      style={{
                        fontSize: '10px',
                        fontFamily: 'monospace',
                        fontWeight: 600,
                        color: '#6366F1',
                        backgroundColor: '#EEF2FF',
                        border: '1px solid #C7D2FE',
                        padding: '1px 6px',
                        borderRadius: '4px',
                      }}
                    >
                      {step.toolName}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {step.duration && (
                    <span style={{ fontSize: '11px', color: '#94A3B8', fontFamily: 'monospace' }}>
                      {step.duration}
                    </span>
                  )}
                  <span style={{ fontSize: '10px', color: '#94A3B8' }}>{isExpanded ? '▲' : '▼'}</span>
                </div>
              </div>

              {/* Accordion Detail Drawer */}
              {isExpanded && step.details && (
                <div
                  style={{
                    marginTop: '8px',
                    marginLeft: '28px',
                    padding: '8px 12px',
                    backgroundColor: '#F8FAFC',
                    borderRadius: '6px',
                    border: '1px solid #E2E8F0',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                    color: '#475569',
                  }}
                >
                  <ul style={{ margin: 0, paddingLeft: '16px' }}>
                    {step.details.map((item, dIdx) => (
                      <li key={dIdx} style={{ margin: '2px 0' }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AgentPlanningBlock;
