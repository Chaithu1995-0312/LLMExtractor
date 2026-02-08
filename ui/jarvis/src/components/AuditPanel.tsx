
import React, { useEffect, useState } from 'react';
import { Terminal, Cpu, DollarSign, Activity, ChevronDown, ChevronUp } from 'lucide-react';

interface AuditEvent {
  timestamp: string;
  event: string;
  component: string;
  agent: string;
  topic_id?: string;
  run_id?: string;
  model_tier?: string;
  cost?: {
    usd: number;
    tokens_in: number;
    tokens_out: number;
  };
  decision: {
    action: string;
    reason: string;
  };
  metadata: any;
}

export const AuditPanel: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchEvents = async () => {
    try {
      const resp = await fetch('/api/audit/events?limit=50');
      const data = await resp.json();
      setEvents(data.events || []);
    } catch (e) {
      console.error("Failed to fetch audit events", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    const interval = setInterval(fetchEvents, 5000);
    return () => clearInterval(interval);
  }, []);

  const getTierColor = (tier?: string) => {
    switch (tier) {
      case 'L1': return 'text-green-400 border-green-900/50 bg-green-950/20';
      case 'L2': return 'text-blue-400 border-blue-900/50 bg-blue-950/20';
      case 'L3': return 'text-purple-400 border-purple-900/50 bg-purple-950/20';
      default: return 'text-gray-400 border-gray-800 bg-gray-900/20';
    }
  };

  return (
    <div className="flex flex-col h-full bg-black/90 border-l border-white/10 w-96 font-mono">
      <div className="p-4 border-b border-white/10 flex items-center gap-2 bg-white/5">
        <Activity className="w-4 h-4 text-blue-400" />
        <h2 className="text-xs font-bold uppercase tracking-widest text-white/70">Observatory: Audit Trail</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && <div className="p-8 text-center text-[10px] text-white/30 animate-pulse">SCANNING FORENSIC LOGS...</div>}
        
        {!loading && events.map((evt, idx) => (
          <div key={idx} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
            <div 
              className="p-3 cursor-pointer flex flex-col gap-2"
              onClick={() => setExpandedId(expandedId === idx.toString() ? null : idx.toString())}
            >
              <div className="flex justify-between items-start">
                <span className="text-[9px] text-white/40">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                <div className="flex gap-1">
                  {evt.model_tier && (
                    <span className={`text-[8px] px-1.5 py-0.5 rounded border ${getTierColor(evt.model_tier)}`}>
                      {evt.model_tier}
                    </span>
                  )}
                  <span className="text-[8px] px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-white/60">
                    {evt.component}
                  </span>
                </div>
              </div>

              <div className="text-[10px] font-bold text-blue-100/90 leading-tight">
                {evt.event.replace(/_/g, ' ')}
              </div>

              <div className="flex items-center gap-2 text-[9px] text-white/50">
                <span className="text-white/30 italic">{evt.agent}</span>
                {evt.cost && evt.cost.usd > 0 && (
                  <span className="flex items-center gap-0.5 text-amber-400/80">
                    <DollarSign className="w-2.5 h-2.5" />
                    {evt.cost.usd.toFixed(4)}
                  </span>
                )}
              </div>

              <div className="text-[9px] text-white/40 bg-black/40 p-1.5 rounded border border-white/5 line-clamp-2">
                <span className="text-white/20 uppercase mr-1">Reason:</span>
                {evt.decision.reason}
              </div>
            </div>

            {expandedId === idx.toString() && (
              <div className="bg-blue-950/20 p-3 border-t border-blue-900/30">
                <pre className="text-[8px] text-blue-200/60 overflow-x-auto">
                  {JSON.stringify(evt.metadata, null, 2)}
                </pre>
                {evt.run_id && (
                  <div className="mt-2 pt-2 border-t border-white/5 text-[8px] text-white/30">
                    RUN_ID: <span className="text-white/60">{evt.run_id}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
