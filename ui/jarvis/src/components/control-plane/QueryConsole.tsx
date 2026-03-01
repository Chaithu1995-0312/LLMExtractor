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
    <div className="flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center gap-2.5">
        <span className="font-bold text-xs tracking-[0.2em] text-cyan-400">QUERY CONSOLE</span>
        <div className="flex items-center gap-1.5 text-[9px] font-semibold text-white/30 tracking-widest">
          <HelpCircle
            size={12}
            className="text-white/20"
            data-tooltip-id="query-help"
            data-tooltip-content="Press Enter to execute, Shift+Enter for a new line."
          />
          <Tooltip id="query-help" place="top" effect="solid" className="tooltip" />
        </div>
      </div>

      {/* Main input container */}
      <div className="flex gap-2 p-1.5 rounded-lg bg-[#1A1A2E] border border-white/10 focus-within:border-cyan-400 transition-all">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Nexus..."
          rows={2}
          className="flex-1 bg-transparent border-none outline-none resize-none text-white/90 text-sm font-mono p-2.5 tracking-wider placeholder:text-white/20"
        />
        <button
          onClick={() => execute(query)}
          disabled={disabled}
          data-tooltip-id="exec-button-tooltip"
          data-tooltip-content={!query.trim() ? 'Type a query to enable execution' : ''}
          className="self-end mb-1 mr-1 px-5 py-2.5 rounded-md flex items-center gap-2.5 text-xs font-bold tracking-widest transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: disabled ? 'rgba(0, 217, 255, 0.1)' : '#00D9FF',
            color: disabled ? 'rgba(0, 217, 255, 0.5)' : '#030609',
            boxShadow: disabled ? 'none' : '0 0 15px 0 rgba(0, 217, 255, 0.4)',
          }}
        >
          <Send size={14} />
          <span>{loading ? 'EXECUTING…' : 'EXECUTE'}</span>
        </button>
        {!disabled && <Tooltip id="exec-button-tooltip" place="top" effect="solid" />}
      </div>
    </div>
  );
}
