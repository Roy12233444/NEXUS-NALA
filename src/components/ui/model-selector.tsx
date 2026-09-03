import React, { useState, useRef, useEffect } from 'react';
import { IconSparkles, IconZap, IconBrain, IconCheck, IconChevronDown } from './LucideIcons';

export type Model = 'deepseek-chat' | 'fast-v' | 'claude-3.5-sonnet' | 'llama-3-local' | 'gpt-4o';

export interface ModelOption {
  id: Model;
  name: string;
  provider: string;
  description: string;
  badge?: string;
  icon?: React.ReactNode;
}

export const MODELS: ModelOption[] = [
  {
    id: 'deepseek-chat',
    name: 'DeepSeek Chat (V3 / R1)',
    provider: 'DeepSeek',
    description: 'High-reasoning open weights model with low latency',
    badge: 'Popular',
    icon: <IconBrain size={14} style={{ color: '#0284C7' }} />,
  },
  {
    id: 'fast-v',
    name: 'Fast v (Default)',
    provider: 'Nexus AI',
    description: 'Ultra-fast sub-millisecond inference for live execution',
    badge: 'Fast',
    icon: <IconZap size={14} style={{ color: '#E8791A' }} />,
  },
  {
    id: 'claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    description: 'State-of-the-art reasoning for complex code and research',
    badge: 'Smart',
    icon: <IconSparkles size={14} style={{ color: '#D97706' }} />,
  },
  {
    id: 'llama-3-local',
    name: 'Local LLaMA 3 (70B)',
    provider: 'Local Sandbox',
    description: '100% offline, privacy-first local model execution',
    badge: 'Local',
    icon: <IconBrain size={14} style={{ color: '#10B981' }} />,
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    description: 'Multimodal intelligence for vision and code synthesis',
    icon: <IconSparkles size={14} style={{ color: '#10B981' }} />,
  },
];

interface ModelSelectorProps {
  value?: Model;
  defaultValue?: Model;
  onChange?: (model: Model) => void;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  value,
  defaultValue = 'deepseek-chat',
  onChange,
}) => {
  const [internalValue, setInternalValue] = useState<Model>(defaultValue);
  const activeId = value !== undefined ? value : internalValue;
  const activeModel = MODELS.find((m) => m.id === activeId) || MODELS[0];
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const handleSelect = (id: Model) => {
    if (value === undefined) setInternalValue(id);
    onChange?.(id);
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
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
        <span style={{ display: 'flex', alignItems: 'center' }}>{activeModel.icon}</span>
        <span>{activeModel.name.split(' ')[0]}</span>
        <IconChevronDown size={13} style={{ color: '#64748B', marginLeft: '2px' }} />
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            right: 0,
            marginBottom: '6px',
            width: '260px',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            backgroundColor: '#FFFFFF',
            padding: '4px',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05)',
            zIndex: 100,
          }}
        >
          {MODELS.map((m) => {
            const selected = m.id === activeModel.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => handleSelect(m.id)}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  width: '100%',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: selected ? '#F8FAFC' : 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'background-color 0.12s ease',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', marginTop: '2px' }}>{m.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '12px', fontWeight: selected ? 700 : 600, color: selected ? '#0F172A' : '#334155' }}>
                      {m.name}
                    </span>
                    {m.badge && (
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          color: '#E8791A',
                          backgroundColor: '#FFF7ED',
                          border: '1px solid #FFEDD5',
                          padding: '0 4px',
                          borderRadius: '4px',
                        }}
                      >
                        {m.badge}
                      </span>
                    )}
                  </div>
                  <span
                    style={{
                      display: 'block',
                      fontSize: '10px',
                      color: '#94A3B8',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {m.description}
                  </span>
                </div>
                {selected && <IconCheck size={14} style={{ color: '#E8791A', marginTop: '2px' }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
