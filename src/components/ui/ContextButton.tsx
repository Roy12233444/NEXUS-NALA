import React from 'react';
import './ContextButton.css';

interface ContextButtonProps {
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  className?: string;
}

const ContextButton: React.FC<ContextButtonProps> = ({
  label,
  icon,
  onClick,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  className = '',
}) => {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!disabled && onClick) {
      onClick();
    }
  };

  return (
    <button
      className={`context-btn btn-${variant} btn-${size} ${className}`}
      onClick={handleClick}
      disabled={disabled}
    >
      {icon && <span className="button-icon">{icon}</span>}
      <span className="button-text">{label}</span>
    </button>
  );
};

export default ContextButton;