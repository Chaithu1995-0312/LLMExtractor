// ============================================================
//  AuditStreamPanel — Virtualized Audit Log (Phase 2)
//  Uses TanStack Virtual for O(1) DOM nodes regardless of
//  how many events are in the stream buffer.
//  Socket.IO events → stream-reducer → stream-store → this UI.
// ============================================================

import React, { useEffect, useRef, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { io, Socket } from 'socket.io-client';
import { Wifi, WifiOff, AlertTriangle, Pin } from 'lucide-react';
import { useStreamStore, useFilteredEvents } from '../state/stream-store';
import { handleLegacyAuditEvent } from '../reducers/stream-reducer';
import type { AuditEventPayload } from '../protocol/event-types';

// Single shared socket instance (module-level singleton)
// Connect via relative URL so Vite dev proxy routes it through /socket.io → localhost:5001
const socket: Socket = io('/');

// ─── Constants ────────────────────────────────────────────────
const ROW_HEIGHT = 74; // px — fixed height for each event row

const COMPONENT_OPTIONS = [
  { value: '', label: 'All Components' },
  { value: 'compiler', label: 'Compiler' },
  { value: 'graph', label: 'Graph' },
  { value: 'cognition', label: 'Cognition' },
  { value: 'resolver', label: 'Resolver' },
  { value: 'sync', label: 'Sync' },
];

// ─── Event row background by event name ──────────────────────
function getEventBg(eventName: string): string {
  if (eventName.includes('HALLUCINATION') || eventName.includes('REJECTED') || eventName.includes('KILLED')) {
    return 'border-red-900/30 bg-red-950/20';
  }
  if (eventName.includes('FROZEN') || eventName.includes('PROMOTED')) {
    return 'border-emerald-900/30 bg-emerald-950/20';
  }
  if (eventName.includes('CONFLICT')) {
    return 'border-amber-900/30 bg-amber-950/20';
  }
  return 'border-white/5 bg-transparent';
}

// ─── Single virtualized event row ─────────────────────────────
const EventRow = React.memo(({ event }: { event: AuditEventPayload }) => (
  <div className={`px-3 py-2 border-b ${getEventBg(event.event)}`}>
    {/* Event name + timestamp */}
    <div className="flex justify-between items-start mb-1">
      <span className="font-bold text-white/80 text-[10px] leading-tight">
        {event.event.replace(/_/g, ' ')}
      </span>
      <span className="text-white/30 text-[8px] shrink-0 ml-2">
        {new Date(event.timestamp).toLocaleTimeString()}
      </span>
    </div>

    {/* Component + agent + model tier */}
    <div className="flex items-center gap-2 mb-1">
      <span className="px-1 py-0.5 rounded bg-white/5 border border-white/10 text-white/40 text-[8px]">
        {event.component}
      </span>
      <span className="text-white/30 text-[8px]">{event.agent}</span>
      {event.model_tier && (
        <span className="px-1 py-0.5 rounded bg-blue-900/30 border border-blue-500/20 text-blue-400 text-[8px]">
          {event.model_tier}
        </span>
      )}
    </div>

    {/* Decision reason */}
    {event.decision?.reason && (
      <div className="text-white/40 text-[8px] italic leading-tight line-clamp-1">
        &quot;{event.decision.reason}&quot;
      </div>
    )}

    {/* Cost */}
    {event.cost?.usd !== undefined && event.cost.usd > 0 && (
      <div className="text-emerald-400/70 text-[8px] font-bold mt-0.5">
        💰 ${event.cost.usd.toFixed(6)}
        {event.cost.tokens_in != null && (
          <span className="text-white/20 ml-1 font-normal">
            ({event.cost.tokens_in}↑ {event.cost.tokens_out}↓)
          </span>
        )}
      </div>
    )}
  </div>
));
EventRow.displayName = 'EventRow';

// ─── Main Component ───────────────────────────────────────────
export default function AuditStreamPanel() {
  const { connectionState, gapDetected, activeFilter, sendStreamEvent, setFilter, clearEvents } =
    useStreamStore();
  const filteredEvents = useFilteredEvents();

  // Scroll container ref (required by TanStack Virtual)
  const parentRef = useRef<HTMLDivElement>(null);

  // Auto-scroll-to-bottom lock (inverted scroll)
  const isLockedToBottom = useRef(true);

  // ─── TanStack Virtual setup ─────────────────────────────────
  // We render the list in reverse order (newest first)
  const reversed = [...filteredEvents].reverse();

  const virtualizer = useVirtualizer({
    count: reversed.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8, // render 8 extra rows above/below viewport
  });

  // Auto-scroll to top (newest item) when new events arrive
  useEffect(() => {
    if (isLockedToBottom.current && reversed.length > 0) {
      virtualizer.scrollToIndex(0, { behavior: 'smooth' });
    }
  }, [reversed.length, virtualizer]);

  // Detect manual scroll — unlock auto-scroll if user scrolls up
  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el) return;
    isLockedToBottom.current = el.scrollTop < 20;
  }, []);

  // ─── Socket.IO wiring ───────────────────────────────────────
  useEffect(() => {
    socket.on('connect', () => sendStreamEvent('CONNECT'));
    socket.on('disconnect', () => sendStreamEvent('DISCONNECT'));
    socket.on('connected', () => sendStreamEvent('CONNECT'));
    socket.on('audit_event', (data: Record<string, unknown>) => {
      handleLegacyAuditEvent(data);
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('connected');
      socket.off('audit_event');
    };
  }, [sendStreamEvent]);

  // ─── Connection state color ─────────────────────────────────
  const connColor: Record<string, string> = {
    CONNECTED:       'text-emerald-400',
    STREAMING:       'text-emerald-400',
    BUFFERING:       'text-amber-400',
    RESYNC_REQUIRED: 'text-red-400',
    DISCONNECTED:    'text-white/30',
  };
  const color = connColor[connectionState] ?? 'text-white/30';
  const ConnIcon = connectionState === 'DISCONNECTED' ? WifiOff : Wifi;

  return (
    <div
      className="flex flex-col h-full bg-[#080b10] border border-white/10 rounded-xl overflow-hidden font-mono"
      style={{ fontSize: '11px' }}
    >
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10 bg-black/40 shrink-0">
        <div className="flex items-center gap-2">
          <ConnIcon className={`w-3 h-3 ${color}`} />
          <span className="text-[9px] font-bold uppercase tracking-widest text-white/50">
            Audit Stream
          </span>
          <span className={`text-[8px] px-1.5 py-0.5 rounded border ${color} border-current`}>
            {connectionState}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Lock-to-bottom pin */}
          <button
            onClick={() => {
              isLockedToBottom.current = true;
              virtualizer.scrollToIndex(0);
            }}
            title="Scroll to latest"
            className="text-white/20 hover:text-white/60 transition-colors"
          >
            <Pin className="w-3 h-3" />
          </button>

          {/* Clear button */}
          <button
            onClick={clearEvents}
            className="text-[8px] text-white/20 hover:text-red-400 transition-colors uppercase tracking-wider"
          >
            CLR
          </button>

          {/* Component filter */}
          <select
            value={activeFilter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-black/60 border border-white/10 rounded px-1 py-0.5 text-[9px] text-white/60 outline-none"
          >
            {COMPONENT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Gap Warning Banner ────────────────────────────────── */}
      {gapDetected && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-950/40 border-b border-amber-500/30 text-amber-400 text-[9px] shrink-0">
          <AlertTriangle className="w-3 h-3 shrink-0" />
          <span>Sequence gap — stream may be incomplete. Reconnecting…</span>
        </div>
      )}

      {/* ── Virtualized Event List ────────────────────────────── */}
      <div
        ref={parentRef}
        className="flex-1 overflow-y-auto"
        onScroll={handleScroll}
      >
        {reversed.length === 0 ? (
          <div className="p-6 text-center text-white/20 text-[9px] uppercase tracking-widest">
            Waiting for audit events…
          </div>
        ) : (
          /* TanStack Virtual: outer container sets total height */
          <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualItem) => (
              <div
                key={virtualItem.key}
                data-index={virtualItem.index}
                ref={virtualizer.measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualItem.start}px)`,
                }}
              >
                <EventRow event={reversed[virtualItem.index]} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Footer ───────────────────────────────────────────── */}
      <div className="px-3 py-1.5 border-t border-white/5 flex justify-between text-[8px] text-white/20 shrink-0">
        <span>{filteredEvents.length} events</span>
        <span className="font-mono">
          {virtualizer.getVirtualItems().length} rendered / max 500
        </span>
      </div>
    </div>
  );
}
