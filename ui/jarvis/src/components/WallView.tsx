import React, { useMemo, useState } from "react";
import { NexusNode, NexusNodeProps } from "./NexusNode";

interface WallViewProps {
  bricks: NexusNodeProps[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export const WallView: React.FC<WallViewProps> = ({ bricks, selectedId, onSelect }) => {
  const [activeTab, setActiveTab] = useState<'FROZEN' | 'FORMING' | 'LOOSE' | 'KILLED'>('FROZEN');

  const { frozen, forming, loose, killed } = useMemo(() => {
    return {
      frozen: bricks.filter(b => b.lifecycle === 'FROZEN'),
      forming: bricks.filter(b => b.lifecycle === 'FORMING'),
      loose: bricks.filter(b => b.lifecycle === 'LOOSE'),
      killed: bricks.filter(b => b.lifecycle === 'KILLED'),
    };
  }, [bricks]);

  const tabs = [
    { id: 'FROZEN', label: 'FROZEN', data: frozen, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: null },
    { id: 'FORMING', label: 'FORMING', data: forming, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', icon: null },
    { id: 'LOOSE', label: 'LOOSE', data: loose, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', icon: null },
    { id: 'KILLED', label: 'KILLED', data: killed, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: '☠' },
  ] as const;

  const currentTabData = useMemo(() => {
    return tabs.find(t => t.id === activeTab)?.data || [];
  }, [activeTab, frozen, forming, loose, killed]);

  const currentTabInfo = useMemo(() => {
    return tabs.find(t => t.id === activeTab)!;
  }, [activeTab]);

  return (
    <div className="h-full w-full flex flex-col p-4 md:p-6 lg:p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#05080a] to-black overflow-hidden">
      
      {/* Industrial Tab Navigation */}
      <div className="flex flex-wrap lg:flex-nowrap gap-2 lg:gap-4 mb-8 border-b border-white/5 pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`
              relative flex-1 min-w-[120px] lg:min-w-0 p-4 rounded-t-lg transition-all duration-300 group
              border-t border-x overflow-hidden
              ${activeTab === tab.id 
                ? `${tab.bg} ${tab.border} border-b-transparent translate-y-[1px]` 
                : 'border-transparent hover:bg-white/5 opacity-40 hover:opacity-70'
              }
            `}
          >
            {/* Background Glow Effect */}
            {activeTab === tab.id && (
              <div className={`absolute inset-0 opacity-20 blur-xl animate-pulse ${tab.bg}`} />
            )}

            <div className="relative z-10 flex flex-col items-center gap-1">
              <div className="flex items-center gap-2">
                {tab.icon && <span className={tab.color}>{tab.icon}</span>}
                <span className={`text-[10px] lg:text-xs font-bold tracking-[0.2em] uppercase ${tab.color}`}>
                  {tab.label}
                </span>
              </div>
              <span className="text-[10px] font-mono opacity-40">{tab.data.length}</span>
            </div>

            {/* Selection Indicator bar */}
            {activeTab === tab.id && (
              <div className={`absolute top-0 left-0 right-0 h-[2px] ${tab.color.replace('text-', 'bg-')}`} />
            )}
          </button>
        ))}
      </div>

      {/* Active Tab Content */}
      <div className="flex-1 flex flex-col relative overflow-hidden min-h-0">
        <div className="flex items-center gap-4 mb-4">
           <h2 className={`text-xl font-bold tracking-widest uppercase ${currentTabInfo.color} drop-shadow-md`}>
             {currentTabInfo.label} DATA
           </h2>
           <div className={`h-[1px] flex-1 bg-gradient-to-r from-white/10 to-transparent`} />
        </div>

        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar pb-10">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {currentTabData.map(b => (
              <NexusNode key={b.id} {...b} isFocused={b.id === selectedId} onSelect={onSelect} />
            ))}
          </div>
          
          {currentTabData.length === 0 && (
            <div className="p-12 border border-dashed border-white/10 rounded-xl text-center opacity-30 text-sm font-mono uppercase tracking-[0.3em]">
              Initialising Data Stream... No Bricks Found
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
