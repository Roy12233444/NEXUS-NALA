import React from 'react';
import {
  IconPlus,
  IconImage,
  IconMic,
  IconArrowUp,
} from './LucideIcons';

// Hugeicons mappings to Lucide icons
export const PlusSignIcon = IconPlus;
export const Image01Icon = IconImage;
export const Mic02Icon = IconMic;
export const ArrowUp02Icon = IconArrowUp;
export const SquareIcon: React.FC<any> = ({ size = 16, color = 'currentColor', className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" stroke="none" className={className}>
    <rect x="5" y="5" width="14" height="14" rx="2" />
  </svg>
);

export const HugeiconsIcon: React.FC<{ icon: any; strokeWidth?: number; className?: string }> = ({ icon: IconComponent, strokeWidth, className }) => {
  return <IconComponent className={className} size={16} />;
};

// Simple Shadcn/ui Button compatibility component
export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; size?: string; asChild?: boolean }>(
  ({ children, variant, size, asChild, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`prompt-input-btn-base ${variant || ''} ${size || ''} ${className || ''}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export const PromptInput: React.FC<React.HTMLAttributes<HTMLDivElement> & { onSubmit?: (val: string) => void }> = ({ children, className = '', ...props }) => {
  return <div className={`nexus-prompt-input-card ${className}`} {...props}>{children}</div>;
};

export const PromptInputTextarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`nexus-prompt-textarea ${className || ''}`}
        {...props}
      />
    );
  }
);
PromptInputTextarea.displayName = 'PromptInputTextarea';

export const PromptInputActions: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div className="nexus-prompt-actions">{children}</div>;
};

export const PromptInputActionGroup: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div className="nexus-prompt-action-group">{children}</div>;
};

export const PromptInputAction: React.FC<{ children: React.ReactNode; asChild?: boolean; tooltip?: any }> = ({ children }) => {
  return <>{children}</>;
};
