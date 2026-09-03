import React from 'react';

const pillars = [
  {
    num: '01',
    title: 'Viveka Gate',
    desc: 'Constitutional validation engine enforcing deterministic state safety and step verification before any action is committed to system memory.',
  },
  {
    num: '02',
    title: 'Satya Layer',
    desc: 'Real-time truthfulness and fact-check monitor preventing context drift, hallucinated completion, and unverified data assertions.',
  },
  {
    num: '03',
    title: 'Pramāṇa Router',
    desc: 'Vedic epistemic reasoning router selecting optimal inference paths across Pratyakṣa (Direct Perception) and Anumāna (Logical Inference).',
  },
  {
    num: '04',
    title: 'Fleet Coordinator',
    desc: 'Orchestrates multi-agent task graphs, providing automatic crash recovery, checkpoint LSN rollbacks, and zero state loss.',
  },
  {
    num: '05',
    title: 'Memory Governance',
    desc: 'Dynamic 128K context window budgeting with automated Stage 2 compaction, token allocation, and orphan token pruning.',
  },
  {
    num: '06',
    title: 'Sovereign Compute',
    desc: 'Air-gapped sandboxing preventing unverified process spawning, network leaks, or arbitrary shell permissions.',
  },
];

const ArchitectureSection: React.FC = () => {
  return (
    <section id="architecture" className="website-section">
      <div className="reveal-element">
        <div className="section-label">Architecture</div>
        <h2 className="section-title">Built for Uncompromising Agentic Reliability</h2>
        <p className="section-desc">
          NALA decouples agent reasoning into verifiable, fault-tolerant execution layers that guarantee non-stop operation across hours or days.
        </p>
      </div>

      <div className="cards-grid-3">
        {pillars.map((item, idx) => (
          <div key={item.num} className={`feature-card reveal-element reveal-delay-${(idx % 3) + 1}`}>
            <span className="card-num">{item.num}</span>
            <h3 className="card-title">{item.title}</h3>
            <p className="card-body">{item.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ArchitectureSection;
