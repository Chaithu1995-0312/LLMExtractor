import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { RouteSelected } from '../../types/controlPlane';
import { ChevronDown, SlidersHorizontal, AlertTriangle, X } from 'lucide-react';

export default function AdvancedControls() {
  const { advancedOpen, toggleAdvanced, overrides, setOverrides } = useControlPlaneStore();
  const overrideActive = overrides.force_route || overrides.disable_escalation || (overrides.threshold_override && overrides.threshold_override > 0.4);

  return (
    <div className="bg-black/20 border border-white/5 rounded-lg">
      {/* Toggle row */}
      <button
        onClick={toggleAdvanced}
        className="flex items-center gap-2.5 w-full text-left p-3"
      >
        <ChevronDown
          size={16}
          className={`transition-transform duration-200 text-white/40 ${advancedOpen ? 'rotate-180' : ''}`}
        />
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={12} className="text-cyan-400" />
          <span className="font-bold text-xs tracking-widest text-white/60 group-hover:text-white">
            ADVANCED CONTROLS
          </span>
        </div>
        {overrideActive && (
          <div className="ml-auto flex items-center gap-1.5 text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
            <AlertTriangle size={10} />
            <span className="text-[9px] font-bold tracking-wider">OVERRIDE ACTIVE</span>
          </div>
        )}
      </button>

      {/* Collapsible content */}
      {advancedOpen && (
        <div className="p-4 border-t border-white/5 grid grid-cols-3 gap-6">
          {/* Force Route */}
          <ControlGroup label="FORCE ROUTE">
            <div className="flex gap-1.5">
              {(['', 'graph', 'memory', 'hybrid'] as Array<RouteSelected | ''>).map((v) => {
                const active = (overrides.force_route ?? '') === v;
                return (
                  <button
                    key={v || 'auto'}
                    onClick={() => setOverrides({ force_route: v || undefined })}
                    className={`px-3 py-1 text-[10px] font-bold tracking-wider rounded-md transition-all ${
                      active
                        ? 'bg-cyan-400/20 border-cyan-400/80 text-cyan-300'
                        : 'bg-white/5 border-transparent hover:bg-white/10 text-white/50'
                    }`}
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
              onClick={() => setOverrides({ disable_escalation: !overrides.disable_escalation })}
              className={`px-3 py-1 text-[10px] font-bold tracking-wider rounded-md transition-all ${
                overrides.disable_escalation
                  ? 'bg-red-500/20 border-red-500/80 text-red-400'
                  : 'bg-white/5 border-transparent hover:bg-white/10 text-white/50'
              }`}
            >
              {overrides.disable_escalation ? 'DISABLED' : 'ENABLED'}
            </button>
          </ControlGroup>

          {/* Confidence Threshold Slider */}
          <ControlGroup label={`CONFIDENCE THRESHOLD: ${overrides.threshold_override ? overrides.threshold_override.toFixed(2) : 'DEFAULT (0.40)'}`}>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={overrides.threshold_override ?? 0.4}
                onChange={(e) => setOverrides({ threshold_override: parseFloat(e.target.value) })}
                className="w-full h-1 bg-white/10 rounded-full appearance-none cursor-pointer accent-cyan-400"
              />
              <button
                onClick={() => setOverrides({ threshold_override: undefined })}
                className="text-white/30 hover:text-white"
              >
                <X size={12} />
              </button>
            </div>
          </ControlGroup>

          {/* Reset all overrides */}
          {overrideActive && (
            <div className="col-span-3 flex justify-end pt-2 border-t border-white/5">
              <button
                onClick={() => setOverrides({ force_route: undefined, disable_escalation: false, threshold_override: undefined })}
                className="px-3 py-1 text-[10px] font-bold tracking-wider rounded-md transition-all bg-amber-500/10 border border-amber-500/20 text-amber-400 hover:bg-amber-500/20"
              >
                CLEAR ALL OVERRIDES
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ControlGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[9px] tracking-widest text-white/40 font-semibold mb-2">{label}</div>
      {children}
    </div>
  );
}
