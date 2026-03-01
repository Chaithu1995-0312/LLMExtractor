import { useControlPlaneStore } from '../../store/controlPlaneStore';

function ConfidenceBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 9, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.45)', fontWeight: 700 }}>
          {label}
        </span>
        <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: 'monospace' }}>
          {value.toFixed(3)}
        </span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 2,
            transition: 'width 0.4s ease',
            boxShadow: `0 0 6px ${color}80`,
          }}
        />
      </div>
    </div>
  );
}

export default function ConfidencePanel() {
  const { result } = useControlPlaneStore();

  if (!result) {
    return (
      <div style={panelStyle}>
        <PanelHeader title="CONFIDENCE GATE" />
        <EmptyState />
      </div>
    );
  }

  const { confidence } = result;
  const gateColor = confidence.gate_pass ? '#10b981' : '#ef4444';
  const finalPct = Math.round(confidence.final * 100);
  const thresholdPct = Math.round(confidence.threshold * 100);

  return (
    <div style={panelStyle}>
      <PanelHeader title="CONFIDENCE GATE" />

      {/* Gate Status Banner */}
      <div
        style={{
          marginBottom: 14,
          padding: '8px 12px',
          background: `${gateColor}10`,
          border: `1px solid ${gateColor}40`,
          borderRadius: 4,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: gateColor }}>
          {confidence.gate_pass ? '✓ GATE PASS' : '✗ GATE BLOCKED'}
        </span>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'rgba(255,255,255,0.5)' }}>
          {confidence.final.toFixed(3)} / {confidence.threshold.toFixed(2)}
        </span>
      </div>

      {/* Threshold indicator */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, position: 'relative', overflow: 'visible' }}>
          {/* Threshold marker */}
          <div
            style={{
              position: 'absolute',
              left: `${thresholdPct}%`,
              top: -3,
              width: 2,
              height: 12,
              background: 'rgba(255,255,255,0.35)',
              borderRadius: 1,
            }}
          />
          {/* Score fill */}
          <div
            style={{
              height: '100%',
              width: `${finalPct}%`,
              background: gateColor,
              borderRadius: 3,
              boxShadow: `0 0 8px ${gateColor}60`,
              transition: 'width 0.5s ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em' }}>0.0</span>
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em', position: 'relative', left: `${thresholdPct - 50}%` }}>
            ↑ {confidence.threshold.toFixed(2)}
          </span>
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em' }}>1.0</span>
        </div>
      </div>

      {/* Component breakdown */}
      {confidence.components && (
        <div>
          <div style={{ fontSize: 9, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.25)', marginBottom: 8, fontWeight: 700 }}>
            COMPONENT BREAKDOWN
          </div>
          <ConfidenceBar label="M · TOP SCORE (cosine)" value={confidence.components.M} color="#22d3ee" />
          <ConfidenceBar label="S · MARGIN (ambiguity)" value={confidence.components.S} color="#8b5cf6" />
          <ConfidenceBar label="E · EMBEDDING ALIGNMENT" value={confidence.components.E} color="#10b981" />
          <ConfidenceBar label="C · COVERAGE RATIO" value={confidence.components.C} color="#f59e0b" />
        </div>
      )}

      {/* Block reason */}
      {!confidence.gate_pass && confidence.block_reason && (
        <div
          style={{
            marginTop: 10,
            padding: '8px 10px',
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: 4,
          }}
        >
          <div style={{ fontSize: 9, letterSpacing: '0.12em', color: '#ef4444', fontWeight: 700, marginBottom: 3 }}>
            BLOCK REASON
          </div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)', fontFamily: 'monospace' }}>
            {confidence.block_reason}
          </div>
        </div>
      )}

      {/* Diagnostics */}
      {confidence.diagnostics && Object.keys(confidence.diagnostics).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.2)', marginBottom: 4, fontWeight: 700 }}>
            DIAGNOSTICS
          </div>
          {Object.entries(confidence.diagnostics).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>{k}</span>
              <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>{String(v)}</span>
            </div>
          ))}
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
