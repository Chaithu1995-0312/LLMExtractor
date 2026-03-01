import { useControlPlaneStore } from '../../store/controlPlaneStore';

const INTENT_COLOR: Record<string, string> = {
  governance: '#f59e0b',
  diagnostic: '#3b82f6',
  memory: '#8b5cf6',
  strategic: '#10b981',
  factual: '#6b7280',
};

const ROUTE_COLOR: Record<string, string> = {
  graph: '#22d3ee',
  memory: '#8b5cf6',
  hybrid: '#10b981',
};

export default function RouteInspector() {
  const { result } = useControlPlaneStore();

  if (!result) {
    return (
      <div style={panelStyle}>
        <PanelHeader title="ROUTE INSPECTOR" />
        <EmptyState />
      </div>
    );
  }

  const { route } = result;
  const intentColor = INTENT_COLOR[route.intent] ?? '#6b7280';
  const routeColor = ROUTE_COLOR[route.selected] ?? '#22d3ee';

  return (
    <div style={panelStyle}>
      <PanelHeader title="ROUTE INSPECTOR" />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Intent */}
        <Row label="INTENT" value={route.intent.toUpperCase()} color={intentColor} />

        {/* Selected Route */}
        <Row label="SELECTED ROUTE" value={route.selected.toUpperCase()} color={routeColor} />

        {/* Hybrid used */}
        <Row
          label="HYBRID USED"
          value={route.hybrid_used ? 'YES' : 'NO'}
          color={route.hybrid_used ? '#10b981' : 'rgba(255,255,255,0.3)'}
        />

        {/* Override */}
        {route.overridden && (
          <Row label="OVERRIDE ACTIVE" value="FORCE_ROUTE" color="#f59e0b" />
        )}

        {/* Escalation flag */}
        <Row
          label="ESCALATION FLAG"
          value={route.force_escalate ? 'ARMED' : 'INACTIVE'}
          color={route.force_escalate ? '#f59e0b' : 'rgba(255,255,255,0.3)'}
        />
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 9, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.35)', fontWeight: 700 }}>
        {label}
      </span>
      <span
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.12em',
          color,
          background: `${color}18`,
          padding: '2px 8px',
          borderRadius: 3,
          border: `1px solid ${color}30`,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function PanelHeader({ title }: { title: string }) {
  return (
    <div style={{ marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
      <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.6)', fontWeight: 700 }}>
        {title}
      </span>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', textAlign: 'center', paddingTop: 16 }}>
      AWAITING QUERY EXECUTION
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  background: 'rgba(4,8,13,0.95)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 6,
  padding: '14px 16px',
};
