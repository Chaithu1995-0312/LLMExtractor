import React from "react";
import { ChevronRight, Skull, ShieldCheck, ShieldAlert } from "lucide-react";
import type { Lifecycle } from "../protocol/event-types";
import { validateMutationSync } from "../protocol/validators";

interface ControlStripProps {
  lifecycle: Lifecycle;
  onAction: (action: "promote" | "kill" | "freeze") => void;
  isUpdating?: boolean;
}

export const ControlStrip: React.FC<ControlStripProps> = ({
  lifecycle,
  onAction,
  isUpdating,
}) => {
  // ─── Pre-check governance policy synchronously at render time ──
  // This shows/hides buttons based on policy without needing async.
  const canPromote = validateMutationSync(lifecycle, 'promote').allowed;
  const canKill = validateMutationSync(lifecycle, 'kill').allowed;

  // Fully immutable states — show read-only badge
  if (lifecycle === 'KILLED' || lifecycle === 'SUPERSEDED' || lifecycle === 'FROZEN') {
    const badgeMap: Record<string, { text: string; color: string }> = {
      KILLED: { text: 'TERMINATED', color: 'text-red-400' },
      SUPERSEDED: { text: 'SUPERSEDED (Archived)', color: 'text-indigo-400' },
      FROZEN: { text: 'FROZEN (Immutable)', color: 'text-emerald-400' },
    };
    const badge = badgeMap[lifecycle];

    // FROZEN nodes can still be superseded — show that option
    if (lifecycle === 'FROZEN') {
      return (
        <div className="p-4 bg-black/80 backdrop-blur-xl border-t border-white/10 flex gap-3 items-stretch h-20">
          <div className="flex-1 flex items-center gap-3 px-4 rounded-md border border-emerald-500/20 bg-emerald-950/20">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <div>
              <div className="text-xs font-bold text-emerald-400 uppercase tracking-widest">FROZEN</div>
              <div className="text-[9px] text-emerald-400/60 font-mono">Node is immutable. Use Node Controller to supersede.</div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="p-4 bg-black/40 border-t border-white/5 text-center">
        <span className={`text-[10px] font-mono uppercase tracking-widest ${badge.color}`}>
          STATUS: {badge.text} (ReadOnly)
        </span>
      </div>
    );
  }

  // Define the primary action based on current state
  const isLoose = lifecycle === 'LOOSE';
  const primaryAction = isLoose ? "promote" : "freeze";
  const primaryText = isLoose ? "Promote to FORMING" : "Promote to FROZEN";
  const primaryColor = isLoose
    ? "bg-amber-600 hover:bg-amber-500"
    : "bg-blue-600 hover:bg-blue-500 shadow-[0_0_15px_rgba(37,99,235,0.5)]";

  return (
    <div className="p-4 bg-black/80 backdrop-blur-xl border-t border-white/10 flex gap-3 items-stretch h-20">

      {/* Primary Promote Button — only rendered if policy allows */}
      {canPromote ? (
        <button
          onClick={() => onAction(primaryAction)}
          disabled={isUpdating}
          className={`flex-1 relative overflow-hidden group rounded-md border border-white/10 transition-all ${primaryColor}`}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
          <div className="flex items-center justify-center gap-2 h-full">
            <ShieldCheck className="w-5 h-5 text-white" />
            <div className="text-left">
              <div className="text-xs font-bold text-white uppercase tracking-widest">
                {primaryText}
              </div>
              <div className="text-[9px] text-white/60 font-mono">CONFIDENCE THRESHOLD MET</div>
            </div>
          </div>
        </button>
      ) : (
        // Policy-blocked promote — show disabled state with reason
        <div className="flex-1 flex items-center gap-3 px-4 rounded-md border border-white/5 bg-white/5 opacity-50 cursor-not-allowed">
          <ShieldAlert className="w-4 h-4 text-white/30" />
          <div className="text-[9px] text-white/30 font-mono uppercase tracking-wider">
            Promote blocked by governance policy
          </div>
        </div>
      )}

      {/* Kill Button — only rendered if policy allows */}
      {canKill && (
        <button
          onClick={() => onAction("kill")}
          disabled={isUpdating}
          className="w-32 bg-red-950/40 border border-red-900/50 hover:bg-red-900/60 rounded-md flex flex-col items-center justify-center gap-1 group transition-all"
        >
          <Skull className="w-4 h-4 text-red-500 group-hover:scale-110 transition-transform" />
          <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">
            Kill Idea
          </span>
        </button>
      )}
    </div>
  );
};
