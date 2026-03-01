// ============================================================
//  AppLayout — Horizontal Nav Dashboard Shell
//  Replaces broken resizable-panels with a clean full-screen
//  flex layout: TopStatusBar → NavTabs → Main Content
// ============================================================

import { ReactNode } from 'react';
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
} from 'lucide-react';
import { TopStatusBar } from './TopStatusBar';
import { useNexusStore, type AppMode } from '../store';
import { ConnectionStatusBadge } from '../components/ConnectionStatusBadge';
import { GlobalSearch, GlobalSearchTrigger } from '../components/GlobalSearch';

// ─── Nav tab definitions (matching concept image) ─────────────
const NAV_TABS: { id: AppMode; label: string; accent?: string; icon: any }[] = [
  { id: 'overview',       label: 'COGNITIVE WALL', icon: LayoutDashboard },
  { id: 'graph',          label: 'GRAPH MAP',      icon: Network },
  { id: 'cognition',      label: 'INTENT FOCUS',   icon: Target },
  { id: 'audit',          label: 'AUDIT STREAM',   icon: Activity },
  { id: 'ingestion',      label: 'INGESTION',      icon: ArrowRightCircle },
  { id: 'governance',     label: 'GOVERNANCE',     icon: ShieldCheck },
  { id: 'health',         label: 'OPS CENTER',     icon: Zap },
  { id: 'control_plane',  label: 'CONTROL PLANE',  icon: Cpu, accent: '#00D9FF' },
];

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { mode, setMode } = useNexusStore();

  return (
    <div className="min-h-screen w-screen bg-[#030609] text-white/85">
      <div className="flex flex-col min-h-screen">
        {/* ── Top header (JARVIS branding) ──────────────── */}
        <TopStatusBar />

        {/* ── Horizontal nav tab bar ────────────────────── */}
        <nav
  className="flex flex-shrink-0 items-center px-2 h-10"
  style={{
    background: 'rgba(4, 8, 13, 0.95)',
    borderBottom: 'none',
    margin: 0,
     padding: 0,
  }}
>

        {/* Tab buttons */}
        {NAV_TABS.map((tab) => {
          const active = mode === tab.id;
          const accentColor = tab.accent ?? '#00D9FF';
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setMode(tab.id)}
              className="relative px-5 h-full flex items-center gap-2.5 transition-all group overflow-hidden"
              style={{
                fontSize: 10,
                fontWeight: active ? 800 : 600,
                letterSpacing: '0.12em',
                color: active ? accentColor : 'rgba(255,255,255,0.45)',
                background: active ? `linear-gradient(to bottom, ${accentColor}15, ${accentColor}05)` : 'transparent',
                borderBottom: active ? `2px solid ${accentColor}` : '2px solid transparent',
              }}
            >
              <Icon
                style={{
                  width: 14,
                  height: 14,
                  color: active ? accentColor : 'rgba(255,255,255,0.3)',
                  filter: active ? `drop-shadow(0 0 5px ${accentColor}80)` : 'none',
                }}
              />
              <span className="relative z-10">{tab.label}</span>

              {/* Active glow & background highlights */}
              {active && (
                <>
                  <div
                    className="absolute inset-0 opacity-20"
                    style={{
                      background: `radial-gradient(circle at center, ${accentColor}40 0%, transparent 70%)`,
                    }}
                  />
                  <span
                    className="absolute bottom-0 left-0 right-0 h-[2px]"
                    style={{
                      background: accentColor,
                      boxShadow: `0 0 15px 2px ${accentColor}`,
                    }}
                  />
                </>
              )}

              {/* Hover effect for inactive tabs */}
              {!active && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
                />
              )}
            </button>
          );
        })}

        {/* Right side controls */}
        <div className="ml-auto flex items-center gap-3 pr-2">
          {/* Global Search trigger */}
          <GlobalSearchTrigger />
          {/* Live WebSocket connection indicator */}
          <ConnectionStatusBadge />

          {[
            { Icon: Lock,     title: 'Security' },
            { Icon: Bell,     title: 'Alerts' },
            { Icon: Settings, title: 'Settings' },
          ].map(({ Icon, title }) => (
            <button
              key={title}
              title={title}
              className="p-1.5 rounded transition-colors"
              style={{ color: 'rgba(255,255,255,0.25)' }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = 'rgba(255,255,255,0.7)')
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = 'rgba(255,255,255,0.25)')
              }
            >
              <Icon style={{ width: 14, height: 14 }} />
            </button>
          ))}
          <div
            className="flex items-center gap-1.5 ml-2 px-2 py-1 rounded border"
            style={{
              borderColor: 'rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.03)',
            }}
          >
            <User style={{ width: 12, height: 12, color: 'rgba(255,255,255,0.4)' }} />
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: 'rgba(255,255,255,0.5)',
              }}
            >
              SYS_ADMIN
            </span>
          </div>
        </div>
      </nav>

        {/* ── Main content area ─────────────────────────── */}
        <main className="flex-1 overflow-hidden">
          <div className="h-full w-full overflow-auto">{children}</div>
        </main>
      </div>

      {/* ── Global Search overlay (mounted once at root) ── */}
      <GlobalSearch />
    </div>
  );
}
