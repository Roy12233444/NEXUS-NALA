import React, { memo, useCallback, useEffect, useRef, useState } from 'react';
import { IconChevronDown } from './LucideIcons';

export type ModeOption = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  description?: string;
};

export type ModeSelectorProps = {
  modes: ModeOption[];
  value?: string;
  defaultValue?: string;
  onChange?: (modeId: string) => void;
  className?: string;
};

export const ModeSelector = memo(function ModeSelector({
  modes,
  value,
  defaultValue = 'agent',
  onChange,
}: ModeSelectorProps) {
  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState(defaultValue);
  const activeId = isControlled ? value : internalValue;
  const activeMode = modes.find((m) => m.id === activeId) ?? modes[0];
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);

  const handleSelect = useCallback(
    (id: string) => {
      if (!isControlled) setInternalValue(id);
      onChange?.(id);
      setOpen(false);
    },
    [isControlled, onChange]
  );

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (modes.length === 0) return null;

  return (
    <span ref={wrapRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          height: '28px',
          padding: '0 10px',
          borderRadius: '6px',
          fontSize: '12px',
          fontWeight: 600,
          color: '#334155',
          backgroundColor: open ? '#F1F5F9' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center' }}>{activeMode?.icon}</span>
        <span>{activeMode?.label}</span>
        <IconChevronDown size={13} style={{ color: '#64748B', marginLeft: '2px' }} />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            left: 0,
            marginBottom: '6px',
            minWidth: '220px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            backgroundColor: '#FFFFFF',
            padding: '4px',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05)',
            zIndex: 50,
          }}
        >
          {modes.map((mode) => {
            const isActive = mode.id === activeMode?.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => handleSelect(mode.id)}
                style={{
                  display: 'flex',
                  width: '100%',
                  alignItems: 'flex-start',
                  gap: '8px',
                  borderRadius: '6px',
                  padding: '6px 8px',
                  textAlign: 'left',
                  fontSize: '12px',
                  backgroundColor: isActive ? '#F8FAFC' : 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background-color 0.12s ease',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', marginTop: '2px' }}>{mode.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      display: 'block',
                      fontWeight: isActive ? 700 : 600,
                      color: isActive ? '#0F172A' : '#475569',
                    }}
                  >
                    {mode.label}
                  </span>
                  {mode.description && (
                    <span style={{ display: 'block', fontSize: '11px', color: '#94A3B8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {mode.description}
                    </span>
                  )}
                </div>
                {isActive && <span style={{ color: '#E8791A', fontWeight: 700 }}>✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </span>
  );
});

export default ModeSelector;
