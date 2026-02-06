import React, { useMemo, useState } from "react";
import { NexusNode, NexusNodeProps } from "./NexusNode";

interface WallViewProps {
  bricks: NexusNodeProps[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export const WallView: React.FC<WallViewProps> = ({ bricks, selectedId, onSelect }) => {
  const [killedExpanded, setKilledExpanded] = useState(false);

  const { frozen, forming, loose, killed } = useMemo(() => {
    return {
      frozen: bricks.filter(b => b.lifecycle === 'FROZEN'),
      forming: bricks.filter(b => b.lifecycle === 'FORMING'),
      loose: bricks.filter(b => b.lifecycle === 'LOOSE'),
      killed: bricks.filter(b => b.lifecycle === 'KILLED'),
    };
  }, [bricks]);

  const Lane = ({ title, colorClass, data }: { title: string, colorClass: string, data: NexusNodeProps[] }) => (
    <div className="flex flex-col h-full min-w-full lg:min-w-[300px] flex-1 relative">
      <div className="mb-4 lg:mb-6 flex items-center gap-4">
        <h2 className={`text-base lg:text-lg font-bold tracking-widest uppercase ${colorClass} drop-shadow-md`}>{title}</h2>
        <div className={`h-[1px] flex-1 bg-gradient-to-r from-white/10 to-transparent`} />
        <span className="text-[10px] font-mono opacity-40">{data.length}</span>
      </div>
      
      <div className="flex-1 overflow-y-auto lg:pr-2 custom-scrollbar space-y-4 pb-10 lg:pb-20">
        {data.map(b => (
          <NexusNode key={b.id} {...b} isFocused={b.id === selectedId} onSelect={onSelect} />
        ))}
        {data.length === 0 && (
          <div className="p-6 border border-dashed border-white/10 rounded-lg text-center opacity-30 text-xs font-mono uppercase">
            No Data
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full w-full flex flex-col p-4 md:p-6 lg:p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#05080a] to-black overflow-y-auto lg:overflow-hidden">
      
      {/* Main Swimlanes - Stacked on mobile, 3-col on desktop */}
      <div className="flex-1 flex flex-col lg:grid lg:grid-cols-3 gap-8 lg:overflow-hidden">
        <Lane title="FROZEN" colorClass="text-emerald-400" data={frozen} />
        <Lane title="FORMING" colorClass="text-amber-400" data={forming} />
        <Lane title="LOOSE" colorClass="text-cyan-400" data={loose} />
      </div>

      {/* Killed Floor */}
      <div className="mt-8 lg:mt-4 relative group shrink-0">
        <div 
          onClick={() => setKilledExpanded(!killedExpanded)}
          className={`
            cursor-pointer border border-red-900/40 bg-red-950/20 rounded-md p-3 flex items-center gap-4 transition-all
            ${killedExpanded ? 'h-auto min-h-32 lg:h-48' : 'h-12 hover:bg-red-900/10'}
          `}
        >
          <div className="flex items-center gap-3">
             <div className="text-red-500">☠</div>
             <span className="text-red-500 font-bold uppercase tracking-widest text-[10px] lg:text-xs">{killed.length} Killed Ideas</span>
          </div>
          
          {!killedExpanded && <div className="h-[1px] flex-1 bg-red-900/30" />}

          {killedExpanded && (
             <div className="flex-1 overflow-x-auto lg:overflow-x-visible flex lg:grid lg:grid-cols-4 gap-4 p-2 h-full items-center">
                {killed.map(k => (
                  <div key={k.id} className="min-w-[200px] lg:min-w-0 opacity-70 hover:opacity-100">
                    <NexusNode {...k} isFocused={selectedId === k.id} onSelect={onSelect} />
                  </div>
                ))}
             </div>
          )}
        </div>
      </div>
    </div>
  );
};
