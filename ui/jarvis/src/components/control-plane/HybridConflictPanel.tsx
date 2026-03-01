import { useControlPlaneStore } from '../../store/controlPlaneStore';

export default function HybridConflictPanel() {
  const { result } = useControlPlaneStore();

  if (!result) return null;

  const { hybrid_conflict, route } = result;

  // Only show when hybrid was attempted or conflict detected
  if (!route.hybrid_used && !hybrid_conflict.detected) return null;

  const conflictColor = hybrid_conflict.detected ? '#ef4444' : '#10b981';
  const deltaWidth = Math.min(hybrid_conflict.delta * 100 * 6, 100); // scale for visual

  return (
    <div
      style={{
        background: hybrid_conflict.detected ? 'rgba(239,68,68,0.06)' : 'rgba(4,8,13,0.95)',
        border: `1px solid ${hybrid_conflict.detected ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.07)'}`,
        borderRadius: 6,
        padding: '14px 16px',
      }}
    >
      <div style={{ marginBottom: 12, paddingBottom: 8, borderBottom: `1px solid ${hybrid_conflict.detected ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.06)'}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: conflictColor, fontWeight: 700 }}>
          HYBRID CONFLICT
        </span>
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: conflictColor,
            background: `${conflictColor}12`,
            padding: '2px 7px',
            borderRadius: 3,
            border: `1px solid ${conflictColor}30`,
          }}
        >
          {hybrid_conflict.detected ? 'CONFLICT DETECTED' : 'RESOLVED'}
        </span>
      </div>

      {/* Graph vs Memory confidence bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <SourceBar
          label="GRAPH CONFIDENCE"
          value={hybrid_conflict.graph_conf}
          color="#22d3ee"
          dominant={hybrid_conflict.dominant === 'graph'}
        />
        <SourceBar
          label="MEMORY CONFIDENCE"
          value={hybrid_conflict.memory_conf}
          color="#8b5cf6"
          dominant={hybrid_conflict.dominant === 'memory'}
        />
      </div>

      {/* Delta */}
      <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.35)', fontWeight: 700 }}>
          DELTA
        </span>
        <div style={{ flex: 1, margin: '0 10px', height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${deltaWidth}%`,
              background: conflictColor,
              borderRadius: 2,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: conflictColor, fontWeight: 700 }}>
          {hybrid_conflict.delta.toFixed(3)}
        </span>
      </div>

      {/* Threshold note */}
      <div style={{ marginTop: 6, fontSize: 9, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.08em' }}>
        Conflict threshold: 0.150 · {hybrid_conflict.detected ? 'L3 escalation recommended' : 'Within tolerance'}
      </div>

      {/* Recommendation banner */}
      {hybrid_conflict.detected && hybrid_conflict.recommendation && (
        <div
          style={{
            marginTop: 10,
            padding: '6px 10px',
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 4,
            fontSize: 9,
            color: '#ef4444',
            letterSpacing: '0.1em',
            fontWeight: 700,
          }}
        >
          ⚠ {hybrid_conflict.recommendation.replace(/_/g, ' ').toUpperCase()}
        </div>
      )}
    </div>
  );
}

function SourceBar({
  label,
  value,
  color,
  dominant,
}: {
  label: string;
  value: number;
  color: string;
  dominant: boolean;
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.4)', fontWeight: 700 }}>
            {label}
          </span>
          {dominant && (
            <span
              style={{
                fontSize: 8,
                fontWeight: 700,
                color: '#10b981',
                background: 'rgba(16,185,129,0.12)',
                padding: '1px 5px',
                borderRadius: 2,
                letterSpacing: '0.1em',
              }}
            >
              DOMINANT
            </span>
          )}
        </div>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color, fontWeight: 700 }}>
          {value.toFixed(3)}
        </span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${Math.round(value * 100)}%`,
            background: color,
            borderRadius: 2,
            boxShadow: `0 0 6px ${color}60`,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
    </div>
  );
}
