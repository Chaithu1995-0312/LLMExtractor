# FILE_INDEX

## UI Source Tree

### `ui/jarvis/src/`

#### `App.tsx`
Main application orchestrator. Handles routing, global layout, and top-level data orchestration via TanStack Query.
- **`handleSend`**: Manages chat input and triggers recall mutations. (Risk: MED | Impact: Local State)
- **`getLayoutedElements`**: Calculates Dagre layout for React Flow nodes. (Risk: LOW | Impact: UI Layout)
- **`onNodesChange` / `onEdgesChange`**: Standard React Flow state handlers. (Risk: LOW | Impact: UI State)

#### `store.ts`
Zustand global store for UI mode and selection tracking.
- **`setMode`**: Switches between Ask, Explore, Visualize, and Audit. (Risk: LOW | Impact: UI Mode)
- **`setSelectedBrickId`**: Updates global selection and opens right panel. (Risk: LOW | Impact: Selection State)

### `ui/jarvis/src/components/`

#### `AuditPanel.tsx`
Real-time forensic audit log viewer.
- **`fetchEvents`**: Polls `/api/audit/events`. (Risk: LOW | Impact: Read-Only)

#### `ControlPanel.tsx`
Administrative "Terminal" for triggering backend cognitive tasks.
- **`triggerSync`**: Invokes background sync task. (Risk: MED | Impact: External API)

#### `CortexVisualizer.tsx`
Cytoscape-based n-dimensional graph visualization.
- **`useEffect (data transformation)`**: Maps backend graph nodes to Cytoscape elements. (Risk: LOW | Impact: UI Rendering)

#### `NexusNode.tsx`
Custom React Flow node component for "Knowledge Wall".
- **`NexusNode` (Functional Component)**: Renders node status, lifecycle, and confidence. (Risk: LOW | Impact: UI Rendering)

#### `NodeEditor.tsx`
Lifecycle management interface for promoting or killing nodes.
- **`onUpdate`**: Dispatches promotion/kill/supersede actions to the store/API. (Risk: HIGH | Impact: DB Write)

#### `WallView.tsx`
Grid-based explorer for the knowledge base.
- **`WallView` (Functional Component)**: Filters and renders `NexusNode` instances. (Risk: LOW | Impact: UI Rendering)

#### `Panel.tsx`
Evidence viewer sidebar showing full text, sources, and history.
- **`Panel` (Functional Component)**: Displays metadata for selected bricks. (Risk: LOW | Impact: UI Rendering)

#### `ControlStrip.tsx`
Context-aware action bar for rapid anchoring/rejection (Implied/Partial implementation).
- **Implied Methods**: `handleAnchor`, `handleReject`. (Risk: HIGH | Impact: DB Write)
