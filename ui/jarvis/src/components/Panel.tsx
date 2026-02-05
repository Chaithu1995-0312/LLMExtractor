import React from "react";

export interface PanelProps {
  nodeId: string;
  lifecycle: string;
  title: string;
  fullText: string;
  sources: string[];
  conflicts: string[];
  supersededBy?: string;
  history: {
    timestamp: string;
    note: string;
  }[];
  onPromote: () => void;
  onKill: () => void;
}

export const Panel: React.FC<PanelProps> = ({
  nodeId,
  lifecycle,
  title,
  fullText,
  sources,
  conflicts,
  supersededBy,
  history,
  onPromote,
  onKill,
}) => {
  const canPromote = lifecycle === 'FORMING' && conflicts.length === 0;
  const canKill = lifecycle !== 'KILLED';

  return (
    <div className="nexus-panel panel-focused flex flex-col h-full">
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <div className="flex items-center justify-between mb-4">
          <h2 className="panel-title text-xl font-bold">{title}</h2>
          <span className={`px-2 py-0.5 rounded text-xs font-mono uppercase border 
            ${lifecycle === 'FROZEN' ? 'border-emerald-500 text-emerald-400' : 
              lifecycle === 'FORMING' ? 'border-amber-500 text-amber-400' :
              lifecycle === 'KILLED' ? 'border-red-500 text-red-500' :
              'border-cyan-500 text-cyan-400'}`}>
            {lifecycle}
          </span>
        </div>

        <section className="panel-section mb-6">
          <p className="panel-text text-gray-300 leading-relaxed">{fullText}</p>
        </section>

        {supersededBy && (
           <section className="panel-section mb-6 border border-yellow-500/30 bg-yellow-500/10 p-3 rounded">
            <h4 className="text-yellow-500 font-bold mb-1">Superseded By</h4>
            <p className="text-sm font-mono">{supersededBy}</p>
          </section>
        )}

        {sources.length > 0 && (
          <section className="panel-section mb-6">
            <h4 className="text-xs uppercase tracking-widest text-gray-500 mb-2">Sources</h4>
            <ul className="space-y-1">
              {sources.map((s, i) => (
                <li key={i} className="text-sm text-cyan-300/80 truncate">{s}</li>
              ))}
            </ul>
          </section>
        )}

        {conflicts.length > 0 && (
          <section className="panel-section warning mb-6 p-3 border border-red-500/30 bg-red-900/10 rounded">
            <h4 className="text-red-400 font-bold mb-2">Conflicts</h4>
            <ul className="space-y-1">
              {conflicts.map((c, i) => (
                <li key={i} className="text-sm text-red-300">{c}</li>
              ))}
            </ul>
          </section>
        )}

        {history.length > 0 && (
          <section className="panel-section muted mt-8 border-t border-white/10 pt-4">
            <h4 className="text-xs uppercase tracking-widest text-gray-600 mb-2">History</h4>
            <ul className="space-y-2">
              {history.map((h, i) => (
                <li key={i} className="text-xs text-gray-500 font-mono">
                  <span className="text-gray-600 mr-2">{h.timestamp.split('T')[0]}</span>
                  {h.note}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {/* Action Bar */}
      <div className="mt-4 pt-4 border-t border-white/10 flex gap-4">
        {canPromote && (
          <button 
            onClick={onPromote}
            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded transition-colors uppercase tracking-wider text-sm shadow-[0_0_15px_rgba(37,99,235,0.3)]"
          >
            Promote to Frozen
          </button>
        )}
        
        {canKill && (
          <button 
            onClick={onKill}
            className={`flex-1 border border-red-800 text-red-500 hover:bg-red-900/30 hover:text-red-400 font-bold py-2 px-4 rounded transition-colors uppercase tracking-wider text-sm
              ${!canPromote ? 'w-full' : ''}`}
          >
            Kill Idea
          </button>
        )}
      </div>
    </div>
  );
};
