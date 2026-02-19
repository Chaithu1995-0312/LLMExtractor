// ============================================================
//  AuditLogPanel — Bottom-right: recent audit events + risk
// ============================================================

import { AlertTriangle } from 'lucide-react';
import { useFilteredEvents } from '../state/stream-store';

const EVENT_COLORS: Record<string, string> = {
  PROMPT_FALLBACK:        '#fbbf24',
  NODE_FROZEN:            '#34d399',
  GOVERNANCE_VIOLATION:   '#f87171',
  CONFLICT_DETECTED:      '#fb923c',
  NODE_KILLED:            '#ef4444',
};

function getEventColor(event: string): string {
  const key = Object.keys(EVENT_COLORS).find((k) => event.includes(k));
  return key ? EVENT_COLORS[key] : 'rgba(255,255,255,0.35)';
}

const SYSTEM_RISKS = [
  { label: 'SQLite Lock Risk', level: 'warn' },
  { label: 'LLM Latency ↑',   level: 'warn' },
  { label: 'Low Coverage',     level: 'info' },
];

export function AuditLogPanel() {
  const events = useFilteredEvents();
  const recent = [...events].reverse().slice(0, 6);

  return (
    <div
      className="flex flex-col h-full border-t overflow-hidden"
      style={{
        background: 'rgba(3,6,10,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Audit Log section */}
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[0.2em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          — Audit Log
        </span>
        <span
          className="text-[8px] font-mono"
          style={{ color: 'rgba(255,255,255,0.2)' }}
        >
          Last {Math.min(events.length, 50)} Events —
        </span>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Event list */}
        <div
          className="flex-1 overflow-y-auto px-2 py-1"
          style={{ scrollbarWidth: 'none', minHeight: 0 }}
        >
          {recent.length === 0 ? (
            <div
              className="py-4 text-center text-[9px] uppercase tracking-widest"
              style={{ color: 'rgba(255,255,255,0.1)' }}
            >
              No events yet
            </div>
          ) : (
            <div className="flex flex-col">
              {recent.map((ev, i) => {
                const color = getEventColor(ev.event);
                const ts = new Date(ev.timestamp).toLocaleTimeString('en-US', {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                });
                return (
                  <div
                    key={i}
                    className="flex items-start gap-2 py-1.5 border-b"
                    style={{ borderColor: 'rgba(255,255,255,0.04)' }}
                  >
                    <span
                      className="text-[8px] font-mono shrink-0 mt-0.5"
                      style={{ color: 'rgba(255,255,255,0.3)' }}
                    >
                      {ts}
                    </span>
                    <div className="flex flex-col min-w-0">
                      <span
                        className="text-[9px] font-bold leading-tight"
                        style={{ color, textShadow: `0 0 6px ${color}60` }}
                      >
                        {ev.event.replace(/_/g, ' ')}
                      </span>
                      {ev.decision?.reason && (
                        <span
                          className="text-[8px] truncate"
                          style={{ color: 'rgba(255,255,255,0.3)' }}
                        >
                          {ev.decision.reason}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* System Risk section */}
        <div
          className="shrink-0 border-t px-2 py-2"
          style={{ borderColor: 'rgba(255,255,255,0.06)' }}
        >
          <div
            className="text-[8px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'rgba(255,255,255,0.2)' }}
          >
            // System Risk
          </div>
          <div className="flex flex-col gap-1">
            {SYSTEM_RISKS.map((risk) => (
              <div key={risk.label} className="flex items-center gap-2">
                <AlertTriangle
                  style={{
                    width: 10,
                    height: 10,
                    color: risk.level === 'warn' ? '#fbbf24' : '#22d3ee',
                    flexShrink: 0,
                  }}
                />
                <span
                  className="text-[9px] font-bold"
                  style={{
                    color: risk.level === 'warn' ? '#fbbf24' : '#22d3ee',
                  }}
                >
                  {risk.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
