import React from 'react';

const problems = [
  {
    icon: '📉',
    title: 'Context Drift & Attention Decay',
    body: 'Standard LLM agents lose instruction fidelity as execution history grows beyond 10,000 tokens, degrading accuracy on long-horizon objectives.',
  },
  {
    icon: '🌀',
    title: 'Hallucinated Task Completion',
    body: 'Agents prematurely claim success without empirical runtime verification, masking silent step failures under polite summary responses.',
  },
  {
    icon: '💥',
    title: 'State Loss on Crash',
    body: 'Process restarts wipe in-memory thread loops, losing hours of execution context and requiring complete restarts from scratch.',
  },
  {
    icon: '⚠️',
    title: 'Unchecked System Permissions',
    body: 'Unbounded shell access allows catastrophic file deletions, unverified dependency installs, and network data leaks without audit trails.',
  },
];

const ProblemSection: React.FC = () => {
  return (
    <section id="problem" className="website-section" style={{ backgroundColor: 'var(--color-brand-bg)' }}>
      <div className="reveal-element">
        <div className="section-label">The Core Challenge</div>
        <h2 className="section-title">Why Standard AI Agents Fail on Long Horizon Tasks</h2>
        <p className="section-desc">
          Today's AI frameworks work well for short 5-minute tasks, but break down when tasked with complex 10-hour or multi-day engineering workflows.
        </p>
      </div>

      <div className="cards-grid-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        {problems.map((item, idx) => (
          <div key={idx} className={`feature-card reveal-element reveal-delay-${(idx % 4) + 1}`} style={{ background: '#FAF9F6' }}>
            <span style={{ fontSize: '32px' }}>{item.icon}</span>
            <h3 className="card-title" style={{ fontSize: '20px' }}>{item.title}</h3>
            <p className="card-body">{item.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ProblemSection;
