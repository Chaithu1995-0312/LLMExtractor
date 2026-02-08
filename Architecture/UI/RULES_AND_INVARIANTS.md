# RULES_AND_INVARIANTS

## UI Architectural Invariants
1. **Unidirectional Selection**: Selecting a node in any visualizer (`WallView`, `CortexVisualizer`, `AskMode Bricks`) MUST update the global `selectedBrickId` in the Zustand store. The `Panel` component MUST only react to this global selection.
2. **Read/Write Separation**: 
    - All data fetching MUST use TanStack Query `useQuery` hooks.
    - All state mutations (Promotion, Killing, Sync) MUST use `useMutation` hooks to ensure cache invalidation.
3. **Layout Determinism**: The `App.tsx` layout engine (Dagre) MUST be used to calculate initial positions, but user-interacted positions in React Flow SHOULD be preserved until a manual "Re-layout" is triggered.

## Agent Safety Rails
These rules define "Do Not Touch" zones and mandatory verification hooks for automated agents interacting with the UI code.

### 1. Data Integrity & State
- **ZONE**: `store.ts`
- **RULE**: Never add component-specific state to the global store unless it is required for cross-module synchronization.
- **VERIFICATION**: Ensure every new state variable has a corresponding setter and clear documentation of which components consume it.

### 2. Lifecycle Boundaries
- **ZONE**: `NodeEditor.tsx` -> `onUpdate`
- **RULE**: Promotion or Killing of a node MUST be followed by a Query Invalidation of `['graph-index']`.
- **VERIFICATION**: Check that `queryClient.invalidateQueries` is called in the `onSuccess` handler of the mutation.

### 3. Visual Logic & Coordinate Systems
- **ZONE**: `CortexVisualizer.tsx` (Cytoscape)
- **RULE**: Do not mix React Flow coordinate logic with Cytoscape layout logic. They are independent visualization layers.
- **VERIFICATION**: Ensure `getLayoutedElements` in `App.tsx` remains specific to React Flow data structures.

## Mandatory Verification Hooks
- **Security**: Any action triggering a POST request to `/jarvis/node/*` MUST include the `actor` field (defaulting to 'user' in UI).
- **Governance**: Before a `supersede` action is dispatched, the UI MUST verify that `new_node_id` exists in the current `graph-index`.
- **Transparency**: Every cognitive assembly trigger in `ControlPanel.tsx` MUST be logged as a local event if the background task fails to initiate.
