import { create } from 'zustand';

interface NexusState {
  mode: 'ask' | 'explore' | 'visualize' | 'audit';
  selectedBrickId: string | null;
  selectedNodeId: string | null;
  rightPanelOpen: boolean;
  
  setMode: (mode: 'ask' | 'explore' | 'visualize' | 'audit') => void;
  setSelectedBrickId: (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  toggleRightPanel: (force?: boolean) => void;
}

export const useNexusStore = create<NexusState>((set) => ({
  mode: 'ask',
  selectedBrickId: null,
  selectedNodeId: null,
  rightPanelOpen: true,

  setMode: (mode) => set({ mode }),
  setSelectedBrickId: (id) => set({ selectedBrickId: id, rightPanelOpen: id !== null }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id, rightPanelOpen: id !== null }),
  toggleRightPanel: (force) => set((state) => ({ 
    rightPanelOpen: force !== undefined ? force : !state.rightPanelOpen 
  })),
}));
