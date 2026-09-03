import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import './MemoryPanel.css';

interface MemoryFact {
  line: number;
  text: string;
  date?: string;
}

interface MemoryState {
  content: string;
  revision: string;
  facts: MemoryFact[];
  loaded: boolean;
  saving: boolean;
  notice: string;
  error: string;
  rawEditing: boolean;
  search: string;
  addInput: string;
}

const SOCKET_URL = 'http://localhost:3001';

const MemoryPanel: React.FC = () => {
  const socketRef = useRef<Socket | null>(null);
  const [state, setState] = useState<MemoryState>({
    content: '',
    revision: '',
    facts: [],
    loaded: false,
    saving: false,
    notice: '',
    error: '',
    rawEditing: false,
    search: '',
    addInput: '',
  });

  // Connect to NALA backend and load memory on mount
  useEffect(() => {
    const socket = io(SOCKET_URL, { transports: ['websocket', 'polling'] });
    socketRef.current = socket;

    socket.on('connect', () => {
      socket.emit('get_memory', {});
    });

    socket.on('memory_data', (data: any) => {
      setState(prev => ({
        ...prev,
        content: data.content ?? '',
        revision: data.revision ?? '',
        facts: data.facts ?? [],
        loaded: true,
        error: data.error ?? '',
        notice: '',
      }));
    });

    socket.on('memory_saved', (data: any) => {
      if (data.ok) {
        setState(prev => ({
          ...prev,
          content: data.content ?? prev.content,
          revision: data.revision ?? prev.revision,
          facts: data.facts ?? prev.facts,
          saving: false,
          notice: 'Saved ✓',
          error: '',
        }));
      } else {
        setState(prev => ({
          ...prev,
          saving: false,
          error: data.conflict
            ? 'Memory changed elsewhere. Copy your edits and refresh.'
            : (data.error ?? 'Save failed.'),
          notice: '',
        }));
      }
    });

    socket.on('memory_updated', (data: any) => {
      if (data.ok) {
        setState(prev => ({
          ...prev,
          content: data.content ?? prev.content,
          revision: data.revision ?? prev.revision,
          facts: data.facts ?? prev.facts,
          notice: '',
          error: '',
        }));
      } else {
        setState(prev => ({ ...prev, error: data.error ?? 'Operation failed.' }));
      }
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const refresh = useCallback(() => {
    setState(prev => ({ ...prev, loaded: false, notice: '', error: '' }));
    socketRef.current?.emit('get_memory', {});
  }, []);

  const saveRaw = useCallback(() => {
    if (state.saving) return;
    setState(prev => ({ ...prev, saving: true, notice: '', error: '' }));
    socketRef.current?.emit('save_memory', {
      content: state.content,
      revision: state.revision,
    });
  }, [state.content, state.revision, state.saving]);

  const deleteFact = useCallback((lineIndex: number) => {
    socketRef.current?.emit('delete_memory_fact', { line: lineIndex });
  }, []);

  const addFact = useCallback(() => {
    const fact = state.addInput.trim();
    if (!fact) return;
    socketRef.current?.emit('add_memory_fact', { fact });
    setState(prev => ({ ...prev, addInput: '' }));
  }, [state.addInput]);

  const visibleFacts = state.facts.filter(f =>
    !state.search || f.text.toLowerCase().includes(state.search.toLowerCase())
  );

  const isDirty = state.loaded && state.content !== state.content;

  return (
    <div className="memory-panel">
      {/* Header — from qm-main pane-head pattern */}
      <div className="memory-panel-head">
        <div>
          <h2 className="memory-panel-title">Memory</h2>
          <p className="memory-panel-subtitle">Facts NALA carries into your conversations.</p>
        </div>
        <div className="memory-panel-actions">
          <button
            className={`memory-tab-btn ${!state.rawEditing ? 'active' : ''}`}
            onClick={() => setState(prev => ({ ...prev, rawEditing: false }))}
            title="View & search individual facts"
          >
            Facts view
          </button>
          <button
            className={`memory-tab-btn ${state.rawEditing ? 'active' : ''}`}
            onClick={() => setState(prev => ({ ...prev, rawEditing: true }))}
            title="Edit raw notebook"
          >
            ✏️ Edit notebook
          </button>
          <button
            className="memory-refresh-btn"
            onClick={refresh}
            title="Refresh memory"
            aria-label="Refresh memory"
          >
            ↻
          </button>
        </div>
      </div>

      {/* Status notice */}
      {(state.notice || state.error || !state.loaded) && (
        <div className={`memory-status ${state.error ? 'error' : ''}`}>
          {!state.loaded && !state.error ? 'Loading…' : state.error || state.notice}
        </div>
      )}

      <div className="memory-editor-area">
        {state.rawEditing ? (
          /* Raw notebook editor — qm-main memory-text pattern */
          <>
            <p className="memory-help-text">
              Edit the notebook directly. Switch to Facts view to search or remove individual facts.
            </p>
            <textarea
              className="memory-raw-textarea"
              spellCheck={false}
              disabled={state.saving || !state.loaded}
              value={state.content}
              onChange={e => setState(prev => ({ ...prev, content: e.target.value }))}
              placeholder="# Memory&#10;&#10;- Your first memory fact goes here..."
            />
            <div className="memory-save-bar">
              <button
                className="memory-save-btn"
                disabled={state.saving || !state.loaded}
                onClick={saveRaw}
              >
                {state.saving ? 'Saving…' : 'Save changes'}
              </button>
              {isDirty && !state.saving && (
                <span className="memory-unsaved-hint">Unsaved changes</span>
              )}
            </div>
          </>
        ) : (
          /* Facts view — qm-main memory-facts pattern */
          <>
            {/* Search bar */}
            <div className="memory-search-bar">
              <span className="memory-search-icon">🔍</span>
              <input
                type="search"
                className="memory-search-input"
                placeholder="Search remembered facts…"
                value={state.search}
                onChange={e => setState(prev => ({ ...prev, search: e.target.value }))}
                aria-label="Search memory"
              />
            </div>

            {/* Facts list */}
            <div className="memory-facts-list">
              {!state.loaded ? (
                <div className="memory-empty-state">Loading facts…</div>
              ) : visibleFacts.length === 0 ? (
                <div className="memory-empty-state">
                  {state.search
                    ? 'No remembered facts match this search.'
                    : "NALA hasn't noted any facts yet. Add one below!"}
                </div>
              ) : (
                visibleFacts.map(fact => (
                  <div key={fact.line} className="memory-fact-card">
                    <div className="memory-fact-body">
                      <span className="memory-fact-text">{fact.text}</span>
                      {fact.date && (
                        <span className="memory-fact-date">Captured {fact.date}</span>
                      )}
                    </div>
                    <button
                      className="memory-forget-btn"
                      title="Forget this fact"
                      aria-label="Forget this fact"
                      onClick={() => deleteFact(fact.line)}
                    >
                      🗑
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Add fact bar */}
            <div className="memory-add-bar">
              <input
                type="text"
                className="memory-add-input"
                placeholder="Add a new fact…"
                value={state.addInput}
                onChange={e => setState(prev => ({ ...prev, addInput: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter') addFact(); }}
              />
              <button
                className="memory-add-btn"
                onClick={addFact}
                disabled={!state.addInput.trim()}
              >
                + Add
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MemoryPanel;
