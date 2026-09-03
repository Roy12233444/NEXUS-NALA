import React, { useState } from 'react';
import { IconChevronDown, IconChevronUp, IconCheck, IconCopy, IconTerminal } from './LucideIcons';

export interface ExecutionCellProps {
  command: string;
  stdout?: string;
  stderr?: string;
  exitCode?: number;
  durationMs?: number;
  status?: 'running' | 'success' | 'failed';
  memoryMb?: string;
  timestamp?: string;
}

export const ExecutionCell: React.FC<ExecutionCellProps> = ({
  command,
  stdout = '',
  stderr = '',
  exitCode = 0,
  durationMs = 380,
  status = 'success',
  memoryMb = '42.5MB / 256MB',
  timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  const durationSec = (durationMs / 1000).toFixed(1);
  const hasOutput = Boolean(stdout.trim() || stderr.trim());

  const handleCopyLogs = () => {
    const textToCopy = `> ${command}\n${stdout}\n${stderr}`.trim();
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="execution-cell-container" style={{
      margin: '10px 0',
      borderRadius: '8px',
      border: '1px solid #E2E8F0',
      backgroundColor: '#FFFFFF',
      color: '#1E293B',
      fontFamily: 'monospace',
      fontSize: '13px',
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
    }}>
      {/* Terminal Card Header */}
      <div
        className="execution-cell-header"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          backgroundColor: '#F8FAFC',
          borderBottom: isExpanded ? '1px solid #E2E8F0' : 'none',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
          <IconTerminal size={15} style={{ color: '#0284C7', flexShrink: 0 }} />
          <span style={{ color: '#0284C7', fontWeight: 600 }}>$</span>
          <span style={{
            color: '#0F172A',
            fontWeight: 600,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {command}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          {/* Status Badge */}
          {status === 'running' && (
            <span style={{
              padding: '2px 8px',
              borderRadius: '12px',
              backgroundColor: '#FEF3C7',
              color: '#92400E',
              fontSize: '11px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              <span className="pulse-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#D97706' }} />
              RUNNING
            </span>
          )}

          {status === 'success' && (
            <span style={{
              padding: '2px 8px',
              borderRadius: '12px',
              backgroundColor: '#DCFCE7',
              color: '#166534',
              fontSize: '11px',
              fontWeight: 600,
            }}>
              SUCCESS ({durationSec}s)
            </span>
          )}

          {status === 'failed' && (
            <span style={{
              padding: '2px 8px',
              borderRadius: '12px',
              backgroundColor: '#FEE2E2',
              color: '#991B1B',
              fontSize: '11px',
              fontWeight: 600,
            }}>
              FAILED ({exitCode})
            </span>
          )}

          {/* Sandbox Memory Telemetry Badge */}
          <span style={{
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: '#F1F5F9',
            color: '#475569',
            fontSize: '11px',
            border: '1px solid #E2E8F0',
            fontWeight: 500,
          }} title="Kernel Job Object Memory Limit">
            🔒 {memoryMb}
          </span>

          {/* Copy Button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleCopyLogs();
            }}
            title="Copy terminal log"
            style={{
              background: 'none',
              border: 'none',
              color: copied ? '#166534' : '#64748B',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '2px',
            }}
          >
            {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
          </button>

          {/* Expand/Collapse Chevron */}
          <span style={{ color: '#64748B', display: 'flex', alignItems: 'center' }}>
            {isExpanded ? <IconChevronUp size={15} /> : <IconChevronDown size={15} />}
          </span>
        </div>
      </div>

      {/* Terminal Log Output Container */}
      {isExpanded && (
        <div className="execution-cell-body" style={{ padding: '10px 12px', backgroundColor: '#F8FAFC' }}>
          {stdout && (
            <pre style={{
              margin: 0,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: '#334155',
              lineHeight: '1.5',
              fontFamily: 'monospace',
              fontSize: '12px',
            }}>
              {stdout}
            </pre>
          )}

          {stderr && (
            <pre style={{
              margin: '6px 0 0 0',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: '#DC2626',
              lineHeight: '1.5',
              fontFamily: 'monospace',
              fontSize: '12px',
            }}>
              {stderr}
            </pre>
          )}

          {!hasOutput && status === 'running' && (
            <div style={{ color: '#64748B', fontStyle: 'italic', fontSize: '12px' }}>
              Streaming stdout/stderr output from Windows Job Object sandbox...
            </div>
          )}

          {!hasOutput && status !== 'running' && (
            <div style={{ color: '#64748B', fontStyle: 'italic', fontSize: '12px' }}>
              (Process exited with code {exitCode} - No console output)
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExecutionCell;
