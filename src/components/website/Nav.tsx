import React from 'react';

interface NavProps {
  onLaunchApp?: () => void;
}

const Nav: React.FC<NavProps> = ({ onLaunchApp }) => {
  return (
    <header className="website-nav">
      <div className="nav-container">
        {/* Clean Prestigious NALA Brand Title */}
        <div className="nav-brand-static" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <span className="nav-title-text">NALA</span>
          <span className="nav-title-dot"></span>
        </div>

        <nav className="nav-links">
          <a href="#problem" className="nav-link">Problem</a>
          <a href="#architecture" className="nav-link">Architecture</a>
          <a href="#rigor" className="nav-link">Rigor</a>
          <a href="#roadmap" className="nav-link">Roadmap</a>
          <a href="#research" className="nav-link">Research</a>
          <button className="nav-cta-btn" onClick={onLaunchApp}>
            Launch Control Room ➔
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Nav;
