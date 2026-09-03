import React from 'react';

export const MessageLoading: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '10px 14px',
        borderRadius: '16px',
        borderTopLeftRadius: '4px',
        backgroundColor: '#F1F5F9',
        width: 'fit-content',
        margin: '6px 0',
      }}
    >
      <span className="dot-pulse" style={{ animationDelay: '0s' }}></span>
      <span className="dot-pulse" style={{ animationDelay: '0.2s' }}></span>
      <span className="dot-pulse" style={{ animationDelay: '0.4s' }}></span>
      <style>{`
        .dot-pulse {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background-color: #64748B;
          display: inline-block;
          animation: dotPulse 1.4s infinite ease-in-out both;
        }
        @keyframes dotPulse {
          0%, 80%, 100% {
            transform: scale(0.6);
            opacity: 0.4;
          }
          40% {
            transform: scale(1.1);
            opacity: 1;
            background-color: #E8791A;
          }
        }
      `}</style>
    </div>
  );
};

export default MessageLoading;
