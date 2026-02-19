// ============================================================
//  LiveCognitiveStreamPanel — Bottom-left: real-time events
// ============================================================

import { useStreamStore, useFilteredEvents } from '../state/stream-store';

const EVENT_STYLES: Record<string, { color: string; bg: string; border: string; label: string }> = {
  PROMPT_FETCHED:    { color: '#22d3ee', bg: 'rgba(34,211,238,0.12)',  border: 'rgba(34,211,238,0.3)',  label: 'PROMPT FETCHED' },
  NODE_CREATED:      { color: '#34d399', bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.3)',  label: 'NODE CREATED' },
  EDGE_CREATED:      { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.3)', label: 'EDGE CREATED' },
  CONFLICT_DETECTED: { color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', label: 'CONFLICT DETECTED' },
  NODE_FROZEN:       { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)',  border: 'rgba(251,191,36,0.3)',  label: 'NODE FROZEN' },
  NODE_KILLED:       { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.3)',   label: 'NODE KILLED' },
};

function getStyle(eventName: string) {
  // Try exact match first, then partial match
  if (EVENT_STYLES[eventName]) return EVENT_STYLES[eventName];
  const key = Object.keys(EVENT_STYLES).find((k) => eventName.includes(k));
  return key
    ? EVENT_STYLES[key]
    : { color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.03)', border: 'rgba(255,255,255,0.08)', label: eventName };
}

export function LiveCognitiveStreamPanel() {
  const { connectionState } = useStreamStore();
  const events = useFilteredEvents();
  const recent = [...events].reverse().slice(0, 12);

  const connColors: Record<string, string> = {
    CONNECTED: '#34d399',
    STREAMING: '#34d399',
    DISCONNECTED: 'rgba(255,255,255,0.2)',
    BUFFERING: '#fbbf24',
  };
  const connColor = connColors[connectionState] ?? 'rgba(255,255,255,0.2)';

  return (
    <div
      className="flex flex-col h-full border-r border-t overflow-hidden"
      style={{
        background: 'rgba(3,6,10,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: connColor,
              boxShadow: `0 0 4px ${connColor}`,
              animation: connectionState === 'CONNECTED' || connectionState === 'STREAMING'
                ? 'pulse 2s ease-in-out infinite'
                : 'none',
            }}
          />
          <span
            className="text-[9px] font-bold uppercase tracking-[0.2em]"
            style={{ color: '#fbbf24', textShadow: '0 0 8px rgba(251,191,36,0.4)' }}
          >
            Live Cognitive Stream
          </span>
        </div>
        <span
          className="text-[8px] font-mono"
          style={{ color: 'rgba(255,255,255,0.2)' }}
        >
          {events.length} events
        </span>
      </div>

      {/* Event list */}
      <div className="flex-1 overflow-y-auto px-2 py-1" style={{ scrollbarWidth: 'none' }}>
        {recent.length === 0 ? (
          <div
            className="h-full flex items-center justify-center text-[9px] uppercase tracking-widest"
            style={{ color: 'rgba(255,255,255,0.15)' }}
          >
            Waiting for events…
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            {recent.map((ev, i) => {
              const style = getStyle(ev.event);
              const ts = new Date(ev.timestamp).toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              });

              return (
                <div key={i} className="flex items-center gap-2 py-1 px-1 rounded" style={{ minHeight: 22 }}>
                  {/* Timestamp */}
                  <span
                    className="text-[8px] font-mono shrink-0 w-14"
                    style={{ color: 'rgba(255,255,255,0.3)' }}
                  >
                    {ts}
                  </span>

                  {/* Event badge */}
                  <span
                    className="text-[8px] font-bold px-1.5 py-0.5 rounded shrink-0"
                    style={{
                      color: style.color,
                      background: style.bg,
                      border: `1px solid ${style.border}`,
                      letterSpacing: '0.05em',
                      textShadow: `0 0 6px ${style.color}80`,
                    }}
                  >
                    {style.label.length > 14 ? style.label.slice(0, 13) + '…' : style.label}
                  </span>

                  {/* Detail */}
                  <span
                    className="text-[9px] truncate flex-1 font-mono"
                    style={{ color: 'rgba(255,255,255,0.45)' }}
                  >
                    {ev.decision?.reason || ev.component || ev.agent || '—'}
                  </span>

                  {/* Mini activity bar */}
                  <svg width="24" height="10" className="shrink-0 ml-1">
                    {[3, 6, 4, 8, 5, 7, 6].map((h, j) => (
                      <rect
                        key={j}
                        x={j * 3.4}
                        y={10 - h}
                        width="2.5"
                        height={h}
                        fill={style.color}
                        opacity={j === 6 ? 0.8 : 0.3 + j * 0.07}
                      />
                    ))}
                  </svg>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
