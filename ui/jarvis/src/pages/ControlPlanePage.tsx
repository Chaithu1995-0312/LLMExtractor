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
          padding: '12px 20px',
          borderBottom: '1px solid rgba(0, 217, 255, 0.15)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexShrink: 0,
          background: 'rgba(0, 217, 255, 0.02)',
        }}
      >
        <h1
          style={{
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: '0.3em',
            color: '#00D9FF',
            textShadow: '0 0 10px rgba(0, 217, 255, 0.4)',
          }}
        >
          COGNITIVE CONTROL PLANE
        </h1>
        <div
          style={{
            height: 12,
            width: 1,
            background: 'rgba(255,255,255,0.15)',
          }}
        />
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.15em',
            color: 'rgba(255,255,255,0.4)',
            textTransform: 'uppercase',
          }}
        >
          Nexus Instance
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: 8,
            fontWeight: 800,
            letterSpacing: '0.1em',
            color: '#00D9FF',
            background: 'rgba(0, 217, 255, 0.1)',
            border: '1px solid rgba(0, 217, 255, 0.3)',
            padding: '2px 8px',
            borderRadius: 4,
            textShadow: '0 0 5px rgba(0, 217, 255, 0.5)',
          }}
        >
          V2.0.4-STABLE
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
