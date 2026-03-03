import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { useQueryExecution } from '../../hooks/useQueryExecution';
import { Send, CornerDownLeft, HelpCircle } from 'lucide-react';
import { Tooltip } from 'react-tooltip';

export default function QueryConsole() {
  const { query, setQuery, loading } = useControlPlaneStore();
  const { execute } = useQueryExecution();
  const disabled = loading || !query.trim();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled) execute(query);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <span className="font-black text-[10px] tracking-[0.25em] text-cyan-400 uppercase">Query Console</span>
        <div className="flex items-center gap-1.5 text-[9px] font-bold text-white/20 tracking-widest uppercase">
          <HelpCircle
            size={12}
            className="text-white/20"
            data-tooltip-id="query-help"
            data-tooltip-content="Press Enter to execute, Shift+Enter for a new line."
          />
          <Tooltip id="query-help" place="top" effect="solid" className="tooltip" />
          {!loading && <span>Ready for input</span>}
        </div>
      </div>

      {/* Main input container */}
      <div className="flex gap-2 p-2 rounded-xl bg-[#090e14] border border-white/10 focus-within:border-cyan-400/50 transition-all shadow-lg">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your command or question for Nexus..."
          rows={2}
          className="flex-1 bg-transparent border-none outline-none resize-none text-white/90 text-[14px] font-mono p-3 tracking-wide placeholder:text-white/10"
        />
        <button
          onClick={() => execute(query)}
          disabled={disabled}
          data-tooltip-id="exec-button-tooltip"
          data-tooltip-content={!query.trim() ? 'Type a query to enable execution' : ''}
          className="self-end mb-1 mr-1 px-6 py-3 rounded-lg flex items-center gap-3 text-[11px] font-black tracking-[0.15em] transition-all disabled:opacity-20 disabled:cursor-not-allowed uppercase group"
          style={{
            background: disabled ? 'rgba(255, 255, 255, 0.05)' : '#00D9FF',
            color: disabled ? 'rgba(255, 255, 255, 0.2)' : '#030609',
            boxShadow: disabled ? 'none' : '0 0 20px 0 rgba(0, 217, 255, 0.3)',
          }}
        >
          <Send size={14} className={loading ? 'animate-pulse' : 'group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform'} />
          <span>{loading ? 'Processing...' : 'Execute'}</span>
        </button>
        {!disabled && <Tooltip id="exec-button-tooltip" place="top" effect="solid" />}
      </div>
    </div>
  );
}
