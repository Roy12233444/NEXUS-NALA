import React from 'react';
import './DotMatrix.css';

export interface DotMatrixState {
  id: number;
  dots: boolean[];
}

// Helper to construct 5x5 states (25 dots)
const makeState = (id: number, template: number[]): DotMatrixState => ({
  id,
  dots: template.map(val => val === 1),
});

// 16 distinct 5x5 matrix dot patterns (0 through 15)
export const dotMatrixStates: DotMatrixState[] = [
  // 0: Center dot
  makeState(0, [
    0,0,0,0,0,
    0,0,0,0,0,
    0,0,1,0,0,
    0,0,0,0,0,
    0,0,0,0,0,
  ]),
  // 1: Center 3x3 Ring
  makeState(1, [
    0,0,0,0,0,
    0,1,1,1,0,
    0,1,0,1,0,
    0,1,1,1,0,
    0,0,0,0,0,
  ]),
  // 2: Cross / Plus
  makeState(2, [
    0,0,1,0,0,
    0,0,1,0,0,
    1,1,1,1,1,
    0,0,1,0,0,
    0,0,1,0,0,
  ]),
  // 3: X-pattern
  makeState(3, [
    1,0,0,0,1,
    0,1,0,1,0,
    0,0,1,0,0,
    0,1,0,1,0,
    1,0,0,0,1,
  ]),
  // 4: Outer Perimeter Ring
  makeState(4, [
    1,1,1,1,1,
    1,0,0,0,1,
    1,0,0,0,1,
    1,0,0,0,1,
    1,1,1,1,1,
  ]),
  // 5: 4 Corners
  makeState(5, [
    1,1,0,1,1,
    1,0,0,0,1,
    0,0,0,0,0,
    1,0,0,0,1,
    1,1,0,1,1,
  ]),
  // 6: Diagonal TL-BR
  makeState(6, [
    1,0,0,0,0,
    0,1,0,0,0,
    0,0,1,0,0,
    0,0,0,1,0,
    0,0,0,0,1,
  ]),
  // 7: Diagonal TR-BL
  makeState(7, [
    0,0,0,0,1,
    0,0,0,1,0,
    0,0,1,0,0,
    0,1,0,0,0,
    1,0,0,0,0,
  ]),
  // 8: Checkerboard Alternating A
  makeState(8, [
    1,0,1,0,1,
    0,1,0,1,0,
    1,0,1,0,1,
    0,1,0,1,0,
    1,0,1,0,1,
  ]),
  // 9: Checkerboard Alternating B
  makeState(9, [
    0,1,0,1,0,
    1,0,1,0,1,
    0,1,0,1,0,
    1,0,1,0,1,
    0,1,0,1,0,
  ]),
  // 10: Horizontal Bars
  makeState(10, [
    1,1,1,1,1,
    0,0,0,0,0,
    1,1,1,1,1,
    0,0,0,0,0,
    1,1,1,1,1,
  ]),
  // 11: Vertical Bars
  makeState(11, [
    1,0,1,0,1,
    1,0,1,0,1,
    1,0,1,0,1,
    1,0,1,0,1,
    1,0,1,0,1,
  ]),
  // 12: Diamond Frame
  makeState(12, [
    0,0,1,0,0,
    0,1,0,1,0,
    1,0,0,0,1,
    0,1,0,1,0,
    0,0,1,0,0,
  ]),
  // 13: Core 3x3 Solid
  makeState(13, [
    0,0,0,0,0,
    0,1,1,1,0,
    0,1,1,1,0,
    0,1,1,1,0,
    0,0,0,0,0,
  ]),
  // 14: Concentric Target
  makeState(14, [
    1,1,1,1,1,
    1,0,0,0,1,
    1,0,1,0,1,
    1,0,0,0,1,
    1,1,1,1,1,
  ]),
  // 15: Full Matrix (All active)
  makeState(15, [
    1,1,1,1,1,
    1,1,1,1,1,
    1,1,1,1,1,
    1,1,1,1,1,
    1,1,1,1,1,
  ]),
];

export interface DotMatrixProps {
  state?: DotMatrixState;
  stateIndex?: number;
  className?: string;
  color?: string;
  size?: number;
  isLoading?: boolean;
}

export const DotMatrix: React.FC<DotMatrixProps> = ({
  state,
  stateIndex = 0,
  className = '',
  color = '#E8791A',
  size = 16,
  isLoading = false,
}) => {
  const activeState = state || dotMatrixStates[stateIndex % dotMatrixStates.length] || dotMatrixStates[0];
  const activeDots = isLoading ? Array(25).fill(true) : activeState.dots;

  return (
    <div
      className={`dot-matrix-container ${isLoading ? 'is-loading' : ''} ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
      }}
      title={isLoading ? 'NALA is thinking...' : `DotMatrix Pattern #${activeState.id}`}
    >
      <div className="dot-matrix-grid">
        {activeDots.map((active, idx) => {
          const row = Math.floor(idx / 5);
          const col = idx % 5;
          
          // Staggered loading waves vs pattern breathe
          const delay = isLoading
            ? (row * 0.08 + col * 0.08) - 1.6
            : (Math.abs(2 - row) + Math.abs(2 - col)) * 0.12 - 1.2;

          const duration = isLoading ? 0.7 : 1.0 + (idx % 3) * 0.15;

          return (
            <span
              key={idx}
              className={`dot-matrix-cell ${active ? 'active' : 'inactive'}`}
              style={{
                backgroundColor: active ? color : 'rgba(148, 163, 184, 0.15)',
                boxShadow: active ? `0 0 5px ${color}66` : 'none',
                animationDelay: `${delay}s`,
                animationDuration: `${duration}s`,
                '--dot-matrix-hi': active ? '1' : '0.15',
                '--dot-matrix-lo': active ? '0.2' : '0.05',
              } as React.CSSProperties}
            />
          );
        })}
      </div>
    </div>
  );
};

export default DotMatrix;
