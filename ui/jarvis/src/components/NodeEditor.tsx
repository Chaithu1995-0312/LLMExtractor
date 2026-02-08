import React, { useState } from "react";
import { Lifecycle } from "./NexusNode";

interface NodeEditorProps {
  nodeId: string;
  currentLifecycle: Lifecycle;
  onUpdate: (nodeId: string, action: "promote" | "kill", data?: any) => void;
  onClose: () => void;
}

export const NodeEditor: React.FC<NodeEditorProps> = ({
  nodeId,
  currentLifecycle,
  onUpdate,
  onClose,
}) => {
  const [killReason, setKillReason] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const handlePromote = async () => {
    setIsUpdating(true);
    await onUpdate(nodeId, "promote");
    setIsUpdating(false);
  };

  const handleKill = async () => {
    if (!killReason) {
      alert("Please provide a reason for killing this node.");
      return;
    }
    setIsUpdating(true);
    await onUpdate(nodeId, "kill", { reason: killReason });
    setIsUpdating(false);
  };

  return (
    <div className="flex flex-col gap-6 p-6 bg-slate-900/90 border border-white/10 rounded-lg shadow-2xl backdrop-blur-md">
      <div className="flex justify-between items-center border-b border-white/5 pb-4">
        <h3 className="text-lg font-bold tracking-widest uppercase text-white/90">
          Node Controller
        </h3>
        <button 
          onClick={onClose}
          className="text-white/40 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40">Selected Node ID</span>
        <code className="text-xs font-mono text-cyan-400 bg-black/40 p-2 rounded border border-white/5">
          {nodeId}
        </code>
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40">Current State</span>
        <span className={`text-xs font-bold px-2 py-1 rounded w-max border ${
          currentLifecycle === 'FROZEN' ? 'border-emerald-500/40 text-emerald-400' :
          currentLifecycle === 'FORMING' ? 'border-amber-500/40 text-amber-400' :
          currentLifecycle === 'LOOSE' ? 'border-cyan-500/40 text-cyan-400' :
          'border-red-500/40 text-red-400'
        }`}>
          {currentLifecycle}
        </span>
      </div>

      {currentLifecycle !== 'FROZEN' && currentLifecycle !== 'KILLED' && (
        <button
          disabled={isUpdating}
          onClick={handlePromote}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold py-3 rounded uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
        >
          {isUpdating ? "Promoting..." : "Promote to Frozen"}
        </button>
      )}

      {currentLifecycle !== 'KILLED' && (
        <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-white/40">Rejection Protocol</span>
          <textarea
            value={killReason}
            onChange={(e) => setKillReason(e.target.value)}
            placeholder="Enter reason for rejection..."
            className="bg-black/40 border border-white/10 rounded p-3 text-xs text-white/80 focus:border-red-500/50 outline-none h-20 resize-none font-mono"
          />
          <button
            disabled={isUpdating}
            onClick={handleKill}
            className="bg-red-900/40 hover:bg-red-800/60 border border-red-500/50 disabled:opacity-50 text-red-400 text-xs font-bold py-3 rounded uppercase tracking-widest transition-all"
          >
            {isUpdating ? "Killing..." : "Terminate Node"}
          </button>
        </div>
      )}

      <div className="text-[9px] uppercase tracking-[0.2em] text-white/20 italic text-center">
        Action will be logged in Phase 3 Audit Trace
      </div>
    </div>
  );
};
