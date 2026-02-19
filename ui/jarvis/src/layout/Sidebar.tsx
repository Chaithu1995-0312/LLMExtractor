import { 
  LayoutGrid, 
  Database, 
  Brain, 
  Network, 
  ShieldAlert, 
  Search, 
  Activity, 
  Server,
} from 'lucide-react';
import { useNexusStore } from '../store';

const navItems = [
  { id: 'overview',    label: 'Overview',       icon: LayoutGrid },
  { id: 'ingestion',   label: 'Ingestion',      icon: Database },
  { id: 'cognition',   label: 'Cognition',      icon: Brain },
  { id: 'graph',       label: 'Graph',           icon: Network },
  { id: 'governance',  label: 'Governance',     icon: ShieldAlert },
  { id: 'recall',      label: 'Recall',          icon: Search },
  { id: 'audit',       label: 'Audit',           icon: Activity },
  { id: 'health',      label: 'System Health',  icon: Server },
];

interface SidebarProps {
  /** When true, render icon-only compact mode */
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  const { mode, setMode } = useNexusStore();

  return (
    <aside
      className={`
        hidden md:flex flex-col items-center py-6
        glass-panel border-r z-20 bg-background/95 backdrop-blur
        h-full transition-all duration-300 overflow-hidden
        ${collapsed ? 'w-12 px-1' : 'w-20 px-2'}
      `}
    >
      {/* Logo mark */}
      <div className={`
        bg-primary/20 rounded-xl flex items-center justify-center mb-8
        shadow-[0_0_15px_rgba(59,130,246,0.2)] shrink-0 transition-all duration-300
        ${collapsed ? 'w-8 h-8' : 'w-10 h-10'}
      `}>
        <Activity className={`text-primary transition-all ${collapsed ? 'w-4 h-4' : 'w-5 h-5'}`} />
      </div>

      <nav className="flex flex-col gap-4 w-full">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setMode(item.id as any)}
            className={`
              group relative flex flex-col items-center justify-center
              rounded-xl transition-all duration-200
              ${collapsed ? 'p-2' : 'p-3'}
              ${mode === item.id
                ? 'bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(59,130,246,0.1)]'
                : 'text-white/40 hover:text-white hover:bg-white/5'
              }
            `}
            title={item.label}
          >
            <item.icon className={`
              transition-transform group-hover:scale-110
              ${collapsed ? 'w-4 h-4' : 'w-6 h-6 mb-1'}
              ${mode === item.id ? 'text-primary' : ''}
            `} />

            {/* Tooltip — always shown on hover, regardless of collapsed state */}
            <span className="
              text-[9px] font-bold uppercase tracking-wider
              opacity-0 group-hover:opacity-100
              absolute left-full ml-2 bg-black/90 px-2 py-1 rounded
              border border-white/10 whitespace-nowrap z-50
              pointer-events-none transition-opacity
            ">
              {item.label}
            </span>

            {/* Inline label (only in expanded mode) */}
            {!collapsed && (
              <span className="text-[8px] font-bold uppercase tracking-wider truncate w-full text-center opacity-50">
                {item.label}
              </span>
            )}
          </button>
        ))}
      </nav>
    </aside>
  );
}
