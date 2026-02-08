import React, { useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';

cytoscape.use(dagre);

interface CortexVisualizerProps {
  data: {
    nodes: any[];
    edges: any[];
    type: 'graph' | 'radar' | 'trace' | 'matrix' | 'tree';
  };
}

export const CortexVisualizer: React.FC<CortexVisualizerProps> = ({ data }) => {
  const [elements, setElements] = useState<any[]>([]);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!data) return;

    // Transform generic data to Cytoscape elements
    const nodes = data.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.label || n.id.substring(0, 8),
        type: n.type || 'default',
        lifecycle: n.lifecycle || 'loose' // loose, frozen, killed
      },
      classes: n.lifecycle || 'loose'
    }));

    const edges = data.edges.map((e, idx) => ({
      data: {
        id: e.id || `e${idx}`,
        source: e.source.id || e.source, // Handle both object and string refs
        target: e.target.id || e.target,
        label: e.type
      }
    }));

    setElements([...nodes, ...edges]);
  }, [data]);

  const styles = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'color': '#fff',
        'font-family': 'JetBrains Mono',
        'font-size': '10px',
        'width': '20px',
        'height': '20px',
        'background-color': '#05080a',
        'border-width': 2,
        'border-color': '#00fff9'
      }
    },
    {
      selector: 'node.frozen',
      style: {
        'border-color': '#0080FF',
        'background-color': '#001a33',
        'width': '25px',
        'height': '25px'
      }
    },
    {
      selector: 'node.killed',
      style: {
        'border-color': '#FF0055',
        'background-color': '#1a0000',
        'opacity': 0.6
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#0080FF',
        'target-arrow-color': '#0080FF',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.5
      }
    }
  ];

  const layout = {
    name: 'dagre',
    rankDir: 'LR',
    spacingFactor: 1.2,
    animate: true
  };

  return (
    <div className="relative w-full h-full bg-[#05080a]/40 rounded-xl overflow-hidden border border-white/5 backdrop-blur-sm shadow-2xl">
      <div className="scanline absolute inset-0 pointer-events-none z-10" />
      
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={styles}
        layout={layout}
        cy={(cy) => { cyRef.current = cy; }}
        className="block w-full h-full cursor-crosshair"
      />

      {/* HUD Overlays */}
      <div className="absolute top-4 left-4 font-mono-data text-[10px] text-primary/60 tracking-widest uppercase pointer-events-none select-none">
        System_Visualizer_V3 // CYTOSCAPE_CORE<br/>
        Nodes: {data.nodes.length} // Edges: {data.edges.length}
      </div>
      <div className="absolute bottom-4 right-4 font-mono-data text-[10px] text-primary/40 tracking-tighter pointer-events-none select-none">
        [ MODE-1 ENFORCED // NO GENAI LINKING ]
      </div>
    </div>
  );
};
