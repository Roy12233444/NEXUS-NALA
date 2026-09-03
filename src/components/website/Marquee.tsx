import React from 'react';

const principles = [
  'Persistent State',
  'Self-Verification',
  'Constitutional Safety',
  'Crash Recovery',
  'Cost-Aware Routing',
  'Epistemic Consensus',
  'Sovereign Compute',
];

const Marquee: React.FC = () => {
  return (
    <div className="marquee-banner">
      <div className="marquee-track">
        {[...principles, ...principles, ...principles].map((item, idx) => (
          <div key={idx} className="marquee-item">
            <span>{item}</span>
            <span className="nav-brand-dot"></span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Marquee;
