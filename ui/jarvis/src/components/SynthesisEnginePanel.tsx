// ============================================================
//  SynthesisEnginePanel — Bottom-center: batch processing status
// ============================================================

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Square, Loader } from 'lucide-react';
import { useSystemStore } from '../state/system-store';
import { useGraphStore } from '../state/graph-store';

// Animated 3D sphere using nested SVG circles
function CognitiveSphere({ active }: { active: boolean }) {
  return (
    <div className="relative flex items-center justify-center" style={{ width: 64, height: 64 }}>
      {/* Outer glow */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: active
            ? 'radial-gradient(circle, rgba(34,211,238,0.3) 0%, transparent 70%)'
            : 'radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%)',
          animation: active ? 'pulse 2s ease-in-out infinite' : 'none',
        }}
      />
      <svg width="56" height="56" viewBox="0 0 56 56">
        <defs>
          <radialGradient id="sphere-grad" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stopColor={active ? '#67e8f9' : '#475569'} />
            <stop offset="60%" stopColor={active ? '#0891b2' : '#1e293b'} />
            <stop offset="100%" stopColor={active ? '#0c4a6e' : '#0f172a'} />
          </radialGradient>
          <filter id="sphere-shadow">
            <feDropShadow
              dx="0"
              dy="0"
              stdDeviation={active ? '4' : '2'}
              floodColor={active ? '#22d3ee' : '#000'}
              floodOpacity={active ? '0.6' : '0.3'}
            />
          </filter>
        </defs>
        {/* Main sphere */}
        <circle cx="28" cy="28" r="24" fill="url(#sphere-grad)" filter="url(#sphere-shadow)" />
        {/* Wireframe lines */}
        {[0, 45, 90, 135].map((angle) => (
          <ellipse
            key={angle}
            cx="28"
            cy="28"
            rx="24"
            ry="10"
            fill="none"
            stroke={active ? 'rgba(34,211,238,0.25)' : 'rgba(255,255,255,0.06)'}
            strokeWidth="0.8"
            transform={`rotate(${angle}, 28, 28)`}
            style={{ animation: active ? `holo-spin1 ${4 + angle / 45}s linear infinite` : 'none' }}
          />
        ))}
        {/* Highlight */}
        <ellipse cx="22" cy="20" rx="8" ry="5" fill="rgba(255,255,255,0.12)" />
      </svg>
    </div>
  );
}

export function SynthesisEnginePanel() {
  const { cognitivePhase, isProcessing } = useSystemStore();
  // Use scalar selectors to avoid infinite re-renders from new array references
  const nodeCount = useGraphStore((s) => Object.keys(s.nodes).length);
  const edgeCount = useGraphStore((s) => Object.keys(s.edges).length);
  const conflictCount = useGraphStore((s) =>
    Object.values(s.nodes).filter((n) => n.lifecycle === 'LOOSE').length
  );
  const [isStopped, setIsStopped] = useState(false);

  const isActive = isProcessing && !isStopped;

  return (
    <div
      className="flex flex-col h-full border-r border-t overflow-hidden"
      style={{
        background: 'rgba(3,6,10,0.95)',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[0.2em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Synthesis Engine
        </span>
        <div
          className="w-3 h-3 rounded-full"
          style={{
            background: isActive ? '#ef4444' : 'rgba(255,255,255,0.1)',
            boxShadow: isActive ? '0 0 6px rgba(239,68,68,0.6)' : 'none',
          }}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center gap-3 px-4 py-2">
        {/* Sphere + status text */}
        <CognitiveSphere active={isActive} />

        <AnimatePresence mode="wait">
          <motion.p
            key={cognitivePhase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-[10px] font-bold"
            style={{
              color: isActive ? '#22d3ee' : 'rgba(255,255,255,0.3)',
              textShadow: isActive ? '0 0 8px rgba(34,211,238,0.5)' : 'none',
              letterSpacing: '0.1em',
            }}
          >
            {isActive ? `${cognitivePhase}...` : 'Batch processing...'}
          </motion.p>
        </AnimatePresence>

        {/* Stats row */}
        <div className="flex items-center gap-3 w-full justify-center">
          {[
            { label: 'Nodes', value: nodeCount, color: 'rgba(255,255,255,0.7)' },
            { label: 'Edges', value: edgeCount, color: 'rgba(255,255,255,0.7)' },
            { label: 'Conflicts', value: conflictCount, color: conflictCount > 0 ? '#f87171' : 'rgba(255,255,255,0.4)' },
          ].map(({ label, value, color }) => (
            <div key={label} className="flex flex-col items-center">
              <span
                className="text-xl font-black font-mono leading-none"
                style={{
                  color,
                  textShadow: label === 'Conflicts' && conflictCount > 0
                    ? '0 0 10px rgba(248,113,113,0.6)'
                    : 'none',
                }}
              >
                {value}
              </span>
              <span
                className="text-[8px] font-bold uppercase tracking-wider mt-0.5"
                style={{ color: 'rgba(255,255,255,0.25)' }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* STOP button */}
        <button
          onClick={() => setIsStopped((v) => !v)}
          className="flex items-center gap-2 px-5 py-2 rounded font-bold uppercase transition-all"
          style={{
            fontSize: 10,
            letterSpacing: '0.2em',
            background: isStopped
              ? 'rgba(34,211,238,0.08)'
              : 'rgba(239,68,68,0.12)',
            border: `1px solid ${isStopped ? 'rgba(34,211,238,0.3)' : 'rgba(239,68,68,0.4)'}`,
            color: isStopped ? '#22d3ee' : '#f87171',
            boxShadow: isStopped
              ? '0 0 8px rgba(34,211,238,0.1)'
              : '0 0 8px rgba(239,68,68,0.2)',
          }}
        >
          {isStopped ? (
            <><Loader style={{ width: 11, height: 11 }} /> RESUME</>
          ) : (
            <><Square style={{ width: 11, height: 11 }} /> STOP</>
          )}
        </button>
      </div>
    </div>
  );
}
