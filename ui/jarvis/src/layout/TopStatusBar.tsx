import { useEffect, useState } from 'react';
import { useSystemStore } from '../state/system-store';
import { hydrateHealthFromApi } from '../reducers/system-reducer';
import { ConnectionStatusBadge } from '../components/ConnectionStatusBadge';

const HEALTH_POLL_INTERVAL_MS = 15000;

export function TopStatusBar() {
  const { health, systemState } = useSystemStore();
  const [metrics, setMetrics] = useState({ nodes: 0, edges: 0, alerts: 0, topic: 'NEXUS-42' });

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) hydrateHealthFromApi(await res.json());
      } catch {}
    };

    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/metrics/overview');
        if (res.ok) {
          const d = await res.json();
          setMetrics({
            nodes: d.nodes ?? 0,
            edges: d.edges ?? 0,
            alerts: d.alerts ?? 0,
            topic: d.topic ?? 'NEXUS-42',
          });
        }
      } catch {}
    };

    fetchHealth();
    fetchMetrics();
    const i1 = setInterval(fetchHealth, HEALTH_POLL_INTERVAL_MS);
    const i2 = setInterval(fetchMetrics, 10000);

    return () => {
      clearInterval(i1);
      clearInterval(i2);
    };
  }, []);

  const healthItems = [
    { label: 'Sync Engine', status: systemState !== 'BOOTING' ? 'ACTIVE' : 'BOOTING' },
    { label: 'LLM Cognition', status: health?.llm === 'ONLINE' ? 'ONLINE' : health?.llm === 'DEGRADED' ? 'DEGRADED' : 'OFFLINE' },
    { label: 'Graph DB', status: health?.db === 'ONLINE' ? 'OPTIMAL' : 'DEGRADED' },
    { label: 'Redis Queue', status: health?.redis === 'ONLINE' ? 'ACTIVE' : 'OFFLINE' },
  ];

  return (
    <header
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '140px',
        borderBottom: '1px solid rgba(34, 211, 238, 0.2)',
        background: 'linear-gradient(rgb(2, 5, 8) 0%, rgb(4, 8, 13) 100%)',
        paddingLeft: '48px',
        paddingRight: '48px',
        paddingTop: '32px',
        paddingBottom: '32px',
        overflow: 'hidden',
      }}
    >
      {/* ====== ANIMATIONS ====== */}
      <style>{`
        @keyframes holo-spin1 {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes holo-spin2 {
          from { transform: rotate(0deg); }
          to { transform: rotate(-360deg); }
        }
        @keyframes holo-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.1); }
        }
      `}</style>

      {/* Background glow */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: 'radial-gradient(circle, rgba(34, 211, 238, 0.06), transparent 70%)',
        }}
      />

      {/* THREE-COLUMN GRID */}
      <div
        style={{
          position: 'relative',
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          alignItems: 'center',
          height: '100%',
          gap: '32px',
        }}
      >
        {/* ========== LEFT COLUMN: System Health (VERTICAL) ========== */}
        <div>
          <div className="flex flex-col">
            <span className="text-[10px] tracking-[0.35em] uppercase text-white/30">
              SYSTEM HEALTH ─
            </span>

            <div
              style={{
                marginTop: '12px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
                whiteSpace: 'normal',
              }}
            >
              {healthItems.map((item, i) => (
                <HealthMetric key={i} icon={<CheckIcon />} label={item.label} status={item.status} />
              ))}
            </div>
          </div>
        </div>

        {/* ========== CENTER COLUMN: JARVIS Logo + Center Info Panel ========== */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '24px',
          }}
        >
          {/* Logo with orbs */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '48px',
            }}
          >
            <HoloOrb />
            <div className="text-center">
              <h1
                className="text-[34px] font-black tracking-[0.45em] text-white"
                style={{
                  textShadow:
                    'rgba(34, 211, 238, 0.6) 0px 0px 20px, rgba(34, 211, 238, 0.2) 0px 0px 50px',
                }}
              >
                JARVIS
              </h1>
              <p
                className="text-[10px] tracking-[0.35em] uppercase mt-1"
                style={{ color: 'rgba(34, 211, 238, 0.55)' }}
              >
                COGNITIVE CONTROL SYSTEM
              </p>
            </div>
            <HoloOrb />
          </div>

          {/* ✨ CENTER INFO PANEL: Active Topic + System Stats ✨ */}
          <div
            style={{
              display: 'flex',
              gap: '16px',
              justifyContent: 'center',
              padding: '12px 20px',
              background: 'rgba(34, 211, 238, 0.05)',
              borderRadius: '8px',
              border: '1px solid rgba(34, 211, 238, 0.2)',
            }}
          >
            {/* Active Topic */}
            <div style={{ textAlign: 'center' }}>
              <div className="text-[8px] uppercase tracking-[0.2em] font-bold" style={{ color: 'rgba(255, 255, 255, 0.35)' }}>
                Active Topic
              </div>
              <div className="text-[12px] font-bold font-mono mt-1" style={{ color: 'rgb(250, 204, 21)', textShadow: 'rgba(250, 204, 21, 0.6) 0px 0px 12px' }}>
                {metrics.topic}
              </div>
            </div>

            {/* Divider */}
            <div style={{ width: '1px', background: 'rgba(34, 211, 238, 0.2)' }} />

            {/* Nodes */}
            <div style={{ textAlign: 'center' }}>
              <div className="text-[8px] uppercase tracking-[0.2em] font-bold" style={{ color: 'rgba(255, 255, 255, 0.35)' }}>
                Nodes
              </div>
              <div className="text-[12px] font-bold font-mono mt-1" style={{ color: 'rgb(34, 211, 238)' }}>
                {metrics.nodes.toLocaleString()}
              </div>
            </div>

            {/* Divider */}
            <div style={{ width: '1px', background: 'rgba(34, 211, 238, 0.2)' }} />

            {/* Edges */}
            <div style={{ textAlign: 'center' }}>
              <div className="text-[8px] uppercase tracking-[0.2em] font-bold" style={{ color: 'rgba(255, 255, 255, 0.35)' }}>
                Edges
              </div>
              <div className="text-[12px] font-bold font-mono mt-1" style={{ color: 'rgb(34, 211, 238)' }}>
                {metrics.edges.toLocaleString()}
              </div>
            </div>

            {/* Divider */}
            <div style={{ width: '1px', background: 'rgba(34, 211, 238, 0.2)' }} />

            {/* Alerts */}
            <div style={{ textAlign: 'center' }}>
              <div className="text-[8px] uppercase tracking-[0.2em] font-bold" style={{ color: 'rgba(255, 255, 255, 0.35)' }}>
                Alerts
              </div>
              <div className="text-[12px] font-bold font-mono mt-1" style={{ color: metrics.alerts > 0 ? 'rgb(248, 113, 113)' : 'rgb(52, 211, 153)' }}>
                {metrics.alerts}
              </div>
            </div>
          </div>
        </div>

        {/* ========== RIGHT COLUMN: LLM Status ========== */}
        <div
          style={{
            display: 'flex',
            gap: '48px',
            justifyContent: 'flex-end',
          }}
        >
          <div className="flex flex-col gap-3 w-[240px]">
            <span
              className="text-[10px] tracking-[0.35em] uppercase"
              style={{ color: 'rgba(255, 255, 255, 0.3)' }}
            >
              ─ LLM STATUS
            </span>

            <div className="flex items-center gap-2">
              <span className="text-[9px] w-20 shrink-0" style={{ color: 'rgba(255, 255, 255, 0.45)' }}>
                Extraction
              </span>
              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255, 255, 255, 0.06)' }}>
                <div className="h-full rounded-full" style={{ width: '100%', background: 'rgb(52, 211, 153)' }} />
              </div>
              <span className="text-[9px] font-bold w-8 text-right font-mono" style={{ color: 'rgb(52, 211, 153)' }}>
                100%
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[9px] w-20 shrink-0" style={{ color: 'rgba(255, 255, 255, 0.45)' }}>
                Rerank
              </span>
              <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255, 255, 255, 0.06)' }}>
                <div className="h-full rounded-full" style={{ width: '96%', background: 'rgb(52, 211, 153)' }} />
              </div>
              <span className="text-[9px] font-bold w-8 text-right font-mono" style={{ color: 'rgb(52, 211, 153)' }}>
                96%
              </span>
            </div>

            <div className="flex justify-between text-[10px]" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
              <span>Fallbacks</span>
              <span className="font-mono">2</span>
            </div>
          </div>

          <div className="flex flex-col items-center gap-1">
            <svg width="58" height="58" viewBox="0 0 58 58">
              <circle cx="29" cy="29" r={22} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
              <circle
                cx="29"
                cy="29"
                r={22}
                fill="none"
                stroke="#22d3ee"
                strokeWidth="5"
                style={{ filter: 'drop-shadow(rgba(34, 211, 238, 0.8) 0px 0px 4px)' }}
                strokeDasharray="77 138"
              />
              <text
                x="29"
                y="30"
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="11"
                fontWeight="bold"
                fontFamily="monospace"
                fill="#67e8f9"
              >
                74%
              </text>
            </svg>
            <span className="text-[8px] uppercase tracking-[0.2em] font-bold" style={{ color: 'rgba(255, 255, 255, 0.3)' }}>
              Cognitive Load
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

// ====== HELPER COMPONENTS ======

/**
 * HoloOrb - Animated holographic ring with spinning elements
 */
function HoloOrb() {
  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '86px',
        height: '86px',
        flexShrink: 0,
      }}
    >
      {/* Outer glow halo */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '9999px',
          background: 'radial-gradient(circle, rgba(34, 211, 238, 0.15) 0%, transparent 70%)',
        }}
      />

      {/* Spinning Ring 1 (cyan) - 10s rotation */}
      <div
        style={{
          position: 'absolute',
          borderRadius: '9999px',
          border: '1px solid rgba(34, 211, 238, 0.2)',
          width: '81.7px',
          height: '81.7px',
          animation: 'holo-spin1 10s linear infinite',
          background: 'conic-gradient(transparent 70%, rgba(34, 211, 238, 0.4) 100%)',
        }}
      />

      {/* Spinning Ring 2 (yellow) - 7s reverse rotation */}
      <div
        style={{
          position: 'absolute',
          borderRadius: '9999px',
          border: '1px solid rgba(250, 204, 21, 0.3)',
          width: '61.92px',
          height: '61.92px',
          animation: 'holo-spin2 7s linear infinite reverse',
          background: 'conic-gradient(from 90deg, transparent 60%, rgba(250, 204, 21, 0.3) 100%)',
        }}
      />

      {/* Static Ring 3 (inner cyan) */}
      <div
        style={{
          position: 'absolute',
          borderRadius: '9999px',
          border: '2px solid rgba(103, 232, 249, 0.4)',
          width: '43px',
          height: '43px',
          animation: 'holo-spin1 4s linear infinite',
        }}
      />

      {/* Central Pulsing Core */}
      <div
        style={{
          position: 'absolute',
          width: '24px',
          height: '24px',
          borderRadius: '9999px',
          background: 'rgba(34, 211, 238, 0.9)',
          boxShadow: 'rgba(34, 211, 238, 0.8) 0px 0px 12px 4px, rgba(34, 211, 238, 0.4) 0px 0px 30px 8px',
          animation: 'holo-pulse 2s ease-in-out infinite',
        }}
      />
    </div>
  );
}

function HealthMetric({ icon, label, status }: { icon: React.ReactNode; label: string; status: string }) {
  const ok = status === 'ACTIVE' || status === 'ONLINE' || status === 'OPTIMAL';
  return (
    <div className="flex items-center gap-2">
      <div style={{ color: ok ? 'rgb(52, 211, 153)' : 'rgb(248, 113, 113)' }}>{icon}</div>
      <span className="text-[10px] w-28 shrink-0" style={{ color: 'rgba(255, 255, 255, 0.55)' }}>
        {label}
      </span>
      <span className="text-[8px] font-bold px-1.5 py-0.5 rounded border" style={{ color: ok ? 'rgb(52, 211, 153)' : 'rgb(248, 113, 113)', borderColor: ok ? 'rgba(52, 211, 153, 0.3)' : 'rgba(248, 113, 113, 0.3)', background: ok ? 'rgba(52, 211, 153, 0.08)' : 'rgba(248, 113, 113, 0.08)' }}>
        {status}
      </span>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3 shrink-0">
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
