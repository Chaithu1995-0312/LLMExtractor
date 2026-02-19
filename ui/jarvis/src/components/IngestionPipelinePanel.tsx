// ============================================================
//  IngestionPipelinePanel — Left panel showing pipeline flow
//  Raw JSON → Tree Splitter → Compiler → Bricks → Graph Nodes
// ============================================================

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileJson, Scissors, Layers, Box, Network, PlayCircle, RefreshCw
} from 'lucide-react';

const PIPELINE_STEPS = [
  {
    icon: FileJson,
    label: 'Raw JSON',
    color: '#22d3ee',
    glow: 'rgba(34,211,238,0.4)',
    desc: 'Source conversations ingested',
  },
  {
    icon: Scissors,
    label: 'Tree Splitter',
    color: '#a78bfa',
    glow: 'rgba(167,139,250,0.4)',
    desc: 'Segment conversation trees',
  },
  {
    icon: Layers,
    label: 'Compiler',
    color: '#fbbf24',
    glow: 'rgba(251,191,36,0.4)',
    desc: 'Extract semantic bricks',
  },
  {
    icon: Box,
    label: 'Bricks',
    color: '#fb923c',
    glow: 'rgba(251,146,60,0.4)',
    desc: 'Structured knowledge atoms',
  },
  {
    icon: Network,
    label: 'Graph Nodes',
    color: '#34d399',
    glow: 'rgba(52,211,153,0.4)',
    desc: 'Lifecycle-managed intents',
  },
];

const STAGE_PROGRESS = [0, 25, 50, 75, 100];

interface IngestionPipelinePanelProps {
  onRunSync?: () => void;
  isSyncing?: boolean;
  currentStage?: number; // 0–4
}

export function IngestionPipelinePanel({
  onRunSync,
  isSyncing = false,
  currentStage = -1,
}: IngestionPipelinePanelProps) {
  const [hoveredStep, setHoveredStep] = useState<number | null>(null);

  return (
    <div
      className="flex flex-col h-full border-r"
      style={{
        background: 'rgba(4,8,14,0.9)',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[0.25em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          — Ingestion Pipeline —
        </span>
      </div>

      {/* Pipeline steps */}
      <div className="flex-1 flex flex-col items-center justify-center gap-0 px-4 py-4 overflow-hidden">
        {PIPELINE_STEPS.map((step, i) => {
          const Icon = step.icon;
          const isActive = i === currentStage;
          const isDone = i < currentStage;
          const isHovered = hoveredStep === i;

          return (
            <div key={step.label} className="flex flex-col items-center w-full">
              {/* Step node */}
              <motion.div
                className="flex flex-col items-center cursor-pointer w-full"
                onHoverStart={() => setHoveredStep(i)}
                onHoverEnd={() => setHoveredStep(null)}
                animate={isActive ? { scale: [1, 1.03, 1] } : { scale: 1 }}
                transition={isActive ? { repeat: Infinity, duration: 1.5 } : {}}
              >
                <div
                  className="flex items-center gap-3 w-full px-3 py-2 rounded-lg transition-all"
                  style={{
                    background:
                      isActive
                        ? `rgba(${step.glow.slice(5, -1)}, 0.15)`
                        : isHovered
                        ? 'rgba(255,255,255,0.03)'
                        : 'transparent',
                    border: `1px solid ${
                      isActive
                        ? step.color + '50'
                        : 'rgba(255,255,255,0.05)'
                    }`,
                    boxShadow: isActive
                      ? `0 0 12px ${step.glow}`
                      : 'none',
                  }}
                >
                  {/* Icon circle */}
                  <div
                    className="flex items-center justify-center rounded-lg shrink-0"
                    style={{
                      width: 36,
                      height: 36,
                      background: isActive
                        ? step.glow.replace('0.4', '0.2')
                        : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${
                        isActive || isDone
                          ? step.color + '60'
                          : 'rgba(255,255,255,0.08)'
                      }`,
                    }}
                  >
                    <Icon
                      style={{
                        width: 16,
                        height: 16,
                        color: isActive || isDone ? step.color : 'rgba(255,255,255,0.25)',
                        filter: isActive ? `drop-shadow(0 0 4px ${step.glow})` : 'none',
                      }}
                    />
                  </div>

                  {/* Label */}
                  <div className="flex flex-col min-w-0">
                    <span
                      className="text-[11px] font-bold"
                      style={{
                        color: isActive
                          ? step.color
                          : isDone
                          ? 'rgba(255,255,255,0.6)'
                          : 'rgba(255,255,255,0.3)',
                        textShadow: isActive ? `0 0 8px ${step.glow}` : 'none',
                      }}
                    >
                      {step.label}
                    </span>
                    {(isHovered || isActive) && (
                      <span
                        className="text-[9px] truncate"
                        style={{ color: 'rgba(255,255,255,0.3)' }}
                      >
                        {step.desc}
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>

              {/* Connector arrow (skip after last) */}
              {i < PIPELINE_STEPS.length - 1 && (
                <div
                  className="flex flex-col items-center my-1"
                  style={{ height: 18 }}
                >
                  <div
                    className="w-px flex-1 transition-all duration-300"
                    style={{
                      background:
                        i < currentStage
                          ? `linear-gradient(to bottom, ${step.color}80, ${PIPELINE_STEPS[i + 1].color}80)`
                          : 'rgba(255,255,255,0.08)',
                    }}
                  />
                  <div
                    className="text-[8px] font-bold"
                    style={{
                      color:
                        i < currentStage
                          ? step.color
                          : 'rgba(255,255,255,0.1)',
                    }}
                  >
                    ▼
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* RUN SYNC button */}
      <div className="px-4 pb-4 shrink-0">
        <button
          onClick={onRunSync}
          disabled={isSyncing}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-bold uppercase transition-all"
          style={{
            fontSize: 11,
            letterSpacing: '0.2em',
            background: isSyncing
              ? 'rgba(34,211,238,0.05)'
              : 'linear-gradient(135deg, rgba(34,211,238,0.15) 0%, rgba(59,130,246,0.15) 100%)',
            border: `1px solid ${isSyncing ? 'rgba(34,211,238,0.2)' : 'rgba(34,211,238,0.4)'}`,
            color: isSyncing ? 'rgba(34,211,238,0.5)' : '#22d3ee',
            boxShadow: isSyncing
              ? 'none'
              : '0 0 12px rgba(34,211,238,0.15), inset 0 0 8px rgba(34,211,238,0.05)',
          }}
        >
          {isSyncing ? (
            <RefreshCw style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} />
          ) : (
            <PlayCircle style={{ width: 14, height: 14 }} />
          )}
          {isSyncing ? 'SYNCING...' : 'RUN SYNC'}
        </button>

        {/* Pipeline status bar */}
        <div className="mt-3">
          <div
            className="text-[8px] font-bold uppercase tracking-widest mb-1.5"
            style={{ color: 'rgba(255,255,255,0.2)' }}
          >
            — Pipeline Status
          </div>
          <div className="flex items-center justify-between gap-1">
            {['Sync', 'Compile', 'Graph', 'Synthesis'].map((label, i) => (
              <div key={label} className="flex flex-col items-center gap-1">
                <div
                  className="rounded-full transition-all duration-500"
                  style={{
                    width: 6,
                    height: 6,
                    background:
                      i <= currentStage
                        ? PIPELINE_STEPS[Math.min(i, 4)].color
                        : 'rgba(255,255,255,0.1)',
                    boxShadow:
                      i <= currentStage
                        ? `0 0 6px ${PIPELINE_STEPS[Math.min(i, 4)].glow}`
                        : 'none',
                  }}
                />
                <span
                  className="text-[7px] font-bold uppercase"
                  style={{
                    color:
                      i <= currentStage
                        ? 'rgba(255,255,255,0.5)'
                        : 'rgba(255,255,255,0.15)',
                  }}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
