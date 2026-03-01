import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { TimelineStatus } from '../../types/controlPlane';

const STATUS_CONFIG: Record<TimelineStatus, { color: string; icon: string }> = {
  complete: { color: '#10b981', icon: '✓' },
  failed: { color: '#ef4444', icon: '✗' },
  warn: { color: '#f59e0b', icon: '⚠' },
  blocked: { color: '#6b7280', icon: '⊘' },
};

const STEP_LABELS: Record<string, string> = {
  classified: 'Query Classified',
  graph_retrieved: 'Graph Retrieved',
  memory_retrieved: 'Memory Retrieved',
  confidence_evaluated: 'Confidence Evaluated',
  hybrid_conflict_detected: 'Hybrid Conflict',
  escalated: 'L3 Escalated',
  escalation_skipped: 'Escalation Skipped',
  generated: 'Response Generated',
};

export default function ExecutionTimeline() {
  const { result, loading } = useControlPlaneStore();

  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.6)', fontWeight: 700 }}>
          EXECUTION TIMELINE
        </span>
        {result && (
          <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
            {result.elapsed_ms}ms
          </span>
        )}
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {['Classifying', 'Retrieving', 'Evaluating'].map((s) => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 9, color: '#22d3ee', animation: 'pulse 1.5s infinite' }}>◌</span>
              <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }}>{s}…</span>
            </div>
          ))}
        </div>
      )}

      {!loading && !result && (
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', textAlign: 'center', paddingTop: 16 }}>
          AWAITING QUERY EXECUTION
        </div>
      )}

      {!loading && result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {result.timeline.map((step, i) => {
            const cfg = STATUS_CONFIG[step.status] ?? STATUS_CONFIG.complete;
            const label = STEP_LABELS[step.step] ?? step.step.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
            const isLast = i === result.timeline.length - 1;

            return (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                {/* Connector line + icon */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 18 }}>
                  <div
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      background: `${cfg.color}18`,
                      border: `1px solid ${cfg.color}60`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 9,
                      color: cfg.color,
                      flexShrink: 0,
                    }}
                  >
                    {cfg.icon}
                  </div>
                  {!isLast && (
                    <div style={{ width: 1, flex: 1, minHeight: 8, background: 'rgba(255,255,255,0.08)', marginTop: 2, marginBottom: 2 }} />
                  )}
                </div>

                {/* Content */}
                <div style={{ paddingBottom: isLast ? 0 : 6, flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.7)', letterSpacing: '0.04em' }}>
                      {label}
                    </span>
                    <span
                      style={{
                        fontSize: 8,
                        fontWeight: 700,
                        letterSpacing: '0.12em',
                        color: cfg.color,
                        background: `${cfg.color}12`,
                        padding: '1px 5px',
                        borderRadius: 2,
                      }}
                    >
                      {step.status.toUpperCase()}
                    </span>
                  </div>
                  {step.detail && (
                    <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace', marginTop: 1 }}>
                      {step.detail}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  background: 'rgba(4,8,13,0.95)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 6,
  padding: '14px 16px',
};
