// ============================================================
//  OverviewPage — Main JARVIS Dashboard (matches concept image)
//  Layout: 2 rows × 3 columns
//  Row 1: [Ingestion Pipeline] [Knowledge Graph] [Intent Focus]
//  Row 2: [Live Stream] [Synthesis Engine] [Audit Log]
// ============================================================

import { useEffect, useMemo, useState, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, {
  Background,
  Controls,
  applyNodeChanges,
  applyEdgeChanges,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  NodeProps,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';

import { IngestionPipelinePanel } from '../components/IngestionPipelinePanel';
import { IntentFocusPanel } from '../components/IntentFocusPanel';
import { LiveCognitiveStreamPanel } from '../components/LiveCognitiveStreamPanel';
import { SynthesisEnginePanel } from '../components/SynthesisEnginePanel';
import { AuditLogPanel } from '../components/AuditLogPanel';
import { useSystemStore } from '../state/system-store';
import { hydrateFromApiResponse } from '../reducers/graph-reducer';

// ─── Lifecycle colours ─────────────────────────────────────────
const LC_COLORS: Record<string, { node: string; border: string; glow: string; text: string }> = {
  LOOSE:     { node: '#0f1a24', border: '#475569', glow: 'none',                        text: '#94a3b8' },
  FORMING:   { node: '#0d1f28', border: '#22d3ee', glow: '0 0 12px rgba(34,211,238,0.5)', text: '#22d3ee' },
  FROZEN:    { node: '#1a1500', border: '#fbbf24', glow: '0 0 12px rgba(251,191,36,0.5)', text: '#fbbf24' },
  SUPERSEDED:{ node: '#130d1e', border: '#a78bfa', glow: '0 0 8px rgba(167,139,250,0.4)', text: '#a78bfa' },
  KILLED:    { node: '#1a0808', border: '#ef4444', glow: '0 0 10px rgba(239,68,68,0.5)',  text: '#f87171' },
};

// ─── Mini graph node ───────────────────────────────────────────
const GraphNode = memo(({ data }: NodeProps) => {
  const lc: string = (data.lifecycle || data.status || 'LOOSE').toUpperCase();
  const cols = LC_COLORS[lc] ?? LC_COLORS.LOOSE;
  const label: string = data.label || data.statement || data.node_id || '?';
  const short = label.length > 28 ? label.slice(0, 27) + '…' : label;

  return (
    <div
      style={{
        background: cols.node,
        border: `1px solid ${cols.border}`,
        borderRadius: 8,
        padding: '6px 10px',
        minWidth: 140,
        maxWidth: 180,
        boxShadow: cols.glow,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: cols.border, width: 6, height: 6 }} />
      <div style={{ fontSize: 7, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 2 }}>
        {lc}
      </div>
      <div style={{ fontSize: 10, fontWeight: 700, color: cols.text, lineHeight: 1.3 }}>
        {short}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: cols.border, width: 6, height: 6 }} />
    </div>
  );
});
GraphNode.displayName = 'GraphNode';

const NODE_TYPES = { nexus: GraphNode };

// ─── Dagre layout ─────────────────────────────────────────────
function layoutGraph(rawNodes: Node[], rawEdges: Edge[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', ranksep: 60, nodesep: 30 });
  rawNodes.forEach((n) => g.setNode(n.id, { width: 180, height: 80 }));
  rawEdges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return {
    nodes: rawNodes.map((n) => {
      const pos = g.node(n.id);
      return { ...n, position: { x: pos.x - 90, y: pos.y - 40 } };
    }),
    edges: rawEdges,
  };
}

// ─── Lifecycle legend dot ──────────────────────────────────────
function LegendDot({ label, color }: { label: string; color: string }) {
  return (
    <div className="flex items-center gap-1">
      <div
        className="rounded-full"
        style={{
          width: 7,
          height: 7,
          background: color,
          boxShadow: `0 0 4px ${color}`,
        }}
      />
      <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </span>
    </div>
  );
}

// ─── Centre Knowledge Graph panel ─────────────────────────────
function KnowledgeGraphPanel() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  const { data: graphData } = useQuery({
    queryKey: ['graph-index'],
    queryFn: async () => {
      const res = await fetch('/jarvis/graph-index');
      if (!res.ok) throw new Error('graph fetch failed');
      return res.json();
    },
    refetchInterval: 15_000,
  });

  useEffect(() => {
    if (!graphData) return;
    const rawNodes: any[] = Array.isArray(graphData.nodes) ? graphData.nodes : (graphData.nodes?.nodes ?? []);
    const rawEdges: any[] = Array.isArray(graphData.edges) ? graphData.edges : (graphData.edges?.edges ?? []);

    hydrateFromApiResponse({ nodes: rawNodes, edges: rawEdges });

    const rfNodes: Node[] = rawNodes.map((n: any) => ({
      id: n.id ?? n.node_id,
      type: 'nexus',
      data: { ...n, label: n.statement ?? n.label ?? n.id },
      position: { x: 0, y: 0 },
    }));

    const rfEdges: Edge[] = rawEdges.map((e: any) => ({
      id: `${e.source ?? e.from}-${e.target ?? e.to}`,
      source: e.source ?? e.from,
      target: e.target ?? e.to,
      label: e.type,
      style: { stroke: 'rgba(34,211,238,0.3)', strokeWidth: 1 },
      labelStyle: { fontSize: 8, fill: 'rgba(255,255,255,0.3)' },
    }));

    const { nodes: ln, edges: le } = layoutGraph(rfNodes, rfEdges);
    setNodes((prev) =>
      ln.map((n) => {
        const existing = prev.find((p) => p.id === n.id);
        return existing ? { ...n, position: existing.position } : n;
      })
    );
    setEdges(le);
  }, [graphData]);

  return (
    <div
      className="flex flex-col h-full relative border-r"
      style={{ background: 'rgba(3,5,9,0.97)', borderColor: 'rgba(255,255,255,0.06)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <span
          className="text-[9px] font-bold uppercase tracking-[0.25em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Knowledge Graph
        </span>
        <div className="flex items-center gap-3">
          <input
            placeholder="Search Nodes / Intents"
            className="px-2 py-0.5 rounded border text-[9px] outline-none"
            style={{
              background: 'rgba(255,255,255,0.03)',
              borderColor: 'rgba(255,255,255,0.1)',
              color: 'rgba(255,255,255,0.5)',
              width: 160,
            }}
          />
          <span
            className="text-[8px] px-2 py-0.5 rounded border"
            style={{ color: 'rgba(255,255,255,0.3)', borderColor: 'rgba(255,255,255,0.1)' }}
          >
            Filter by: Lifecycle ▾
          </span>
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 min-h-0 relative">
        {nodes.length === 0 ? (
          <div
            className="absolute inset-0 flex items-center justify-center text-[10px] uppercase tracking-widest"
            style={{ color: 'rgba(255,255,255,0.12)' }}
          >
            No graph data — Run Sync to populate
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={(changes: NodeChange[]) =>
              setNodes((ns) => applyNodeChanges(changes, ns))
            }
            onEdgesChange={(changes: EdgeChange[]) =>
              setEdges((es) => applyEdgeChanges(changes, es))
            }
            nodeTypes={NODE_TYPES}
            onNodeClick={(_, node) => setSelected(node.id)}
            fitView
            minZoom={0.1}
            style={{ background: 'transparent' }}
          >
            <Background color="rgba(255,255,255,0.03)" gap={20} />
            <Controls
              style={{
                background: 'rgba(4,8,14,0.8)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6,
              }}
            />
          </ReactFlow>
        )}
      </div>

      {/* Legend */}
      <div
        className="flex items-center gap-4 px-3 py-1.5 border-t shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.05)' }}
      >
        <LegendDot label="Loose"     color="#475569" />
        <LegendDot label="Forming"   color="#22d3ee" />
        <LegendDot label="Frozen"    color="#fbbf24" />
        <LegendDot label="Conflicts" color="#fb923c" />
        <LegendDot label="Killed"    color="#ef4444" />
      </div>
    </div>
  );
}

// ─── Selected intent state (shared between graph + focus panel) ──
function useSelectedIntent(graphData: any) {
  return useMemo(() => {
    if (!graphData) return null;
    const rawNodes: any[] = Array.isArray(graphData.nodes) ? graphData.nodes : (graphData.nodes?.nodes ?? []);
    // Pick the first FROZEN or FORMING node as the "focused" intent
    const frozen = rawNodes.find((n: any) => (n.lifecycle ?? n.status ?? '').toUpperCase() === 'FROZEN');
    const forming = rawNodes.find((n: any) => (n.lifecycle ?? n.status ?? '').toUpperCase() === 'FORMING');
    const candidate = frozen ?? forming ?? rawNodes[0];
    if (!candidate) return null;
    const lc = ((candidate.lifecycle ?? candidate.status ?? 'LOOSE').toUpperCase()) as any;
    return {
      intentId: candidate.id ?? candidate.node_id ?? '—',
      title: candidate.statement ?? candidate.label ?? 'Untitled',
      status: lc,
      confidence: Math.round((candidate.confidence ?? 0.5) * 100),
      sourceChain: ['SRC-77', 'BRK-12', candidate.id?.slice(0, 6) ?? 'I-???'],
      conflicts: (rawNodes as any[])
        .filter((n: any) => (n.lifecycle ?? '').toUpperCase() === 'LOOSE' && n.id !== candidate.id)
        .slice(0, 2)
        .map((n: any) => ({ id: n.id?.slice(0, 6) ?? '??', label: n.statement?.slice(0, 20) ?? '—' })),
    };
  }, [graphData]);
}

// ─── Main OverviewPage ─────────────────────────────────────────
export default function OverviewPage() {
  const { cognitivePhase } = useSystemStore();
  const [isSyncing, setIsSyncing] = useState(false);

  const stageMap: Record<string, number> = {
    IDLE: -1, SYNCING: 0, COMPILING: 2, SYNTHESIZING: 3, STREAMING: 4,
  };
  const currentStage = stageMap[cognitivePhase] ?? -1;

  const handleRunSync = async () => {
    setIsSyncing(true);
    try {
      await fetch('/api/sync/run', { method: 'POST' });
    } catch {}
    setTimeout(() => setIsSyncing(false), 5000);
  };

  const { data: graphData } = useQuery({
    queryKey: ['graph-index'],
    queryFn: async () => {
      const res = await fetch('/jarvis/graph-index');
      if (!res.ok) throw new Error('graph fetch failed');
      return res.json();
    },
    refetchInterval: 15_000,
  });

  const focusedIntent = useSelectedIntent(graphData);

  return (
    <div
      className="h-full w-full"
      style={{
        display: 'grid',
        gridTemplateRows: '1fr 220px',
        gridTemplateColumns: '100%',
        background: '#030609',
      }}
    >
      {/* ── TOP ROW: 3 columns ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '220px 1fr 280px',
          minHeight: 0,
        }}
      >
        {/* Left: Ingestion Pipeline */}
        <IngestionPipelinePanel
          onRunSync={handleRunSync}
          isSyncing={isSyncing}
          currentStage={currentStage}
        />

        {/* Center: Knowledge Graph */}
        <KnowledgeGraphPanel />

        {/* Right: Intent Focus */}
        <IntentFocusPanel
          intentId={focusedIntent?.intentId}
          title={focusedIntent?.title}
          status={focusedIntent?.status}
          confidence={focusedIntent?.confidence ?? 0}
          sourceChain={focusedIntent?.sourceChain ?? []}
          conflicts={focusedIntent?.conflicts ?? []}
        />
      </div>

      {/* ── BOTTOM ROW: 3 columns ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          minHeight: 0,
        }}
      >
        {/* Left: Live Cognitive Stream */}
        <LiveCognitiveStreamPanel />

        {/* Center: Synthesis Engine */}
        <SynthesisEnginePanel />

        {/* Right: Audit Log + System Risk */}
        <AuditLogPanel />
      </div>
    </div>
  );
}
