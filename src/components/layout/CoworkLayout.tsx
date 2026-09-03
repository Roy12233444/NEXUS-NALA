import React, { useState, useCallback } from 'react';
import ChatSection from '../features/chat/ChatSection';
import MemoryPanel from '../features/memory/MemoryPanel';
import DashboardContainer from '../features/dashboard/DashboardContainer';
import DotMatrix from '../ui/DotMatrix';
import {
  IconMenu,
  IconMessageSquare,
  IconPlus,
  IconHistory,
  IconFolder,
  IconFiles,
  IconClock,
  IconKeyRound,
  IconRocket,
  IconBrain,
  IconBox,
  IconMonitor,
  IconChevronDown,
  IconTrash,
  IconPanelLeft,
  IconUser,
  IconUsers,
  IconHash,
  IconPin,
  IconArchive,
  IconArrowLeft,
  IconSun,
  IconLogOut,
  IconX,
  IconArrowUp,
} from '../ui/LucideIcons';
import './CoworkLayout.css';


interface CoworkLayoutProps {
  onBackToWebsite?: () => void;
}

export type TopWorkMode = 'chat' | 'work';

interface ProjectScope {
  id: string;
  name: string;
  kind: 'personal' | 'project' | 'group' | 'channel';
}

interface Conversation {
  id: string;
  title: string;          // First message becomes the title
  createdAt: number;
  scopeId: string;
  pinned?: boolean;
  archived?: boolean;
}

const INITIAL_SCOPES: ProjectScope[] = [
  { id: 'scope-personal', name: 'Personal', kind: 'personal' },
  { id: 'scope-nala', name: 'NALA-Project', kind: 'project' },
  { id: 'scope-group-dm', name: 'Group DM (Nexus Founders)', kind: 'group' },
];

interface Pane {
  id: string;
  sessionId: string | null;
  view: 'chats' | 'memory' | 'files' | 'crons' | 'keychain' | 'apps' | 'skills' | 'dashboard';
  widthPercent: number;
}

const SEED_CONVERSATIONS: Conversation[] = [
  { id: 'seed-1', title: 'Replicate & extend key research results from Brown et al. (2024)', createdAt: Date.now() - 3000, scopeId: 'scope-nala', pinned: true },
  { id: 'seed-2', title: 'Behavior Monitor Telemetry Test', createdAt: Date.now() - 2000, scopeId: 'scope-personal' },
  { id: 'seed-3', title: 'Audit PEP 578 Sandbox Hooks', createdAt: Date.now() - 1000, scopeId: 'scope-personal' },
  { id: 'seed-4', title: 'Archived test chat thread', createdAt: Date.now() - 500, scopeId: 'scope-personal', archived: true },
];

const CoworkLayout: React.FC<CoworkLayoutProps> = ({ onBackToWebsite }) => {
  const [activeWorkMode, setActiveWorkMode] = useState<TopWorkMode>('work');
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [activeMission, setActiveMission] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState<boolean>(true);
  const [webOnly, setWebOnly] = useState<boolean>(false);
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('webui:sidebar-w');
      if (saved) {
        const w = parseInt(saved, 10);
        if (w >= 200 && w <= 520) return w;
      }
    } catch (e) {}
    return 250;
  });
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeScopeId, setActiveScopeId] = useState<string>('scope-personal');
  const [collapsedScopes, setCollapsedScopes] = useState<Record<string, boolean>>({});
  const [showArchived, setShowArchived] = useState<boolean>(false);

  // ── Session message persistence ──────────────────────────────────────────
  // Map of sessionId -> Message[] stored in localStorage so switching sessions
  // restores the conversation history.
  const [sessionMessages, setSessionMessages] = useState<Record<string, any[]>>(() => {
    try {
      const raw = localStorage.getItem('nala:session-messages');
      if (raw) return JSON.parse(raw);
    } catch {}
    return {};
  });

  // ── Save messages for a session — uses functional setState to always read
  //    the freshest snapshot and avoid stale-closure data loss.
  const handleSessionMessagesChange = useCallback((sessionId: string, msgs: any[]) => {
    setSessionMessages(prev => {
      const updated = { ...prev, [sessionId]: msgs };
      try {
        // Keep only last 50 sessions to avoid exceeding localStorage quota
        const keys = Object.keys(updated);
        const trimmed: Record<string, any[]> = {};
        keys.slice(-50).forEach(k => { trimmed[k] = updated[k]; });
        localStorage.setItem('nala:session-messages', JSON.stringify(trimmed));
      } catch {}
      return updated;
    });
  }, []);

  const [panes, setPanes] = useState<Pane[]>([
    { id: 'pane-initial', sessionId: 'seed-1', view: 'chats', widthPercent: 100 }
  ]);
  const [focusedPaneId, setFocusedPaneId] = useState<string>('pane-initial');
  const [maximizedPaneId, setMaximizedPaneId] = useState<string | null>(null);

  const [conversations, setConversationsInternal] = useState<Conversation[]>(() => {
    try {
      const raw = localStorage.getItem('nala:conversations');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    return SEED_CONVERSATIONS;
  });

  const setConversations = (updater: Conversation[] | ((prev: Conversation[]) => Conversation[])) => {
    setConversationsInternal(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      try { localStorage.setItem('nala:conversations', JSON.stringify(next)); } catch {}
      return next;
    });
  };

  const setFocusedPaneView = useCallback((view: Pane['view'], sessionId: string | null = null) => {
    setPanes(prev => prev.map(p => p.id === focusedPaneId ? { ...p, view, sessionId: sessionId !== null ? sessionId : p.sessionId } : p));
  }, [focusedPaneId]);

  const splitPane = (paneId: string) => {
    if (panes.length >= 3) return; // limit to 3 panes side-by-side
    const newId = `pane-${Date.now()}`;
    setPanes(prev => {
      const idx = prev.findIndex(p => p.id === paneId);
      if (idx === -1) return prev;
      const current = prev[idx];
      const newWidth = current.widthPercent / 2;
      const newPane: Pane = {
        id: newId,
        sessionId: null,
        view: current.view,
        widthPercent: newWidth
      };
      const updated = [...prev];
      updated[idx] = { ...current, widthPercent: newWidth };
      updated.splice(idx + 1, 0, newPane);
      return updated;
    });
    setFocusedPaneId(newId);
  };

  const closePane = (paneId: string) => {
    if (panes.length <= 1) return;
    setPanes(prev => {
      const idx = prev.findIndex(p => p.id === paneId);
      if (idx === -1) return prev;
      const closed = prev[idx];
      const updated = prev.filter(p => p.id !== paneId);
      const targetIdx = idx === 0 ? 0 : idx - 1;
      if (updated[targetIdx]) {
        updated[targetIdx].widthPercent += closed.widthPercent;
      }
      return updated;
    });
    if (focusedPaneId === paneId) {
      const remaining = panes.filter(p => p.id !== paneId);
      if (remaining.length > 0) setFocusedPaneId(remaining[remaining.length - 1].id);
    }
    if (maximizedPaneId === paneId) setMaximizedPaneId(null);
  };

  const toggleMaximizePane = (paneId: string) => {
    setMaximizedPaneId(prev => prev === paneId ? null : paneId);
  };

  // Start a brand new conversation thread
  const startNewConversation = useCallback((scopeId: string = 'scope-personal') => {
    const newId = `conv-${Date.now()}`;
    setActiveConversationId(newId);
    setActiveMission(null);
    setActiveScopeId(scopeId);
    setCollapsedScopes(prev => ({ ...prev, [scopeId]: false }));
    setPanes(prev => prev.map(p => p.id === focusedPaneId ? { ...p, view: 'chats', sessionId: newId } : p));
  }, [focusedPaneId]);

  // Called when the user sends the FIRST message in the active thread
  const handleSendMessageInPane = useCallback((paneId: string, msg: string) => {
    if (!msg) return;
    const pane = panes.find(p => p.id === paneId);
    if (!pane) return;
    const currentSessionId = pane.sessionId;

    setConversations(prev => {
      if (currentSessionId && prev.some(c => c.id === currentSessionId)) {
        return prev;
      }
      const id = currentSessionId || `conv-${Date.now()}`;
      setPanes(oldPanes => oldPanes.map(p => p.id === paneId ? { ...p, sessionId: id } : p));
      return [{ id, title: msg, createdAt: Date.now(), scopeId: activeScopeId }, ...prev];
    });
  }, [panes, activeScopeId]);

  const handleDeleteConversation = (convId: string) => {
    setConversations(prev => prev.filter(c => c.id !== convId));
    setPanes(prev => prev.map(p => p.sessionId === convId ? { ...p, sessionId: null } : p));
    if (activeConversationId === convId) {
      setActiveConversationId(null);
      setActiveMission(null);
    }
  };

  const getScopeIcon = (kind: ProjectScope['kind']) => {
    switch (kind) {
      case 'personal': return IconUser;
      case 'group': return IconUsers;
      case 'channel': return IconHash;
      case 'project':
      default:
        return IconFolder;
    }
  };

  const renderSessionRow = (conv: Conversation) => {
    const focusedPane = panes.find(p => p.id === focusedPaneId);
    const isActive = focusedPane?.view === 'chats' && focusedPane?.sessionId === conv.id;
    const displayTitle = conv.title.length > 24 ? conv.title.substring(0, 22) + '...' : conv.title;
    return (
      <div
        key={conv.id}
        className={`history-item ${isActive ? 'active' : ''}`}
        onClick={() => {
          setActiveConversationId(conv.id);
          setFocusedPaneView('chats', conv.id);
        }}
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, minWidth: 0 }}>
          <span className="session-dot" />
          <span className="session-title-label">{displayTitle}</span>
        </div>
        <button
          className="btn-delete-history"
          title="Delete conversation"
          onClick={(e) => {
            e.stopPropagation();
            handleDeleteConversation(conv.id);
          }}
        >
          <IconTrash size={12} />
        </button>
      </div>
    );
  };

  const handlePaneResize = (e: React.PointerEvent, index: number) => {
    e.preventDefault();
    const handle = e.currentTarget as HTMLElement;
    const startX = e.clientX;
    const leftPane = panes[index];
    const rightPane = panes[index + 1];
    if (!leftPane || !rightPane) return;
    const startLeftW = leftPane.widthPercent;
    const startRightW = rightPane.widthPercent;

    const coworkBody = handle.closest('.cowork-body');
    if (!coworkBody) return;
    const totalW = coworkBody.getBoundingClientRect().width;

    handle.setPointerCapture(e.pointerId);
    document.body.classList.add("resizing-pane");

    const onMove = (ev: PointerEvent) => {
      const diffX = ev.clientX - startX;
      const diffPercent = (diffX / totalW) * 100;

      const nextLeftW = Math.max(15, Math.min(85, startLeftW + diffPercent));
      const nextRightW = Math.max(15, Math.min(85, startRightW - (nextLeftW - startLeftW)));

      setPanes(prev => {
        const updated = [...prev];
        updated[index] = { ...updated[index], widthPercent: nextLeftW };
        updated[index + 1] = { ...updated[index + 1], widthPercent: nextRightW };
        return updated;
      });
    };

    const onUp = () => {
      handle.removeEventListener("pointermove", onMove as any);
      handle.removeEventListener("pointerup", onUp as any);
      handle.removeEventListener("lostpointercapture", onUp as any);
      document.body.classList.remove("resizing-pane");
    };

    handle.addEventListener("pointermove", onMove as any);
    handle.addEventListener("pointerup", onUp as any);
    handle.addEventListener("lostpointercapture", onUp as any);
  };

  return (
    <div className="cowork-container">
      {/* Top Floating Workspace Bar */}
      <header className="cowork-topbar">
        <div className="topbar-left">
          <div className="cowork-brand" onClick={onBackToWebsite} title="Return to Website">
            <span className="brand-name">NALA</span>
            <span className="brand-dot"></span>
          </div>
        </div>

        <div className="topbar-right">
        </div>
      </header>

      {/* Main Workspace Area with Collapsible Left Sidebar */}
      <div className={`cowork-body ${sidebarOpen ? '' : 'sidebar-closed'}`}>
        {/* Left Sidebar Context & History */}
        <aside className="cowork-sidebar" style={{ width: sidebarWidth }}>
          {/* Brand Row (qm-main pattern) */}
          <div className="brand">
            <div className="brand-lockup">
              <span className="brand-mark">N</span>
              <span className="brand-name">NALA</span>
            </div>
            <button
              className="sidebar-collapse-toggle icon-btn subtle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            >
              <IconPanelLeft size={17} />
            </button>
          </div>

          {/* New Session Button */}
          <button className="new-chat" onClick={startNewConversation}>
            <IconPlus size={17} />
            <span>New session</span>
          </button>

            {/* ── Browse nav group (qm-main pattern) ── */}
            <nav className="sidebar-nav">
              {/* Collapsible "Browse" group header */}
              <button
                className={`nav-section-toggle`}
                type="button"
                aria-expanded={browseOpen ? 'true' : 'false'}
                aria-controls="nav-browse"
                onClick={() => setBrowseOpen(o => !o)}
              >
                <span>Browse</span>
                <span className="nav-section-chevron">
                  <IconChevronDown size={14} />
                </span>
              </button>

              <div id="nav-browse" className={`nav-group ${browseOpen ? '' : 'collapsed'}`}>
                <div className="nav-group-inner">

                  {/* Chats */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'chats' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('chats')}
                  >
                    <IconMessageSquare size={17} />
                    <span>Chats</span>
                  </button>

                  {/* Dashboard */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'dashboard' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('dashboard')}
                  >
                    <IconMonitor size={17} />
                    <span>Dashboard</span>
                  </button>

                  {/* Projects */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'chats' && false ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('chats')}
                  >
                    <IconFolder size={17} />
                    <span>Projects</span>
                  </button>

                  {/* Files */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'files' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('files')}
                  >
                    <IconFiles size={17} />
                    <span>Files</span>
                  </button>

                  {/* Crons */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'crons' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('crons')}
                  >
                    <IconClock size={17} />
                    <span>Crons</span>
                  </button>

                  {/* Keychain */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'keychain' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('keychain')}
                  >
                    <IconKeyRound size={17} />
                    <span>Keychain</span>
                  </button>

                  {/* Apps */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'apps' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('apps')}
                  >
                    <IconRocket size={17} />
                    <span>Apps</span>
                  </button>

                  {/* Memory */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'memory' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('memory')}
                  >
                    <IconBrain size={17} />
                    <span>Memory</span>
                  </button>

                  {/* Skills */}
                  <button
                    className={`navrow ${panes.find(p => p.id === focusedPaneId)?.view === 'skills' ? 'active' : ''}`}
                    type="button"
                    onClick={() => setFocusedPaneView('skills')}
                  >
                    <IconBox size={17} />
                    <span>Skills</span>
                  </button>

                </div>
              </div>
            </nav>

            {/* Recent Conversation Threads — shown only when Chats is active */}
            {panes.find(p => p.id === focusedPaneId)?.view === 'chats' && (() => {
              const filtered = conversations.filter(
                conv => !webOnly || conv.id.startsWith('conv-') || conv.id.startsWith('seed-')
              );
              const pinned = filtered.filter(c => c.pinned && !c.archived);
              const activeUnpinned = filtered.filter(c => !c.pinned && !c.archived);
              const archived = filtered.filter(c => c.archived);

              return (
                <div className="sidebar-section sidebar-recents" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {/* Sessions Header Row with Web Only Toggle */}
                  <div className="sidebar-recents-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: '8px' }}>
                    <span className="sidebar-recents-label">Sessions</span>
                    <button
                      className={`web-only-toggle ${webOnly ? 'on' : ''}`}
                      type="button"
                      role="switch"
                      aria-checked={webOnly ? 'true' : 'false'}
                      onClick={() => setWebOnly(!webOnly)}
                    >
                      <span>Web only</span>
                      <span className="mini-switch">
                        <span className="mini-knob"></span>
                      </span>
                    </button>
                  </div>

                  <div className="sidebar-recents-scroll" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {/* 1. Pinned Group */}
                    {pinned.length > 0 && (
                      <div className="recents-group-section">
                        <div className="recents-group-head" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', padding: '4px 8px' }}>
                          <IconPin size={11} />
                          <span>Pinned</span>
                        </div>
                        <div className="recents-group-children" style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                          {pinned.map(conv => renderSessionRow(conv))}
                        </div>
                      </div>
                    )}

                    {/* 2. Grouped Active Project Scopes */}
                    {INITIAL_SCOPES.map(scope => {
                      const scopeSessions = activeUnpinned.filter(s => s.scopeId === scope.id);
                      const isCollapsed = collapsedScopes[scope.id];
                      const Icon = getScopeIcon(scope.kind);

                      if (scopeSessions.length === 0) return null;

                      const focusedPane = panes.find(p => p.id === focusedPaneId);
                      const currentSessionId = focusedPane?.sessionId;

                      return (
                        <section key={scope.id} className={`recent-project ${scopeSessions.some(s => s.id === currentSessionId) ? 'active' : ''}`} style={{ margin: '2px 4px 4px' }}>
                          <div className="recent-project-head" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 6px', borderRadius: '6px', background: 'transparent', transition: 'background 0.12s ease' }}>
                            <button
                              className="recent-project-toggle"
                              type="button"
                              onClick={() => setCollapsedScopes(prev => ({ ...prev, [scope.id]: !isCollapsed }))}
                              style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'transparent', border: 'none', cursor: 'pointer', font: 'inherit', fontSize: '13px', fontWeight: 600, color: '#1E293B', padding: 0, flex: 1, textAlign: 'left' }}
                            >
                              <IconChevronDown
                                size={12}
                                className={`dropdown-chevron ${isCollapsed ? 'collapsed' : 'open'}`}
                                style={{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.15s ease', color: '#94A3B8' }}
                              />
                              <Icon size={14} style={{ color: '#475569' }} />
                              <span className="recent-project-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{scope.name}</span>
                            </button>
                            
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span className="recent-project-count" style={{ fontSize: '10px', fontWeight: 700, color: '#64748B', background: '#F1F5F9', padding: '1px 5px', borderRadius: '10px' }}>{scopeSessions.length}</span>
                              <button
                                className="recent-project-new-chat"
                                type="button"
                                title={`New chat in ${scope.name}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  startNewConversation(scope.id);
                                }}
                                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px', background: 'transparent', border: 'none', color: '#94A3B8', cursor: 'pointer', borderRadius: '4px', transition: 'all 0.12s ease' }}
                              >
                                <IconPlus size={13} />
                              </button>
                            </div>
                          </div>

                          {!isCollapsed && (
                            <div className="recent-project-children" style={{ display: 'flex', flexDirection: 'column', gap: '1px', paddingLeft: '14px', borderLeft: '1px solid #E2E8F0', marginLeft: '12px', marginTop: '2px' }}>
                              {scopeSessions.map(conv => renderSessionRow(conv))}
                            </div>
                          )}
                        </section>
                      );
                    })}

                    {/* 3. Archived Group */}
                    {archived.length > 0 && (
                      <div className="recents-group-section" style={{ marginTop: '8px', borderTop: '1px solid #F1F5F9', paddingTop: '8px' }}>
                        <button
                          className={`archived-toggle ${showArchived ? 'open' : ''}`}
                          onClick={() => setShowArchived(!showArchived)}
                          style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px 8px', borderRadius: '6px', font: 'inherit', fontSize: '12px', fontWeight: 600, color: '#64748B', textAlign: 'left' }}
                        >
                          <IconChevronDown
                            size={12}
                            style={{ transform: showArchived ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.15s ease', color: '#94A3B8' }}
                          />
                          <IconArchive size={14} />
                          <span>Archived</span>
                          <span className="archived-count" style={{ marginLeft: 'auto', fontSize: '10px', fontWeight: 700, color: '#64748B', background: '#F1F5F9', padding: '1px 5px', borderRadius: '10px' }}>{archived.length}</span>
                        </button>
                        {showArchived && (
                          <div className="recents-group-children" style={{ display: 'flex', flexDirection: 'column', gap: '1px', marginTop: '2px' }}>
                            {archived.map(conv => renderSessionRow(conv))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* User Account Footer (qm-main pattern) */}
            <div className="sidebar-user-footer" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 4px 4px', borderTop: '1px solid #F1F5F9', marginTop: 'auto', gap: '8px' }}>
              <div className="user-pill" style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                <span className="user-avatar" style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#E8791A', color: '#FFFFFF', fontSize: '11px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>SR</span>
                <span className="user-email" style={{ fontSize: '11px', fontWeight: 600, color: '#475569', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title="sourav@nexuslab.ai">sourav@nexuslab...</span>
              </div>
              <div className="user-toolbar" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <a className="icon-btn subtle" href="#" title="Back to admin" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '26px', height: '26px', borderRadius: '6px', color: '#64748B', transition: 'all 0.12s ease', cursor: 'pointer' }}>
                  <IconArrowLeft size={16} />
                </a>
                <button className="icon-btn subtle" title="Toggle Theme" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '26px', height: '26px', borderRadius: '6px', color: '#64748B', background: 'transparent', border: 'none', transition: 'all 0.12s ease', cursor: 'pointer' }}>
                  <IconSun size={16} />
                </button>
                <button className="icon-btn subtle" title="Sign out" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '26px', height: '26px', borderRadius: '6px', color: '#64748B', background: 'transparent', border: 'none', transition: 'all 0.12s ease', cursor: 'pointer' }}>
                  <IconLogOut size={16} />
                </button>
              </div>
            </div>
          </aside>

        {sidebarOpen && (
          <div
            className="sidebar-resize-handle"
            title="Drag to resize · double-click to reset"
            onPointerDown={(e) => {
              e.preventDefault();
              const handle = e.currentTarget;
              const startX = e.clientX;
              const startW = sidebarWidth;
              handle.setPointerCapture(e.pointerId);
              document.body.classList.add("resizing-sidebar");

              const onMove = (ev: PointerEvent) => {
                const nextW = Math.min(520, Math.max(200, startW + (ev.clientX - startX)));
                setSidebarWidth(nextW);
              };

              const onUp = () => {
                handle.removeEventListener("pointermove", onMove as any);
                handle.removeEventListener("pointerup", onUp as any);
                handle.removeEventListener("lostpointercapture", onUp as any);
                document.body.classList.remove("resizing-sidebar");
                try {
                  localStorage.setItem('webui:sidebar-w', String(sidebarWidth));
                } catch (err) {}
              };

              handle.addEventListener("pointermove", onMove as any);
              handle.addEventListener("pointerup", onUp as any);
              handle.addEventListener("lostpointercapture", onUp as any);
            }}
            onDoubleClick={() => {
              setSidebarWidth(250);
              try {
                localStorage.removeItem('webui:sidebar-w');
              } catch (err) {}
            }}
          />
        )}

        {/* Main Control Center & Directive Stream (Split Pane Layout) */}
        <div className="workspace-panes-container" style={{ display: 'flex', flex: 1, gap: maximizedPaneId ? 0 : '8px', height: '100%', overflow: 'hidden', alignSelf: 'stretch', position: 'relative', padding: '12px' }}>
          {panes.map((pane, idx) => {
            const isMaximized = maximizedPaneId === pane.id;
            const isHidden = maximizedPaneId !== null && !isMaximized;
            if (isHidden) return null;

            const isFocused = focusedPaneId === pane.id;
            const paneStyle: React.CSSProperties = {
              width: maximizedPaneId ? '100%' : `${pane.widthPercent}%`,
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
              minWidth: maximizedPaneId ? '100%' : '15%',
              border: isFocused ? '1px solid #4F46E5' : '1px solid rgba(17, 24, 39, 0.08)',
              borderRadius: '12px',
              overflow: 'hidden',
              boxShadow: isFocused ? '0 0 0 2px rgba(79, 70, 229, 0.15), 0 4px 12px rgba(0, 0, 0, 0.03)' : '0 2px 8px rgba(0, 0, 0, 0.02)',
              background: '#FFFFFF',
              position: 'relative',
              transition: 'border-color 0.12s ease, box-shadow 0.12s ease'
            };

            return (
              <React.Fragment key={pane.id}>
                <div
                  className={`workspace-pane ${isFocused ? 'focused' : ''}`}
                  style={paneStyle}
                  onClickCapture={() => setFocusedPaneId(pane.id)}
                >
                  {/* Pane Title Bar / Header */}
                  <div className="pane-header-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: '#F8FAFC', borderBottom: '1px solid #E2E8F0', userSelect: 'none' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="pane-status-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: pane.sessionId ? '#3B82F6' : '#94A3B8' }} />
                      <span className="pane-title" style={{ fontSize: '13px', fontWeight: 700, color: '#1E293B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }}>
                        {pane.sessionId 
                          ? (conversations.find(c => c.id === pane.sessionId)?.title ?? 'Session')
                          : `Empty Pane (${pane.view.charAt(0).toUpperCase() + pane.view.slice(1)})`}
                      </span>
                    </div>

                    <div className="pane-controls" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {/* Split pane button */}
                      <button
                        className="pane-btn"
                        onClick={(e) => { e.stopPropagation(); splitPane(pane.id); }}
                        title="Split pane side-by-side"
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#64748B', borderRadius: '4px' }}
                      >
                        <IconPlus size={14} />
                      </button>

                      {/* Maximize / Contract button */}
                      <button
                        className="pane-btn"
                        onClick={(e) => { e.stopPropagation(); toggleMaximizePane(pane.id); }}
                        title={isMaximized ? "Restore pane size" : "Maximize pane"}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#64748B', borderRadius: '4px' }}
                      >
                        {isMaximized ? <IconChevronDown size={14} /> : <IconArrowUp size={14} style={{ transform: 'rotate(45deg)' }} />}
                      </button>

                      {/* Close button */}
                      {panes.length > 1 && (
                        <button
                          className="pane-btn close"
                          onClick={(e) => { e.stopPropagation(); closePane(pane.id); }}
                          title="Close pane"
                          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', height: '22px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#64748B', borderRadius: '4px' }}
                        >
                          <IconX size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Pane Content View */}
                  <div className="pane-content-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    {pane.view === 'dashboard' ? (
                      <DashboardContainer />
                    ) : pane.view === 'memory' ? (
                      <MemoryPanel />
                    ) : (
                      <ChatSection
                        activeMission={pane.sessionId ? (conversations.find(c => c.id === pane.sessionId)?.title ?? null) : null}
                        onSendMessage={(msg) => handleSendMessageInPane(pane.id, msg)}
                        activeWorkMode={activeWorkMode}
                        onWorkModeChange={(mode) => setActiveWorkMode(mode)}
                        sessionId={pane.sessionId}
                        initialMessages={pane.sessionId ? (sessionMessages[pane.sessionId] ?? []) : []}
                        onMessagesChange={(msgs) => pane.sessionId && handleSessionMessagesChange(pane.sessionId, msgs)}
                      />
                    )}
                  </div>
                </div>

                {/* Resizer Rail between panes */}
                {!isMaximized && idx < panes.length - 1 && (
                  <div
                    className="pane-resize-handle"
                    onPointerDown={(e) => handlePaneResize(e, idx)}
                    style={{ width: '6px', cursor: 'col-resize', display: 'flex', alignSelf: 'stretch', zIndex: 10, position: 'relative' }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CoworkLayout;
