// ============================================================
//  Stream Reducer — Deterministic Audit Event Processor
//  Receives AUDIT_EVENT events from the WebSocket dispatcher
//  and appends them to the stream buffer store.
// ============================================================

import type { AuditStreamEvent, InboundEvent } from '../protocol/event-types';
import { useStreamStore } from '../state/stream-store';

// ─── Event Handler ────────────────────────────────────────────

export function handleAuditEvent(event: AuditStreamEvent): void {
  useStreamStore
    .getState()
    .appendEvent(event.payload, event.sequence);
}

// ─── Adapt legacy Socket.IO raw event ────────────────────────
// The current server emits raw audit_event objects without
// the versioned envelope. This adapter normalises them.

export function adaptLegacyAuditEvent(raw: Record<string, unknown>): AuditStreamEvent {
  return {
    event_id: `legacy-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    sequence: -1, // Legacy events have no sequence
    timestamp: Date.now(),
    type: 'AUDIT_EVENT',
    payload: {
      timestamp: (raw.timestamp as string) ?? new Date().toISOString(),
      event: (raw.event as string) ?? 'UNKNOWN',
      component: (raw.component as string) ?? 'unknown',
      agent: (raw.agent as string) ?? 'system',
      topic_id: raw.topic_id as string | undefined,
      run_id: raw.run_id as string | undefined,
      model_tier: raw.model_tier as string | undefined,
      cost: raw.cost as AuditStreamEvent['payload']['cost'],
      decision: (raw.decision as { action: string; reason: string }) ?? {
        action: 'UNKNOWN',
        reason: '',
      },
      metadata: raw.metadata as Record<string, unknown> | undefined,
    },
  };
}

/**
 * Handle a raw legacy socket.io audit_event payload.
 * Used in AuditStreamPanel until the backend emits envelopes.
 */
export function handleLegacyAuditEvent(raw: Record<string, unknown>): void {
  const adapted = adaptLegacyAuditEvent(raw);
  handleAuditEvent(adapted);
}

// ─── Main Dispatch Router ─────────────────────────────────────

export function dispatchStreamEvent(event: InboundEvent): boolean {
  switch (event.type) {
    case 'AUDIT_EVENT':
      handleAuditEvent(event as AuditStreamEvent);
      return true;
    default:
      return false;
  }
}
