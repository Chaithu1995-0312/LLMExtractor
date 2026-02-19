// ============================================================
//  System Store (Governance Bits — Plane 4 + Global FSM)
//  Drives: TopStatusBar, global glow, disabled interactions.
//  Transitions are enforced by the Global System FSM.
// ============================================================

import { create } from 'zustand';
import type { SystemStatus } from '../protocol/event-types';
import {
  createGlobalSystemFSM,
  createCognitiveEngineFSM,
  type GlobalSystemState,
  type GlobalSystemEvent,
  type CognitiveEngineState,
  type CognitiveEngineEvent,
} from '../utils/fsm';

// Singleton FSMs (live outside React, driven by store actions)
const globalSystemFSM = createGlobalSystemFSM();
const cognitiveEngineFSM = createCognitiveEngineFSM();

export interface SystemHealth {
  db: SystemStatus;
  redis: SystemStatus;
  llm: SystemStatus;
  sync: SystemStatus;
  celery_workers: number;
  last_sync: string;
}

export interface SystemStoreState {
  // ─── Global System FSM ───────────────────────────────────
  systemState: GlobalSystemState;

  // ─── Cognitive Engine FSM ────────────────────────────────
  cognitivePhase: CognitiveEngineState;
  activeTopic: string | null;

  // ─── Raw health data (from backend) ─────────────────────
  health: SystemHealth | null;

  // ─── Derived UI flags ────────────────────────────────────
  /** Whether any interaction should be globally disabled */
  isSystemCritical: boolean;
  /** Whether backend is currently processing something */
  isProcessing: boolean;

  // ─── Actions ─────────────────────────────────────────────

  /** Drive the global system FSM with an event */
  sendSystemEvent: (event: GlobalSystemEvent) => void;

  /** Drive the cognitive engine FSM with an event */
  sendCognitiveEvent: (event: CognitiveEngineEvent, topicId?: string) => void;

  /** Update raw health data (from API poll or WebSocket) */
  applyHealthUpdate: (health: Partial<SystemHealth>) => void;

  /** Boot sequence complete */
  markBooted: () => void;
}

export const useSystemStore = create<SystemStoreState>((set) => ({
  systemState: 'BOOTING',
  cognitivePhase: 'IDLE',
  activeTopic: null,
  health: null,
  isSystemCritical: false,
  isProcessing: false,

  sendSystemEvent(event) {
    const succeeded = globalSystemFSM.send(event);
    if (!succeeded) {
      console.warn(`[SystemStore] FSM rejected event: ${event} from state: ${globalSystemFSM.getState()}`);
      return;
    }

    const newState = globalSystemFSM.getState();
    set({
      systemState: newState,
      isSystemCritical: newState === 'CRITICAL',
    });
  },

  sendCognitiveEvent(event, topicId) {
    const succeeded = cognitiveEngineFSM.send(event);
    if (!succeeded) {
      console.warn(`[SystemStore] CognitiveFSM rejected event: ${event} from state: ${cognitiveEngineFSM.getState()}`);
      return;
    }

    const newPhase = cognitiveEngineFSM.getState();
    set({
      cognitivePhase: newPhase,
      activeTopic: topicId ?? null,
      isProcessing: newPhase !== 'IDLE',
    });
  },

  applyHealthUpdate(partialHealth) {
    set((state) => {
      const merged: SystemHealth = {
        ...(state.health ?? {
          db: 'ONLINE',
          redis: 'ONLINE',
          llm: 'ONLINE',
          sync: 'ONLINE',
          celery_workers: 0,
          last_sync: new Date().toISOString(),
        }),
        ...partialHealth,
      };

      // Drive FSM from health data
      if (merged.db === 'OFFLINE') {
        globalSystemFSM.send('DB_FAILURE');
      } else if (merged.llm === 'OFFLINE' || merged.llm === 'DEGRADED') {
        globalSystemFSM.send('LLM_OFFLINE');
      } else if (state.systemState === 'DEGRADED' || state.systemState === 'CRITICAL') {
        globalSystemFSM.send('HEALTH_RESTORED');
      }

      return {
        health: merged,
        systemState: globalSystemFSM.getState(),
        isSystemCritical: globalSystemFSM.matches('CRITICAL'),
      };
    });
  },

  markBooted() {
    globalSystemFSM.send('BOOT_COMPLETE');
    set({
      systemState: globalSystemFSM.getState(),
      isSystemCritical: false,
    });
  },
}));
