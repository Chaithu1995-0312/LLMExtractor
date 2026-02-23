# UI Rules & Invariants

## 1. Protocol Invariants
Strict rules governing the data exchange with the Cortex Backend.

### 🔴 Sequence Integrity
*   **Rule**: The UI MUST process `GraphEvents` in strict increasing sequence order.
*   **Enforcement**: `stream-store` checks `event.sequence == last_sequence + 1`.
*   **Fallout**: If a gap is detected, the UI MUST discard the event and request a full snapshot or delta-resync.

### 🔵 Read-Only Authority
*   **Rule**: The UI **NEVER** mutates domain state (Nodes/Edges) optimistically without a corresponding backend event.
*   **Reason**: The backend `GraphManager` is the single source of truth. Optimistic updates risk desync.
*   **Exception**: ephemeral UI state (e.g., selection highlighting, panel toggles).

## 2. Component Architecture Rules

### 🔒 Unidirectional Data Flow
*   **Rule**: Components read from Stores (`useGraphStore`) and dispatch Actions.
*   **Forbidden**: Components directly modifying store state or importing `set` functions outside of actions.

### 🧩 Visual Separation
*   **Rule**: `CortexVisualizer` is strictly a **Renderer**. It does not handle business logic.
*   **Input**: Receives `nodes` / `edges` prop.
*   **Output**: Emits `onNodeClick` events.
*   **Reason**: Keeps the heavy Cytoscape integration isolated from React state updates.

## 3. Styling Invariants (Cyberpunk Aesthetic)

### 🎨 The "Glass Pane" Look
*   **Rule**: All panels must use `backdrop-blur-sm`, `bg-[#05080a]/xx`, and `border-white/5`.
*   **Font**: Data must be `font-mono` (JetBrains Mono). Headers can be sans-serif.
*   **Scanlines**: The global `scanline` CSS class must be present on the root container.

## 4. Performance Guardrails

### ⚡ Virtualization Mandatory
*   **Rule**: Any list capable of unbounded growth (Audit Log, Node List) **MUST** use `@tanstack/react-virtual`.
*   **Limit**: Rendering > 100 DOM nodes for a list is forbidden.

### 🛑 Graph Throttling
*   **Rule**: `CortexVisualizer` updates must be debounced (e.g., 100ms) to prevent layout thrashing during high-volume syncs.
