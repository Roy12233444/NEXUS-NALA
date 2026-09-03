import React, { useState } from 'react';
import './ToolExecutionTrace.css';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ToolStepStatus = 'completed' | 'active' | 'pending' | 'error';

export interface ToolStepItem {
  id: string;
  title: string;
  status: ToolStepStatus;
  duration?: string;
  toolName?: string;
  details?: string[];
  errorMessage?: string;
  params?: Record<string, unknown>;
  output?: string;
}

interface ToolExecutionTraceProps {
  steps: ToolStepItem[];
  isActive?: boolean; // true while NALA is still running
  defaultOpen?: boolean;
}

// ─── Icon Helpers (pure SVG, no color wrappers) ───────────────────────────────

/** Check circle */
const IcoCheck = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="m9 12 2 2 4-4"/>
  </svg>
);

/** X circle (error) */
const IcoXCircle = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="m15 9-6 6"/><path d="m9 9 6 6"/>
  </svg>
);

/** Spinning loader */
const IcoLoader = () => (
  <svg className="tet-spin" width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
  </svg>
);

/** Pending dot */
const IcoDot = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="4"/>
  </svg>
);

/** Chevron right */
const IcoChevronRight = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m9 18 6-6-6-6"/>
  </svg>
);

/** Chevron down */
const IcoChevronDown = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m6 9 6 6 6-6"/>
  </svg>
);

/** Tool icons mapped by toolName keyword */
const toolIcon = (toolName?: string): React.ReactNode => {
  const t = (toolName || '').toLowerCase();
  if (t.includes('read') || t.includes('file'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/>
      </svg>
    );
  if (t.includes('write') || t.includes('edit') || t.includes('create'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    );
  if (t.includes('search') || t.includes('grep') || t.includes('find'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
    );
  if (t.includes('run') || t.includes('command') || t.includes('exec') || t.includes('terminal'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>
      </svg>
    );
  if (t.includes('recall') || t.includes('memory') || t.includes('database'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/>
      </svg>
    );
  if (t.includes('plan') || t.includes('think') || t.includes('reason'))
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a8 8 0 0 1 8 8v.5a3.5 3.5 0 0 1-3.5 3.5H15a3 3 0 0 0-3 3v1a2 2 0 0 1-4 0v-1a7 7 0 0 1-7-7A8 8 0 0 1 12 2z"/>
        <path d="M12 18v2"/><path d="M9 21h6"/>
      </svg>
    );
  // Default: zap
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  );
};

// ─── Step Row ─────────────────────────────────────────────────────────────────

interface StepRowProps {
  step: ToolStepItem;
  isLast: boolean;
}

const StepRow: React.FC<StepRowProps> = ({ step, isLast }) => {
  const [open, setOpen] = useState(step.status === 'active' || step.status === 'error');

  const hasDetail = Boolean(
    step.details?.length || step.output || step.params || step.errorMessage
  );

  const statusNode = () => {
    switch (step.status) {
      case 'completed': return <span className="tet-status-icon completed"><IcoCheck /></span>;
      case 'error':     return <span className="tet-status-icon error"><IcoXCircle /></span>;
      case 'active':    return <span className="tet-status-icon active"><IcoLoader /></span>;
      default:          return <span className="tet-status-icon pending"><IcoDot /></span>;
    }
  };

  return (
    <div className={`tet-step ${step.status} ${isLast ? 'last' : ''}`}>
      {/* Timeline rail dot + connector line */}
      <div className="tet-rail">
        {statusNode()}
        {!isLast && <div className={`tet-connector ${step.status === 'completed' ? 'filled' : ''}`} />}
      </div>

      {/* Step body */}
      <div className="tet-body">
        {/* Header row */}
        <div
          className={`tet-step-header ${hasDetail ? 'clickable' : ''}`}
          onClick={() => hasDetail && setOpen(!open)}
        >
          <span className="tet-tool-icon">{toolIcon(step.toolName || step.title)}</span>

          {step.toolName && (
            <span className="tet-tool-badge">{step.toolName}</span>
          )}

          <span className="tet-step-title">{step.title}</span>

          <div className="tet-step-meta">
            {step.duration && (
              <span className="tet-duration">{step.duration}</span>
            )}
            {hasDetail && (
              <span className={`tet-chevron ${open ? 'open' : ''}`}>
                {open ? <IcoChevronDown /> : <IcoChevronRight />}
              </span>
            )}
          </div>
        </div>

        {/* Expanded detail panel */}
        {open && hasDetail && (
          <div className="tet-detail-panel">
            {/* Params / Input */}
            {step.params && Object.keys(step.params).length > 0 && (
              <div className="tet-detail-block">
                <div className="tet-detail-label">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                  </svg>
                  Input Parameters
                </div>
                <pre className="tet-code-block">{JSON.stringify(step.params, null, 2)}</pre>
              </div>
            )}

            {/* Details bullet list */}
            {step.details && step.details.length > 0 && (
              <div className="tet-detail-block">
                <div className="tet-detail-label">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>
                  </svg>
                  Execution Log
                </div>
                <ul className="tet-details-list">
                  {step.details.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Output console */}
            {step.output && (
              <div className="tet-detail-block">
                <div className="tet-detail-label">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>
                  </svg>
                  Output
                </div>
                <pre className="tet-output-block">{step.output}</pre>
              </div>
            )}

            {/* Error callout */}
            {step.errorMessage && (
              <div className="tet-error-callout">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>
                </svg>
                <span>{step.errorMessage}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────

export const ToolExecutionTrace: React.FC<ToolExecutionTraceProps> = ({
  steps,
  isActive = false,
  defaultOpen = true,
}) => {
  const [open, setOpen] = useState(defaultOpen);

  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const errorCount = steps.filter((s) => s.status === 'error').length;
  const total = steps.length;
  const allDone = !isActive && completedCount + errorCount === total && total > 0;

  // Total elapsed from durations if available
  const headerLabel = isActive
    ? `${completedCount} / ${total} completed`
    : allDone
    ? `${total} tool call${total !== 1 ? 's' : ''} · done`
    : `${total} tool call${total !== 1 ? 's' : ''}`;

  const headerStatusIcon = () => {
    if (isActive)
      return (
        <svg className="tet-spin" width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
      );
    if (allDone && errorCount === 0)
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
        </svg>
      );
    if (errorCount > 0)
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <path d="M12 9v4"/><path d="M12 17h.01"/>
        </svg>
      );
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    );
  };

  return (
    <div className={`tet-root ${isActive ? 'active' : ''} ${allDone ? 'done' : ''} ${errorCount > 0 ? 'has-error' : ''}`}>
      {/* Collapsed summary header */}
      <button
        className="tet-header"
        onClick={() => setOpen(!open)}
        type="button"
        aria-expanded={open}
      >
        <div className="tet-header-left">
          <span className={`tet-header-icon ${isActive ? 'active' : allDone && errorCount === 0 ? 'done' : errorCount > 0 ? 'error' : ''}`}>
            {headerStatusIcon()}
          </span>
          <span className="tet-header-label">{headerLabel}</span>
          {errorCount > 0 && (
            <span className="tet-error-badge">{errorCount} error{errorCount > 1 ? 's' : ''}</span>
          )}
        </div>
        <span className={`tet-header-chevron ${open ? 'open' : ''}`}>
          {open ? <IcoChevronDown /> : <IcoChevronRight />}
        </span>
      </button>

      {/* Expandable step tree */}
      {open && (
        <div className="tet-steps-tree">
          {steps.map((step, idx) => (
            <StepRow
              key={step.id}
              step={step}
              isLast={idx === steps.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ToolExecutionTrace;
