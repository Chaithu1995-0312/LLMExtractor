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
        style={{
          padding: '10px 20px 6px',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.25em',
            color: '#22d3ee',
          }}
        >
          NEXUS
        </span>
        <span style={{ color: 'rgba(255,255,255,0.1)', fontSize: 10 }}>·</span>
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.2em',
            color: 'rgba(255,255,255,0.4)',
          }}
        >
          COGNITIVE CONTROL PLANE
        </span>
        <span
          style={{
            marginLeft: 6,
            fontSize: 8,
            fontWeight: 700,
            letterSpacing: '0.15em',
            color: 'rgba(16,185,129,0.7)',
            background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.2)',
            padding: '1px 7px',
            borderRadius: 3,
          }}
        >
          v2
        </span>
      </div>

      {/* ── Scrollable main body ───────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px 10px' }}>
        {/* Query input row */}
        <div style={{ marginBottom: 8 }}>
          <QueryConsole />
        </div>

        {/* Advanced controls (collapsible) */}
        <div style={{ marginBottom: 14 }}>
          <AdvancedControls />
        </div>

        {/* Main 3-column grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 12,
            alignItems: 'start',
          }}
        >
          {/* Column 1: Route + Timeline */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <RouteInspector />
            <ExecutionTimeline />
          </div>

          {/* Column 2: Confidence + Hybrid Conflict + Escalation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <ConfidencePanel />
            <HybridConflictPanel />
            <EscalationPanel />
          </div>

          {/* Column 3: Retrieval + Response */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
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
