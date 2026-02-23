# UI File Index & Component Intelligence

## 1. Components (`src/components`)

### `src/components/CortexVisualizer.tsx`
**Core Visualization**: Renders the graph.
*   **Risk**: HIGH (Performance bottleneck)
*   **Props**: `data: { nodes, edges }`
*   **Logic**: Maps backend nodes to Cytoscape elements. Handles layout (`dagre`) and styling based on lifecycle.

### `src/components/AuditStreamPanel.tsx`
**Live Feed**: Displays the governance log.
*   **Risk**: MED (High frequency updates)
*   **Logic**: Subscribes to `stream-store`. Renders virtualized list of `AuditEvents`.

### `src/components/ControlPanel.tsx`
**Interactivity**: Global controls.
*   **Risk**: LOW
*   **Logic**: Dispatches actions to `system-store` (e.g., Trigger Sync, Change Mode).

### `src/components/NexusNode.tsx`
**Detail View**: Individual node inspector.
*   **Risk**: LOW
*   **Logic**: Displays node metadata (Confidence, Lifecycle) and allows editing/promotion.

## 2. State Management (`src/state`)

### `src/store.ts` (Root)
**Ephemeral UI State**.
*   **Scope**: Selection, Navigation, Panels.
*   **Persistence**: None (Reset on reload).

### `src/state/graph-store.ts`
**Structural Data**.
*   **Scope**: Nodes, Edges, Graph Topology.
*   **Logic**: Merges incoming deltas (`NODE_PATCH`) into local graph state.

### `src/state/stream-store.ts`
**Temporal Data**.
*   **Scope**: Audit Logs, System Health.
*   **Logic**: Appends new events to a rolling buffer.

## 3. Protocol (`src/protocol`)

### `src/protocol/event-types.ts`
**Contract Definition**.
*   **Risk**: **CRITICAL** (Must match backend)
*   **Content**: TypeScript interfaces for `EventEnvelope`, `NodeData`, `GraphEventType`.

### `src/protocol/validators.ts` (Inferred)
**Runtime Safety**.
*   **Logic**: Zod/Runtime checks to ensure incoming payloads match expected shapes.

## 4. Layout (`src/layout`)

### `src/layout/AppLayout.tsx`
**Shell**.
*   **Logic**: Grid structure (Sidebar, Main, RightPanel). Handles responsiveness (if any).
