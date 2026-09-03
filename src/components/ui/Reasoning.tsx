import React, { useState } from 'react';

// Official Lucide Brain Icon SVG (https://lucide.dev/icons/brain)
const BrainIcon: React.FC<{ size?: number; className?: string }> = ({ size = 16, className }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    style={{ minWidth: size, minHeight: size }}
  >
    <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
    <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
    <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/>
    <path d="M17.599 6.5a3 3 0 0 0-.399-1.375"/>
    <path d="M6.001 6.5a3 3 0 0 1 .399-1.375"/>
    <path d="M12 18v-5"/>
  </svg>
);

const IconChevronDown: React.FC<any> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconChevronUp: React.FC<any> = ({ size = 14, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="18 15 12 9 6 15" />
  </svg>
);

interface ReasoningContextProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  isStreaming: boolean;
}

const ReasoningContext = React.createContext<ReasoningContextProps | undefined>(undefined);

export const Reasoning: React.FC<{ children: React.ReactNode; isStreaming?: boolean }> = ({ children, isStreaming = false }) => {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <ReasoningContext.Provider value={{ isOpen, setIsOpen, isStreaming }}>
      <div className="nexus-reasoning-container">
        {children}
      </div>
    </ReasoningContext.Provider>
  );
};

export const ReasoningTrigger: React.FC = () => {
  const context = React.useContext(ReasoningContext);
  if (!context) throw new Error('ReasoningTrigger must be used within Reasoning');
  const { isOpen, setIsOpen, isStreaming } = context;

  return (
    <div className="nexus-reasoning-trigger" onClick={() => setIsOpen(!isOpen)}>
      <BrainIcon size={16} className="nexus-reasoning-brain-icon" />
      <span className="nexus-reasoning-title">
        {isStreaming ? 'Thinking...' : 'Thought for 4 seconds'}
      </span>
      {isOpen ? <IconChevronUp size={14} className="nexus-reasoning-chevron" /> : <IconChevronDown size={14} className="nexus-reasoning-chevron" />}
    </div>
  );
};

export const ReasoningContent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const context = React.useContext(ReasoningContext);
  if (!context) throw new Error('ReasoningContent must be used within Reasoning');
  const { isOpen } = context;

  if (!isOpen) return null;

  return (
    <div className="nexus-reasoning-content">
      {children}
    </div>
  );
};
