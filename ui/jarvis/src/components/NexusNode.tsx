import React from "react";

export type Lifecycle = "LOOSE" | "FORMING" | "FROZEN" | "KILLED";

export interface NexusNodeProps {
  id: string;
  title: string;
  summary: string;
  lifecycle: Lifecycle;
  confidence: number;
  sourceCount: number;
  lastUpdatedAt: string;
  isFocused: boolean;
  onSelect: (id: string) => void;
  chatName?: string;
  projectName?: string;
}

export const NexusNode: React.FC<NexusNodeProps> = ({
  id,
  title,
  summary,
  lifecycle,
  confidence,
  sourceCount,
  lastUpdatedAt,
  isFocused,
  onSelect,
  chatName,
  projectName,
}) => {
  
  // Visual Configuration based on Image
  const variants = {
    LOOSE: {
      wrapper: "border-cyan-500/30 bg-cyan-950/20 text-cyan-100 hover:border-cyan-400/60 hover:shadow-glow-loose",
      indicator: "bg-cyan-400",
      progress: "bg-cyan-500/30"
    },
    FORMING: {
      wrapper: "border-amber-500/40 bg-amber-950/20 text-amber-100 hover:border-amber-400/80 hover:shadow-glow-forming",
      indicator: "bg-amber-400",
      progress: "bg-amber-500/30"
    },
    FROZEN: {
      wrapper: "border-emerald-500/40 bg-emerald-950/20 text-emerald-100 hover:border-emerald-400/80 hover:shadow-glow-frozen",
      indicator: "bg-emerald-400",
      progress: "bg-emerald-500/30"
    },
    KILLED: {
      wrapper: "border-red-900/40 bg-red-950/20 text-red-300 opacity-60 grayscale-[0.5] hover:opacity-100 hover:grayscale-0",
      indicator: "bg-red-500",
      progress: "bg-red-900/30"
    }
  };

  const currentVar = variants[lifecycle];
  
  // Mocking the "dots" seen in the image for data density
  const dots = Array.from({ length: 6 }).map((_, i) => (
    <div key={i} className={`h-1 w-1 rounded-full ${i < confidence * 6 ? currentVar.indicator : 'bg-white/10'}`} />
  ));

  return (
    <div
      onClick={() => onSelect(id)}
      className={`
        relative group flex flex-col p-4 rounded-sm border transition-all duration-300 cursor-pointer select-none
        ${currentVar.wrapper}
        ${isFocused ? "ring-1 ring-white/50 scale-[1.02] z-10 !opacity-100 !grayscale-0" : ""}
      `}
    >
      {/* Top Decorator Line */}
      <div className={`absolute top-0 left-2 right-2 h-[1px] ${currentVar.indicator} opacity-50 shadow-[0_0_10px_currentColor]`} />

      <div className="flex flex-col gap-1 mb-3">
        {chatName && (
          <div className="text-[10px] font-bold tracking-widest opacity-40 uppercase truncate">
            {chatName}
          </div>
        )}
        <div className="flex justify-between items-start">
          <h3 className="font-bold text-sm tracking-wide leading-tight drop-shadow-md truncate">
            {title}
          </h3>
          <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] ${currentVar.indicator} shrink-0 ml-2`} />
        </div>
      </div>

      <p className="text-[11px] leading-relaxed opacity-80 mb-4 line-clamp-3 font-mono-data text-white/70">
        {summary}
      </p>

      {/* Footer / Telemetry */}
      <div className="mt-auto border-t border-white/5 pt-3 flex items-center justify-between text-[9px] uppercase tracking-widest font-mono-data opacity-70">
        <div className="flex flex-col gap-1">
          <span>sources : {sourceCount}</span>
          <span>updated : {lastUpdatedAt}</span>
        </div>
        
        {/* Visual Confidence Meter */}
        <div className="flex gap-1 items-center">
          {dots}
        </div>
      </div>
    </div>
  );
};
