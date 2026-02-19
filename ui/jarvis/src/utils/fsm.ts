// ============================================================
//  Finite State Machine (FSM) Utility
//  A generic, typed FSM factory. Used by all 4 state machines
//  in the JARVIS runtime (Global System, Cognitive Engine,
//  Graph Node Lifecycle, Stream).
// ============================================================

export type FSMTransition<TState extends string, TEvent extends string> = {
  from: TState | TState[];
  event: TEvent;
  to: TState;
  guard?: () => boolean;
  effect?: () => void;
};

export interface FSMConfig<TState extends string, TEvent extends string> {
  initial: TState;
  transitions: FSMTransition<TState, TEvent>[];
  onIllegalTransition?: (from: TState, event: TEvent) => void;
}

export interface FSMInstance<TState extends string, TEvent extends string> {
  getState: () => TState;
  send: (event: TEvent) => boolean;
  can: (event: TEvent) => boolean;
  matches: (...states: TState[]) => boolean;
  reset: () => void;
}

/**
 * Create a deterministic FSM instance.
 *
 * @example
 * const machine = createFSM({
 *   initial: 'IDLE',
 *   transitions: [
 *     { from: 'IDLE', event: 'START_SYNC', to: 'SYNCING' },
 *     { from: 'SYNCING', event: 'DONE', to: 'IDLE' },
 *   ]
 * });
 * machine.send('START_SYNC'); // returns true
 * machine.getState(); // 'SYNCING'
 */
export function createFSM<TState extends string, TEvent extends string>(
  config: FSMConfig<TState, TEvent>
): FSMInstance<TState, TEvent> {
  let currentState: TState = config.initial;

  function findTransition(
    from: TState,
    event: TEvent
  ): FSMTransition<TState, TEvent> | undefined {
    return config.transitions.find((t) => {
      const fromMatch = Array.isArray(t.from)
        ? t.from.includes(from)
        : t.from === from;
      return fromMatch && t.event === event;
    });
  }

  return {
    getState: () => currentState,

    send(event: TEvent): boolean {
      const transition = findTransition(currentState, event);

      if (!transition) {
        config.onIllegalTransition?.(currentState, event);
        return false;
      }

      if (transition.guard && !transition.guard()) {
        return false;
      }

      currentState = transition.to;
      transition.effect?.();
      return true;
    },

    can(event: TEvent): boolean {
      const transition = findTransition(currentState, event);
      if (!transition) return false;
      if (transition.guard && !transition.guard()) return false;
      return true;
    },

    matches(...states: TState[]): boolean {
      return states.includes(currentState);
    },

    reset() {
      currentState = config.initial;
    },
  };
}

// ─── Pre-built JARVIS FSM Definitions ────────────────────────

// 1. Global System FSM
export type GlobalSystemState =
  | 'BOOTING'
  | 'READY'
  | 'DEGRADED'
  | 'CRITICAL'
  | 'RECOVERING';

export type GlobalSystemEvent =
  | 'BOOT_COMPLETE'
  | 'LLM_OFFLINE'
  | 'DB_FAILURE'
  | 'RECOVERY_START'
  | 'RECOVERY_COMPLETE'
  | 'HEALTH_RESTORED';

export function createGlobalSystemFSM() {
  return createFSM<GlobalSystemState, GlobalSystemEvent>({
    initial: 'BOOTING',
    transitions: [
      { from: 'BOOTING', event: 'BOOT_COMPLETE', to: 'READY' },
      { from: 'READY', event: 'LLM_OFFLINE', to: 'DEGRADED' },
      { from: 'READY', event: 'DB_FAILURE', to: 'CRITICAL' },
      { from: 'DEGRADED', event: 'DB_FAILURE', to: 'CRITICAL' },
      { from: 'DEGRADED', event: 'HEALTH_RESTORED', to: 'READY' },
      { from: 'CRITICAL', event: 'RECOVERY_START', to: 'RECOVERING' },
      { from: 'RECOVERING', event: 'RECOVERY_COMPLETE', to: 'READY' },
    ],
    onIllegalTransition: (from, event) => {
      console.warn(`[SystemFSM] Illegal transition: ${from} --${event}--> ?`);
    },
  });
}

// 2. Cognitive Engine FSM
export type CognitiveEngineState =
  | 'IDLE'
  | 'SYNCING'
  | 'COMPILING'
  | 'SYNTHESIZING'
  | 'STREAMING';

export type CognitiveEngineEvent =
  | 'SYNC_START'
  | 'SYNC_DONE'
  | 'COMPILE_START'
  | 'COMPILE_DONE'
  | 'SYNTHESIZE_START'
  | 'SYNTHESIZE_DONE'
  | 'STREAM_START'
  | 'STREAM_DONE'
  | 'RESET';

export function createCognitiveEngineFSM() {
  return createFSM<CognitiveEngineState, CognitiveEngineEvent>({
    initial: 'IDLE',
    transitions: [
      { from: 'IDLE', event: 'SYNC_START', to: 'SYNCING' },
      { from: 'SYNCING', event: 'SYNC_DONE', to: 'IDLE' },
      { from: 'IDLE', event: 'COMPILE_START', to: 'COMPILING' },
      { from: 'COMPILING', event: 'COMPILE_DONE', to: 'IDLE' },
      { from: 'IDLE', event: 'SYNTHESIZE_START', to: 'SYNTHESIZING' },
      { from: 'SYNTHESIZING', event: 'SYNTHESIZE_DONE', to: 'IDLE' },
      { from: 'SYNTHESIZING', event: 'STREAM_START', to: 'STREAMING' },
      { from: 'STREAMING', event: 'STREAM_DONE', to: 'IDLE' },
      {
        from: ['SYNCING', 'COMPILING', 'SYNTHESIZING', 'STREAMING'],
        event: 'RESET',
        to: 'IDLE',
      },
    ],
  });
}

// 3. Stream Connection FSM
export type StreamState =
  | 'DISCONNECTED'
  | 'CONNECTED'
  | 'STREAMING'
  | 'BUFFERING'
  | 'RESYNC_REQUIRED';

export type StreamEvent =
  | 'CONNECT'
  | 'FIRST_EVENT'
  | 'BUFFER_FULL'
  | 'SEQ_GAP_DETECTED'
  | 'RESYNC_DONE'
  | 'DISCONNECT';

export function createStreamFSM() {
  return createFSM<StreamState, StreamEvent>({
    initial: 'DISCONNECTED',
    transitions: [
      { from: 'DISCONNECTED', event: 'CONNECT', to: 'CONNECTED' },
      { from: 'CONNECTED', event: 'FIRST_EVENT', to: 'STREAMING' },
      { from: 'STREAMING', event: 'BUFFER_FULL', to: 'BUFFERING' },
      { from: 'BUFFERING', event: 'FIRST_EVENT', to: 'STREAMING' },
      {
        from: ['STREAMING', 'BUFFERING'],
        event: 'SEQ_GAP_DETECTED',
        to: 'RESYNC_REQUIRED',
      },
      { from: 'RESYNC_REQUIRED', event: 'RESYNC_DONE', to: 'STREAMING' },
      {
        from: ['CONNECTED', 'STREAMING', 'BUFFERING', 'RESYNC_REQUIRED'],
        event: 'DISCONNECT',
        to: 'DISCONNECTED',
      },
    ],
    onIllegalTransition: (from, event) => {
      console.warn(`[StreamFSM] Illegal transition: ${from} --${event}--> ?`);
    },
  });
}
