import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="nala-sci-footer">
      {/* Corner Crosshair Anchors */}
      <span className="corner-crosshair top-left">+</span>
      <span className="corner-crosshair top-right">+</span>
      <span className="corner-crosshair bottom-left">+</span>
      <span className="corner-crosshair bottom-right">+</span>

      <div className="sci-footer-container">
        {/* Top Main Section */}
        <div className="sci-footer-main">
          {/* Left Hero Brand Box */}
          <div className="sci-brand-box">
            <div className="sci-logo-header">
              <h2 className="sci-logo-title">NALA</h2>
              <p className="sci-logo-sub">Nexus Lab AI Research Lab · Bengaluru, India</p>
            </div>
            <h1 className="sci-hero-motto">
              Memory systems for<br />
              agents that must endure<span className="sci-gold-dot">.</span>
            </h1>
          </div>

          {/* Right Status Badge & Links Column */}
          <div className="sci-nav-box">
            {/* Top Right System Status Badge */}
            <div className="sci-status-badge">
              <span className="badge-bracket top-l">┌</span>
              <span className="badge-bracket top-r">┐</span>
              <span className="badge-dot"></span>
              <span className="badge-text">RESEARCH SYSTEM ONLINE</span>
              <span className="badge-bracket bottom-l">└</span>
              <span className="badge-bracket bottom-r">┘</span>
            </div>

            {/* Link Columns */}
            <div className="sci-columns-wrapper">
              {/* Column 1: Research */}
              <div className="sci-col">
                <div className="sci-col-header">
                  <span>RESEARCH</span>
                  <span className="sci-dashed-line"></span>
                  <span className="sci-col-plus">+</span>
                </div>
                <ul className="sci-link-list">
                  <li><a href="#architecture">Architecture <span className="sci-plus">+</span></a></li>
                  <li><a href="#rigor">Epistemic Rigor <span className="sci-plus">+</span></a></li>
                  <li><a href="#roadmap">Roadmap <span className="sci-plus">+</span></a></li>
                </ul>
              </div>

              {/* Column 2: Organization */}
              <div className="sci-col">
                <div className="sci-col-header">
                  <span>ORGANIZATION</span>
                  <span className="sci-dashed-line"></span>
                  <span className="sci-col-plus">+</span>
                </div>
                <div className="sci-org-details">
                  <p>Nexus Lab AI</p>
                  <p>Bengaluru, India</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Center Golden Reticle Divider */}
        <div className="sci-divider-reticle">
          <span className="reticle-icon">✛</span>
        </div>

        {/* Bottom Facility & Metadata Bar */}
        <div className="sci-footer-bottom">
          <div className="sci-coords-box">
            <div className="vert-label">HUB</div>
            <div className="coords-content">
              <span className="coords-title">RESEARCH FACILITY</span>
              <span className="coords-val">Bengaluru Hub · Sovereign AI Engine</span>
            </div>
          </div>

          <div className="sci-copyright">
            © 2026 Nexus Lab AI. All rights reserved. Sovereign. Original. Indian.
          </div>

          <div className="sci-version-box">
            <div className="sci-cyan-indicators">
              <span className="indicator-square active"></span>
              <span className="indicator-square"></span>
              <span className="indicator-square"></span>
            </div>
            <span className="sci-vert-separator">|</span>
            <span className="sci-version-text">NALA Infrastructure v1.3.2</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
