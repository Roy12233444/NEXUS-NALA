import React from 'react';

const papers = [
  {
    title: 'Sovereign Long-Running AI Agents: Architecture & Formal Verification',
    date: 'June 2026',
    authors: 'Nexus Lab AI Research Team',
    desc: 'Presents the NALA architecture for multi-day agent execution, introducing zero-state-loss checkpointing and deterministic AST sandboxing.',
  },
  {
    title: 'Epistemic Verification via Pramāṇa Reasoning Routers',
    date: 'May 2026',
    authors: 'Nexus Lab AI Research Team',
    desc: 'Mathematical formalization of the Ṛta-Score metric and Vedic epistemic inference path selection across direct observation and logical deduction.',
  },
  {
    title: 'Constitutional State Guardrails for Multi-Day Agent Execution',
    date: 'April 2026',
    authors: 'Nexus Lab AI Research Team',
    desc: 'Empirical analysis of context drift, attention decay, and Viveka Gate constitutional validation algorithms.',
  },
];

const ResearchSection: React.FC = () => {
  return (
    <section id="research" className="website-section">
      <div className="section-label">Publications & Technical Papers</div>
      <h2 className="section-title">Open Research & Benchmark Publications</h2>
      <p className="section-desc">
        We believe in open scientific publication and transparent benchmark verification for autonomous AI systems.
      </p>

      <div className="cards-grid-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        {papers.map((paper, idx) => (
          <div key={idx} className="feature-card" style={{ justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--color-saffron)', fontWeight: 700 }}>{paper.date}</div>
              <h3 className="card-title" style={{ fontSize: '20px', marginTop: '8px' }}>{paper.title}</h3>
              <p className="card-body" style={{ marginTop: '12px', fontSize: '14px' }}>{paper.desc}</p>
            </div>
            <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'rgba(17,24,39,0.6)', fontWeight: 600 }}>{paper.authors}</span>
              <span style={{ fontSize: '13px', color: 'var(--color-saffron)', fontWeight: 700, cursor: 'pointer' }}>PDF ➔</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ResearchSection;
