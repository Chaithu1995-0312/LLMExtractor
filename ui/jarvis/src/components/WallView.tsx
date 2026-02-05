import React, { useMemo, useState } from "react";
import { NexusNode, NexusNodeProps, Lifecycle } from "./NexusNode";

interface WallViewProps {
  bricks: NexusNodeProps[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const lifecycleRank: Record<Lifecycle, number> = {
  FROZEN: 0,
  FORMING: 1,
  LOOSE: 2,
  KILLED: 3,
};

const lifecycleZ: Record<Lifecycle, number> = {
  FROZEN: 0,
  FORMING: -40,
  LOOSE: -80,
  KILLED: -140,
};

const lifecycleOpacity: Record<Lifecycle, number> = {
  FROZEN: 1,
  FORMING: 0.9,
  LOOSE: 0.8,
  KILLED: 0.5,
};

export function orderBricks(bricks: NexusNodeProps[]): NexusNodeProps[] {
  return [...bricks].sort((a, b) => {
    const r = lifecycleRank[a.lifecycle] - lifecycleRank[b.lifecycle];
    if (r !== 0) return r;
    // tie-breaker: confidence (higher first)
    return b.confidence - a.confidence;
  });
}

export const WallView: React.FC<WallViewProps> = ({ bricks, selectedId, onSelect }) => {
  const [killedExpanded, setKilledExpanded] = useState(false);

  // Filter and Sort
  const { visibleBricks, killedBricks } = useMemo(() => {
    const sorted = orderBricks(bricks);
    const killed = sorted.filter(b => b.lifecycle === 'KILLED');
    const visible = sorted.filter(b => b.lifecycle !== 'KILLED');
    return { visibleBricks: visible, killedBricks: killed };
  }, [bricks]);

  return (
    <div 
      className="w-full h-full overflow-y-auto overflow-x-hidden p-8"
      style={{ perspective: '1000px' }}
    >
      <div 
        className="w-full max-w-4xl mx-auto space-y-4"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Active Wall (Frozen, Forming, Loose) */}
        {visibleBricks.map((brick) => (
          <div
            key={brick.id}
            style={{
              transform: `translateZ(${lifecycleZ[brick.lifecycle]}px)`,
              opacity: lifecycleOpacity[brick.lifecycle],
              transition: 'transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.5s',
            }}
          >
            <NexusNode
              {...brick}
              isFocused={brick.id === selectedId}
              onSelect={onSelect}
            />
          </div>
        ))}

        {/* Cemetery (Killed) */}
        {killedBricks.length > 0 && (
          <div 
            className="mt-12 border-t border-white/10 pt-8"
            style={{ 
              transform: `translateZ(${lifecycleZ.KILLED}px)`,
              opacity: killedExpanded ? 1 : 0.6,
              transition: 'all 0.3s'
            }}
          >
            <button
              onClick={() => setKilledExpanded(!killedExpanded)}
              className="flex items-center gap-2 text-xs uppercase tracking-widest text-white/40 hover:text-white mb-4 transition-colors"
            >
              <span>☠ {killedBricks.length} Killed Ideas</span>
              <span>{killedExpanded ? '−' : '+'}</span>
            </button>

            {killedExpanded && (
              <div className="space-y-4 pl-4 border-l-2 border-red-900/30">
                {killedBricks.map((brick) => (
                  <NexusNode
                    key={brick.id}
                    {...brick}
                    isFocused={brick.id === selectedId}
                    onSelect={onSelect}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
