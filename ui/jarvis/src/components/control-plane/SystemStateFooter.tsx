import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { HealthStatus } from '../../types/controlPlane';

const STATUS_DOT: Record<HealthStatus, { color: string; label: string }> = {
  healthy: { color: '#10b981', label: '●' },
  empty:   { color: '#f59e0b', label: '●' },
  warn:    { color: '#f59e0b', label: '●' },
  fail:    { color: '#ef4444', label: '●' },
  unavailable: { color: '#ef4444', label: '●' },
  unknown: { color: '#6b7280', label: '○' },
};

export default function SystemStateFooter() {
  const { result } = useControlPlaneStore();

  const s = result?.system_state;

  const graphDot  = STATUS_DOT[s?.graph_index  ?? 'unknown'];
  const memDot    = STATUS_DOT[s?.memory_index ?? 'unknown'];
  const budgetOk  = s?.budget_pressure === 'low' || s?.budget_pressure === 'normal';

  const lastCheck = s?.last_health_check
    ? new Date(s.last_health_check).toLocaleTimeString()
    : '—';

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '6px 20px',
        alignItems: 'center',
        padding: '8px 14px',
        background: 'rgba(2,5,8,0.98)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 5,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '0.12em',
      }}
    >
      <span style={{ color: 'rgba(255,255,255,0.2)' }}>SYSTEM STATE</span>

      <Indicator
        dot={graphDot}
        label="GRAPH"
        value={`${s?.graph_index ?? 'unknown'}${s?.graph_node_count !== undefined ? ` · ${s.graph_node_count} nodes` : ''}`}
      />
      <Indicator
        dot={memDot}
        label="MEMORY"
        value={`${s?.memory_index ?? 'unknown'}${s?.memory_vector_count !== undefined ? ` · ${s.memory_vector_count.toLocaleString()} vectors` : ''}`}
      />
      <Indicator
        dot={{ color: budgetOk ? '#10b981' : '#f59e0b', label: budgetOk ? '●' : '●' }}
        label="BUDGET"
        value={s?.budget_pressure ?? 'unknown'}
      />
      <Indicator
        dot={{ color: '#6b7280', label: '◆' }}
        label="MODEL"
        value={s?.embedding_model ?? 'nomic-embed-text'}
      />
      <span style={{ marginLeft: 'auto', color: 'rgba(255,255,255,0.2)', fontFamily: 'monospace' }}>
        last check {lastCheck}
      </span>
    </div>
  );
}

function Indicator({
  dot,
  label,
  value,
}: {
  dot: { color: string; label: string };
  label: string;
  value: string;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <span style={{ color: dot.color, fontSize: 8 }}>{dot.label}</span>
      <span style={{ color: 'rgba(255,255,255,0.3)' }}>{label}</span>
      <span style={{ color: 'rgba(255,255,255,0.55)', fontFamily: 'monospace', fontWeight: 400 }}>
        {value.toUpperCase()}
      </span>
    </div>
  );
}
