import React from 'react';

interface HeroProps {
  onLaunchApp?: () => void;
}

const Hero: React.FC<HeroProps> = ({ onLaunchApp }) => {
  return (
    <section className="hero-section">
      <div className="hero-container">
        {/* Lab Tag */}
        <div className="hero-tag">
          <span className="nav-brand-dot"></span>
          <span className="hero-tag-text">Nexus Lab AI Research Lab · Bengaluru, India</span>
        </div>

        {/* Headline */}
        <h1 className="hero-headline">
          Sovereign Infrastructure for <span className="text-saffron italic">Long Running</span> AI Agents.
        </h1>

        {/* Subhead */}
        <p className="hero-subhead">
          Agents that run for hours or days — without losing state, without hallucinating completion, and without violating constitutional safety rules.
        </p>

        {/* CTA Buttons */}
        <div className="hero-cta-group">
          <button className="btn-primary-dark" onClick={onLaunchApp}>
            <span>Launch Agent Control Room</span>
            <span>➔</span>
          </button>
          <a href="#architecture" className="btn-outline-dark" style={{ textDecoration: 'none' }}>
            Read the Architecture
          </a>
        </div>
      </div>
    </section>
  );
};

export default Hero;
