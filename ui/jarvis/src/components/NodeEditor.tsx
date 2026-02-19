import React, { useState } from "react";
import { ShieldAlert, AlertCircle } from "lucide-react";
import type { Lifecycle } from "../protocol/event-types";
import { validateMutation } from "../protocol/validators";

interface NodeEditorProps {
  nodeId: string;
  currentLifecycle: Lifecycle;
  onUpdate: (nodeId: string, action: "promote" | "kill" | "supersede", data?: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}

export const NodeEditor: React.FC<NodeEditorProps> = ({
  nodeId,
  currentLifecycle,
  onUpdate,
  onClose,
}) => {
  const [killReason, setKillReason] = useState("");
  const [supersedeReason, setSupersedeReason] = useState("");
  const [newNodeId, setNewNodeId] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  // ─── Policy-gated error state ─────────────────────────────
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policyGuardId, setPolicyGuardId] = useState<string | null>(null);

  function clearPolicyError() {
    setPolicyError(null);
    setPolicyGuardId(null);
  }

  // ─── Validate + dispatch helpers ─────────────────────────

  const handlePromote = async () => {
    clearPolicyError();

    // FSM governance check BEFORE API call
    const check = await validateMutation(currentLifecycle, 'promote');
    if (!check.allowed) {
      setPolicyError(check.error ?? 'Action blocked by governance policy.');
      setPolicyGuardId(check.guard_id ?? null);
      return;
    }

    setIsUpdating(true);
    try {
      await onUpdate(nodeId, "promote");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleKill = async () => {
    clearPolicyError();

    // FSM governance check BEFORE API call
    const check = await validateMutation(currentLifecycle, 'kill', { reason: killReason });
    if (!check.allowed) {
      setPolicyError(check.error ?? 'Action blocked by governance policy.');
      setPolicyGuardId(check.guard_id ?? null);
      return;
    }

    setIsUpdating(true);
    try {
      await onUpdate(nodeId, "kill", { reason: killReason });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleSupersede = async () => {
    clearPolicyError();

    // FSM governance check BEFORE API call
    const check = await validateMutation(currentLifecycle, 'supersede', {
      new_node_id: newNodeId,
      reason: supersedeReason,
    });
    if (!check.allowed) {
      setPolicyError(check.error ?? 'Action blocked by governance policy.');
      setPolicyGuardId(check.guard_id ?? null);
      return;
    }

    setIsUpdating(true);
    try {
      await onUpdate(nodeId, "supersede", { new_node_id: newNodeId, reason: supersedeReason });
    } finally {
      setIsUpdating(false);
    }
  };

  // ─── Lifecycle color map ──────────────────────────────────
  const lifecycleStyle: Record<Lifecycle, string> = {
    FROZEN: 'border-emerald-500/40 text-emerald-400',
    FORMING: 'border-amber-500/40 text-amber-400',
    LOOSE: 'border-cyan-500/40 text-cyan-400',
    KILLED: 'border-red-500/40 text-red-400',
    SUPERSEDED: 'border-indigo-500/40 text-indigo-400',
  };

  return (
    <div className="flex flex-col gap-6 p-6 bg-slate-900/90 border border-white/10 rounded-lg shadow-2xl backdrop-blur-md">
      
      {/* Header */}
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

      {/* Node ID */}
      <div className="flex flex-col gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40">Selected Node ID</span>
        <code className="text-xs font-mono text-cyan-400 bg-black/40 p-2 rounded border border-white/5 break-all">
          {nodeId}
        </code>
      </div>

      {/* Current State */}
      <div className="flex flex-col gap-2">
        <span className="text-[10px] uppercase tracking-widest text-white/40">Current State</span>
        <span className={`text-xs font-bold px-2 py-1 rounded w-max border ${lifecycleStyle[currentLifecycle]}`}>
          {currentLifecycle}
        </span>
      </div>

      {/* ── Policy Error Banner ─────────────────────────── */}
      {policyError && (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-red-950/40 border border-red-500/40">
          <ShieldAlert className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-red-400">
              Governance Policy Violation
            </span>
            <p className="text-xs text-red-300/80">{policyError}</p>
            {policyGuardId && (
              <code className="text-[9px] text-red-400/50 font-mono mt-1">
                guard: {policyGuardId}
              </code>
            )}
          </div>
        </div>
      )}

      {/* ── Immutable state notice ─────────────────────── */}
      {(currentLifecycle === 'KILLED' || currentLifecycle === 'SUPERSEDED') && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5 border border-white/10">
          <AlertCircle className="w-4 h-4 text-white/40" />
          <span className="text-xs text-white/40">
            This node is in an immutable state ({currentLifecycle}) and cannot be modified.
          </span>
        </div>
      )}

      {/* ── Action: Promote ──────────────────────────────── */}
      {currentLifecycle !== 'FROZEN' && currentLifecycle !== 'KILLED' && currentLifecycle !== 'SUPERSEDED' && (
        <button
          disabled={isUpdating}
          onClick={handlePromote}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold py-3 rounded uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
        >
          {isUpdating ? "Promoting..." : "Promote to Frozen"}
        </button>
      )}

      {/* ── Action: Supersede (Only for FROZEN) ─────────── */}
      {currentLifecycle === 'FROZEN' && (
        <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-white/40">
            Evolution Protocol (Supersede)
          </span>
          <input
            value={newNodeId}
            onChange={(e) => { setNewNodeId(e.target.value); clearPolicyError(); }}
            placeholder="Replacement Node ID (UUID)"
            className="bg-black/40 border border-white/10 rounded p-3 text-xs text-white/80 focus:border-blue-500/50 outline-none font-mono"
          />
          <textarea
            value={supersedeReason}
            onChange={(e) => { setSupersedeReason(e.target.value); clearPolicyError(); }}
            placeholder="Reason for supersession (min 10 chars)..."
            className="bg-black/40 border border-white/10 rounded p-3 text-xs text-white/80 focus:border-blue-500/50 outline-none h-20 resize-none font-mono"
          />
          <button
            disabled={isUpdating}
            onClick={handleSupersede}
            className="bg-blue-900/40 hover:bg-blue-800/60 border border-blue-500/50 disabled:opacity-50 text-blue-400 text-xs font-bold py-3 rounded uppercase tracking-widest transition-all"
          >
            {isUpdating ? "Processing..." : "Supersede Node"}
          </button>
        </div>
      )}

      {/* ── Action: Kill ─────────────────────────────────── */}
      {currentLifecycle !== 'KILLED' && currentLifecycle !== 'SUPERSEDED' && currentLifecycle !== 'FROZEN' && (
        <div className="flex flex-col gap-3 pt-4 border-t border-white/5">
          <span className="text-[10px] uppercase tracking-widest text-white/40">
            Rejection Protocol
          </span>
          <textarea
            value={killReason}
            onChange={(e) => { setKillReason(e.target.value); clearPolicyError(); }}
            placeholder="Enter reason for rejection (min 10 chars)..."
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

      {/* Footer */}
      <div className="text-[9px] uppercase tracking-[0.2em] text-white/20 italic text-center">
        All actions are validated against governance policy and logged in the audit trace
      </div>
    </div>
  );
};
