import React from 'react';

const phases = [
  {
    phase: 'Phase 1 · Q1 2026',
    title: 'Sovereign Agent Core & Viveka Gate',
    status: 'COMPLETE ✓',
    statusCls: '#10B981',
    desc: 'Core execution sandbox, constitutional guardrails, and deterministic file system isolation.',
  },
  {
    phase: 'Phase 2 · Q2 2026',
    title: 'Vedic Epistemics & Ṛta-Score Engine',
    status: 'ACTIVE ●',
    statusCls: '#E8791A',
    desc: 'Real-time factuality verification, Satya Layer integration, and Pramāṇa Router model switching.',
  },
  {
    phase: 'Phase 3 · Q3 2026',
    title: 'Autonomous Fleet & Crash Recovery',
    status: 'UPCOMING ○',
    statusCls: '#64748B',
    desc: 'Multi-agent Task Graph execution, LSN checkpoint rollback, and zero-loss state persistence.',
  },
  {
    phase: 'Phase 4 · Q4 2026',
    title: 'AGI Long-Horizon Benchmark Control',
    status: 'UPCOMING ○',
    statusCls: '#64748B',
    desc: 'Enterprise multi-day reasoning benchmarks, air-gapped security compliance, and open research release.',
  },
];

const RoadmapSection: React.FC = () => {
  return (
    <section id="roadmap" className="website-section" style={{ backgroundColor: 'var(--color-brand-bg)' }}>
      <div className="section-label">Development Milestones</div>
      <h2 className="section-title">Research & Product Roadmap</h2>
      <p className="section-desc">
        Our multi-phase research trajectory toward building autonomous, sovereign, long-running agent infrastructure.
      </p>

      <div style={{ marginTop: '48px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {phases.map((item, idx) => (
          <div
            key={idx}
            className="feature-card"
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '24px',
              padding: '28px 36px',
            }}
          >
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-saffron)', fontWeight: 700 }}>{item.phase}</div>
              <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '24px', color: 'var(--color-ink)', marginTop: '4px' }}>
                {item.title}
              </h3>
              <p style={{ fontSize: '14px', color: 'rgba(17,24,39,0.7)', marginTop: '6px', maxWidth: '640px' }}>
                {item.desc}
              </p>
            </div>
            <span style={{ fontSize: '12px', fontWeight: 800, color: item.statusCls, background: 'rgba(0,0,0,0.04)', padding: '6px 14px', borderRadius: '20px' }}>
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};

export default RoadmapSection;
