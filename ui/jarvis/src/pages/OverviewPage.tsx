import { useEffect, useState } from 'react';
import { 
  MessageSquare, 
  Database, 
  Box, 
  Network, 
  Share2 
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

// --- Types ---
interface OverviewMetrics {
  conversations: number;
  source_runs: number;
  bricks: number;
  nodes: number;
  edges: number;
}

interface LifecycleMetrics {
  LOOSE: number;
  FORMING: number;
  FROZEN: number;
  SUPERSEDED: number;
  KILLED: number;
}

interface SystemHealth {
  db: 'healthy' | 'unhealthy';
  redis: 'healthy' | 'unhealthy';
  celery_workers: number;
  llm: 'available' | 'degraded';
  last_sync: string;
}

// --- Components ---

const KPICard = ({ title, value, icon: Icon, color }: { title: string; value: number; icon: any; color: string }) => (
  <div className="glass-panel p-4 rounded-xl flex flex-col justify-between border-white/5 bg-white/5 relative overflow-hidden group">
    <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full opacity-10 transition-transform group-hover:scale-150 ${color}`} />
    <div className="flex justify-between items-start z-10">
      <div>
        <p className="text-[10px] uppercase font-bold tracking-widest text-white/40 mb-1">{title}</p>
        <h3 className="text-3xl font-mono-data font-bold text-white/90">{value.toLocaleString()}</h3>
      </div>
      <div className={`p-2 rounded-lg bg-white/5 ${color.replace('bg-', 'text-')}`}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  </div>
);

const COLORS = {
  LOOSE: '#9CA3AF',      // Gray
  FORMING: '#FBBF24',    // Amber
  FROZEN: '#10B981',     // Emerald
  SUPERSEDED: '#6366F1', // Indigo
  KILLED: '#EF4444',     // Red
};

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [lifecycle, setLifecycle] = useState<LifecycleMetrics | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mRes, lRes, hRes] = await Promise.all([
          fetch('/api/metrics/overview'),
          fetch('/api/metrics/lifecycle'),
          fetch('/api/health')
        ]);
        
        if (mRes.ok) setMetrics(await mRes.json());
        if (lRes.ok) setLifecycle(await lRes.json());
        if (hRes.ok) setHealth(await hRes.json());
      } catch (e) {
        console.error("Failed to fetch overview data", e);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s refresh
    return () => clearInterval(interval);
  }, []);

  if (!metrics || !lifecycle || !health) {
    return <div className="h-full flex items-center justify-center text-white/30 text-xs uppercase tracking-widest">Loading System Telemetry...</div>;
  }

  const lifecycleData = Object.entries(lifecycle).map(([name, value]) => ({ name, value }));

  return (
    <div className="p-8 h-full overflow-y-auto no-scrollbar space-y-8">
      
      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KPICard title="Conversations" value={metrics.conversations} icon={MessageSquare} color="bg-blue-500" />
        <KPICard title="Source Runs" value={metrics.source_runs} icon={Database} color="bg-purple-500" />
        <KPICard title="Raw Bricks" value={metrics.bricks} icon={Box} color="bg-orange-500" />
        <KPICard title="Graph Nodes" value={metrics.nodes} icon={Network} color="bg-emerald-500" />
        <KPICard title="Edges" value={metrics.edges} icon={Share2} color="bg-pink-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Lifecycle Chart */}
        <div className="glass-panel p-6 rounded-xl col-span-2 flex flex-col">
          <h3 className="text-xs uppercase font-bold tracking-widest text-white/40 mb-6">Intent Lifecycle Distribution</h3>
          <div className="h-64 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={lifecycleData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {lifecycleData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS] || '#fff'} stroke="none" />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111', borderColor: '#333', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff', fontSize: '12px', textTransform: 'uppercase' }}
                />
                <Legend 
                  layout="vertical" 
                  verticalAlign="middle" 
                  align="right"
                  iconType="circle"
                  formatter={(value: string) => <span className="text-xs font-bold text-white/60 ml-2">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* System Health Detailed */}
        <div className="glass-panel p-6 rounded-xl space-y-6">
          <h3 className="text-xs uppercase font-bold tracking-widest text-white/40 mb-4">Infrastructure Status</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
              <span className="text-sm font-bold text-white/80">Database</span>
              <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${health.db === 'healthy' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                {health.db}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
              <span className="text-sm font-bold text-white/80">Redis Queue</span>
              <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${health.redis === 'healthy' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                {health.redis}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
              <span className="text-sm font-bold text-white/80">Celery Workers</span>
              <span className="px-2 py-1 rounded text-[10px] font-bold uppercase bg-blue-500/20 text-blue-500">
                {health.celery_workers} Active
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
              <span className="text-sm font-bold text-white/80">LLM Engine</span>
              <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${health.llm === 'available' ? 'bg-green-500/20 text-green-500' : 'bg-amber-500/20 text-amber-500'}`}>
                {health.llm}
              </span>
            </div>

            <div className="mt-8 pt-4 border-t border-white/10">
              <p className="text-[10px] text-white/40 uppercase tracking-widest mb-1">Last Sync Timestamp</p>
              <p className="font-mono-data text-xs text-white/80">
                {new Date(health.last_sync).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
