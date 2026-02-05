import React from "react";
import { Lifecycle } from "./NexusNode";
import { ChevronRight, Skull, ShieldCheck } from "lucide-react";

interface ControlStripProps {
  lifecycle: Lifecycle;
  onAction: (action: 'promote' | 'kill' | 'freeze') => void;
  isUpdating?: boolean;
}

export const ControlStrip: React.FC<ControlStripProps> = ({ lifecycle, onAction, isUpdating }) => {
  
  if (lifecycle === 'KILLED' || lifecycle === 'FROZEN') {
     return (
       <div className="p-4 bg-black/40 border-t border-white/5 text-center text-xs text-white/30 font-mono uppercase tracking-widest">
         STATUS: {lifecycle} (ReadOnly)
       </div>
     )
  }

  // Define the primary action based on current state
  const isLoose = lifecycle === 'LOOSE';
  const primaryAction = isLoose ? 'promote' : 'freeze';
  const primaryText = isLoose ? 'Promote to FORMING' : 'Promote to FROZEN';
  const primaryColor = isLoose ? 'bg-amber-600 hover:bg-amber-500' : 'bg-blue-600 hover:bg-blue-500 shadow-[0_0_15px_rgba(37,99,235,0.5)]';

  return (
    <div className="p-4 bg-black/80 backdrop-blur-xl border-t border-white/10 flex gap-3 items-stretch h-20">
      
      {/* Big Promote Button */}
      <button 
        onClick={() => onAction(primaryAction)}
        disabled={isUpdating}
        className={`flex-1 relative overflow-hidden group rounded-md border border-white/10 transition-all ${primaryColor}`}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
        <div className="flex items-center justify-center gap-2 h-full">
           <ShieldCheck className="w-5 h-5 text-white" />
           <div className="text-left">
             <div className="text-xs font-bold text-white uppercase tracking-widest">{primaryText}</div>
             <div className="text-[9px] text-white/60 font-mono">CONFIDENCE THRESHOLD MET</div>
           </div>
        </div>
      </button>

      {/* Kill Button */}
      <button 
        onClick={() => onAction('kill')}
        disabled={isUpdating}
        className="w-32 bg-red-950/40 border border-red-900/50 hover:bg-red-900/60 rounded-md flex flex-col items-center justify-center gap-1 group transition-all"
      >
        <Skull className="w-4 h-4 text-red-500 group-hover:scale-110 transition-transform" />
        <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Kill Idea</span>
      </button>
    </div>
  );
};
