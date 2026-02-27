// ============================================================
//  GlobalSearch — Cmd+K style search overlay
//  Searches across: Nodes/Bricks, Navigation shortcuts, Actions.
//  Wired to: /jarvis/graph-index (client-side filter, no extra fetch)
//
//  P1 Enhancement: Added 'action' result kind for:
//    - Trigger Sync   → POST /api/sync/trigger
//    - Refresh Metrics → POST /api/evolution/refresh-metrics
//    - Force L3 Run   → POST /api/cognition/l3/trigger
// ============================================================

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Network, Activity, Hash, ChevronRight, Zap } from 'lucide-react';
import { useNexusStore, type AppMode } from '../store';
import { useGraphStore } from '../state/graph-store';

// ─── Types ────────────────────────────────────────────────────
type ResultKind = 'node' | 'event' | 'nav' | 'action';

interface SearchResult {
  id: string;
  kind: ResultKind;
  title: string;
  subtitle: string;
  lifecycle?: string;
  navTarget?: AppMode;
  actionFn?: () => Promise<void>;
}

// ─── Static nav shortcuts ─────────────────────────────────────
const NAV_SHORTCUTS: SearchResult[] = [
  { id: 'nav-overview',   kind: 'nav', title: 'Cognitive Wall',   subtitle: 'Overview dashboard',         navTarget: 'overview'   },
  { id: 'nav-graph',      kind: 'nav', title: 'Graph Map',        subtitle: 'ReactFlow graph explorer',   navTarget: 'graph'      },
  { id: 'nav-cognition',  kind: 'nav', title: 'Intent Focus',     subtitle: 'Cytoscape cortex view',      navTarget: 'cognition'  },
  { id: 'nav-audit',      kind: 'nav', title: 'Audit Stream',     subtitle: 'Live event log',             navTarget: 'audit'      },
  { id: 'nav-governance', kind: 'nav', title: 'Governance Center',subtitle: 'Rules & prompts',            navTarget: 'governance' },
  { id: 'nav-health',     kind: 'nav', title: 'Ops Center',       subtitle: 'System health',              navTarget: 'health'     },
  { id: 'nav-recall',     kind: 'nav', title: 'Recall / Chat',    subtitle: 'Ask the knowledge engine',  navTarget: 'recall'     },
];

// ─── Action commands (POST to Cortex API) ────────────────────
const ACTION_COMMANDS: SearchResult[] = [
  {
    id: 'action-sync',
    kind: 'action',
    title: 'Trigger Sync',
    subtitle: 'POST /api/sync/trigger — start a full ingest cycle',
    actionFn: async () => {
      const res = await fetch('/api/sync/trigger', { method: 'POST' });
      if (!res.ok) throw new Error(`Sync trigger failed: ${res.status}`);
      console.info('[GlobalSearch] Sync triggered');
    },
  },
  {
    id: 'action-refresh-metrics',
    kind: 'action',
    title: 'Refresh Metrics',
    subtitle: 'POST /api/evolution/refresh-metrics — rebuild materialized views',
    actionFn: async () => {
      const res = await fetch('/api/evolution/refresh-metrics', { method: 'POST' });
      if (!res.ok) throw new Error(`Metrics refresh failed: ${res.status}`);
      console.info('[GlobalSearch] Metrics refreshed');
    },
  },
  {
    id: 'action-l3-trigger',
    kind: 'action',
    title: 'Force L3 Sage Run',
    subtitle: 'POST /api/cognition/l3/trigger — enqueue an L3 synthesis task',
    actionFn: async () => {
      const res = await fetch('/api/cognition/l3/trigger', { method: 'POST' });
      if (!res.ok) throw new Error(`L3 trigger failed: ${res.status}`);
      console.info('[GlobalSearch] L3 Sage run triggered');
    },
  },
];

// ─── Lifecycle colours ────────────────────────────────────────
const LC_COLOR: Record<string, string> = {
  FROZEN:     '#fbbf24',
  FORMING:    '#22d3ee',
  LOOSE:      '#475569',
  KILLED:     '#f87171',
  SUPERSEDED: '#a78bfa',
};

// ─── Result Row ───────────────────────────────────────────────
function ResultRow({
  result,
  isActive,
  onClick,
  isPending,
}: {
  result: SearchResult;
  isActive: boolean;
  onClick: () => void;
  isPending?: boolean;
}) {
  const KindIcon =
    result.kind === 'node'   ? Network   :
    result.kind === 'event'  ? Activity  :
    result.kind === 'action' ? Zap       : Hash;

  const accentColor =
    result.kind === 'action' ? '#a78bfa' : '#22d3ee';

  const lcColor = result.lifecycle ? (LC_COLOR[result.lifecycle] ?? '#475569') : accentColor;

  return (
    <div
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-all"
      style={{
        background: isActive ? `${accentColor}12` : 'transparent',
        borderLeft: `2px solid ${isActive ? accentColor : 'transparent'}`,
        opacity: isPending ? 0.6 : 1,
      }}
    >
      <div
        className="w-7 h-7 flex items-center justify-center rounded-md shrink-0"
        style={{
          background: isActive ? `${accentColor}18` : 'rgba(255,255,255,0.04)',
          border: `1px solid ${isActive ? `${accentColor}40` : 'rgba(255,255,255,0.06)'}`,
        }}
      >
        <KindIcon style={{ width: 12, height: 12, color: isActive ? accentColor : 'rgba(255,255,255,0.3)' }} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className="text-[11px] font-bold truncate"
            style={{ color: isActive ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.65)' }}
          >
            {isPending ? '⟳ Running…' : result.title}
          </span>
          {result.lifecycle && (
            <span
              className="text-[7px] font-black px-1 rounded shrink-0"
              style={{ color: lcColor, background: `${lcColor}18`, letterSpacing: '0.1em' }}
            >
              {result.lifecycle}
            </span>
          )}
          {result.kind === 'action' && (
            <span
              className="text-[7px] font-black px-1 rounded shrink-0"
              style={{ color: '#a78bfa', background: 'rgba(167,139,250,0.12)', letterSpacing: '0.1em' }}
            >
              ACTION
            </span>
          )}
        </div>
        <div className="text-[9px] truncate" style={{ color: 'rgba(255,255,255,0.3)' }}>
          {result.subtitle}
        </div>
      </div>

      <ChevronRight
        style={{ width: 10, height: 10, color: isActive ? accentColor : 'rgba(255,255,255,0.1)', flexShrink: 0 }}
      />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────
export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const [pendingActionId, setPendingActionId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { setMode, setSelectedBrickId, toggleRightPanel } = useNexusStore();

  // Pull nodes from graph store (already hydrated)
  const nodeMap = useGraphStore(s => s.nodes);

  // ── Keyboard shortcut: Ctrl+K / Cmd+K ──────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Auto-focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setActiveIdx(0);
      setActionError(null);
    }
  }, [open]);

  // ── Build results ─────────────────────────────────────────
  const results = useMemo<SearchResult[]>(() => {
    const q = query.trim().toLowerCase();

    if (!q) return [...NAV_SHORTCUTS, ...ACTION_COMMANDS];

    const nodeResults: SearchResult[] = Object.values(nodeMap)
      .filter(n => {
        const title   = (n.statement ?? (n as any).label ?? n.node_id ?? '').toLowerCase();
        const summary = ((n as any).summary ?? '').toLowerCase();
        return title.includes(q) || summary.includes(q);
      })
      .slice(0, 8)
      .map(n => ({
        id: n.node_id,
        kind: 'node' as const,
        title: (n.statement ?? (n as any).label ?? n.node_id).slice(0, 60),
        subtitle: ((n as any).summary ?? 'No summary').slice(0, 80),
        lifecycle: (n.lifecycle ?? 'LOOSE').toUpperCase(),
      }));

    const navResults = NAV_SHORTCUTS.filter(s =>
      s.title.toLowerCase().includes(q) || s.subtitle.toLowerCase().includes(q)
    );

    const actionResults = ACTION_COMMANDS.filter(a =>
      a.title.toLowerCase().includes(q) || a.subtitle.toLowerCase().includes(q)
    );

    return [...nodeResults, ...navResults, ...actionResults];
  }, [query, nodeMap]);

  // ── Keyboard navigation ───────────────────────────────────
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, results.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter')     { e.preventDefault(); handleSelect(results[activeIdx]); }
  }, [results, activeIdx]);

  const handleSelect = useCallback(async (result: SearchResult) => {
    if (result.kind === 'nav' && result.navTarget) {
      setMode(result.navTarget);
      setOpen(false);
    } else if (result.kind === 'node') {
      setMode('graph');
      setSelectedBrickId(result.id);
      toggleRightPanel(true);
      setOpen(false);
    } else if (result.kind === 'action' && result.actionFn) {
      setPendingActionId(result.id);
      setActionError(null);
      try {
        await result.actionFn();
        setOpen(false);
      } catch (err: any) {
        setActionError(err?.message ?? 'Action failed');
      } finally {
        setPendingActionId(null);
      }
    }
  }, [setMode, setSelectedBrickId, toggleRightPanel]);

  // Section helpers
  const firstNodeIdx   = results.findIndex(r => r.kind === 'node');
  const firstNavIdx    = results.findIndex(r => r.kind === 'nav');
  const firstActionIdx = results.findIndex(r => r.kind === 'action');

  return (
    <>
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-50"
              style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.97 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className="fixed top-[15%] left-1/2 -translate-x-1/2 z-50 w-full max-w-xl rounded-xl overflow-hidden shadow-2xl"
              style={{ border: '1px solid rgba(34,211,238,0.2)', background: 'rgba(4,8,14,0.98)' }}
            >
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                <Search style={{ width: 14, height: 14, color: '#22d3ee', flexShrink: 0 }} />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => { setQuery(e.target.value); setActiveIdx(0); }}
                  onKeyDown={handleKeyDown}
                  placeholder="Search nodes, navigation, run actions…"
                  className="flex-1 bg-transparent outline-none text-[13px] font-mono"
                  style={{ color: 'rgba(255,255,255,0.85)', caretColor: '#22d3ee' }}
                />
                {query && (
                  <button onClick={() => setQuery('')} style={{ color: 'rgba(255,255,255,0.3)' }}>
                    <X style={{ width: 12, height: 12 }} />
                  </button>
                )}
                <kbd className="text-[9px] px-1.5 py-0.5 rounded border font-mono"
                  style={{ color: 'rgba(255,255,255,0.25)', borderColor: 'rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)' }}>
                  ESC
                </kbd>
              </div>

              {/* Action error banner */}
              {actionError && (
                <div className="px-4 py-2 text-[9px] font-mono"
                  style={{ background: 'rgba(248,113,113,0.08)', borderBottom: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}>
                  ✕ {actionError}
                </div>
              )}

              {/* Results */}
              <div className="max-h-[380px] overflow-y-auto" style={{ scrollbarWidth: 'none' }}>
                {results.length === 0 ? (
                  <div className="py-10 text-center text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.15)' }}>
                    No results for "{query}"
                  </div>
                ) : (
                  <div className="py-1">
                    {results.map((r, i) => {
                      const showNodeHeader   = i === firstNodeIdx   && firstNodeIdx   >= 0;
                      const showNavHeader    = i === firstNavIdx    && firstNavIdx    >= 0;
                      const showActionHeader = i === firstActionIdx && firstActionIdx >= 0;
                      return (
                        <div key={r.id}>
                          {showNodeHeader && (
                            <div className="px-4 py-1.5 text-[8px] font-bold uppercase tracking-[0.25em]"
                              style={{ color: 'rgba(255,255,255,0.2)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              Knowledge Nodes
                            </div>
                          )}
                          {showNavHeader && firstNodeIdx >= 0 && (
                            <div className="px-4 py-1.5 text-[8px] font-bold uppercase tracking-[0.25em]"
                              style={{ color: 'rgba(255,255,255,0.2)', borderTop: '1px solid rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              Navigation
                            </div>
                          )}
                          {!query && showNavHeader && firstNodeIdx < 0 && (
                            <div className="px-4 py-1.5 text-[8px] font-bold uppercase tracking-[0.25em]"
                              style={{ color: 'rgba(255,255,255,0.2)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              Quick Navigation
                            </div>
                          )}
                          {showActionHeader && (
                            <div className="px-4 py-1.5 text-[8px] font-bold uppercase tracking-[0.25em]"
                              style={{ color: 'rgba(167,139,250,0.5)', borderTop: '1px solid rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                              ⚡ Actions
                            </div>
                          )}
                          <ResultRow
                            result={r}
                            isActive={i === activeIdx}
                            onClick={() => handleSelect(r)}
                            isPending={pendingActionId === r.id}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer hint */}
              <div className="flex items-center gap-4 px-4 py-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
                {[['↑↓', 'Navigate'], ['↵', 'Select / Run'], ['Esc', 'Close']].map(([key, label]) => (
                  <div key={key} className="flex items-center gap-1.5">
                    <kbd className="text-[8px] px-1.5 py-0.5 rounded border font-mono"
                      style={{ color: 'rgba(255,255,255,0.3)', borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.04)' }}>
                      {key}
                    </kbd>
                    <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.2)' }}>{label}</span>
                  </div>
                ))}
                <span className="ml-auto text-[8px]" style={{ color: 'rgba(255,255,255,0.15)' }}>
                  {results.length} result{results.length !== 1 ? 's' : ''}
                </span>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

// ─── Trigger Button (for nav bar) ─────────────────────────────
export function GlobalSearchTrigger() {
  return (
    <button
      onClick={() => {
        const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
        window.dispatchEvent(event);
      }}
      className="flex items-center gap-2 px-3 py-1 rounded-md border transition-all"
      style={{
        background: 'rgba(255,255,255,0.03)',
        borderColor: 'rgba(255,255,255,0.08)',
        color: 'rgba(255,255,255,0.3)',
        fontSize: 10,
        letterSpacing: '0.1em',
      }}
      title="Global Search (Ctrl+K)"
    >
      <Search style={{ width: 11, height: 11 }} />
      <span className="hidden md:inline">SEARCH</span>
      <kbd className="text-[8px] px-1 rounded border"
        style={{ color: 'rgba(255,255,255,0.2)', borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.04)' }}>
        ⌃K
      </kbd>
    </button>
  );
}
