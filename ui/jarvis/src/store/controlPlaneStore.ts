/**
 * controlPlaneStore.ts
 * =====================
 * Zustand store for the v2 Cognitive Control Plane.
 *
 * This is the single source of truth for all Control Plane UI state.
 * All panels subscribe here — no panel passes props to another panel.
 * No panel computes derived data — all data comes from the backend payload.
 */

import { create } from 'zustand';
import {
  ControlPlaneState,
  QueryExecutionPayload,
  OverrideFlags,
} from '../types/controlPlane';

interface ControlPlaneActions {
  setQuery: (q: string) => void;
  setLoading: (loading: boolean) => void;
  setResult: (result: QueryExecutionPayload) => void;
  setError: (error: string | null) => void;
  setOverrides: (overrides: OverrideFlags) => void;
  toggleAdvanced: () => void;
  reset: () => void;
}

const initialState: ControlPlaneState = {
  query: '',
  loading: false,
  result: null,
  error: null,
  overrides: {},
  advancedOpen: false,
};

export const useControlPlaneStore = create<ControlPlaneState & ControlPlaneActions>(
  (set) => ({
    ...initialState,

    setQuery: (query) => set({ query }),

    setLoading: (loading) => set({ loading, ...(loading ? { error: null } : {}) }),

    setResult: (result) =>
      set({
        result,
        loading: false,
        error: null,
      }),

    setError: (error) =>
      set({
        error,
        loading: false,
      }),

    setOverrides: (overrides) =>
      set((state) => ({
        overrides: { ...state.overrides, ...overrides },
      })),

    toggleAdvanced: () =>
      set((state) => ({ advancedOpen: !state.advancedOpen })),

    reset: () => set(initialState),
  })
);
