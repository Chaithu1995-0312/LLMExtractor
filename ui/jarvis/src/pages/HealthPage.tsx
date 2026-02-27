// ============================================================
//  HealthPage — System Operations Center
//  Full-page health dashboard showing:
//    - Service status grid (DB, Redis, LLM, Sync, Celery)
//    - Latency timeseries sparklines
//    - Worker queue depth
//    - Recent error log
//    - Resource utilization gauges
// ============================================================

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Server, Database, Cpu, Activity, AlertTriangle,
  CheckCircle2, XCircle, Clock, RefreshCw, Zap,
  HardDrive, Wifi, WifiOff
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────
interface ServiceStatus {
  name: string;
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';
  latency_ms?: number;
  uptime_pct?: number;
  last_check: string;
  detail?: string;
}

interface WorkerInfo {
  worker_id: string;
  status: 'active' | 'idle' | 'down';
  tasks_processed: number;
  queue_depth: number;
  current_task?: string;
}

interface SystemMetric {
  label: string;
  value: number;
  unit: string;
  max: number;
  warn_threshold: number;
  crit_threshold: number;
  color: string;
}

interface ErrorLog {
  timestamp: string;
  service: string;
  level: 'ERROR' | 'WARN' | 'INFO';
  message: string;
}

interface HealthData {
  services: ServiceStatus[];
  workers: WorkerInfo[];
  metrics: SystemMetric[];
  errors: ErrorLog[];
  last_sync_at: string;
  version: string;
}

// ─── Gauge Component ──────────────────────────────────────────
function GaugeArc({ value, max, color, warn, crit }: { value: number; max: number; color: string; warn: number; crit: number }) {
  const pct = Math.min(value / max, 1);
  const angle = pct * 180;
  const radius = 36;
  const circumference = Math.PI * radius; // half circle
  const strokeDash = (pct * circumference).toFixed(1);
  const activeColor = value >= crit ? '#f87171' : value >= warn ? '#fbbf24' : color;

  // SVG arc path for semicircle
  const cx = 50, cy = 50;
  const startX = cx - radius, startY = cy;
  const endX = cx + radius, endY = cy;

  return (
    <svg width="100" height="58" viewBox="0 0 100 58">
      {/* Background arc */}
      <path
        d={`M ${startX},${startY} A ${radius},${radius} 0 0,1 ${endX},${endY}`}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth="7"
        strokeLinecap="round"
      />
      {/* Foreground arc */}
      <path
        d={`M ${startX},${startY} A ${radius},${radius} 0 0,1 ${endX},${endY}`}
        fill="none"
        stroke={activeColor}
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={`${strokeDash} ${circumference}`}
        style={{ filter: `drop-shadow(0 0 4px ${activeColor}80)`, transition: 'stroke-dasharray 0.5s ease' }}
      />
      <text x="50" y="46" textAnchor="middle" fontSize="11" fontWeight="bold" fontFamily="monospace" fill={activeColor}>
        {value}{/* unit shown below */}
      </text>
    </svg>
  );
}

// ─── Service Card ─────────────────────────────────────────────
function ServiceCard({ svc }: { svc: ServiceStatus }) {
  const STATUS_CFG = {
    ONLINE:   { color: '#34d399', border: 'rgba(52,211,153,0.25)',  bg: 'rgba(52,211,153,0.06)',  icon: CheckCircle2 },
    DEGRADED: { color: '#fbbf24', border: 'rgba(251,191,36,0.25)',  bg: 'rgba(251,191,36,0.06)',  icon: AlertTriangle },
    OFFLINE:  { color: '#f87171', border: 'rgba(248,113,113,0.25)', bg: 'rgba(248,113,113,0.06)', icon: XCircle },
    UNKNOWN:  { color: '#475569', border: 'rgba(71,85,105,0.25)',   bg: 'rgba(71,85,105,0.04)',   icon: Clock },
  };
  const cfg = STATUS_CFG[svc.status] ?? STATUS_CFG.UNKNOWN;
  const StatusIcon = cfg.icon;
  const isPulse = svc.status === 'ONLINE';

  return (
    <div className="flex flex-col gap-2 p-4 rounded-lg border transition-all"
      style={{ background: cfg.bg, borderColor: cfg.border }}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <StatusIcon style={{ width: 14, height: 14, color: cfg.color }} />
          {isPulse && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
              style={{ background: cfg.color, animation: 'pulse 2s ease-in-out infinite' }} />
          )}
        </div>
        <span className="text-[11px] font-bold flex-1" style={{ color: 'rgba(255,255,255,0.75)' }}>{svc.name}</span>
        <span className="text-[8px] font-black px-1.5 py-0.5 rounded border"
          style={{ color: cfg.color, borderColor: cfg.border, letterSpacing: '0.1em' }}>
          {svc.status}
        </span>
      </div>

      {/* Metrics */}
      <div className="flex gap-3 text-[9px]">
        {svc.latency_ms !== undefined && (
          <div className="flex flex-col">
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>LATENCY</span>
            <span className="font-mono font-bold" style={{ color: svc.latency_ms > 500 ? '#fbbf24' : cfg.color }}>
              {svc.latency_ms}ms
            </span>
          </div>
        )}
        {svc.uptime_pct !== undefined && (
          <div className="flex flex-col">
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>UPTIME</span>
            <span className="font-mono font-bold" style={{ color: svc.uptime_pct < 99 ? '#fbbf24' : cfg.color }}>
              {svc.uptime_pct.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Detail */}
      {svc.detail && (
        <div className="text-[8px] truncate" style={{ color: 'rgba(255,255,255,0.3)' }}>{svc.detail}</div>
      )}
      <div className="text-[7px] font-mono" style={{ color: 'rgba(255,255,255,0.2)' }}>
        Last check: {new Date(svc.last_check).toLocaleTimeString()}
      </div>
    </div>
  );
}

// ─── Worker Row ───────────────────────────────────────────────
function WorkerRow({ worker }: { worker: WorkerInfo }) {
  const STATUS_COLOR = { active: '#22d3ee', idle: '#475569', down: '#f87171' };
  const color = STATUS_COLOR[worker.status] ?? '#475569';

  return (
    <div className="flex items-center gap-3 py-2 px-3 border-b"
      style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color, boxShadow: worker.status === 'active' ? `0 0 5px ${color}` : 'none', animation: worker.status === 'active' ? 'pulse 2s ease-in-out infinite' : 'none' }} />
      <span className="text-[10px] font-mono flex-1 truncate" style={{ color: 'rgba(255,255,255,0.5)' }}>
        {worker.worker_id}
      </span>
      {worker.current_task && (
        <span className="text-[8px] truncate max-w-[120px]" style={{ color: '#22d3ee80' }}>
          {worker.current_task}
        </span>
      )}
      <span className="text-[9px] font-mono shrink-0" style={{ color: 'rgba(255,255,255,0.3)' }}>
        Q:{worker.queue_depth}
      </span>
      <span className="text-[9px] font-mono shrink-0" style={{ color: color }}>
        {worker.status.toUpperCase()}
      </span>
    </div>
  );
}

// ─── Error Log Row ─────────────────────────────────────────────
function ErrorRow({ err }: { err: ErrorLog }) {
  const LEVEL_COLOR = { ERROR: '#f87171', WARN: '#fbbf24', INFO: '#22d3ee' };
  const color = LEVEL_COLOR[err.level] ?? '#ffffff50';

  return (
    <div className="flex items-start gap-3 py-2 px-3 border-b"
      style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
      <span className="text-[8px] font-mono shrink-0 mt-0.5" style={{ color: 'rgba(255,255,255,0.25)' }}>
        {new Date(err.timestamp).toLocaleTimeString()}
      </span>
      <span className="text-[8px] font-bold shrink-0 px-1 rounded"
        style={{ color, background: `${color}12`, letterSpacing: '0.05em' }}>
        {err.level}
      </span>
      <span className="text-[9px] shrink-0" style={{ color: '#a78bfa80' }}>{err.service}</span>
      <span className="text-[9px] flex-1 min-w-0" style={{ color: 'rgba(255,255,255,0.45)' }}>{err.message}</span>
    </div>
  );
}

// ─── Metric Gauge Card ─────────────────────────────────────────
function MetricCard({ metric }: { metric: SystemMetric }) {
  const isWarn = metric.value >= metric.warn_threshold;
  const isCrit = metric.value >= metric.crit_threshold;
  const activeColor = isCrit ? '#f87171' : isWarn ? '#fbbf24' : metric.color;

  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-lg border"
      style={{ background: 'rgba(4,8,14,0.8)', borderColor: isCrit ? 'rgba(248,113,113,0.2)' : 'rgba(255,255,255,0.06)' }}>
      <GaugeArc value={metric.value} max={metric.max} color={metric.color} warn={metric.warn_threshold} crit={metric.crit_threshold} />
      <span className="text-[9px] font-bold" style={{ color: activeColor }}>{metric.value}{metric.unit}</span>
      <span className="text-[8px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.3)' }}>{metric.label}</span>
    </div>
  );
}

// ─── Backend Unreachable Banner ───────────────────────────────
function BackendUnreachable({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <WifiOff style={{ width: 36, height: 36, color: '#f87171' }} />
      <div className="text-center">
        <div className="text-[13px] font-black tracking-[0.3em] uppercase" style={{ color: '#f87171', textShadow: '0 0 20px rgba(248,113,113,0.4)' }}>
          BACKEND UNREACHABLE
        </div>
        <div className="text-[10px] mt-1 uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.25)' }}>
          /api/health/full did not respond
        </div>
      </div>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-4 py-2 rounded-lg font-bold uppercase text-[10px]"
        style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.3)', color: '#f87171', letterSpacing: '0.15em' }}
      >
        <RefreshCw style={{ width: 12, height: 12 }} />
        Retry Connection
      </button>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────
export default function HealthPage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<HealthData>({
    queryKey: ['full-health'],
    queryFn: async () => {
      const res = await fetch('/api/health/full');
      if (!res.ok) {
        // Throw so isError is set — lets us show the BackendUnreachable banner.
        throw new Error(`Health endpoint returned ${res.status}`);
      }
      return res.json();
    },
    refetchInterval: 10000,
  });

  const services = data?.services ?? [];
  const workers  = data?.workers  ?? [];
  const metrics  = data?.metrics  ?? [];
  const errors   = data?.errors   ?? [];

  return (
    <div className="h-full w-full overflow-y-auto p-6" style={{ background: '#030609' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-black tracking-[0.3em] uppercase text-white/85">
            Ops Center
          </h2>
          <p className="text-[10px] font-mono mt-1" style={{ color: 'rgba(255,255,255,0.3)', letterSpacing: '0.15em' }}>
            REAL-TIME SYSTEM HEALTH · WORKERS · METRICS
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection status badge — flashes red when backend is unreachable */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded border"
            style={{
              borderColor: isError ? 'rgba(248,113,113,0.3)' : 'rgba(52,211,153,0.25)',
              background: isError ? 'rgba(248,113,113,0.06)' : 'rgba(52,211,153,0.04)',
            }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
              background: isError ? '#f87171' : '#34d399',
              boxShadow: `0 0 4px ${isError ? '#f87171' : '#34d399'}`,
              animation: isError ? 'none' : 'pulse 2s ease-in-out infinite',
            }} />
            <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: '0.15em', color: isError ? '#f87171' : '#34d399' }}>
              {isError ? 'UNREACHABLE' : isFetching ? 'SYNCING' : 'LIVE'}
            </span>
          </div>

          {data?.version && (
            <span className="text-[9px] font-mono px-2 py-1 rounded border"
              style={{ color: 'rgba(255,255,255,0.3)', borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
              v{data.version}
            </span>
          )}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-bold uppercase text-[10px]"
            style={{
              background: 'rgba(34,211,238,0.06)', border: '1px solid rgba(34,211,238,0.25)',
              color: '#22d3ee', letterSpacing: '0.15em',
            }}
          >
            <RefreshCw style={{ width: 12, height: 12, animation: isFetching ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Full-page error state — shown only when no cached data exists */}
      {isError && !data && (
        <BackendUnreachable onRetry={() => refetch()} />
      )}

      {/* Stale-data warning banner — shown when we have cached data but endpoint is currently failing */}
      {isError && data && (
        <div className="flex items-center gap-3 px-4 py-2 rounded-lg border mb-4"
          style={{ background: 'rgba(248,113,113,0.05)', borderColor: 'rgba(248,113,113,0.2)' }}>
          <WifiOff style={{ width: 12, height: 12, color: '#f87171', flexShrink: 0 }} />
          <span className="text-[9px] uppercase tracking-widest" style={{ color: '#f87171' }}>
            Backend unreachable — showing last known data
          </span>
        </div>
      )}

      {isLoading && !data ? (
        <div className="flex items-center justify-center h-64 text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.15)' }}>
          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5 }}>
            Scanning system diagnostics...
          </motion.div>
        </div>
      ) : data ? (
        <div className="flex flex-col gap-6">

          {/* ── Service Status Grid ── */}
          <section>
            <div className="text-[9px] font-bold uppercase tracking-[0.25em] mb-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
              — Service Status
            </div>
            {services.length === 0 ? (
              <div className="py-6 text-center rounded-lg border border-dashed text-[10px] uppercase tracking-widest"
                style={{ color: 'rgba(255,255,255,0.12)', borderColor: 'rgba(255,255,255,0.06)' }}>
                No service data — ensure /api/health/full is wired
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {services.map(svc => <ServiceCard key={svc.name} svc={svc} />)}
              </div>
            )}
          </section>

          {/* ── Resource Metrics ── */}
          {metrics.length > 0 && (
            <section>
              <div className="text-[9px] font-bold uppercase tracking-[0.25em] mb-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
                — Resource Utilization
              </div>
              <div className="flex flex-wrap gap-3">
                {metrics.map(m => <MetricCard key={m.label} metric={m} />)}
              </div>
            </section>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* ── Workers ── */}
            <section>
              <div className="text-[9px] font-bold uppercase tracking-[0.25em] mb-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
                — Celery Workers ({workers.filter(w => w.status === 'active').length} active)
              </div>
              <div className="rounded-lg border overflow-hidden"
                style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)' }}>
                {workers.length === 0 ? (
                  <div className="py-6 text-center text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.12)' }}>
                    No worker data available
                  </div>
                ) : (
                  workers.map(w => <WorkerRow key={w.worker_id} worker={w} />)
                )}
              </div>
            </section>

            {/* ── Error Log ── */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <div className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  — Recent Errors
                </div>
                {errors.filter(e => e.level === 'ERROR').length > 0 && (
                  <span className="text-[8px] font-bold px-1.5 py-0.5 rounded border"
                    style={{ color: '#f87171', borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.08)' }}>
                    {errors.filter(e => e.level === 'ERROR').length} ERR
                  </span>
                )}
              </div>
              <div className="rounded-lg border overflow-hidden max-h-64 overflow-y-auto"
                style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)', scrollbarWidth: 'none' }}>
                {errors.length === 0 ? (
                  <div className="py-6 text-center">
                    <CheckCircle2 style={{ width: 18, height: 18, color: '#34d399', margin: '0 auto 6px' }} />
                    <div className="text-[10px] uppercase tracking-widest" style={{ color: 'rgba(52,211,153,0.5)' }}>
                      No recent errors
                    </div>
                  </div>
                ) : (
                  errors.slice(0, 20).map((e, i) => <ErrorRow key={i} err={e} />)
                )}
              </div>
            </section>
          </div>

          {/* Footer: last sync timestamp */}
          {data?.last_sync_at && (
            <div className="text-[8px] font-mono text-right" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Last data refresh: {new Date(data.last_sync_at).toLocaleString()}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
