# UI Gaps & TODOs

## 1. Critical User Experience Gaps
- [ ] **Accessibility (A11y)**: The UI fails WCAG 2.1 contrast ratios (Grey on Black). Needs a "High Contrast" mode for operators.
- [ ] **Mobile Support**: The layout breaks on screens < 1024px. The `Sidebar` and `ControlPanel` are fixed-width and consume too much space.
- [ ] **Empty States**: No "Zero State" designs for empty graphs, empty audit logs, or disconnected states.

## 2. Technical Debt
- [ ] **Graph Performance**: Cytoscape re-renders the entire graph on every delta update. Needs differential updating (only touching changed nodes).
- [ ] **Testing**: Zero unit or integration tests visible. Need `vitest` + `react-testing-library`.
- [ ] **Type Safety**: Some components use `any` for incoming props (seen in `CortexVisualizer.tsx`). Need stricter Zod validation at the boundary.

## 3. Missing Features
- [ ] **Search**: No global search bar to jump to specific nodes/intents.
- [ ] **Time Travel**: The backend supports it (via Audit Log), but the UI has no slider to replay the graph state.
- [ ] **Connection Status**: No visible indicator if the Socket.IO connection drops.

## 4. Governance
- [ ] **Auth Screens**: No Login/Logout flow. Assumes internal network access.
- [ ] **Role-Based Access**: All users see all controls. Need "Read-Only" vs "Admin" views.
