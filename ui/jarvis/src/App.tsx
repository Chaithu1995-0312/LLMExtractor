import { useState, useRef, useEffect, useMemo, memo } from 'react';
import { useNexusStore } from './store';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, 
  Share2, 
  ChevronRight, 
  ChevronLeft, 
  Search, 
  Send, 
  BookOpen, 
  Activity,
  Maximize2,
  ExternalLink,
  LayoutGrid,
  Network,
  Menu,
  X
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import ReactFlow, { 
  Background, 
  Controls, 
  applyNodeChanges, 
  applyEdgeChanges,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection,
  addEdge,
  NodeProps
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NexusNode, NexusNodeProps, Lifecycle } from './components/NexusNode';
import { WallView } from './components/WallView';
import { Panel } from './components/Panel';
import { CortexVisualizer } from './components/CortexVisualizer';

// --- Adapters ---

const GraphNodeWrapper = memo(({ data, id, selected }: NodeProps) => {
  const props: NexusNodeProps = {
    id: id,
    title: data.label || 'Untitled',
    summary: data.summary || 'No summary available.',
    lifecycle: (data.status as Lifecycle) || 'LOOSE',
    confidence: data.confidence || 0.5,
    sourceCount: data.sourceCount || 0,
    lastUpdatedAt: data.lastUpdatedAt || 'Unknown',
    isFocused: selected,
    onSelect: () => {},
  };
  return <div style={{ minWidth: '180px' }}><NexusNode {...props} /></div>;
});

const nodeTypes = {
  nexus: GraphNodeWrapper,
};

// Initialize mermaid
mermaid.initialize({ startOnLoad: true, theme: 'dark' });

// --- Components ---

const Mermaid = ({ content }: { content: string }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, content).then((res) => {
        if (ref.current) ref.current.innerHTML = res.svg;
      });
    }
  }, [content]);

  return (
    <motion.div 
      whileHover={{ scale: 1.01 }}
      ref={ref} 
      className="my-4 bg-secondary/30 glass border border-white/5 p-4 rounded-lg overflow-auto cursor-zoom-in shadow-inner max-w-full" 
    />
  );
};

interface Message {
  role: string;
  content: string;
  bricks?: any[];
}

const ChatMessage = ({ role, content }: Message) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-6 md:mb-8`}
    >
      <div className={`max-w-[90%] md:max-w-[85%] p-4 md:p-5 rounded-xl ${
        role === 'user' 
        ? 'bg-primary text-primary-foreground md:ml-12 shadow-[0_0_20px_-5px_rgba(59,130,246,0.3)]' 
        : 'glass-panel md:mr-12 shadow-2xl'
      }`}>
        <ReactMarkdown
          remarkPlugins={[remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            code({ node, inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              if (!inline && match && match[1] === 'mermaid') {
                return <Mermaid content={String(children).replace(/\n$/, '')} />;
              }
              return (
                <code className={`${className} bg-black/30 px-1 rounded break-all whitespace-pre-wrap`} {...props}>
                  {children}
                </code>
              );
            },
            p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed text-sm md:text-base">{children}</p>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </motion.div>
  );
};

// --- Main App ---

const panelTransition = {
  type: "spring" as const,
  stiffness: 300,
  damping: 30,
};

export default function App() {
  const { mode, setMode, rightPanelOpen, toggleRightPanel, selectedBrickId, setSelectedBrickId, selectedNodeId, setSelectedNodeId } = useNexusStore();
  const [query, setQuery] = useState('');
  const [useGenAI, setUseGenAI] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome to the **Nexus Workbench**. How can I help you explore the knowledge base today?' }
  ]);
  const [viewMode, setViewMode] = useState<'wall' | 'graph'>('wall'); 
  const queryClient = useQueryClient();

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const onNodesChange = (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds));
  const onEdgesChange = (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds));
  const onConnect = (params: Connection) => setEdges((eds) => addEdge(params, eds));

  const { data: graphData } = useQuery({
    queryKey: ['graph-index'],
    queryFn: async () => {
      const res = await fetch('/jarvis/graph-index');
      if (!res.ok) throw new Error('Failed to fetch graph');
      return res.json();
    }
  });

  const { data: brickMeta } = useQuery({
    queryKey: ['brick-meta', selectedBrickId],
    queryFn: async () => {
      const res = await fetch(`/jarvis/brick-meta?brick_id=${selectedBrickId}`);
      if (!res.ok) throw new Error('Failed to fetch brick meta');
      return res.json();
    },
    enabled: !!selectedBrickId
  });

  const { data: brickFull } = useQuery({
    queryKey: ['brick-full', selectedBrickId],
    queryFn: async () => {
      const res = await fetch(`/jarvis/brick-full?brick_id=${selectedBrickId}`);
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!selectedBrickId
  });

  const askMutation = useMutation({
    mutationFn: async (q: string) => {
      const res = await fetch(`/jarvis/ask-preview?query=${encodeURIComponent(q)}&use_genai=${useGenAI}`);
      if (!res.ok) throw new Error('Query failed');
      return res.json();
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `I found ${data.top_bricks.length} matching bricks for your query.`,
        bricks: data.top_bricks
      }]);
    }
  });

  const promoteMutation = useMutation({
    mutationFn: async ({ nodeId }: { nodeId: string }) => {
      const res = await fetch('/jarvis/node/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, promote_bricks: [], actor: 'user' })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Promote failed');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graph-index'] });
    }
  });

  const killMutation = useMutation({
    mutationFn: async ({ nodeId }: { nodeId: string }) => {
      const res = await fetch('/jarvis/node/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, reason: 'Killed via UI', actor: 'user' })
      });
      if (!res.ok) {
         const err = await res.json();
         throw new Error(err.error || 'Kill failed');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['graph-index'] });
    }
  });

  // Prepare data for WallView
  const wallBricks = useMemo<NexusNodeProps[]>(() => {
    if (!graphData || !graphData.nodes) return [];
    const rawNodes = Array.isArray(graphData.nodes) ? graphData.nodes : graphData.nodes.nodes;
    const rawEdges = Array.isArray(graphData.edges) ? graphData.edges : (graphData.edges?.edges || []);

    return rawNodes.map((n: any) => {
      const sourceCount = rawEdges.filter((e: any) => 
        e.source === n.id && e.type === 'derived_from'
      ).length;

      const title = n.statement ? (n.statement.length > 50 ? n.statement.substring(0, 50) + '...' : n.statement) : (n.label || n.id);
      const summary = n.statement || n.summary || 'No content available.';

      return {
        id: n.id,
        title: title,
        summary: summary,
        lifecycle: ((n.status || n.lifecycle || 'loose').toUpperCase() as Lifecycle),
        confidence: n.confidence || 0.5,
        sourceCount: sourceCount,
        lastUpdatedAt: n.updated_at || n.created_at ? new Date(n.updated_at || n.created_at).toLocaleDateString() : 'Today',
        isFocused: false,
        onSelect: () => {},
      };
    });
  }, [graphData]);

  const selectedBrickData = useMemo(() => {
    return wallBricks.find(b => b.id === selectedBrickId);
  }, [wallBricks, selectedBrickId]);

  const handlePromote = () => {
    if (selectedBrickId) {
      promoteMutation.mutate({ nodeId: selectedBrickId });
    }
  };

  const handleKill = () => {
    if (selectedBrickId) {
      killMutation.mutate({ nodeId: selectedBrickId });
    }
  };

  useEffect(() => {
    if (graphData && graphData.nodes) {
      const initialNodes = (Array.isArray(graphData.nodes) ? graphData.nodes : graphData.nodes.nodes).map((n: any, i: number) => ({
        id: n.id,
        type: 'nexus',
        position: { x: Math.random() * 800, y: Math.random() * 600 },
        data: { ...n, type: n.type || 'Fact' }
      }));
      const initialEdges = (Array.isArray(graphData.edges) ? graphData.edges : graphData.edges.edges).map((e: any) => ({
        id: `${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        label: e.type,
        animated: e.type === 'OVERRIDES'
      }));
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  }, [graphData]);

  const handleSend = () => {
    if (!query.trim()) return;
    const userQ = query;
    setMessages(prev => [...prev, { role: 'user', content: userQ }]);
    setQuery('');
    askMutation.mutate(userQ);
  };

  const navItems = [
    { id: 'ask', label: 'Ask & Recall', icon: MessageSquare },
    { id: 'explore', label: 'Explore Wall', icon: LayoutGrid },
    { id: 'visualize', label: 'Cortex Visualizer', icon: Maximize2 },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden flex-col md:flex-row">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-16 flex-col items-center py-6 glass-panel border-r z-20">
        <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center mb-10 shadow-[0_0_20px_rgba(0,128,255,0.4)]">
          <Activity className="text-primary-foreground w-6 h-6" />
        </div>
        
        <nav className="flex flex-col gap-6">
          {navItems.map((item) => (
            <button 
              key={item.id}
              onClick={() => setMode(item.id as any)}
              className={`p-3 rounded-xl transition-all ${mode === item.id ? 'bg-white/10 text-white shadow-inner' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
              title={item.label}
            >
              <item.icon className="w-6 h-6" />
            </button>
          ))}
        </nav>

        <div className="mt-auto">
           <button className="p-3 text-white/40 hover:text-white">
             <BookOpen className="w-6 h-6" />
           </button>
        </div>
      </aside>

      {/* Mobile Top Nav */}
      <div className="md:hidden h-14 glass-panel border-b flex items-center justify-between px-4 z-30">
        <div className="flex items-center gap-2">
           <Activity className="text-primary w-5 h-5" />
           <span className="font-bold tracking-tighter uppercase text-sm">Nexus Workbench</span>
        </div>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Mobile Dropdown Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="md:hidden absolute top-14 left-0 w-full glass-panel border-b z-20 flex flex-col p-4 gap-4"
          >
            {navItems.map((item) => (
               <button 
                key={item.id}
                onClick={() => { setMode(item.id as any); setMobileMenuOpen(false); }}
                className={`flex items-center gap-4 p-3 rounded-lg ${mode === item.id ? 'bg-primary/20 text-white' : 'text-white/60'}`}
               >
                 <item.icon className="w-5 h-5" />
                 <span className="font-semibold uppercase text-xs tracking-widest">{item.label}</span>
               </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Stage */}
      <main className="flex-1 flex flex-col relative bg-background overflow-hidden">
        <header className="hidden md:flex h-16 border-b border-white/5 items-center justify-between px-8 glass-panel sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg tracking-tighter uppercase">
              {mode === 'ask' ? 'Ask & Recall' : mode === 'explore' ? 'Knowledge Wall' : 'Visualizer'}
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] bg-primary/20 text-primary uppercase font-bold tracking-widest">Nexus v3</span>
          </div>
          
          <div className="flex items-center gap-4">
             {mode === 'explore' && (
              <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
                <button
                  onClick={() => setViewMode('wall')}
                  className={`p-1.5 rounded-md transition-all ${viewMode === 'wall' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white'}`}
                  title="Wall View"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('graph')}
                  className={`p-1.5 rounded-md transition-all ${viewMode === 'graph' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white'}`}
                  title="Graph View (Legacy)"
                >
                  <Network className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20 group-focus-within:text-primary transition-colors" />
              <input 
                type="text" 
                placeholder="Quick search..." 
                className="bg-black/40 border border-white/5 rounded-md py-1.5 pl-10 pr-4 text-xs w-64 focus:outline-none focus:border-primary/50 transition-all font-mono-data uppercase tracking-widest"
              />
            </div>
            <button 
              onClick={() => toggleRightPanel()}
              className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/60"
            >
              {rightPanelOpen ? <ChevronRight /> : <ChevronLeft />}
            </button>
          </div>
        </header>

        {/* Mobile Subheader */}
        <div className="md:hidden flex items-center justify-between px-4 py-2 border-b border-white/5 glass-panel">
            <h1 className="font-bold text-[10px] tracking-tighter uppercase text-white/60">
               {mode === 'ask' ? 'Ask & Recall' : mode === 'explore' ? 'Wall' : 'Visualizer'}
            </h1>
            <button 
              onClick={() => toggleRightPanel()}
              className="p-1 hover:bg-white/5 rounded transition-colors text-white/60"
            >
               <Activity className={`w-4 h-4 ${selectedBrickId ? 'text-primary' : 'opacity-20'}`} />
            </button>
        </div>

        <div className="flex-1 overflow-hidden relative">
          <AnimatePresence mode="wait">
            {mode === 'visualize' ? (
              <motion.div 
                key="visualize"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full w-full p-4 md:p-8"
              >
                <div className="flex flex-col h-full gap-4 md:gap-6">
                  <div className="hidden md:block">
                    <h2 className="text-2xl font-bold glitch-text uppercase tracking-widest" data-text="Cortex Visualizer">Cortex Visualizer</h2>
                    <p className="text-xs text-white/40 font-mono-data mt-1">LOCKED RULES: MODE-1 ACTIVE // NON-GENAI TOPIC LINKING</p>
                  </div>
                  
                  <div className="flex-1 min-h-0">
                    <CortexVisualizer 
                      data={{
                        nodes: graphData?.nodes || [],
                        edges: graphData?.edges || [],
                        type: 'graph'
                      }} 
                    />
                  </div>
                </div>
              </motion.div>
            ) : mode === 'ask' ? (
              <motion.div 
                key="chat"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="h-full flex flex-col max-w-4xl mx-auto w-full px-4 md:px-6"
              >
                <div className="flex-1 overflow-y-auto py-4 md:py-8 no-scrollbar">
                  {messages.map((msg, i) => (
                    <ChatMessage key={i} {...msg} />
                  ))}
                </div>
                
                <div className="pb-6 md:p-8">
                  {/* GenAI Toggle */}
                  <div className="flex items-center gap-4 md:gap-6 mb-4 px-2">
                    <span className="text-[9px] md:text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">Mode:</span>
                    <div className="flex bg-black/40 rounded-md p-1 border border-white/5">
                      <button
                        onClick={() => setUseGenAI(false)}
                        className={`px-2 md:px-3 py-1 rounded text-[9px] md:text-[10px] font-bold transition-all uppercase tracking-widest ${!useGenAI ? 'bg-white/10 text-white shadow-inner' : 'text-white/30'}`}
                      >
                        STD
                      </button>
                      <button
                        onClick={() => setUseGenAI(true)}
                        className={`px-2 md:px-3 py-1 rounded text-[9px] md:text-[10px] font-bold transition-all uppercase tracking-widest flex items-center gap-2 ${useGenAI ? 'bg-primary/20 text-primary shadow-[0_0_10px_rgba(59,130,246,0.3)]' : 'text-white/30'}`}
                      >
                        <Activity className="w-3 h-3" />
                        AI+
                      </button>
                    </div>
                  </div>

                  <div className="relative glass-panel rounded-lg p-2 shadow-2xl border-white/5">
                    <textarea 
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="CONSULT KNOWLEDGE ENGINE..."
                      className="w-full bg-transparent p-3 md:p-4 pr-12 md:pr-16 focus:outline-none resize-none text-white/90 text-sm font-mono-data tracking-tight"
                      rows={2}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                    />
                    <button 
                      onClick={handleSend}
                      className="absolute right-3 bottom-3 md:right-4 md:bottom-4 p-2 md:p-3 bg-primary rounded-md text-primary-foreground hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(0,128,255,0.5)]"
                    >
                      <Send className="w-4 h-4 md:w-5 md:h-5" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="explore"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-full w-full"
              >
                {viewMode === 'wall' ? (
                  <WallView 
                    bricks={wallBricks} 
                    selectedId={selectedBrickId} 
                    onSelect={setSelectedBrickId} 
                  />
                ) : (
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    nodeTypes={nodeTypes}
                    onNodeClick={(_, node) => setSelectedBrickId(node.id)}
                    fitView
                  >
                    <Background color="#222" gap={20} />
                    <Controls />
                  </ReactFlow>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Right Panel - Context & Evidence (Desktop Sidebar / Mobile Overlay) */}
      <AnimatePresence>
        {rightPanelOpen && selectedBrickId && (
          <motion.aside 
            initial={window.innerWidth < 768 ? { y: '100%' } : { x: 300, opacity: 0 }}
            animate={window.innerWidth < 768 ? { y: 0 } : { x: 0, opacity: 1 }}
            exit={window.innerWidth < 768 ? { y: '100%' } : { x: 300, opacity: 0 }}
            transition={panelTransition}
            className={`
               glass-panel border-white/10 flex flex-col overflow-hidden relative z-40
               ${window.innerWidth < 768 ? 'fixed bottom-0 left-0 w-full h-[80vh] rounded-t-3xl border-t' : 'border-l w-[400px]'}
            `}
          >
            <div className="p-4 md:p-6 border-b border-white/5 flex items-center justify-between">
               <h3 className="font-semibold uppercase text-xs tracking-[0.2em] text-white/40">Evidence_Viewer</h3>
               <button onClick={() => toggleRightPanel(false)} className="p-2 text-white/20 hover:text-white transition-colors">
                  <X className="w-5 h-5" />
               </button>
            </div>

            <div className="flex-1 overflow-y-auto p-0 no-scrollbar flex flex-col">
               {brickMeta ? (
                 <div className="flex-1 h-full p-4 md:p-6 pb-20 md:pb-6">
                   <Panel
                     nodeId={selectedBrickId}
                     lifecycle={selectedBrickData?.lifecycle || 'LOOSE'}
                     title={brickMeta.title || `Brick ${selectedBrickId.substring(0, 8)}`}
                     fullText={brickFull?.full_text || brickMeta.fullText || brickMeta.text_sample || 'No content available.'}
                     sources={brickMeta.sources || [brickMeta.source_file || 'Unknown source']}
                     conflicts={brickMeta.conflicts || []}
                     supersededBy={brickMeta.superseded_by}
                     history={brickMeta.history || [{ timestamp: 'Now', note: 'Viewed' }]}
                     onPromote={handlePromote}
                     onKill={handleKill}
                   />
                 </div>
               ) : (
                 <div className="p-8 text-center text-white/30 text-xs uppercase tracking-widest">
                   Loading Data Stream...
                 </div>
               )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}
