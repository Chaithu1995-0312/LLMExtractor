import { useEffect, useState } from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { useSystemStore } from '../state/system-store';
import { hydrateHealthFromApi } from '../reducers/system-reducer';

const HEALTH_POLL_INTERVAL_MS = 15_000;

// ─── CoreOrb (formerly HolographicRing) ─────────────────────────────────────────
function CoreOrb({ size = 72 }: { size?: number }) {
  return (
    <div
      className="relative flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      {/* Outer glow halo */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background:
            'radial-gradient(circle, rgba(34,211,238,0.15) 0%, transparent 70%)',
        }}
      />
      {/* Ring 1 */}
      <div
        className="absolute rounded-full border border-cyan-400/20"
        style={{
          width: size * 0.95,
          height: size * 0.95,
          animation: 'holo-spin1 10s linear infinite',
          background:
            'conic-gradient(from 0deg, transparent 70%, rgba(34,211,238,0.4) 100%)',
        }}
      />
      {/* Ring 2 */}
      <div
        className="absolute rounded-full border border-yellow-400/30"
        style={{
          width: size * 0.72,
          height: size * 0.72,
          animation: 'holo-spin2 7s linear infinite reverse',
          background:
            'conic-gradient(from 90deg, transparent 60%, rgba(250,204,21,0.3) 100%)',
        }}
      />
      {/* Ring 3 */}
      <div
        className="absolute rounded-full border-2 border-cyan-300/40"
        style={{
          width: size * 0.5,
          height: size * 0.5,
          animation: 'holo-spin1 4s linear infinite',
        }}
      />
      {/* Inner pulse */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.28,
          height: size * 0.28,
          background: 'rgba(34,211,238,0.9)',
          boxShadow:
            '0 0 12px 4px rgba(34,211,238,0.8), 0 0 30px 8px rgba(34,211,238,0.4)',
          animation: 'holo-pulse 2s ease-in-out infinite',
        }}
      />
    </div>
  );
}

// ─── StatusBar (formerly LLMMetricRow) ───────────────────────────────────────────
function StatusBar({label,value,color = '#34d399',}: {label: string;value: number;color?: string;}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="text-[9px] w-20 shrink-0"
        style={{ color: 'rgba(255,255,255,0.45)' }}
      >
        {label}
      </span>
      <div
        className="flex-1 h-1 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
      <span
        className="text-[9px] font-bold w-8 text-right font-mono"
        style={{ color }}
      >
        {value}%
      </span>
    </div>
  );
}

// ─── CognitiveGauge (formerly MiniCircularGauge) ─────────────────────────────────────
function CognitiveGauge({ percent, label = "Cognitive Load" }: { percent: number; label?: string }) {
  const r = 22;
  const circ = 2 * Math.PI * r;
  const arc = circ * 0.75; // 270°
  const filled = arc * (percent / 100);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative">
        <svg width="58" height="58" viewBox="0 0 58 58" className="overflow-visible">
          {/* Track */}
          <circle
            cx="29"
            cy="29"
            r={r}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="5"
            strokeDasharray={`${arc} ${circ}`}
            strokeDashoffset="0"
            strokeLinecap="round"
            transform="rotate(135, 29, 29)"
          />
          {/* Fill */}
          <circle
            cx="29"
            cy="29"
            r={r}
            fill="none"
            stroke="#22d3ee"
            strokeWidth="5"
            strokeDasharray={`${filled} ${circ}`}
            strokeDashoffset="0"
            strokeLinecap="round"
            transform="rotate(135, 29, 29)"
            style={{
              filter: 'drop-shadow(0 0 4px rgba(34,211,238,0.8))',
              transition: 'stroke-dasharray 0.8s ease',
            }}
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
            {percent}%
          </text>
        </svg>
      </div>
      <span
        className="text-[8px] uppercase tracking-[0.2em] font-bold"
        style={{ color: 'rgba(255,255,255,0.3)' }}
      >
        {label}
      </span>
    </div>
  );
}

// ─── Health Status Item ───────────────────────────────────────
function HealthItem({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  const ok = status === 'ACTIVE' || status === 'ONLINE' || status === 'OPTIMAL'; // Simple heuristic for 'ok'
  return (
    <div className="flex items-center gap-2">
      <CheckCircle2
        className="w-3 h-3 shrink-0"
        style={{ color: ok ? '#34d399' : '#f87171' }}
      />
      <span
        className="text-[10px] w-28 shrink-0"
        style={{ color: 'rgba(255,255,255,0.55)' }}
      >
        {label}
      </span>
      <span
        className="text-[8px] font-bold px-1.5 py-0.5 rounded border"
        style={{
          color: ok ? '#34d399' : '#f87171',
          borderColor: ok ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)',
          background: ok ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
        }}
      >
        {status}
      </span>
    </div>
  );
}

// ─── Main TopStatusBar ────────────────────────────────────────
export function TopStatusBar() {
  const { health, systemState } = useSystemStore();
  const [metrics, setMetrics] = useState({ nodes: 0, edges: 0 });

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
          setMetrics({ nodes: d.nodes ?? 0, edges: d.edges ?? 0 });
        }
      } catch {}
    };

    fetchHealth();
    fetchMetrics();
    const i1 = setInterval(fetchHealth, HEALTH_POLL_INTERVAL_MS);
    const i2 = setInterval(fetchMetrics, 10_000);
    return () => {
      clearInterval(i1);
      clearInterval(i2);
    };
  }, []);

  // This object is not used directly in the new JSX, but the data it contains
  // is implicitly used by the HealthItem components, so it's kept for context
  const healthItems = [
    {
      label: 'Sync Engine',
      status: systemState !== 'BOOTING' ? 'ACTIVE' : 'BOOTING',
      ok: systemState !== 'BOOTING' && systemState !== 'CRITICAL',
    },
    {
      label: 'LLM Cognition',
      status:
        health?.llm === 'ONLINE'
          ? 'ONLINE'
          : health?.llm === 'DEGRADED'
          ? 'DEGRADED'
          : 'OFFLINE',
      ok: health?.llm === 'ONLINE',
    },
    {
      label: 'Graph DB',
      status: health?.db === 'ONLINE' ? 'OPTIMAL' : 'DEGRADED',
      ok: health?.db === 'ONLINE',
    },
    {
      label: 'Redis Queue',
      status: health?.redis === 'ONLINE' ? 'ACTIVE' : 'OFFLINE',
      ok: health?.redis === 'ONLINE',
    },
  ];

  return (
    <header className="relative w-full min-h-[120px] border-b border-cyan-500/20 bg-gradient-to-b from-[#020508] to-[#04080d] px-12 py-8 overflow-hidden">

      {/* Cinematic Glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(circle at center, rgba(34,211,238,0.06), transparent 70%)',
        }}
      />

      {/* GRID LAYOUT — 3 TRUE COLUMNS */}
      <div className="relative grid grid-cols-[1fr_auto_1fr] items-center h-full">

        {/* ───────── LEFT ───────── */}
        <div className="justify-self-start">

          <div className="flex flex-col">
            <span className="text-[10px] tracking-[0.35em] uppercase text-white/30">
              SYSTEM HEALTH ─
            </span>

            <div className="flex items-center gap-6 mt-3 whitespace-nowrap">
              {healthItems.map((item, i) => (
                <HealthItem key={i} label={item.label} status={item.status} />
              ))}
            </div>
          </div>

        </div>

        {/* ───────── CENTER ───────── */}
        <div className="justify-self-center flex items-center gap-12">

          <CoreOrb size={86} />

          <div className="text-center">
            <h1
              className="text-[34px] font-black tracking-[0.45em] text-white"
              style={{
                textShadow:
                  '0 0 20px rgba(34,211,238,0.6), 0 0 50px rgba(34,211,238,0.2)',
              }}
            >
              JARVIS
            </h1>

            <p className="text-[10px] tracking-[0.35em] uppercase text-cyan-300/50 mt-1">
              COGNITIVE CONTROL SYSTEM
            </p>
          </div>

          <CoreOrb size={86} />

        </div>

        {/* ───────── RIGHT ───────── */}
        <div className="justify-self-end flex items-center gap-12">

          <div className="flex flex-col gap-3 w-[240px]">
            <span className="text-[10px] tracking-[0.35em] uppercase text-white/30 text-right">
              ─ LLM STATUS
            </span>

            <StatusBar label="Extraction" value={100} />
            <StatusBar label="Rerank" value={96} />

            <div className="flex justify-between text-[10px] text-white/50 font-mono">
              <span>Fallbacks</span>
              <span>2</span>
            </div>
          </div>

          <CognitiveGauge percent={74} />

        </div>

      </div>

    </header>
  );
}
