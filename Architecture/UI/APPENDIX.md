# APPENDIX

## Master Class → Method Intelligence Table

| Class / Component | Method | Responsibility | Risk | Inputs | Outputs | Idempotency | State Impact |
|-------------------|--------|----------------|------|--------|---------|-------------|--------------|
| `App.tsx` | `handleSend` | Orchestrates query flow | MED | Query String | Chat History Update | ✅ | Messages State |
| `App.tsx` | `getLayoutedElements` | Node positioning logic | LOW | Node/Edge List | Layouted Elements | ✅ | None (Pure) |
| `NodeEditor` | `onUpdate` | Lifecycle Write Gatekeeper | HIGH | ID, Action, Data | API Response | ✅ | DB State |
| `AuditPanel` | `fetchEvents` | Data ingestion from trail | LOW | Limit/Offset | Event List | ✅ | Local Events State |
| `CortexVisualizer` | `useEffect` (Data) | Cytoscape transformation | LOW | Graph Data | Elements Array | ✅ | Component Elements |
| `ControlPanel` | `triggerSync` | Manual Graph/Vector Sync | MED | None | Task ID | ✅ | Background Task |
| `useNexusStore` | `setSelectedBrickId` | Global Selection Setter | LOW | ID | Store Update | ✅ | selection/panelOpen |

## Method Usage Graph & Ripple Effect

| Method | Called By | Layer | Type | Impact Zone |
|--------|-----------|-------|------|-------------|
| `handleSend` | `App` (Keyboard/Click) | UI | Stateful | Chat Interface |
| `onUpdate` | `NodeEditor` (User Action) | Service | Transactional | Graph Database (SQLite/JSON) |
| `fetchEvents` | `AuditPanel` (Interval) | Ingestion | Read-only | Observatory Dashboard |
| `promote_node` | `Cortex API` | Cognition | Write-Auth | Global Truth Model |
| `recall_bricks` | `Cortex API` | Graph | Pure | Semantic Recall Accuracy |

## Governance & Boundary Labeling

| Component / Method | Boundary Type | Governance Role |
|--------------------|---------------|-----------------|
| `NodeEditor` | Write Boundary | Enforces that only valid actions ('promote', 'kill', 'supersede') are sent to the backend. |
| `AuditPanel` | Security Boundary | Provides read-only visibility into internal agent decisions (forensic trail). |
| `useNexusStore` | Lifecycle Gatekeeper | Manages the primary UI context, ensuring visual synchronization across modes. |
| `getLayoutedElements`| Safety Rail | Prevents manual node dragging from corrupting the logical hierarchical representation. |

## Implied Methods (🧪/🔴)

| Method Name | Status | Description |
|-------------|--------|-------------|
| `handleAnchor` | 🧪 | Implied action in `ControlStrip` to register a raw brick as an anchor. |
| `handleReject` | 🧪 | Implied action in `ControlStrip` to mark a brick as non-knowledge. |
| `showRunTrace` | 🔴 | Planned method to navigate from an audit event to a full execution visualization. |
| `mergeNodes` | 🔴 | Planned method to consolidate multiple graph nodes into a single entity. |
