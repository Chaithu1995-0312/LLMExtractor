import { memo, useMemo } from 'react';
import { Handle, Position } from 'reactflow';

export const NexusNode = memo(({ data }: any) => {
  const isSuperseded = data.status === 'SUPERSEDED';
  const isFrozen = data.status === 'FROZEN';

  const statusOverlay = isSuperseded ? "opacity-40 grayscale sepia-[.2]" : "";
  const borderGlow = data.selected 
    ? "border-primary shadow-[0_0_20px_-5px_rgba(59,130,246,0.5)] node-active" 
    : "border-white/10";

  return (
    <div className={`nexus-node-glow relative rounded-lg border-2 p-4 glass-panel transition-all duration-500 ${statusOverlay} ${borderGlow}`}>
      {/* Visual indicator for 'Source' connectivity */}
      <div className="absolute -top-2 -left-2 w-4 h-4 rounded-full bg-background border border-border flex items-center justify-center z-10">
        <div className={`w-1.5 h-1.5 rounded-full ${isFrozen ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]'}`} />
      </div>

      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-primary border-none" />
      
      <div className="space-y-2 min-w-[140px]">
        <header className="flex justify-between items-center opacity-50 uppercase tracking-tighter text-[10px] font-bold font-mono-data">
          <span>{data.type}</span>
          <span>{data.id.slice(0, 8)}</span>
        </header>
        <p className="text-sm leading-relaxed font-medium text-white/90">{data.label}</p>
        
        {isSuperseded && (
          <div className="mt-2 text-[8px] uppercase tracking-[0.2em] text-red-500/60 font-bold">
            Superseded
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-primary border-none" />
    </div>
  );
});

NexusNode.displayName = 'NexusNode';
