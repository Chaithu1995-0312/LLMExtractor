import React, { useEffect, useRef, useState, useLayoutEffect } from 'react';
import * as d3 from 'd3';
import { motion } from 'framer-motion';

interface CortexVisualizerProps {
  data: {
    nodes: any[];
    edges: any[];
    type: 'graph' | 'radar' | 'trace' | 'matrix' | 'tree';
  };
}

export const CortexVisualizer: React.FC<CortexVisualizerProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Handle Dynamic Resizing
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      if (!entries[0]) return;
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current || !data || dimensions.width === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;

    if (data.type === 'graph') {
      const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.edges).id((d: any) => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));

      const link = svg.append('g')
        .selectAll('line')
        .data(data.edges)
        .enter().append('line')
        .attr('stroke', '#0080FF')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,5');

      const node = svg.append('g')
        .selectAll('circle')
        .data(data.nodes)
        .enter().append('g')
        .call(d3.drag<any, any>()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));

      node.append('circle')
        .attr('r', 10)
        .attr('fill', '#05080a')
        .attr('stroke', '#00fff9')
        .attr('stroke-width', 2)
        .attr('class', 'crt-flicker shadow-glow-loose');

      node.append('text')
        .text((d: any) => d.label || d.id.substring(0, 8))
        .attr('x', 14)
        .attr('y', 4)
        .attr('fill', '#e0e0e0')
        .attr('font-size', '11px')
        .attr('font-family', '"JetBrains Mono", monospace')
        .attr('class', 'select-none pointer-events-none');

      simulation.on('tick', () => {
        link
          .attr('x1', (d: any) => d.source.x)
          .attr('y1', (d: any) => d.source.y)
          .attr('x2', (d: any) => d.target.x)
          .attr('y2', (d: any) => d.target.y);

        node
          .attr('transform', (d: any) => `translate(${d.x},${d.y})`);
      });

      function dragstarted(event: any) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event: any) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragended(event: any) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
    } else if (data.type === 'radar') {
       const radius = Math.min(width, height) / 2 - 60;
       const g = svg.append('g').attr('transform', `translate(${width/2},${height/2})`);

       [0.2, 0.4, 0.6, 0.8, 1].forEach(tick => {
         g.append('circle')
          .attr('r', radius * tick)
          .attr('fill', 'none')
          .attr('stroke', '#0080FF')
          .attr('stroke-opacity', 0.2);
       });

       const points = g.selectAll('.point')
        .data(data.nodes)
        .enter().append('circle')
        .attr('cx', (d, i) => Math.cos(i) * radius * (1 - (d.confidence || 0.5)))
        .attr('cy', (d, i) => Math.sin(i) * radius * (1 - (d.confidence || 0.5)))
        .attr('r', 6)
        .attr('fill', '#ff00c1')
        .attr('class', 'crt-flicker shadow-glow-forming');
    }

  }, [data, dimensions]);

  return (
    <div ref={containerRef} className="relative w-full h-full bg-[#05080a]/40 rounded-xl overflow-hidden border border-white/5 backdrop-blur-sm shadow-2xl">
      <div className="scanline absolute inset-0 pointer-events-none z-10" />
      <svg 
        ref={svgRef} 
        width="100%" 
        height="100%" 
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`} 
        preserveAspectRatio="xMidYMid meet" 
        className="cursor-crosshair"
      />
      {/* HUD Overlays */}
      <div className="absolute top-4 left-4 font-mono-data text-[10px] text-primary/60 tracking-widest uppercase pointer-events-none select-none">
        System_Visualizer_V3 // ONLINE<br/>
        Resolution: {dimensions.width}x{dimensions.height}<br/>
        Nodes: {data.nodes.length} // Edges: {data.edges.length}
      </div>
      <div className="absolute bottom-4 right-4 font-mono-data text-[10px] text-primary/40 tracking-tighter pointer-events-none select-none">
        [ MODE-1 ENFORCED // NO GENAI LINKING ]
      </div>
    </div>
  );
};
