// ============================================================
//  System Reducer — Deterministic Health/Phase Processor
//  Receives SYSTEM_HEALTH and COGNITIVE_PHASE events from
//  the WebSocket delta dispatcher and drives both FSMs.
// ============================================================

import type {
  SystemHealthEvent,
  CognitivePhaseEvent,
  InboundEvent,
} from '../protocol/event-types';
import { useSystemStore } from '../state/system-store';

// ─── Event Handlers ───────────────────────────────────────────

export function handleSystemHealth(event: SystemHealthEvent): void {
  const { payload } = event;
  const store = useSystemStore.getState();

  store.applyHealthUpdate({
    db: payload.db,
    llm: payload.llm,
    sync: payload.sync,
    celery_workers: payload.celery_workers,
    last_sync: payload.last_sync,
  });
}

export function handleCognitivePhase(event: CognitivePhaseEvent): void {
  const { phase, topic_id } = event.payload;
  const store = useSystemStore.getState();

  // Map backend phase → FSM event
  const phaseToEvent: Record<string, Parameters<typeof store.sendCognitiveEvent>[0]> = {
    IDLE: 'RESET',
    SYNCING: 'SYNC_START',
    COMPILING: 'COMPILE_START',
    SYNTHESIZING: 'SYNTHESIZE_START',
    STREAMING: 'STREAM_START',
  };

  const fsmEvent = phaseToEvent[phase];
  if (fsmEvent) {
    store.sendCognitiveEvent(fsmEvent, topic_id);
  } else {
    console.warn(`[SystemReducer] Unknown cognitive phase: ${phase}`);
  }
}

/**
 * Adapt raw /api/health response to the store's health format.
 * Used at boot and during the 15s polling interval.
 */
export function hydrateHealthFromApi(raw: {
  db: string;
  redis: string;
  llm: string;
  celery_workers: number;
  last_sync: string;
}): void {
  const store = useSystemStore.getState();

  // Map legacy API status strings to protocol SystemStatus
  function mapStatus(s: string): 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'LOCK_RISK' {
    switch (s.toLowerCase()) {
      case 'healthy':
      case 'available':
      case 'online':
        return 'ONLINE';
      case 'degraded':
        return 'DEGRADED';
      case 'unhealthy':
      case 'offline':
        return 'OFFLINE';
      case 'lock_risk':
        return 'LOCK_RISK';
      default:
        return 'DEGRADED';
    }
  }

  store.applyHealthUpdate({
    db: mapStatus(raw.db),
    llm: mapStatus(raw.llm),
    sync: 'ONLINE',
    celery_workers: raw.celery_workers,
    last_sync: raw.last_sync,
  });

  // Signal boot complete on first successful health poll
  if (store.systemState === 'BOOTING') {
    store.markBooted();
  }
}

// ─── Main Dispatch Router ─────────────────────────────────────

export function dispatchSystemEvent(event: InboundEvent): boolean {
  switch (event.type) {
    case 'SYSTEM_HEALTH':
      handleSystemHealth(event as SystemHealthEvent);
      return true;
    case 'COGNITIVE_PHASE':
      handleCognitivePhase(event as CognitivePhaseEvent);
      return true;
    default:
      return false;
  }
}
