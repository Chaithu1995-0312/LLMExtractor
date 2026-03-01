import { useControlPlaneStore } from '../../store/controlPlaneStore';

const TIER_LABELS: Record<number, string> = {
  1: 'Local / Tier 1',
  2: 'Flash / Tier 2',
  3: 'Pro / Tier 3',
};

export default function EscalationPanel() {
  const { result } = useControlPlaneStore();

  if (!result) return null;

  const { escalation } = result;

  if (!escalation.triggered) {
    return (
      <div style={panelStyle}>
        <PanelHeader title="L3 ESCALATION" />
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 10px',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: 4,
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em' }}>⊘</span>
          <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.08em' }}>
            Escalation not triggered for this query
          </span>
        </div>
      </div>
    );
  }

  const tierLabel = escalation.tier !== null ? TIER_LABELS[escalation.tier] ?? `Tier ${escalation.tier}` : 'Unknown';
  const hasError = !!escalation.error;

  return (
    <div
      style={{
        ...panelStyle,
        border: hasError ? '1px solid rgba(239,68,68,0.25)' : '1px solid rgba(245,158,11,0.25)',
        background: hasError ? 'rgba(239,68,68,0.04)' : 'rgba(245,158,11,0.04)',
      }}
    >
      <div style={{ marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: hasError ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>
          L3 ESCALATION
        </span>
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.1em',
            color: hasError ? '#ef4444' : '#f59e0b',
            background: hasError ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
            padding: '2px 7px',
            borderRadius: 3,
          }}
        >
          {hasError ? 'FAILED' : 'TRIGGERED'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Tier */}
        <Row label="TIER" value={tierLabel} />

        {/* Model */}
        {escalation.model && (
          <Row label="MODEL" value={escalation.model} />
        )}

        {/* Error */}
        {hasError && (
          <div
            style={{
              padding: '8px 10px',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.25)',
              borderRadius: 4,
            }}
          >
            <div style={{ fontSize: 9, letterSpacing: '0.12em', color: '#ef4444', fontWeight: 700, marginBottom: 3 }}>
              ESCALATION ERROR
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
              {escalation.error}
            </div>
          </div>
        )}

        {/* Advisory */}
        {escalation.advisory && !hasError && (
          <div>
            <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.3)', marginBottom: 6, fontWeight: 700 }}>
              L3 ADVISORY
            </div>
            <div
              style={{
                padding: '10px 12px',
                background: 'rgba(245,158,11,0.06)',
                border: '1px solid rgba(245,158,11,0.15)',
                borderRadius: 4,
                fontSize: 11,
                color: 'rgba(255,255,255,0.7)',
                lineHeight: 1.6,
                maxHeight: 180,
                overflowY: 'auto',
              }}
            >
              {escalation.advisory}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 9, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.35)', fontWeight: 700 }}>
        {label}
      </span>
      <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.6)', fontFamily: 'monospace' }}>
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

const panelStyle: React.CSSProperties = {
  background: 'rgba(4,8,13,0.95)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 6,
  padding: '14px 16px',
};
