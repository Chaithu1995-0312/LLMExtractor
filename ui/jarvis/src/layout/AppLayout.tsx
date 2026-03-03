// ============================================================
//  AppLayout — Horizontal Nav Dashboard Shell
//  Replaces broken resizable-panels with a clean full-screen
//  flex layout: TopStatusBar → NavTabs → Main Content
// ============================================================

import { ReactNode, useState } from 'react';
import {
  Lock,
  Bell,
  Settings,
  User,
  LayoutDashboard,
  Network,
  Target,
  Activity,
  ArrowRightCircle,
  ShieldCheck,
  Zap,
  Cpu,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { TopStatusBar } from './TopStatusBar';
import { useNexusStore, type AppMode } from '../store';
import { GlobalSearch, GlobalSearchTrigger } from '../components/GlobalSearch';

// ─── Nav tab definitions (matching concept image) ─────────────
const NAV_TABS: { id: AppMode; label: string; accent?: string; icon: any }[] = [
  { id: 'overview',       label: 'WALL', icon: LayoutDashboard, accent: '#00D9FF' },
  { id: 'graph',          label: 'MAP',      icon: Network, accent: '#00D9FF' },
  { id: 'cognition',      label: 'FOCUS',   icon: Target, accent: '#00D9FF' },
  { id: 'audit',          label: 'AUDIT',   icon: Activity, accent: '#00D9FF' },
  { id: 'ingestion',      label: 'INGEST',      icon: ArrowRightCircle, accent: '#00D9FF' },
  { id: 'governance',     label: 'GOV',     icon: ShieldCheck, accent: '#00D9FF' },
  { id: 'health',         label: 'OPS',     icon: Zap, accent: '#00D9FF' },
  { id: 'control_plane',  label: 'CONTROL',  icon: Cpu, accent: '#00D9FF' },
];

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { mode, setMode } = useNexusStore();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen w-screen bg-[#030609] text-white/85 flex flex-col">
      {/* ── Top header (JARVIS branding) ──────────────── */}
      <TopStatusBar />

      <div className="flex flex-1 overflow-hidden">
        {/* ── Vertical sidebar navigation ────────────────────── */}
        <aside
          className="flex flex-col flex-shrink-0 border-r border-white/5 transition-all duration-300 relative"
          style={{
            width: collapsed ? '60px' : '200px',
            background: 'rgba(4, 8, 13, 0.95)',
          }}
        >
          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="absolute -right-3 top-4 bg-[#030609] border border-white/10 rounded-full p-1 text-white/40 hover:text-cyan-400 z-50 transition-colors"
          >
            {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
          </button>

          <div className="flex flex-col flex-1 py-4">
            {NAV_TABS.map((tab) => {
              const active = mode === tab.id;
              const accentColor = tab.accent ?? '#00D9FF';
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setMode(tab.id)}
                  className="relative px-5 py-3 flex items-center gap-3 transition-all group overflow-hidden"
                  style={{
                    color: active ? accentColor : 'rgba(255,255,255,0.45)',
                    background: active ? `linear-gradient(to right, ${accentColor}10, transparent)` : 'transparent',
                    borderLeft: active ? `2px solid ${accentColor}` : '2px solid transparent',
                  }}
                >
                  <Icon
                    style={{
                      width: 18,
                      height: 18,
                      color: active ? accentColor : 'rgba(255,255,255,0.3)',
                      filter: active ? `drop-shadow(0 0 5px ${accentColor}80)` : 'none',
                    }}
                  />
                  {!collapsed && (
                    <span className="text-[10px] font-bold tracking-[0.15em] uppercase">
                      {tab.label}
                    </span>
                  )}

                  {/* Active glow */}
                  {active && (
                    <div
                      className="absolute inset-0 opacity-10"
                      style={{
                        background: `radial-gradient(circle at left, ${accentColor} 0%, transparent 70%)`,
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Sidebar Footer: Secondary Actions */}
          <div className="p-4 border-t border-white/5 flex flex-col gap-2">
             <div className="flex items-center gap-3">
                <GlobalSearchTrigger />
                {!collapsed && <span className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Search</span>}
             </div>

            {[
              { Icon: Lock,     title: 'Security' },
              { Icon: Bell,     title: 'Alerts' },
              { Icon: Settings, title: 'Settings' },
            ].map(({ Icon, title }) => (
              <button
                key={title}
                title={title}
                className="flex items-center gap-3 p-1 rounded transition-colors text-white/25 hover:text-white/70"
              >
                <Icon size={16} />
                {!collapsed && <span className="text-[10px] font-bold uppercase tracking-widest">{title}</span>}
              </button>
            ))}

            <div
              className={`flex items-center gap-2 mt-2 p-2 rounded border border-white/5 bg-white/5 transition-all ${collapsed ? 'justify-center' : ''}`}
            >
              <User size={12} className="text-white/40" />
              {!collapsed && (
                <span className="text-[9px] font-extrabold tracking-widest text-white/50 uppercase">
                  SYS_ADMIN
                </span>
              )}
            </div>
          </div>
        </aside>

        {/* ── Main content area ─────────────────────────── */}
        <main className="flex-1 overflow-hidden relative">
          <div className="h-full w-full overflow-auto p-4">{children}</div>
        </main>
      </div>

      {/* ── Global Search overlay (mounted once at root) ── */}
      <GlobalSearch />
    </div>
  );
}
