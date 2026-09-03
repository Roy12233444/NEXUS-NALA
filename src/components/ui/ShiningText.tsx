import React from 'react';

interface ShiningTextProps {
  text: string;
  className?: string;
  style?: React.CSSProperties;
}

export const ShiningText: React.FC<ShiningTextProps> = ({ text, style }) => {
  return (
    <span className="shining-text-element" style={style}>
      {text}
      <style>{`
        .shining-text-element {
          background: linear-gradient(
            90deg,
            #1E293B 0%,
            #E8791A 50%,
            #1E293B 100%
          );
          background-size: 200% auto;
          color: transparent;
          -webkit-background-clip: text;
          background-clip: text;
          animation: shineText 3s linear infinite;
          font-weight: 700;
        }
        @keyframes shineText {
          to {
            background-position: 200% center;
          }
        }
      `}</style>
    </span>
  );
};

export default ShiningText;
