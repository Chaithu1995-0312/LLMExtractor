import { useState, useRef, useEffect } from 'react';
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
  ExternalLink
} from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
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
  addEdge
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NexusNode } from './components/NexusNode';

const nodeTypes = {
  nexus: NexusNode,
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
      className="my-4 bg-secondary/30 glass border border-white/5 p-4 rounded-lg overflow-auto cursor-zoom-in shadow-inner" 
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
      className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-8`}
    >
      <div className={`max-w-[85%] p-5 rounded-xl ${
        role === 'user' 
        ? 'bg-primary text-primary-foreground ml-12 shadow-[0_0_20px_-5px_rgba(59,130,246,0.3)]' 
        : 'glass-panel mr-12 shadow-2xl'
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
                <code className={`${className} bg-black/30 px-1 rounded`} {...props}>
                  {children}
                </code>
              );
            },
            p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed">{children}</p>,
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

const SegmentedBar = ({ confidence }: { confidence: number }) => {
  const segments = 10;
  const activeSegments = Math.round(confidence * segments);
  
  return (
    <div className="segmented-bar">
      {Array.from({ length: segments }).map((_, i) => (
        <div 
          key={i} 
          className={`segmented-bar-item ${i < activeSegments ? 'active' : ''}`}
        />
      ))}
    </div>
  );
};

export default function App() {
  const { mode, setMode, rightPanelOpen, toggleRightPanel, selectedBrickId, setSelectedBrickId, selectedNodeId, setSelectedNodeId } = useNexusStore();
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome to the **Nexus Workbench**. How can I help you explore the knowledge base today?' }
  ]);

  // React Flow State
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
    },
    enabled: mode === 'explore'
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

  const askMutation = useMutation({
    mutationFn: async (q: string) => {
      const res = await fetch(`/jarvis/ask-preview?query=${encodeURIComponent(q)}`);
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

  useEffect(() => {
    if (graphData && graphData.nodes) {
      const initialNodes = (Array.isArray(graphData.nodes) ? graphData.nodes : graphData.nodes.nodes).map((n: any, i: number) => ({
        id: n.id,
        type: 'nexus',
        position: { x: Math.random() * 400, y: i * 100 },
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

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* Left Sidebar - Navigation */}
      {/* Left Sidebar - Navigation */}
      <aside className="w-16 flex flex-col items-center py-6 glass-panel border-r z-20">
        <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center mb-10 shadow-[0_0_20px_rgba(0,128,255,0.4)]">
          <Activity className="text-primary-foreground w-6 h-6" />
        </div>
        
        <nav className="flex flex-col gap-6">
          <button 
            onClick={() => setMode('ask')}
            className={`p-3 rounded-xl transition-all ${mode === 'ask' ? 'bg-white/10 text-white shadow-inner' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
            title="Ask & Recall"
          >
            <MessageSquare className="w-6 h-6" />
          </button>
          <button 
            onClick={() => setMode('explore')}
            className={`p-3 rounded-xl transition-all ${mode === 'explore' ? 'bg-white/10 text-white shadow-inner' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
            title="Explore Graph"
          >
            <Share2 className="w-6 h-6" />
          </button>
        </nav>

        <div className="mt-auto">
           <button className="p-3 text-white/40 hover:text-white">
             <BookOpen className="w-6 h-6" />
           </button>
        </div>
      </aside>

      {/* Main Stage */}
      <main className="flex-1 flex flex-col relative bg-background">
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 glass-panel sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg tracking-tighter uppercase">
              {mode === 'ask' ? 'Ask & Recall' : 'Knowledge Browser'}
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] bg-primary/20 text-primary uppercase font-bold tracking-widest">Nexus v1</span>
          </div>
          
          <div className="flex items-center gap-4">
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

        <div className="flex-1 overflow-hidden relative">
          <AnimatePresence mode="wait">
            {mode === 'ask' ? (
              <motion.div 
                key="chat"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="h-full flex flex-col max-w-4xl mx-auto w-full px-6"
              >
                <div className="flex-1 overflow-y-auto py-8 no-scrollbar">
                  {messages.map((msg, i) => (
                    <ChatMessage key={i} {...msg} />
                  ))}
                </div>
                
                <div className="p-8">
                  <div className="relative glass-panel rounded-lg p-2 shadow-2xl border-white/5">
                    <textarea 
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="CONSULT KNOWLEDGE ENGINE..."
                      className="w-full bg-transparent p-4 pr-16 focus:outline-none resize-none text-white/90 text-sm font-mono-data tracking-tight"
                      rows={2}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                    />
                    <button 
                      onClick={handleSend}
                      className="absolute right-4 bottom-4 p-3 bg-primary rounded-md text-primary-foreground hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(0,128,255,0.5)]"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                  <p className="text-center text-white/20 text-[10px] mt-3 uppercase tracking-[0.2em]">
                    Powered by Nexus Agentic Cognition
                  </p>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="graph"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.02 }}
                className="h-full w-full"
              >
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  nodeTypes={nodeTypes}
                  onNodeClick={(_, node) => setSelectedNodeId(node.id)}
                  fitView
                >
                  <Background color="#222" gap={20} />
                  <Controls />
                </ReactFlow>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Right Panel - Context & Evidence */}
      <AnimatePresence>
        {rightPanelOpen && (
          <motion.aside 
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            transition={panelTransition}
            className="glass-panel border-l border-white/10 w-[400px] flex flex-col overflow-hidden relative z-10"
          >
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
               <h3 className="font-semibold uppercase text-xs tracking-[0.2em] text-white/40">Context & Evidence</h3>
               <button className="text-white/20 hover:text-white transition-colors">
                  <Maximize2 className="w-4 h-4" />
               </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-8 no-scrollbar">
               <section>
                 <h4 className="text-xs font-bold mb-4 text-primary flex items-center gap-2 uppercase tracking-widest">
                   <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                   Thinking Process
                 </h4>
                 <div className="bg-black/40 rounded-lg p-4 border border-white/5 shadow-inner">
                   <p className="text-xs text-white/60 leading-relaxed italic font-mono-data">
                     "Analyzing 12 relevant bricks across 3 architectural plans. Identifying override chain for Intent #892..."
                   </p>
                 </div>
               </section>

               <section>
                 <div className="flex items-center justify-between mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-widest text-white/40">Recalled Evidence</h4>
                    <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-white/40">
                      {[...messages].reverse().find(m => m.bricks)?.bricks?.length || 0} Total
                    </span>
                 </div>
                 
                 <div className="space-y-3">
                   {[...messages].reverse().find(m => m.bricks)?.bricks?.map((brick: any) => (
                     <motion.div 
                        key={brick.brick_id}
                        onClick={() => setSelectedBrickId(brick.brick_id)}
                        whileHover={{ x: 2, backgroundColor: 'rgba(255,255,255,0.02)' }}
                        whileTap={{ scale: 0.98 }}
                        className={`p-4 rounded-lg border transition-all cursor-pointer ${
                          selectedBrickId === brick.brick_id ? 'border-primary bg-primary/5 shadow-[0_0_15px_-5px_rgba(59,130,246,0.2)]' : 'border-white/5'
                        }`}
                     >
                       <div className="flex items-center justify-between mb-3">
                         <span className="text-[10px] font-mono-data text-primary font-bold">{brick.brick_id.substring(0, 16)}</span>
                         <div className="w-16">
                            <SegmentedBar confidence={brick.confidence} />
                         </div>
                       </div>
                       
                       {selectedBrickId === brick.brick_id && brickMeta && (
                         <motion.div 
                          initial={{ height: 0, opacity: 0 }} 
                          animate={{ height: 'auto', opacity: 1 }}
                          className="overflow-hidden"
                         >
                           <p className="text-[11px] text-white/50 mb-3 leading-relaxed border-l border-white/10 pl-3 italic">{brickMeta.text_sample}</p>
                           <div className="flex items-center gap-2 opacity-20 hover:opacity-50 transition-opacity">
                              <ExternalLink className="w-3 h-3" />
                              <span className="text-[9px] font-mono-data truncate">{brickMeta.source_file}</span>
                           </div>
                         </motion.div>
                       )}
                     </motion.div>
                   ))}
                 </div>
               </section>

               <section>
                 <h4 className="text-xs font-bold mb-4 text-white/40 uppercase tracking-widest">Mini-Graph Path</h4>
                 <div className="h-40 bg-secondary/20 rounded-xl border border-white/5 flex items-center justify-center">
                    <Share2 className="w-6 h-6 text-white/10" />
                 </div>
               </section>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}
