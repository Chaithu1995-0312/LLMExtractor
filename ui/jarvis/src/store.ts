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
  setSelectedBrickId: (id) => set({ selectedBrickId: id, rightPanelOpen: id !== null }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id, rightPanelOpen: id !== null }),
  toggleRightPanel: (force) => set((state) => ({ 
    rightPanelOpen: force !== undefined ? force : !state.rightPanelOpen 
  })),
}));
