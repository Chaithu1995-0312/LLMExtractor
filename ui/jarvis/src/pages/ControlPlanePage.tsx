/**
 * ControlPlanePage.tsx
 * =====================
 * Nexus v2 Cognitive Control Plane — full-page layout.
 *
 * Layout:
 *   Top:    QueryConsole + AdvancedControls
 *   Main:   3-column grid of intelligence panels
 *   Bottom: SystemStateFooter (persistent)
 *
 * All panels are state-subscribers — they read from controlPlaneStore only.
 * No data flows through props between panels.
 */

import QueryConsole from '../components/control-plane/QueryConsole';
import AdvancedControls from '../components/control-plane/AdvancedControls';
import RouteInspector from '../components/control-plane/RouteInspector';
import ConfidencePanel from '../components/control-plane/ConfidencePanel';
import ExecutionTimeline from '../components/control-plane/ExecutionTimeline';
import HybridConflictPanel from '../components/control-plane/HybridConflictPanel';
import EscalationPanel from '../components/control-plane/EscalationPanel';
import RetrievalPanel from '../components/control-plane/RetrievalPanel';
import ResponsePanel from '../components/control-plane/ResponsePanel';
import SystemStateFooter from '../components/control-plane/SystemStateFooter';

export default function ControlPlanePage() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#030609',
        color: 'rgba(255,255,255,0.85)',
        overflow: 'hidden',
      }}
    >
      {/* ── Header strip ──────────────────────────────────────────── */}
      <div
        className="flex items-center gap-3 px-5 py-3 border-b border-white/5 bg-white/2"
      >
        <h1 className="text-[12px] font-black tracking-[0.2em] text-cyan-400 uppercase">
          Cognitive Control Plane
        </h1>
        <div className="h-3 w-px bg-white/10" />
        <span className="text-[9px] font-bold tracking-widest text-white/30 uppercase">
          Nexus Instance
        </span>
        <span className="ml-auto text-[8px] font-black tracking-widest text-cyan-400 bg-cyan-400/10 border border-cyan-400/30 px-2 py-1 rounded">
          V2.0.4-STABLE
        </span>
      </div>

      {/* ── Scrollable main body ───────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {/* Query input row */}
        <div style={{ marginBottom: 24 }}>
          <QueryConsole />
        </div>

        {/* Advanced controls (collapsible) */}
        <div style={{ marginBottom: 24 }}>
          <AdvancedControls />
        </div>

        {/* Main 3-column grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '20% 55% 25%',
            gap: 24,
            alignItems: 'start',
          }}
        >
          {/* Column 1: Route + Timeline */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <RouteInspector />
            <ExecutionTimeline />
          </div>

          {/* Column 2: Confidence + Hybrid Conflict + Escalation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <ConfidencePanel />
            <HybridConflictPanel />
            <EscalationPanel />
          </div>

          {/* Column 3: Retrieval + Response */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <RetrievalPanel />
            <ResponsePanel />
          </div>
        </div>
      </div>

      {/* ── Persistent system state footer ────────────────────────── */}
      <div style={{ flexShrink: 0, padding: '0 20px 10px' }}>
        <SystemStateFooter />
      </div>
    </div>
  );
}
