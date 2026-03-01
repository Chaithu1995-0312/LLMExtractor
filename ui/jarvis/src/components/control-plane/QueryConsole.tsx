import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { useQueryExecution } from '../../hooks/useQueryExecution';

export default function QueryConsole() {
  const { query, setQuery, loading } = useControlPlaneStore();
  const { execute } = useQueryExecution();

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      execute(query);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 mb-1">
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.7)', fontWeight: 700 }}>
          COGNITIVE QUERY CONSOLE
        </span>
        <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em' }}>
          v2 · CONTROL PLANE
        </span>
      </div>
      <div
        className="flex gap-3"
        style={{
          background: 'rgba(4,8,13,0.95)',
          border: '1px solid rgba(34,211,238,0.18)',
          borderRadius: 6,
          padding: '2px 4px',
        }}
      >
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Nexus... (Enter to execute, Shift+Enter for newline)"
          rows={2}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            resize: 'none',
            color: 'rgba(255,255,255,0.85)',
            fontSize: 13,
            fontFamily: 'monospace',
            padding: '10px 12px',
            letterSpacing: '0.02em',
          }}
        />
        <button
          onClick={() => execute(query)}
          disabled={loading || !query.trim()}
          style={{
            alignSelf: 'flex-end',
            marginBottom: 6,
            marginRight: 6,
            padding: '6px 20px',
            background: loading ? 'rgba(34,211,238,0.08)' : 'rgba(34,211,238,0.15)',
            border: '1px solid rgba(34,211,238,0.35)',
            borderRadius: 4,
            color: loading ? 'rgba(34,211,238,0.4)' : '#22d3ee',
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.15em',
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {loading ? 'EXECUTING…' : 'EXECUTE'}
        </button>
      </div>
    </div>
  );
}
