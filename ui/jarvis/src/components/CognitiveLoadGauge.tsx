// ============================================================
//  CognitiveLoadGauge — SVG Circular Load Indicator
//  Displays a single metric as a neon-glow arc gauge.
//  Fully controlled — no internal state.
// ============================================================

import React from 'react';
import { motion } from 'framer-motion';

interface CognitiveLoadGaugeProps {
  /** Value 0–100 */
  value: number;
  /** Label under the gauge */
  label: string;
  /** Sub-label / unit string */
  sublabel?: string;
  /** Diameter in pixels (default 80) */
  size?: number;
  /** Colour scheme */
  variant?: 'cyan' | 'amber' | 'emerald' | 'red' | 'purple';
}

const VARIANT_COLORS = {
  cyan:    { stroke: '#22d3ee', glow: 'rgba(34,211,238,0.6)',  text: '#67e8f9' },
  amber:   { stroke: '#fbbf24', glow: 'rgba(251,191,36,0.6)',  text: '#fde68a' },
  emerald: { stroke: '#34d399', glow: 'rgba(52,211,153,0.6)',  text: '#6ee7b7' },
  red:     { stroke: '#f87171', glow: 'rgba(248,113,113,0.6)', text: '#fca5a5' },
  purple:  { stroke: '#a78bfa', glow: 'rgba(167,139,250,0.6)', text: '#c4b5fd' },
};

export const CognitiveLoadGauge: React.FC<CognitiveLoadGaugeProps> = ({
  value,
  label,
  sublabel,
  size = 80,
  variant = 'cyan',
}) => {
  const safeValue = Math.min(100, Math.max(0, value));
  const colors = VARIANT_COLORS[variant];

  // ─── Arc geometry ─────────────────────────────────────────
  const cx = size / 2;
  const cy = size / 2;
  const strokeWidth = size * 0.075; // ~6px for size=80
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;

  // We draw a 270° arc (from 135° to 405°)
  // 270° = 3/4 of full circle
  const arcFraction = 0.75; // 270° / 360°
  const arcLength = circumference * arcFraction;
  const dashOffset = arcLength - (safeValue / 100) * arcLength;

  // Rotation: start at 135° (lower-left)
  const startAngle = 135;

  // ─── Glow filter id (unique per instance) ─────────────────
  const filterId = `glow-${label.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
        >
          <defs>
            <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Track arc (background) */}
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform={`rotate(${startAngle}, ${cx}, ${cy})`}
          />

          {/* Value arc (animated) */}
          <motion.circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            transform={`rotate(${startAngle}, ${cx}, ${cy})`}
            filter={`url(#${filterId})`}
            initial={{ strokeDashoffset: arcLength }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.2, ease: 'easeInOut' }}
            style={{
              filter: `drop-shadow(0 0 4px ${colors.glow})`,
            }}
          />

          {/* Center: value text */}
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={size * 0.22}
            fontWeight="bold"
            fontFamily="monospace"
            fill={colors.text}
          >
            {Math.round(safeValue)}
          </text>

          {/* Center: percent symbol */}
          <text
            x={cx + size * 0.15}
            y={cy - size * 0.08}
            textAnchor="start"
            fontSize={size * 0.1}
            fontFamily="monospace"
            fill={colors.text}
            opacity={0.7}
          >
            %
          </text>
        </svg>
      </div>

      {/* Label */}
      <div className="text-center">
        <div
          className="font-bold uppercase tracking-widest"
          style={{
            fontSize: size * 0.11,
            color: colors.text,
            textShadow: `0 0 8px ${colors.glow}`,
          }}
        >
          {label}
        </div>
        {sublabel && (
          <div
            className="font-mono opacity-50"
            style={{ fontSize: size * 0.085, color: colors.text }}
          >
            {sublabel}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Gauge Row (multiple gauges in a horizontal strip) ─────
interface GaugeRowProps {
  gauges: Array<{
    value: number;
    label: string;
    sublabel?: string;
    variant?: CognitiveLoadGaugeProps['variant'];
  }>;
  size?: number;
}

export const GaugeRow: React.FC<GaugeRowProps> = ({ gauges, size = 80 }) => (
  <div className="flex items-center justify-around gap-4 p-3 bg-black/30 rounded-xl border border-white/5">
    {gauges.map((g, i) => (
      <CognitiveLoadGauge key={i} {...g} size={size} />
    ))}
  </div>
);
