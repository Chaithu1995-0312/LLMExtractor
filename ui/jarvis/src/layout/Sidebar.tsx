import { 
  LayoutGrid, 
  Database, 
  Brain, 
  Network, 
  ShieldAlert, 
  Search, 
  Activity, 
  Server 
} from 'lucide-react';
import { useNexusStore } from '../store';

const navItems = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'ingestion', label: 'Ingestion', icon: Database },
  { id: 'cognition', label: 'Cognition', icon: Brain },
  { id: 'graph', label: 'Graph', icon: Network },
  { id: 'governance', label: 'Governance', icon: ShieldAlert },
  { id: 'recall', label: 'Recall', icon: Search },
  { id: 'audit', label: 'Audit', icon: Activity },
  { id: 'health', label: 'System Health', icon: Server },
];

export function Sidebar() {
  const { mode, setMode } = useNexusStore();

  return (
    <aside className="hidden md:flex w-20 flex-col items-center py-6 glass-panel border-r z-20 bg-background/95 backdrop-blur">
      <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center mb-8 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
        <Activity className="text-primary w-5 h-5" />
      </div>

      <nav className="flex flex-col gap-4 w-full px-2">
        {navItems.map((item) => (
          <button 
            key={item.id}
            onClick={() => setMode(item.id as any)}
            className={`
              group relative flex flex-col items-center justify-center p-3 rounded-xl transition-all duration-200
              ${mode === item.id 
                ? 'bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(59,130,246,0.1)]' 
                : 'text-white/40 hover:text-white hover:bg-white/5'
              }
            `}
            title={item.label}
          >
            <item.icon className={`w-6 h-6 mb-1 transition-transform group-hover:scale-110 ${mode === item.id ? 'text-primary' : ''}`} />
            <span className="text-[9px] font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100 absolute left-16 bg-black/90 px-2 py-1 rounded border border-white/10 whitespace-nowrap z-50 pointer-events-none transition-opacity">
              {item.label}
            </span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
