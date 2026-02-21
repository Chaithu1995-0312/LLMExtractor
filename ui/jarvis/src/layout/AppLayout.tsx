// ============================================================
//  AppLayout — Horizontal Nav Dashboard Shell
//  Replaces broken resizable-panels with a clean full-screen
//  flex layout: TopStatusBar → NavTabs → Main Content
// ============================================================

import { ReactNode } from 'react';
import { Lock, Bell, Settings, User } from 'lucide-react';
import { TopStatusBar } from './TopStatusBar';
import { useNexusStore, type AppMode } from '../store';

// ─── Nav tab definitions (matching concept image) ─────────────
const NAV_TABS: { id: AppMode; label: string }[] = [
  { id: 'overview',    label: 'COGNITIVE WALL' },
  { id: 'graph',       label: 'GRAPH MAP' },
  { id: 'cognition',   label: 'INTENT FOCUS' },
  { id: 'audit',       label: 'AUDIT STREAM' },
  { id: 'governance',  label: 'GOVERNANCE' },
  { id: 'health',      label: 'OPS CENTER' },
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
          return (
            <button
              key={tab.id}
              onClick={() => setMode(tab.id)}
              className="relative px-5 h-full flex items-center transition-all"
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '0.15em',
                color: active
                  ? '#22d3ee'
                  : 'rgba(255,255,255,0.38)',
                borderBottom: active
                  ? '2px solid #22d3ee'
                  : '2px solid transparent',
                background: active
                  ? 'rgba(34,211,238,0.04)'
                  : 'transparent',
                boxShadow: active ? '0 0 8px 2px rgba(34, 211, 238, 0.5)' : 'none',
              }}
            >
              {tab.label}
              {/* Active glow */}
              {active && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{
                    background: '#22d3ee',
                    boxShadow: '0 0 8px 2px rgba(34,211,238,0.5)',
                  }}
                />
              )}
            </button>
          );
        })}

        {/* Right side controls */}
        <div className="ml-auto flex items-center gap-1 pr-2">
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
    </div>
  );
}
