// ============================================================
//  Stream Store (Stream Bits — Plane 2)
//  Append-only audit log buffer. NEVER triggers full re-render.
//  Uses a capped circular buffer (max 500 events) and drives
//  the Stream FSM for connection state tracking.
// ============================================================

import { create } from 'zustand';
import type { AuditEventPayload } from '../protocol/event-types';
import {
  createStreamFSM,
  type StreamState,
  type StreamEvent,
} from '../utils/fsm';

// Singleton stream FSM
const streamFSM = createStreamFSM();

const MAX_EVENTS = 500;
const SEQ_GAP_THRESHOLD = 10;

export interface StreamStoreState {
  // ─── Connection State (FSM-driven) ───────────────────────
  connectionState: StreamState;

  // ─── Append-only event buffer (capped) ───────────────────
  events: AuditEventPayload[];

  // ─── Sequence guard ──────────────────────────────────────
  lastEventSequence: number;
  gapDetected: boolean;

  // ─── Filter state (Ephemeral UI — kept here for co-location)
  activeFilter: string; // component filter

  // ─── Actions ─────────────────────────────────────────────

  /** Append a single audit event (append-only, never replace) */
  appendEvent: (event: AuditEventPayload, sequence?: number) => void;

  /** Bulk append events (e.g. after resync) */
  appendEvents: (events: AuditEventPayload[]) => void;

  /** Drive the stream FSM */
  sendStreamEvent: (event: StreamEvent) => void;

  /** Clear all buffered events (e.g. on reconnect + full resync) */
  clearEvents: () => void;

  /** Set active component filter */
  setFilter: (filter: string) => void;

  /** Mark gap as resolved */
  resolveGap: () => void;
}

export const useStreamStore = create<StreamStoreState>((set, get) => ({
  connectionState: 'DISCONNECTED',
  events: [],
  lastEventSequence: -1,
  gapDetected: false,
  activeFilter: '',

  appendEvent(event, sequence) {
    set((state) => {
      // Sequence gap detection
      let gapDetected = state.gapDetected;
      let lastSeq = state.lastEventSequence;

      if (sequence !== undefined) {
        const expectedNext = state.lastEventSequence + 1;
        const gap = sequence - expectedNext;
        if (state.lastEventSequence >= 0 && gap > SEQ_GAP_THRESHOLD) {
          gapDetected = true;
          streamFSM.send('SEQ_GAP_DETECTED');
          console.warn(`[StreamStore] Sequence gap detected: expected ${expectedNext}, got ${sequence}`);
        }
        lastSeq = sequence;
      }

      // Drive FSM: first event transitions CONNECTED → STREAMING
      if (state.connectionState === 'CONNECTED') {
        streamFSM.send('FIRST_EVENT');
      }

      // Append with circular cap — drop oldest when at MAX
      const newEvents =
        state.events.length >= MAX_EVENTS
          ? [...state.events.slice(1), event]
          : [...state.events, event];

      return {
        events: newEvents,
        lastEventSequence: lastSeq,
        gapDetected,
        connectionState: streamFSM.getState(),
      };
    });
  },

  appendEvents(events) {
    if (events.length === 0) return;
    set((state) => {
      const combined = [...state.events, ...events];
      const capped =
        combined.length > MAX_EVENTS
          ? combined.slice(combined.length - MAX_EVENTS)
          : combined;
      return { events: capped };
    });
  },

  sendStreamEvent(event) {
    const succeeded = streamFSM.send(event);
    if (!succeeded) {
      console.warn(`[StreamStore] FSM rejected event: ${event} from state: ${streamFSM.getState()}`);
      return;
    }
    set({ connectionState: streamFSM.getState() });
  },

  clearEvents() {
    set({ events: [], lastEventSequence: -1, gapDetected: false });
  },

  setFilter(filter) {
    set({ activeFilter: filter });
  },

  resolveGap() {
    streamFSM.send('RESYNC_DONE');
    set({
      gapDetected: false,
      connectionState: streamFSM.getState(),
    });
  },
}));

// ─── Derived selector: filtered events ───────────────────────
// Usage: const filtered = useFilteredEvents();
export function useFilteredEvents(): AuditEventPayload[] {
  const { events, activeFilter } = useStreamStore();
  if (!activeFilter) return events;
  return events.filter((e) => e.component === activeFilter);
}
