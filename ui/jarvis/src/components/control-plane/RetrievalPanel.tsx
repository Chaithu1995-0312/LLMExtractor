import { useState } from 'react';
import { useControlPlaneStore } from '../../store/controlPlaneStore';

export default function RetrievalPanel() {
  const { result } = useControlPlaneStore();
  const [tab, setTab] = useState<'graph' | 'memory'>('graph');

  if (!result) {
    return (
      <div style={panelStyle}>
        <PanelHeader title="RETRIEVAL LAYERS" />
        <EmptyState />
      </div>
    );
  }

  const { retrieval, route } = result;
  const graphData = retrieval.graph;
  const memData = retrieval.memory;

  const showGraph = route.selected === 'graph' || route.selected === 'hybrid';
  const showMemory = route.selected === 'memory' || route.selected === 'hybrid';

  return (
    <div style={panelStyle}>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.6)', fontWeight: 700 }}>
          RETRIEVAL LAYERS
        </span>
        {/* Tab selector for hybrid */}
        {route.selected === 'hybrid' && (
          <div style={{ display: 'flex', gap: 4 }}>
            {(['graph', 'memory'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  padding: '2px 10px',
                  fontSize: 8,
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                  borderRadius: 3,
                  border: tab === t ? '1px solid rgba(34,211,238,0.5)' : '1px solid rgba(255,255,255,0.08)',
                  background: tab === t ? 'rgba(34,211,238,0.1)' : 'transparent',
                  color: tab === t ? '#22d3ee' : 'rgba(255,255,255,0.3)',
                  cursor: 'pointer',
                }}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Graph results */}
      {(showGraph && (route.selected !== 'hybrid' || tab === 'graph')) && (
        <div>
          <SectionHeader
            title="GRAPH"
            color="#22d3ee"
            count={graphData?.result_count ?? 0}
            topScore={graphData?.top_score}
            error={graphData?.error}
          />
          {graphData?.results && graphData.results.length > 0 ? (
            graphData.results.map((r, i) => (
              <ResultCard key={r.id ?? i} title={r.statement} subtitle={`${r.type} · ${r.lifecycle}`} score={r.confidence} color="#22d3ee" />
            ))
          ) : (
            <NoResults />
          )}
        </div>
      )}

      {/* Memory results */}
      {(showMemory && (route.selected !== 'hybrid' || tab === 'memory')) && (
        <div>
          <SectionHeader
            title="MEMORY"
            color="#8b5cf6"
            count={memData?.chunk_count ?? 0}
            topScore={memData?.top_score}
            error={memData?.error}
          />
          {memData?.chunks && memData.chunks.length > 0 ? (
            memData.chunks.map((c, i) => (
              <ResultCard
                key={c.chunk_id ?? i}
                title={c.text}
                subtitle={`${c.metadata?.role ?? 'unknown'} · dataset ${(c.metadata?.dataset_id ?? '').slice(0, 8)}`}
                score={c.score}
                color="#8b5cf6"
              />
            ))
          ) : (
            <NoResults />
          )}
        </div>
      )}
    </div>
  );
}

function SectionHeader({
  title,
  color,
  count,
  topScore,
  error,
}: {
  title: string;
  color: string;
  count: number;
  topScore?: number;
  error?: string;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, alignItems: 'center' }}>
      <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.15em', color }}>
        {title} · {count} result{count !== 1 ? 's' : ''}
      </span>
      {topScore !== undefined && (
        <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'rgba(255,255,255,0.4)' }}>
          top: {topScore.toFixed(3)}
        </span>
      )}
      {error && (
        <span style={{ fontSize: 9, color: '#ef4444', letterSpacing: '0.08em' }}>
          ERROR
        </span>
      )}
    </div>
  );
}

function ResultCard({
  title,
  subtitle,
  score,
  color,
}: {
  title: string;
  subtitle: string;
  score: number;
  color: string;
}) {
  return (
    <div
      style={{
        marginBottom: 6,
        padding: '8px 10px',
        background: `${color}08`,
        border: `1px solid ${color}20`,
        borderRadius: 4,
        borderLeft: `2px solid ${color}60`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div
          style={{
            fontSize: 10,
            color: 'rgba(255,255,255,0.7)',
            lineHeight: 1.4,
            overflow: 'hidden',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {title}
        </div>
        <span
          style={{
            flexShrink: 0,
            fontSize: 9,
            fontFamily: 'monospace',
            fontWeight: 700,
            color,
            background: `${color}15`,
            padding: '1px 5px',
            borderRadius: 2,
          }}
        >
          {score.toFixed(3)}
        </span>
      </div>
      <div style={{ marginTop: 3, fontSize: 8, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.08em', fontFamily: 'monospace' }}>
        {subtitle}
      </div>
    </div>
  );
}

function PanelHeader({ title }: { title: string }) {
  return (
    <div style={{ marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
      <span style={{ fontSize: 9, letterSpacing: '0.18em', color: 'rgba(34,211,238,0.6)', fontWeight: 700 }}>
        {title}
      </span>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', textAlign: 'center', paddingTop: 16 }}>
      AWAITING QUERY EXECUTION
    </div>
  );
}

function NoResults() {
  return (
    <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.2)', padding: '6px 0', letterSpacing: '0.08em' }}>
      No results retrieved
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  background: 'rgba(4,8,13,0.95)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 6,
  padding: '14px 16px',
};
