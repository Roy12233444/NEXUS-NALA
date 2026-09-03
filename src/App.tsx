import React, { useState } from 'react';
import Nav from './components/website/Nav';
import Hero from './components/website/Hero';
import Marquee from './components/website/Marquee';
import ProblemSection from './components/website/ProblemSection';
import ArchitectureSection from './components/website/ArchitectureSection';
import RigorSection from './components/website/RigorSection';
import RoadmapSection from './components/website/RoadmapSection';
import ResearchSection from './components/website/ResearchSection';
import WebsiteFooter from './components/website/Footer';
import { useScrollReveal } from './hooks/useScrollReveal';
import { useLenisScroll } from './hooks/useLenisScroll';
import './components/website/Website.css';

// Claude Cowork Workspace Layout
import CoworkLayout from './components/layout/CoworkLayout';
import './App.css';

function App() {
  const [viewMode, setViewMode] = useState<'website' | 'app'>('website');

  // Activate Smooth Scroll Reveal & Lenis High-Performance Smooth Scroll
  useScrollReveal();
  useLenisScroll();

  if (viewMode === 'app') {
    return <CoworkLayout onBackToWebsite={() => setViewMode('website')} />;
  }

  return (
    <div className="nala-website">
      {/* Top Navbar */}
      <Nav onLaunchApp={() => setViewMode('app')} />

      {/* Hero Section */}
      <Hero onLaunchApp={() => setViewMode('app')} />

      {/* Principles Marquee Ticker */}
      <Marquee />

      {/* 1. Problem Section */}
      <ProblemSection />

      {/* 2. Architecture Section */}
      <ArchitectureSection />

      {/* 3. Rigor Section */}
      <RigorSection />

      {/* 4. Roadmap Section */}
      <RoadmapSection />

      {/* 5. Research Papers Section */}
      <ResearchSection />

      {/* Footer */}
      <WebsiteFooter />
    </div>
  );
}

export default App;