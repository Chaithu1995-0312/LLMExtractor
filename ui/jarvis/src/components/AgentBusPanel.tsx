// ============================================================
//  AgentBusPanel — Cognitive Engine FSM Visualizer
//  Shows the 5 cognitive sub-agents as process bars, driven
//  entirely by the system-store FSM state.
//  Zero polling — all state comes from the store.
// ============================================================

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, RefreshCw, BarChart3, Layers, Zap, CheckCircle2, Clock, Loader } from 'lucide-react';
import { useSystemStore } from '../state/system-store';
import type { CognitiveEngineState } from '../utils/fsm';

// ─── Agent definitions ────────────────────────────────────────
interface AgentDef {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
  activePhase: CognitiveEngineState[];
  accentColor: string;
  glowColor: string;
}

const AGENTS: AgentDef[] = [
  {
    id: 'sync',
    label: 'Sync Agent',
    description: 'Ingests raw conversation chunks',
    icon: RefreshCw,
    activePhase: ['SYNCING'],
    accentColor: 'text-blue-400',
    glowColor: 'shadow-[0_0_12px_rgba(59,130,246,0.6)]',
  },
  {
    id: 'compiler',
    label: 'Compiler Agent',
    description: 'Extracts bricks & resolves graph edges',
    icon: Layers,
    activePhase: ['COMPILING'],
    accentColor: 'text-amber-400',
    glowColor: 'shadow-[0_0_12px_rgba(251,191,36,0.6)]',
  },
  {
    id: 'synthesizer',
    label: 'Synthesizer Agent',
    description: 'Merges evidence, scores confidence',
    icon: BarChart3,
    activePhase: ['SYNTHESIZING'],
    accentColor: 'text-purple-400',
    glowColor: 'shadow-[0_0_12px_rgba(168,85,247,0.6)]',
  },
  {
    id: 'streamer',
    label: 'Stream Agent',
    description: 'Pushes real-time deltas to UI',
    icon: Zap,
    activePhase: ['STREAMING'],
    accentColor: 'text-emerald-400',
    glowColor: 'shadow-[0_0_12px_rgba(52,211,153,0.7)]',
  },
  {
    id: 'cognition',
    label: 'Cognition Core',
    description: 'DSPy modules & LLM reasoning',
    icon: Cpu,
    activePhase: ['SYNTHESIZING', 'COMPILING'],
    accentColor: 'text-cyan-400',
    glowColor: 'shadow-[0_0_12px_rgba(34,211,238,0.6)]',
  },
];

// ─── Phase → progress mapping ────────────────────────────────
const PHASE_PROGRESS: Record<CognitiveEngineState, number> = {
  IDLE:         0,
  SYNCING:      20,
  COMPILING:    45,
  SYNTHESIZING: 70,
  STREAMING:    95,
};

// ─── AgentRow ─────────────────────────────────────────────────
function AgentRow({
  agent,
  isActive,
  phase,
}: {
  agent: AgentDef;
  isActive: boolean;
  phase: CognitiveEngineState;
}) {
  const Icon = agent.icon;
  const progress = isActive ? PHASE_PROGRESS[phase] : 0;

  return (
    <div className={`flex items-center gap-6 flex-wrap p-3 rounded-lg border transition-all duration-500 ${
      isActive
        ? `border-white/20 bg-white/5 ${agent.glowColor}`
        : 'border-white/5 bg-transparent'
    }`}>
      {/* Agent header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`w-3.5 h-3.5 ${isActive ? agent.accentColor : 'text-white/20'} ${isActive ? 'animate-pulse' : ''}`} />
          <span className={`text-[10px] font-bold uppercase tracking-widest ${isActive ? 'text-white/90' : 'text-white/30'}`}>
            {agent.label}
          </span>
        </div>

        {/* Status pill */}
        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[8px] font-bold uppercase tracking-wider ${
          isActive
            ? `${agent.accentColor} border-current bg-current/10`
            : 'text-white/20 border-white/5'
        }`}>
          {isActive ? (
            <>
              <Loader className="w-2.5 h-2.5 animate-spin" />
              RUNNING
            </>
          ) : (
            <>
              <Clock className="w-2.5 h-2.5" />
              IDLE
            </>
          )}
        </div>
      </div>

      {/* Description */}
      <p className={`text-[9px] font-mono ${isActive ? 'text-white/40' : 'text-white/15'}`}>
        {agent.description}
      </p>

      {/* Progress track */}
      <div className="h-0.5 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${isActive ? 'bg-current' : 'bg-white/10'} ${isActive ? agent.accentColor.replace('text-', 'bg-') : ''}`}
          style={{ color: 'inherit' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.8, ease: 'easeInOut' }}
        />
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────
export function AgentBusPanel() {
  const { cognitivePhase, activeTopic, isProcessing } = useSystemStore();

  return (
    <div className="flex flex-col gap-2 bg-[#080b10] border border-white/10 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-cyan-400/60" />
          <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-white/40">
            Cognitive Engine
          </span>
        </div>

        {/* Current phase badge */}
        <AnimatePresence mode="wait">
          <motion.div
            key={cognitivePhase}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-[8px] font-bold uppercase tracking-widest ${
              isProcessing
                ? 'text-cyan-400 border-cyan-500/30 bg-cyan-950/30'
                : 'text-white/20 border-white/5'
            }`}
          >
            {isProcessing ? (
              <><Loader className="w-2.5 h-2.5 animate-spin" /> {cognitivePhase}</>
            ) : (
              <><CheckCircle2 className="w-2.5 h-2.5" /> IDLE</>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Active topic */}
      <AnimatePresence>
        {isProcessing && activeTopic && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 px-2 py-1 rounded bg-blue-950/20 border border-blue-500/20"
          >
            <span className="text-[8px] text-blue-400/60 uppercase tracking-wider font-mono shrink-0">TOPIC</span>
            <code className="text-[9px] text-blue-300 font-mono truncate">{activeTopic}</code>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Agent rows */}
      <div className="flex items-center gap-6 flex-wrap mt-1">
        {AGENTS.map((agent) => (
          <AgentRow
            key={agent.id}
            agent={agent}
            isActive={agent.activePhase.includes(cognitivePhase) && isProcessing}
            phase={cognitivePhase}
          />
        ))}
      </div>

      {/* Phase progress summary */}
      <div className="mt-2 pt-2 border-t border-white/5">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[8px] text-white/20 uppercase tracking-wider">Pipeline Progress</span>
          <span className="text-[8px] text-white/30 font-mono">
            {PHASE_PROGRESS[cognitivePhase]}%
          </span>
        </div>
        <div className="h-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-emerald-500 rounded-full"
            animate={{ width: `${PHASE_PROGRESS[cognitivePhase]}%` }}
            transition={{ duration: 1.2, ease: 'easeInOut' }}
          />
        </div>
      </div>
    </div>
  );
}
