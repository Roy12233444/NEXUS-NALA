import React, { useState, useRef, useEffect } from 'react';
import {
  IconGlobe,
  IconChevronLeft,
  IconChevronRight,
  IconExternalLink,
  IconX,
} from './LucideIcons';
import './Citation.css';

export interface CitationSource {
  url: string;
  title: string;
  description: string;
  author?: string;
  date?: string;
}

export function parseCitationUrl(url: string) {
  try {
    const clean = url.replace(/^<|>$/g, '');
    const parsed = new URL(clean);
    let siteName = parsed.hostname.replace(/^www\./, '');
    const parts = siteName.split('.');
    if (parts.length >= 2) {
      siteName = parts[parts.length - 2];
      siteName = siteName.charAt(0).toUpperCase() + siteName.slice(1);
    }
    return { hostname: parsed.hostname, siteName, cleanUrl: clean };
  } catch {
    return { hostname: 'website', siteName: 'Website', cleanUrl: url };
  }
}

export function resolveCitationSource(source: CitationSource) {
  const { hostname, siteName, cleanUrl } = parseCitationUrl(source.url);
  return { ...source, hostname, siteName, cleanUrl };
}

// Favicon icon resolver with custom SVG/styled fallbacks
export const CitationFavicon: React.FC<{ url: string; size?: number }> = ({ url, size = 14 }) => {
  const { hostname, siteName } = parseCitationUrl(url);
  const letter = siteName ? siteName.charAt(0).toUpperCase() : 'W';

  if (hostname.includes('wikipedia')) {
    return <span className="citation-fav-badge wiki">w</span>;
  }
  if (hostname.includes('github')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
      </svg>
    );
  }
  if (hostname.includes('mozilla') || hostname.includes('developer.mozilla')) {
    return <span className="citation-fav-badge mdn">M</span>;
  }
  if (hostname.includes('worldometers')) {
    return <span className="citation-fav-badge world">W</span>;
  }
  if (hostname.includes('ycombinator')) {
    return <span className="citation-fav-badge yc">Y</span>;
  }

  return <span className="citation-fav-badge default">{letter}</span>;
};

// Main Unified Citation Component (Handles Single, Grouped Carousel, Compact, and Inline)
export interface CitationGroupProps {
  citations: CitationSource[];
  showSiteName?: boolean;
  showFavicon?: boolean;
  label?: string;
  variant?: 'chip' | 'inline' | 'compact';
}

export const Citation: React.FC<CitationGroupProps> = ({
  citations,
  showSiteName = true,
  showFavicon = true,
  label,
  variant = 'chip',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (!citations || citations.length === 0) return null;

  const firstSource = citations[0];
  const resolvedFirst = resolveCitationSource(firstSource);
  const extraCount = citations.length > 1 ? citations.length - 1 : 0;
  const displayLabel = label || (showSiteName ? resolvedFirst.siteName : resolvedFirst.hostname);

  const currentSource = resolveCitationSource(citations[currentIndex]);

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev + 1) % citations.length);
  };

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev - 1 + citations.length) % citations.length);
  };

  return (
    <div className={`citation-container ${variant}`} ref={containerRef}>
      {/* Trigger Button */}
      <button
        className={`citation-pill ${isOpen ? 'active' : ''} ${variant}`}
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        {showFavicon && <CitationFavicon url={firstSource.url} />}
        {showSiteName && <span className="citation-pill-label">{displayLabel}</span>}
        {extraCount > 0 && <span className="citation-pill-count">+{extraCount}</span>}
      </button>

      {/* Popover Card Modal / Carousel */}
      {isOpen && (
        <div className="citation-popover animate-fade-in">
          {/* Header Bar */}
          <div className="popover-header">
            <div className="popover-badge">
              <CitationFavicon url={currentSource.url} />
              <span className="popover-sitename">{currentSource.siteName}</span>
            </div>

            {/* Pagination Controls for Multi-Source Carousels */}
            {citations.length > 1 ? (
              <div className="popover-pagination">
                <button
                  className="pagination-btn"
                  onClick={handlePrev}
                  title="Previous Source"
                  type="button"
                >
                  <IconChevronLeft size={13} />
                </button>
                <span className="pagination-index">
                  {currentIndex + 1}/{citations.length}
                </span>
                <button
                  className="pagination-btn"
                  onClick={handleNext}
                  title="Next Source"
                  type="button"
                >
                  <IconChevronRight size={13} />
                </button>
              </div>
            ) : (
              <span className="popover-single-tag">Source 1/1</span>
            )}
          </div>

          {/* Source Card Body */}
          <div className="popover-body">
            <a
              href={currentSource.cleanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="popover-title-link"
            >
              <h4 className="popover-title">{currentSource.title}</h4>
              <IconExternalLink size={13} className="external-link-icon" />
            </a>

            <p className="popover-description">{currentSource.description}</p>
          </div>

          {/* Footer Direct Link */}
          <div className="popover-footer">
            <span className="popover-domain">{currentSource.hostname}</span>
            <a
              href={currentSource.cleanUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-visit-source"
            >
              <span>Visit Source</span>
              <IconExternalLink size={12} />
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

// Preset Citation Components for direct markdown/JSX embedding
export const SingleCitation: React.FC<{ source: CitationSource }> = ({ source }) => (
  <Citation citations={[source]} />
);

export const MultiSourceCitation: React.FC<{ items: CitationSource[] }> = ({ items }) => (
  <Citation citations={items} />
);

export const InlineCitation: React.FC<{ source: CitationSource }> = ({ source }) => (
  <Citation citations={[source]} variant="inline" />
);

export default Citation;
