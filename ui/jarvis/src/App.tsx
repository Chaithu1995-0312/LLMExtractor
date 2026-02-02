import { useState } from 'react';

// Types strictly following the spec
interface BrickResult {
  brick_id: string;
  confidence: number;
}

interface SelectedBrick {
  brick_id: string;
  source_file: string;
  source_span: object;
  text_sample?: string;
}

interface ExpandedBrick {
  brick_id: string;
  source_file: string;
  message_id: string;
  block_index: number;
  role: string;
  created_at: string | null;
  full_text: string;
}

interface ApiResponse {
  query: string;
  top_bricks: BrickResult[];
  status: string;
}

interface GraphNode {
  id: string;
  label: string;
  bricks?: string[]; // Backward compatibility
  anchors?: {
    hard: string[];
    soft: string[];
  };
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface AnchorOverride {
    concept_id: string;
    brick_id: string;
    action: "promote" | "reject";
    status: string;
}

interface GraphIndexResponse {
  nodes: GraphNode[] | { nodes: GraphNode[] };
  edges: GraphEdge[] | { edges: GraphEdge[] };
  index_content: string;
  anchor_overrides?: AnchorOverride[];
}

type AnchorIntent =
  | { action: "promote"; brickId: string }
  | { action: "reject"; brickId: string };

type HighlightLevel = "strong" | "weak" | "none";

function getHighlightLevel(
  node: GraphNode,
  recalledBricks: string[]
): HighlightLevel {
  if (node.anchors?.hard?.some(id => recalledBricks.includes(id))) {
    return "strong";
  }

  if (node.anchors?.soft?.some(id => recalledBricks.includes(id))) {
    return "weak";
  }

  return "none";
}

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<BrickResult[]>([]);
  const [selectedBrick, setSelectedBrick] = useState<SelectedBrick | null>(null);
  const [expandedBrick, setExpandedBrick] = useState<ExpandedBrick | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New state for Graph View
  const [graphData, setGraphData] = useState<GraphIndexResponse | null>(null);
  const [showGraph, setShowGraph] = useState(false);
  const [anchorIntents, setAnchorIntents] = useState<Record<string, AnchorIntent>>({});
  
  // State for expanded neighbors (traversal)
  const [expandedNeighbors, setExpandedNeighbors] = useState<Set<string>>(new Set());
  // State for showing anchored bricks drawer
  const [showAnchorsFor, setShowAnchorsFor] = useState<Set<string>>(new Set());

  const logPromote = (conceptId: string, brickId: string) => {
    const key = `${conceptId}:${brickId}`;
    if (anchorIntents[key]) return;

    console.log(JSON.stringify({
      action: "PROMOTE_TO_HARD",
      concept_id: conceptId,
      brick_id: brickId,
      timestamp: new Date().toISOString()
    }));

    setAnchorIntents(prev => ({
      ...prev,
      [key]: { action: "promote", brickId }
    }));
  };

  const logReject = (conceptId: string, brickId: string) => {
    const key = `${conceptId}:${brickId}`;
    if (anchorIntents[key]) return;

    console.log(JSON.stringify({
      action: "REJECT_SOFT",
      concept_id: conceptId,
      brick_id: brickId,
      timestamp: new Date().toISOString()
    }));

    setAnchorIntents(prev => ({
      ...prev,
      [key]: { action: "reject", brickId }
    }));
  };

  const handlePreview = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSelectedBrick(null);
    setResults([]); // "Clicking “Preview” replaces results"

    try {
      // NON-NEGOTIABLE: ONLY call GET /jarvis/ask-preview
      const response = await fetch(`/jarvis/ask-preview?query=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const data: ApiResponse = await response.json();
      
      // "Sort results by confidence DESC"
      const sortedBricks = data.top_bricks.sort((a, b) => b.confidence - a.confidence);
      setResults(sortedBricks);

      if (sortedBricks.length === 0) {
        // "If results empty -> show “No matching bricks found”" -> Handled in render
      }

    } catch (err: any) {
      // "If API fails -> show “Preview unavailable”"
      setError('Preview unavailable');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBrickClick = async (brick: BrickResult) => {
    // "brick detail panel (read-only)"
    // Initial loading state / reset
    setSelectedBrick({
      brick_id: brick.brick_id,
      source_file: 'Loading...',
      source_span: {},
      text_sample: 'Loading...'
    });

    try {
      const res = await fetch(`/jarvis/brick-meta?brick_id=${encodeURIComponent(brick.brick_id)}`);
      if (!res.ok) {
        setSelectedBrick({
            brick_id: brick.brick_id,
            source_file: 'Error fetching details',
            source_span: {},
            text_sample: 'Error fetching details'
        });
        return;
      }
      const data: SelectedBrick = await res.json();
      setSelectedBrick(data);
    } catch (e) {
      setSelectedBrick({
        brick_id: brick.brick_id,
        source_file: 'Error fetching details',
        source_span: {},
        text_sample: 'Error fetching details'
      });
    }
  };

  const loadFullBrick = async (brickId: string) => {
    try {
      const res = await fetch(
        `/jarvis/brick-full?brick_id=${encodeURIComponent(brickId)}`
      );

      if (!res.ok) return;

      const data = await res.json();
      setExpandedBrick(data);
    } catch (e) {
      console.error("Failed to load full brick", e);
    }
  };

  const handleGraphView = async () => {
      try {
          const res = await fetch('/jarvis/graph-index');
          if (!res.ok) throw new Error('Failed to load graph index');
          const data: GraphIndexResponse = await res.json();
          setGraphData(data);
          setShowGraph(true);
          
          // Process Overrides
          if (data.anchor_overrides) {
             const newIntents: Record<string, AnchorIntent> = {};
             data.anchor_overrides.forEach(override => {
                 const key = `${override.concept_id}:${override.brick_id}`;
                 newIntents[key] = { 
                     action: override.action, 
                     brickId: override.brick_id 
                 };
             });
             setAnchorIntents(prev => ({ ...prev, ...newIntents }));
          }
      } catch (e) {
          console.error("Error loading graph index", e);
          alert("Failed to load Enhanced AI View");
      }
  };

  const toggleNeighbors = (nodeId: string) => {
      setExpandedNeighbors(prev => {
          const next = new Set(prev);
          if (next.has(nodeId)) next.delete(nodeId);
          else next.add(nodeId);
          return next;
      });
  };

  const toggleAnchors = (nodeId: string) => {
      setShowAnchorsFor(prev => {
          const next = new Set(prev);
          if (next.has(nodeId)) next.delete(nodeId);
          else next.add(nodeId);
          return next;
      });
  };

  // Helper to safely extract nodes array regardless of schema structure
  const getNodes = (data: GraphIndexResponse | null): GraphNode[] => {
    if (!data) return [];
    if (Array.isArray(data.nodes)) return data.nodes;
    // Handle { nodes: [...] } wrapper
    if (data.nodes && Array.isArray((data.nodes as any).nodes)) return (data.nodes as any).nodes;
    return [];
  };

  const getEdges = (data: GraphIndexResponse | null): GraphEdge[] => {
    if (!data) return [];
    if (Array.isArray(data.edges)) return data.edges;
    // Handle { edges: [...] } wrapper
    if (data.edges && Array.isArray((data.edges as any).edges)) return (data.edges as any).edges;
    return [];
  };

  // Derived state for graph rendering
  const nodes = getNodes(graphData);
  const edges = getEdges(graphData);
  const recalledBrickIds = results.map(r => r.brick_id);

  return (
    <div className="container">
      {/* LEFT / TOP: Query Input */}
      <div className="panel left-panel">
        <h2>Jarvis Preview</h2>
        <div className="input-group">
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter query..."
            disabled={loading}
          />
          <button onClick={handlePreview} disabled={loading}>
            {loading ? 'Searching...' : 'Preview'}
          </button>
        </div>
      </div>

      {/* CENTER: Results List */}
      <div className="panel center-panel">
        <h3>Recalled Bricks</h3>
        {error && <div className="error">{error}</div>}
        
        {!loading && !error && results.length === 0 && query && (
          <div className="empty-state">No matching bricks found</div>
        )}

        <div className="brick-list">
          {results.map((brick, index) => (
            <div 
              key={brick.brick_id} 
              className={`brick-item ${selectedBrick?.brick_id === brick.brick_id ? 'selected' : ''}`}
              onClick={() => handleBrickClick(brick)}
            >
              <div className="brick-header">
                <span className="rank">#{index + 1}</span>
                <span className="brick-id" title={brick.brick_id}>
                  {brick.brick_id.substring(0, 8)}...
                </span>
              </div>
              <div className="confidence-bar-container">
                <div 
                  className="confidence-bar" 
                  style={{ width: `${brick.confidence * 100}%` }}
                  title={`Confidence: ${brick.confidence}`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT / BOTTOM: Brick Detail */}
      <div className="panel right-panel">
        <h3>Brick Detail</h3>
        {selectedBrick ? (
          <div className="detail-content">
            <div className="field">
              <label>Brick ID</label>
              <div className="value copyable">{selectedBrick.brick_id}</div>
            </div>
            <div className="field">
              <label>Source File</label>
              <div className="value">{selectedBrick.source_file}</div>
            </div>
            <div className="field">
              <label>Source Span</label>
              <pre className="value">{JSON.stringify(selectedBrick.source_span, null, 2)}</pre>
            </div>
            <div className="field">
              <label>Text Sample</label>
              <div className="value sample">{selectedBrick.text_sample}</div>
            </div>
            
            <div className="brick-actions">
              <button onClick={() => loadFullBrick(selectedBrick.brick_id)}>
                Show
              </button>

              <button onClick={handleGraphView} title="Enhanced AI View">
                Enhanced AI View
              </button>
            </div>
          </div>
        ) : (
          <div className="empty-state">Select a brick to view details</div>
        )}
      </div>

      {/* Expanded Brick Modal */}
      {expandedBrick && (
        <>
          <div className="modal-backdrop" onClick={() => setExpandedBrick(null)} />
          <div className="brick-full-view">
            <h4>Full Brick Content</h4>
            <div className="meta-row">
              <div><b>Role:</b> {expandedBrick.role}</div>
              <div><b>Message ID:</b> {expandedBrick.message_id}</div>
              <div><b>Index:</b> {expandedBrick.block_index}</div>
            </div>
            <pre>{expandedBrick.full_text}</pre>
            <button className="close-btn" onClick={() => setExpandedBrick(null)}>Close</button>
          </div>
        </>
      )}

      {/* Enhanced AI View (Graph Index) Modal */}
      {showGraph && graphData && (
        <>
          <div className="modal-backdrop" onClick={() => setShowGraph(false)} />
          <div className="brick-full-view graph-view" style={{ maxWidth: '800px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                 <h3>Human-curated Concept Index (Preview)</h3>
                 <button className="close-btn" onClick={() => setShowGraph(false)}>Close</button>
            </div>
            
            <div className="graph-content" style={{ overflowY: 'auto', maxHeight: '70vh' }}>
                <div className="markdown-content" style={{ marginBottom: '2rem', padding: '1rem', background: '#f5f5f5', borderRadius: '4px' }}>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>{graphData.index_content}</pre>
                </div>

                <div className="graph-section">
                    <h4>Concepts ({nodes.length})</h4>
                    
                    <div className="concept-legend">
                      <span className="legend-strong">■ Strong (Hard Anchor Match)</span>
                      <span className="legend-weak">■ Weak (Soft Anchor Match)</span>
                      <span className="legend-none">■ Neutral</span>
                    </div>

                    <div style={{ marginTop: '1rem' }}>
                        {nodes.map(node => {
                            const highlight = getHighlightLevel(node, recalledBrickIds);
                            return (
                                <div
                                    key={node.id}
                                    className={`concept-card concept-${highlight}`}
                                >
                                    <div className="concept-title">{node.label}</div>
                                    <div className="concept-meta">
                                        <div>ID: {node.id}</div>
                                        
                                        {/* Traversal Controls */}
                                        <div className="traversal-controls" style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
                                            <button onClick={() => toggleNeighbors(node.id)}>
                                                {expandedNeighbors.has(node.id) ? 'Collapse Neighbors' : 'Expand Neighbors'}
                                            </button>
                                            <button onClick={() => toggleAnchors(node.id)}>
                                                {showAnchorsFor.has(node.id) ? 'Hide Anchors' : 'Show Anchored Bricks'}
                                            </button>
                                        </div>

                                        {/* Anchors Drawer */}
                                        {showAnchorsFor.has(node.id) && (
                                            <div className="anchors-drawer" style={{ marginTop: '1rem', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
                                                {/* Logic to show anchors (hard/soft) or bricks (as soft) */}
                                                {(() => {
                                                    const hardAnchors = node.anchors?.hard || [];
                                                    const softAnchors = node.anchors?.soft || node.bricks || []; // Fallback to bricks as soft
                                                    
                                                    return (
                                                        <>
                                                            <div className="anchors-section">
                                                                <strong>Hard Anchors ({hardAnchors.length})</strong>
                                                                <div className="anchors-list">
                                                                    {hardAnchors.map(brickId => (
                                                                        <div key={brickId} className="anchor-row read-only">
                                                                            <span className="brick-id">{brickId.substring(0, 8)}...</span>
                                                                            <span className="locked-badge">Locked</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                            <div className="anchors-section">
                                                                <strong>Soft Anchors ({softAnchors.length})</strong>
                                                                <div className="anchors-list">
                                                                    {softAnchors.map(brickId => {
                                                                        const key = `${node.id}:${brickId}`;
                                                                        const intent = anchorIntents[key];
                                                                        
                                                                        return (
                                                                            <div key={brickId} className="anchor-row">
                                                                                <span 
                                                                                    className="brick-id link" 
                                                                                    style={{ cursor: 'pointer', textDecoration: 'underline', color: 'blue' }}
                                                                                    onClick={() => { setShowGraph(false); handleBrickClick({ brick_id: brickId, confidence: 0 }); }}
                                                                                >
                                                                                    {brickId.substring(0, 8)}...
                                                                                </span>

                                                                                {!intent && (
                                                                                    <div className="anchor-actions">
                                                                                        <button className="action-btn promote" onClick={() => logPromote(node.id, brickId)}>Promote → Hard</button>
                                                                                        <button className="action-btn reject" onClick={() => logReject(node.id, brickId)}>Reject</button>
                                                                                    </div>
                                                                                )}

                                                                                {intent?.action === "promote" && <span className="intent-badge promote">Promotion Intended</span>}
                                                                                {intent?.action === "reject" && <span className="intent-badge reject">Rejection Intended</span>}
                                                                            </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                        </>
                                                    );
                                                })()}
                                            </div>
                                        )}
                                        
                                        {/* Neighbors Expansion */}
                                        {expandedNeighbors.has(node.id) && (
                                            <div className="neighbors-list" style={{ marginLeft: '1rem', borderLeft: '1px dashed #ccc', paddingLeft: '1rem', marginTop: '0.5rem' }}>
                                                {edges.filter(e => e.source === node.id || e.target === node.id).map((edge, i) => {
                                                    const neighborId = edge.source === node.id ? edge.target : edge.source;
                                                    const neighborNode = nodes.find(n => n.id === neighborId);
                                                    return (
                                                        <div key={i} className="neighbor-item" style={{ background: '#f9f9f9', padding: '0.25rem', marginBottom: '0.25rem' }}>
                                                            <div>{neighborNode?.label || neighborId} <span style={{fontSize: '0.8em', color: '#666'}}>({edge.type})</span></div>
                                                            <div style={{fontSize: '0.8em', fontStyle: 'italic', color: '#888'}}>Contextual — not recalled</div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}

                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="graph-section" style={{ marginTop: '2rem' }}>
                    <h4>Relations ({edges.length})</h4>
                     <ul style={{ listStyle: 'none', padding: 0 }}>
                        {edges.map((edge, i) => (
                            <li key={i} style={{ padding: '0.25rem 0' }}>
                                {edge.source} {"--["}{edge.type}{"]-->"} {edge.target}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
