import { useControlPlaneStore } from '../../store/controlPlaneStore';

const SOURCE_COLOR: Record<string, string> = {
  graph: '#22d3ee',
  memory: '#8b5cf6',
  hybrid: '#10b981',
  l3: '#f59e0b',
};

const SOURCE_LABEL: Record<string, string> = {
  graph: 'GRAPH',
  memory: 'MEMORY',
  hybrid: 'HYBRID',
  l3: 'L3 SAGE',
};

export default function ResponsePanel() {
  const { result, error } = useControlPlaneStore();

  if (error) {
    return (
      <div style={{ ...panelStyle, border: '1px solid rgba(239,68,68,0.35)', background: 'rgba(239,68,68,0.04)' }}>
        <PanelHeader title="RESPONSE" />
        <div style={{ padding: '10px 12px', background: 'rgba(239,68,68,0.08)', borderRadius: 4, border: '1px solid rgba(239,68,68,0.2)' }}>
          <div style={{ fontSize: 9, color: '#ef4444', letterSpacing: '0.12em', fontWeight: 700, marginBottom: 4 }}>
            EXECUTION ERROR
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div style={panelStyle}>
        <PanelHeader title="RESPONSE" />
        <EmptyState />
      </div>
    );
  }

  const { response, confidence } = result;
  const isBlocked = response.status === 'blocked' || !confidence.gate_pass;
  const sourceColor = response.source ? (SOURCE_COLOR[response.source] ?? '#22d3ee') : '#6b7280';
  const sourceLabel = response.source ? (SOURCE_LABEL[response.source] ?? response.source.toUpperCase()) : '—';

  return (
    <div
      style={{
        ...panelStyle,
        border: isBlocked ? '1px solid rgba(239,68,68,0.25)' : `1px solid ${sourceColor}25`,
        background: isBlocked ? 'rgba(239,68,68,0.03)' : `${sourceColor}05`,
      }}
    >
      <div style={{ marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.6)', fontWeight: 700 }}>
          RESPONSE
        </span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {/* Source badge */}
          {!isBlocked && (
            <span
              style={{
                fontSize: 8,
                fontWeight: 700,
                letterSpacing: '0.12em',
                color: sourceColor,
                background: `${sourceColor}15`,
                border: `1px solid ${sourceColor}35`,
                padding: '2px 7px',
                borderRadius: 3,
              }}
            >
              {sourceLabel}
            </span>
          )}
          {/* Confidence badge */}
          <span
            style={{
              fontSize: 8,
              fontWeight: 700,
              letterSpacing: '0.1em',
              color: isBlocked ? '#ef4444' : '#10b981',
              background: isBlocked ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
              border: isBlocked ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.3)',
              padding: '2px 7px',
              borderRadius: 3,
              fontFamily: 'monospace',
            }}
          >
            {isBlocked ? 'BLOCKED' : `CONF ${response.confidence.toFixed(3)}`}
          </span>
        </div>
      </div>

      {/* Blocked state */}
      {isBlocked && (
        <div>
          <div
            style={{
              padding: '10px 12px',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.2)',
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            <div style={{ fontSize: 9, color: '#ef4444', fontWeight: 700, letterSpacing: '0.12em', marginBottom: 3 }}>
              GENERATION BLOCKED
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
              {response.block_reason ?? confidence.block_reason ?? 'Retrieval confidence below threshold'}
            </div>
          </div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.08em' }}>
            Raise threshold or force a route using Advanced Controls to bypass gating.
          </div>
        </div>
      )}

      {/* Success state */}
      {!isBlocked && response.answer && (
        <div>
          <div
            style={{
              padding: '12px 14px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 4,
              fontSize: 12,
              color: 'rgba(255,255,255,0.8)',
              lineHeight: 1.65,
              whiteSpace: 'pre-wrap',
              maxHeight: 300,
              overflowY: 'auto',
            }}
          >
            {response.answer}
          </div>

          {/* Fragment count */}
          {response.fragments && response.fragments.length > 0 && (
            <div style={{ marginTop: 6, fontSize: 9, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.08em' }}>
              {response.fragments.length} source fragment{response.fragments.length !== 1 ? 's' : ''} retrieved
            </div>
          )}
        </div>
      )}

      {/* No content */}
      {!isBlocked && !response.answer && (
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.08em', padding: '8px 0' }}>
          No content returned by the cognitive layer.
        </div>
      )}
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
