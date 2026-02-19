// ============================================================
//  IntentFocusPanel — Right panel: focused intent details
//  Shows intent metadata, source chain, lifecycle, conflicts
// ============================================================

import { motion } from 'framer-motion';
import { Anchor, ArrowRightLeft, ClipboardList, AlertTriangle, TrendingUp } from 'lucide-react';

interface ConflictItem {
  id: string;
  label: string;
}

interface IntentFocusPanelProps {
  intentId?: string;
  title?: string;
  status?: 'FROZEN' | 'FORMING' | 'LOOSE' | 'KILLED' | 'SUPERSEDED';
  confidence?: number;
  sourceChain?: string[];
  conflicts?: ConflictItem[];
  onAnchor?: () => void;
  onSupersede?: () => void;
  onAudit?: () => void;
}

const STATUS_COLORS: Record<string, { color: string; bg: string; border: string; glow: string }> = {
  FROZEN:    { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)',  border: 'rgba(251,191,36,0.4)',  glow: 'rgba(251,191,36,0.3)' },
  FORMING:   { color: '#22d3ee', bg: 'rgba(34,211,238,0.1)',  border: 'rgba(34,211,238,0.4)',  glow: 'rgba(34,211,238,0.3)' },
  LOOSE:     { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', border: 'rgba(148,163,184,0.3)', glow: 'none' },
  KILLED:    { color: '#f87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.4)', glow: 'rgba(248,113,113,0.3)' },
  SUPERSEDED:{ color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', border: 'rgba(167,139,250,0.3)', glow: 'none' },
};

const LIFECYCLE_STAGES = ['LOOSE', 'FORMING', 'FROZEN'];

// Tiny sparkline using SVG
function MiniSparkline({ color }: { color: string }) {
  const pts = [3, 8, 5, 12, 9, 14, 11, 10, 14].map((y, x) => `${x * 9},${20 - y}`).join(' ');
  return (
    <svg width="80" height="22" viewBox="0 0 80 22">
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: `drop-shadow(0 0 3px ${color})` }}
      />
    </svg>
  );
}

export function IntentFocusPanel({
  intentId = '—',
  title = 'No Intent Selected',
  status = 'LOOSE',
  confidence = 0,
  sourceChain = [],
  conflicts = [],
  onAnchor,
  onSupersede,
  onAudit,
}: IntentFocusPanelProps) {
  const sc = STATUS_COLORS[status] ?? STATUS_COLORS.LOOSE;
  const lifecycleIdx = LIFECYCLE_STAGES.indexOf(status);

  return (
    <div
      className="flex flex-col h-full border-l overflow-hidden"
      style={{
        background: 'rgba(4,8,14,0.92)',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[0.25em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Intent Focus
        </span>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-4" style={{ scrollbarWidth: 'none' }}>

        {/* Intent ID + Status badge */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className="text-[9px] font-bold"
                style={{ color: 'rgba(255,255,255,0.3)' }}
              >
                •  Intent:
              </span>
              <span
                className="text-[11px] font-black font-mono"
                style={{ color: sc.color, textShadow: `0 0 8px ${sc.glow}` }}
              >
                {intentId}
              </span>
            </div>
            <p
              className="text-[13px] font-bold leading-tight"
              style={{ color: 'rgba(255,255,255,0.85)' }}
            >
              {title}
            </p>
          </div>
          <span
            className="text-[8px] font-black px-2 py-1 rounded border shrink-0 mt-1"
            style={{
              color: sc.color,
              background: sc.bg,
              border: `1px solid ${sc.border}`,
              boxShadow: `0 0 8px ${sc.glow}`,
              letterSpacing: '0.15em',
            }}
          >
            {status}
          </span>
        </div>

        {/* Confidence */}
        <div>
          <div
            className="text-[9px] font-bold mb-1.5"
            style={{ color: 'rgba(255,255,255,0.35)' }}
          >
            Confidence: <span style={{ color: sc.color }}>{confidence}%</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="flex-1 h-1.5 rounded-full overflow-hidden"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              <motion.div
                className="h-full rounded-full"
                style={{ background: sc.color, boxShadow: `0 0 6px ${sc.glow}` }}
                initial={{ width: 0 }}
                animate={{ width: `${confidence}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
            <MiniSparkline color={sc.color} />
          </div>
        </div>

        {/* Source chain */}
        {sourceChain.length > 0 && (
          <div>
            <div
              className="text-[9px] font-bold uppercase tracking-widest mb-2"
              style={{ color: 'rgba(255,255,255,0.25)' }}
            >
              Source Chain ─
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {sourceChain.map((s, i) => (
                <div key={s} className="flex items-center gap-1.5">
                  <span
                    className="text-[9px] font-bold px-2 py-0.5 rounded font-mono"
                    style={{
                      background:
                        i === sourceChain.length - 1
                          ? 'rgba(251,191,36,0.12)'
                          : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${
                        i === sourceChain.length - 1
                          ? 'rgba(251,191,36,0.3)'
                          : 'rgba(255,255,255,0.08)'
                      }`,
                      color:
                        i === sourceChain.length - 1
                          ? '#fbbf24'
                          : 'rgba(255,255,255,0.55)',
                    }}
                  >
                    {s}
                  </span>
                  {i < sourceChain.length - 1 && (
                    <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: 9 }}>→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Lifecycle progression */}
        <div>
          <div
            className="text-[9px] font-bold uppercase tracking-widest mb-2"
            style={{ color: 'rgba(255,255,255,0.25)' }}
          >
            Lifecycle ─
          </div>
          <div className="flex items-center gap-1">
            {LIFECYCLE_STAGES.map((stage, i) => {
              const isActive = stage === status;
              const isPast = i < lifecycleIdx;
              const stageColor = STATUS_COLORS[stage]?.color ?? '#fff';
              return (
                <div key={stage} className="flex items-center gap-1">
                  <span
                    className="text-[8px] font-bold px-2 py-0.5 rounded border transition-all"
                    style={{
                      color: isActive ? stageColor : isPast ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.2)',
                      background: isActive ? `${stageColor}18` : 'transparent',
                      borderColor: isActive ? `${stageColor}50` : 'rgba(255,255,255,0.08)',
                      boxShadow: isActive ? `0 0 8px ${stageColor}40` : 'none',
                    }}
                  >
                    {stage}
                  </span>
                  {i < LIFECYCLE_STAGES.length - 1 && (
                    <span style={{ color: 'rgba(255,255,255,0.15)', fontSize: 8 }}>→</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {[
            { label: 'Anchor', icon: Anchor, onClick: onAnchor, accent: '#22d3ee' },
            { label: 'Supersede', icon: ArrowRightLeft, onClick: onSupersede, accent: '#a78bfa' },
            { label: 'Audit', icon: ClipboardList, onClick: onAudit, accent: 'rgba(255,255,255,0.5)' },
          ].map(({ label, icon: Icon, onClick, accent }) => (
            <button
              key={label}
              onClick={onClick}
              className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded border transition-all"
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: accent,
                borderColor: `${accent}40`,
                background: `${accent}08`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `${accent}18`;
                e.currentTarget.style.borderColor = `${accent}70`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = `${accent}08`;
                e.currentTarget.style.borderColor = `${accent}40`;
              }}
            >
              <Icon style={{ width: 10, height: 10 }} />
              {label}
            </button>
          ))}
        </div>

        {/* Conflict Radar */}
        {conflicts.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span
                className="text-[9px] font-bold uppercase tracking-widest"
                style={{ color: 'rgba(255,255,255,0.25)' }}
              >
                • Conflict Radar
              </span>
              <button
                className="text-[8px] font-bold"
                style={{ color: 'rgba(34,211,238,0.6)' }}
              >
                View All
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {conflicts.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center gap-2 p-2 rounded border"
                  style={{
                    background: 'rgba(239,68,68,0.06)',
                    borderColor: 'rgba(239,68,68,0.2)',
                  }}
                >
                  <AlertTriangle
                    className="shrink-0"
                    style={{ width: 10, height: 10, color: '#f87171' }}
                  />
                  <span className="text-[9px] font-bold" style={{ color: '#f87171' }}>
                    {c.id}
                  </span>
                  <span className="text-[9px] truncate" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    {c.label}
                  </span>
                  {/* Mini conflict bar */}
                  <svg width="40" height="12" className="ml-auto shrink-0">
                    {[2, 5, 3, 7, 4, 8, 5, 6, 4, 7].map((h, i) => (
                      <rect key={i} x={i * 4} y={12 - h} width="3" height={h} fill="#f87171" opacity="0.6" />
                    ))}
                  </svg>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
