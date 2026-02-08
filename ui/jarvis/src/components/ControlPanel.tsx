import React, { useState } from 'react';
import { RefreshCw, Layers, Zap, Terminal, Activity } from 'lucide-react';

interface ControlPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({ isOpen, onClose }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [topic, setTopic] = useState<string>("");

  const addLog = (msg: string) => {
    setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev]);
  };

  const triggerAction = async (endpoint: string, payload: any = {}, actionName: string) => {
    setLoading(actionName);
    addLog(`INIT: ${actionName}...`);
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.error || 'Request failed');
      
      addLog(`SUCCESS: ${actionName} - ${JSON.stringify(data)}`);
    } catch (err: any) {
      addLog(`ERROR: ${actionName} - ${err.message}`);
    } finally {
      setLoading(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-white/10 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[80vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5 bg-black/20">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-primary" />
            <h2 className="font-bold uppercase tracking-widest text-sm text-white/80">System Control Plane</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8 overflow-y-auto">
          
          {/* Actions Column */}
          <div className="flex flex-col gap-6">
            
            {/* Sync Section */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-widest text-white/40">Ingestion Pipeline</h3>
              <button 
                onClick={() => triggerAction('/tasks/sync', {}, 'Sync Bricks')}
                disabled={!!loading}
                className="w-full flex items-center justify-between p-4 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/20 rounded-md group-hover:bg-blue-500/30 transition-colors">
                    <RefreshCw className={`w-5 h-5 text-blue-400 ${loading === 'Sync Bricks' ? 'animate-spin' : ''}`} />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold text-white/90">Trigger Sync</div>
                    <div className="text-[10px] text-white/50">Ingest {'>'} Graph Migration</div>
                  </div>
                </div>
              </button>
            </div>

            {/* Cognition Section */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-widest text-white/40">Cognitive Engine</h3>
              
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="Target Topic ID..."
                  className="flex-1 bg-black/40 border border-white/10 rounded px-3 text-xs font-mono"
                />
              </div>

              <button 
                onClick={() => triggerAction('/cognition/assemble', { topic }, 'Assemble Topic')}
                disabled={!!loading || !topic}
                className="w-full flex items-center justify-between p-4 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-500/20 rounded-md group-hover:bg-amber-500/30 transition-colors">
                    <Layers className="w-5 h-5 text-amber-400" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold text-white/90">Assemble Topic</div>
                    <div className="text-[10px] text-white/50">Loose Bricks {'>'} Intent Tree</div>
                  </div>
                </div>
              </button>

              <button 
                onClick={() => triggerAction('/cognition/synthesize', { topic_id: topic }, 'Synthesize Relations')}
                disabled={!!loading}
                className="w-full flex items-center justify-between p-4 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 transition-all group disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-500/20 rounded-md group-hover:bg-purple-500/30 transition-colors">
                    <Zap className="w-5 h-5 text-purple-400" />
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-bold text-white/90">Deep Synthesis</div>
                    <div className="text-[10px] text-white/50">L3 Reasoning {'>'} Edges</div>
                  </div>
                </div>
              </button>
            </div>

          </div>

          {/* Logs Column */}
          <div className="flex flex-col gap-2 h-full min-h-[300px]">
             <h3 className="text-xs font-bold uppercase tracking-widest text-white/40 flex justify-between">
               <span>System Output</span>
               <Activity className="w-3 h-3 text-emerald-500 animate-pulse" />
             </h3>
             <div className="flex-1 bg-black/60 rounded-lg border border-white/10 p-3 font-mono text-[10px] text-emerald-500/80 overflow-y-auto custom-scrollbar">
               {logs.length === 0 ? (
                 <span className="text-white/20 italic">// System ready. Waiting for commands...</span>
               ) : (
                 logs.map((log, i) => (
                   <div key={i} className="mb-1 border-b border-white/5 pb-1 last:border-0">{log}</div>
                 ))
               )}
             </div>
          </div>

        </div>
      </div>
    </div>
  );
};
