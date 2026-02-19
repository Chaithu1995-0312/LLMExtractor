// ============================================================
//  Ephemeral UI Store — Plane 1 (Navigation / Selection / Panel)
//  This store is intentionally lean. It only holds UI-local
//  state that doesn't need to survive a page reload.
//
//  Domain state has been split into dedicated stores:
//  - Structural Bits (graph):  src/state/graph-store.ts
//  - Stream Bits (audit log):  src/state/stream-store.ts
//  - Governance / System:      src/state/system-store.ts
// ============================================================

import { create } from 'zustand';

export type AppMode =
  | 'overview'
  | 'ingestion'
  | 'cognition'
  | 'graph'
  | 'governance'
  | 'recall'
  | 'audit'
  | 'health';

interface NexusState {
  mode: AppMode;
  selectedBrickId: string | null;
  selectedNodeId: string | null;
  rightPanelOpen: boolean;

  setMode: (mode: AppMode) => void;
  setSelectedBrickId: (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  toggleRightPanel: (force?: boolean) => void;
}

export const useNexusStore = create<NexusState>((set) => ({
  mode: 'overview',
  selectedBrickId: null,
  selectedNodeId: null,
  rightPanelOpen: false,

  setMode: (mode) => set({ mode }),
  setSelectedBrickId: (id) =>
    set({ selectedBrickId: id, rightPanelOpen: id !== null }),
  setSelectedNodeId: (id) =>
    set({ selectedNodeId: id, rightPanelOpen: id !== null }),
  toggleRightPanel: (force) =>
    set((state) => ({
      rightPanelOpen: force !== undefined ? force : !state.rightPanelOpen,
    })),
}));

// ─── Re-exports for convenience ───────────────────────────────
// Import domain stores directly from their files for new code.
// These re-exports exist only for backward compatibility.
export { useGraphStore } from './state/graph-store';
export { useSystemStore } from './state/system-store';
export { useStreamStore } from './state/stream-store';
