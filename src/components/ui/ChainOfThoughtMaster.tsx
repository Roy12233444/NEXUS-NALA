import React, { useState } from 'react';
import {
  IconBrain,
  IconSearch,
  IconGlobe,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconFolder,
  IconCode,
  IconZap,
  IconDatabase,
  IconExternalLink,
} from './LucideIcons';
import './ChainOfThoughtMaster.css';

export type CoTVariant = 'default' | 'basic' | 'rich' | 'error' | 'no-header';
export type CoTStepStatus = 'completed' | 'active' | 'pending' | 'error';

export interface CoTWebSource {
  title: string;
  domain: string;
  url: string;
}

export interface CoTDataCard {
  label: string;
  value: string;
  subtitle?: string;
}

export interface CoTStepItem {
  id: string;
  title: string;
  status: CoTStepStatus;
  duration?: string;
  icon?: React.ReactNode;
  toolName?: string;
  details?: string[];
  searchQueries?: string[];
  webSources?: CoTWebSource[];
  dataCards?: CoTDataCard[];
  errorMessage?: string;
}

export interface ChainOfThoughtMasterProps {
  variant?: CoTVariant;
  triggerTitle?: string;
  triggerIcon?: React.ReactNode;
  steps: CoTStepItem[];
  completionLabel?: string;
  defaultOpen?: boolean;
  autoCloseOnAllComplete?: boolean;
}

export const ChainOfThoughtMaster: React.FC<ChainOfThoughtMasterProps> = ({
  variant = 'default',
  triggerTitle = 'Executing directive plan...',
  triggerIcon,
  steps,
  completionLabel = 'Directive execution complete',
  defaultOpen = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [expandedSteps, setExpandedSteps] = useState<{ [id: string]: boolean }>({});

  const toggleStep = (id: string) => {
    setExpandedSteps((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const isNoHeader = variant === 'no-header';
  const completedCount = steps.filter((s) => s.status === 'completed').length;

  return (
    <div className={`cot-master-container ${variant} ${isOpen ? 'is-open' : 'is-closed'}`}>
      {/* Accordion Header / Trigger Bar */}
      {!isNoHeader && (
        <button
          className={`cot-trigger-bar ${variant}`}
          onClick={() => setIsOpen(!isOpen)}
          type="button"
        >
          <div className="cot-trigger-left">
            <span className="cot-trigger-icon">
              {triggerIcon || <IconBrain size={16} className="text-amber" />}
            </span>
            <span className="cot-trigger-title">{triggerTitle}</span>
          </div>

          <div className="cot-trigger-right">
            <span className="cot-step-badge">
              {completedCount}/{steps.length} Completed
            </span>
            <span className={`cot-chevron ${isOpen ? 'open' : ''}`}>
              <IconChevronDown size={14} />
            </span>
          </div>
        </button>
      )}

      {/* Accordion Content Body */}
      {(isOpen || isNoHeader) && (
        <div className="cot-content-body animate-slide-down">
          <div className="cot-steps-timeline">
            {steps.map((step) => {
              const isExpanded = expandedSteps[step.id] ?? (step.status === 'active' || step.status === 'error' || Boolean(step.searchQueries?.length));
              const hasSubContent = Boolean(
                step.details?.length ||
                  step.searchQueries?.length ||
                  step.webSources?.length ||
                  step.dataCards?.length ||
                  step.errorMessage
              );

              return (
                <div key={step.id} className={`cot-step-item ${step.status} ${variant}`}>
                  {/* Step Header Line */}
                  <div
                    className={`cot-step-header ${hasSubContent ? 'clickable' : ''}`}
                    onClick={() => hasSubContent && toggleStep(step.id)}
                  >
                    <div className="cot-step-left">
                      {/* Step Status Icon Indicator */}
                      <span className={`cot-status-icon ${step.status}`}>
                        {step.status === 'completed' && <IconCheck size={12} />}
                        {step.status === 'active' && <span className="cot-spinner" />}
                        {step.status === 'error' && <span className="cot-error-dot">!</span>}
                        {step.status === 'pending' && <span className="cot-pending-dot" />}
                      </span>

                      {/* Custom Step Icon */}
                      {step.icon && <span className="cot-custom-icon">{step.icon}</span>}

                      {/* Step Title */}
                      <span className="cot-step-title">{step.title}</span>

                      {/* Tool Tag */}
                      {step.toolName && (
                        <span className="cot-tool-tag">{step.toolName}</span>
                      )}
                    </div>

                    {/* Step Right Duration & Expand Toggle */}
                    <div className="cot-step-right">
                      {step.duration && (
                        <span className="cot-step-duration">{step.duration}</span>
                      )}
                      {hasSubContent && (
                        <span className={`cot-step-arrow ${isExpanded ? 'open' : ''}`}>
                          <IconChevronRight size={13} />
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Expanded Sub-Content Details */}
                  {isExpanded && hasSubContent && (
                    <div className="cot-subcontent-box animate-fade-in">
                      {/* Search Queries Pills */}
                      {step.searchQueries && step.searchQueries.length > 0 && (
                        <div className="cot-queries-wrapper">
                          <div className="cot-queries-row">
                            {step.searchQueries.map((query, i) => (
                              <span key={i} className="cot-query-chip">
                                <IconGlobe size={13} className="query-icon" />
                                <span>{query}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Web Sources List */}
                      {step.webSources && step.webSources.length > 0 && (
                        <div className="cot-sources-list">
                          {step.webSources.map((source, i) => (
                            <a
                              key={i}
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="cot-source-card"
                            >
                              <img
                                src={`https://www.google.com/s2/favicons?domain=${source.domain}&sz=128`}
                                alt=""
                                className="source-favicon"
                              />
                              <span className="source-title">{source.title}</span>
                              <span className="source-domain">{source.domain}</span>
                              <IconExternalLink size={12} className="source-link-icon" />
                            </a>
                          ))}
                        </div>
                      )}

                      {/* Data Cards Grid */}
                      {step.dataCards && step.dataCards.length > 0 && (
                        <div className="cot-datacards-grid">
                          {step.dataCards.map((card, i) => (
                            <div key={i} className="cot-data-card">
                              <span className="card-label">{card.label}</span>
                              <span className="card-value">{card.value}</span>
                              {card.subtitle && (
                                <span className="card-sub">{card.subtitle}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Execution Details Bullet List */}
                      {step.details && step.details.length > 0 && (
                        <ul className="cot-details-list">
                          {step.details.map((detail, i) => (
                            <li key={i}>{detail}</li>
                          ))}
                        </ul>
                      )}

                      {/* Error Callout Box */}
                      {step.errorMessage && (
                        <div className="cot-error-box">
                          <span className="error-title">Execution Error</span>
                          <p className="error-text">{step.errorMessage}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Completion Footer Badge */}
          {completedCount === steps.length && (
            <div className="cot-complete-footer">
              <span className="complete-icon">
                <IconCheck size={14} />
              </span>
              <span className="complete-label">{completionLabel}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChainOfThoughtMaster;
