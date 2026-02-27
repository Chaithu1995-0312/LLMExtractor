// ============================================================
//  ConnectionStatusBadge — live WebSocket connection indicator
//  Displays a pulsing dot + label in TopStatusBar or inline.
//  Reads from stream-store connectionState (FSM-driven).
// ============================================================

import { useStreamStore } from '../state/stream-store';

const STATE_CONFIG: Record<string, { color: string; label: string; pulse: boolean }> = {
  CONNECTED:    { color: '#34d399', label: 'LIVE',         pulse: true  },
  STREAMING:    { color: '#22d3ee', label: 'STREAMING',    pulse: true  },
  BUFFERING:    { color: '#fbbf24', label: 'BUFFERING',    pulse: true  },
  DISCONNECTED: { color: '#ef4444', label: 'DISCONNECTED', pulse: false },
  RECONNECTING: { color: '#fb923c', label: 'RECONNECTING', pulse: true  },
};

interface ConnectionStatusBadgeProps {
  className?: string;
  showLabel?: boolean;
}

export function ConnectionStatusBadge({ className = '', showLabel = true }: ConnectionStatusBadgeProps) {
  const { connectionState } = useStreamStore();
  const cfg = STATE_CONFIG[connectionState] ?? STATE_CONFIG.DISCONNECTED;

  return (
    <div
      className={`flex items-center gap-1.5 ${className}`}
      title={`WebSocket: ${connectionState}`}
    >
      <span
        style={{
          display: 'inline-block',
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: cfg.color,
          boxShadow: `0 0 5px ${cfg.color}`,
          animation: cfg.pulse ? 'pulse 2s ease-in-out infinite' : 'none',
          flexShrink: 0,
        }}
      />
      {showLabel && (
        <span
          style={{
            fontSize: 8,
            fontWeight: 700,
            letterSpacing: '0.15em',
            color: cfg.color,
            textTransform: 'uppercase',
          }}
        >
          {cfg.label}
        </span>
      )}
    </div>
  );
}
