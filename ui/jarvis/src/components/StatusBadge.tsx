import React from 'react';

export type StatusType = 'ACTIVE' | 'ONLINE' | 'HEALTHY' | 'OPTIMAL' | 'BOOTING' | 'DEGRADED' | 'OFFLINE' | 'ERROR' | 'UNKNOWN';

interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className = '' }: StatusBadgeProps) {
  const getStatusConfig = (s: string) => {
    switch (s.toUpperCase()) {
      case 'ACTIVE':
      case 'ONLINE':
      case 'OPTIMAL':
      case 'HEALTHY':
        return { color: '#00D9FF', bg: 'rgba(0, 217, 255, 0.1)', border: 'rgba(0, 217, 255, 0.3)' };
      case 'BOOTING':
        return { color: '#FFA500', bg: 'rgba(255, 165, 0, 0.1)', border: 'rgba(255, 165, 0, 0.3)' };
      case 'DEGRADED':
        return { color: '#FF6B35', bg: 'rgba(255, 107, 53, 0.1)', border: 'rgba(255, 107, 53, 0.3)' };
      case 'OFFLINE':
      case 'ERROR':
        return { color: '#FF0000', bg: 'rgba(255, 0, 0, 0.1)', border: 'rgba(255, 0, 0, 0.3)' };
      default:
        return { color: '#4A4A5E', bg: 'rgba(74, 74, 94, 0.1)', border: 'rgba(74, 74, 94, 0.3)' };
    }
  };

  const config = getStatusConfig(status);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {label && (
        <span className="text-[10px] font-medium text-white/55">
          {label}
        </span>
      )}
      <span
        className="text-[8px] font-bold px-1.5 py-0.5 rounded border tracking-wider uppercase"
        style={{
          color: config.color,
          borderColor: config.border,
          background: config.bg,
        }}
      >
        {status}
      </span>
    </div>
  );
}
