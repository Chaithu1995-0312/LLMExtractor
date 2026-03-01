import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { RouteSelected } from '../../types/controlPlane';

export default function AdvancedControls() {
  const { advancedOpen, toggleAdvanced, overrides, setOverrides } = useControlPlaneStore();

  return (
    <div>
      {/* Toggle row */}
      <button
        onClick={toggleAdvanced}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '4px 0',
          color: advancedOpen ? '#22d3ee' : 'rgba(255,255,255,0.3)',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.18em',
          transition: 'color 0.15s',
        }}
      >
        <span>{advancedOpen ? '▼' : '▶'}</span>
        ADVANCED CONTROLS
        {(overrides.force_route || overrides.disable_escalation || (overrides.threshold_override && overrides.threshold_override > 0)) && (
          <span
            style={{
              fontSize: 8,
              background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.35)',
              color: '#f59e0b',
              padding: '1px 6px',
              borderRadius: 3,
              letterSpacing: '0.1em',
            }}
          >
            OVERRIDE ACTIVE
          </span>
        )}
      </button>

      {advancedOpen && (
        <div
          style={{
            marginTop: 8,
            padding: '14px 16px',
            background: 'rgba(245,158,11,0.04)',
            border: '1px solid rgba(245,158,11,0.15)',
            borderRadius: 6,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 16,
            alignItems: 'flex-end',
          }}
        >
          {/* Force Route */}
          <ControlGroup label="FORCE ROUTE">
            <div style={{ display: 'flex', gap: 4 }}>
              {(['', 'graph', 'memory', 'hybrid'] as Array<RouteSelected | ''>) .map((v) => {
                const active = (overrides.force_route ?? '') === v;
                return (
                  <button
                    key={v || 'auto'}
                    onClick={() => setOverrides({ force_route: v || undefined })}
                    style={{
                      padding: '4px 10px',
                      fontSize: 9,
                      fontWeight: 700,
                      letterSpacing: '0.1em',
                      borderRadius: 3,
                      border: active ? '1px solid rgba(34,211,238,0.6)' : '1px solid rgba(255,255,255,0.1)',
                      background: active ? 'rgba(34,211,238,0.12)' : 'rgba(255,255,255,0.03)',
                      color: active ? '#22d3ee' : 'rgba(255,255,255,0.4)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {v ? v.toUpperCase() : 'AUTO'}
                  </button>
                );
              })}
            </div>
          </ControlGroup>

          {/* Disable Escalation */}
          <ControlGroup label="ESCALATION">
            <button
              onClick={() =>
                setOverrides({ disable_escalation: !overrides.disable_escalation })
              }
              style={{
                padding: '4px 12px',
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.1em',
                borderRadius: 3,
                border: overrides.disable_escalation
                  ? '1px solid rgba(239,68,68,0.5)'
                  : '1px solid rgba(255,255,255,0.1)',
                background: overrides.disable_escalation
                  ? 'rgba(239,68,68,0.1)'
                  : 'rgba(255,255,255,0.03)',
                color: overrides.disable_escalation ? '#ef4444' : 'rgba(255,255,255,0.4)',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {overrides.disable_escalation ? 'DISABLED' : 'ENABLED'}
            </button>
          </ControlGroup>

          {/* Confidence Threshold Slider */}
          <ControlGroup label={`CONFIDENCE THRESHOLD ${overrides.threshold_override ? `· ${overrides.threshold_override.toFixed(2)}` : '· DEFAULT (0.40)'}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={overrides.threshold_override ?? 0.4}
                onChange={(e) =>
                  setOverrides({ threshold_override: parseFloat(e.target.value) })
                }
                style={{
                  width: 140,
                  accentColor: '#22d3ee',
                  cursor: 'pointer',
                }}
              />
              <button
                onClick={() => setOverrides({ threshold_override: undefined })}
                style={{
                  fontSize: 8,
                  padding: '2px 7px',
                  borderRadius: 2,
                  border: '1px solid rgba(255,255,255,0.1)',
                  background: 'rgba(255,255,255,0.03)',
                  color: 'rgba(255,255,255,0.3)',
                  cursor: 'pointer',
                  letterSpacing: '0.1em',
                }}
              >
                RESET
              </button>
            </div>
          </ControlGroup>

          {/* Reset all overrides */}
          <button
            onClick={() => setOverrides({ force_route: undefined, disable_escalation: false, threshold_override: undefined })}
            style={{
              padding: '5px 14px',
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.12em',
              borderRadius: 3,
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.04)',
              color: 'rgba(255,255,255,0.4)',
              cursor: 'pointer',
              marginLeft: 'auto',
            }}
          >
            CLEAR ALL OVERRIDES
          </button>
        </div>
      )}
    </div>
  );
}

function ControlGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 8, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.3)', fontWeight: 700, marginBottom: 5 }}>
        {label}
      </div>
      {children}
    </div>
  );
}
