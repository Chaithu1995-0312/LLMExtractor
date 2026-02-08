# GAPS_AND_TODOS

## Backend Capabilities Missing from UI
The following functionalities are implemented in the `services/cortex` backend or the `nexus` core but lack dedicated user interfaces or are only partially exposed.

| Backend Feature | Implementation | UI Status | Priority | Gap Description |
|-----------------|----------------|-----------|----------|-----------------|
| **Topic Synthesis** | `cognition/synthesize` | 🟡 Partial | MED | Triggerable via Terminal, but lacks a "Status View" for long-running Celery tasks. |
| **Run Deep-Dive** | `/api/runs/<run_id>` | 🔴 Missing | HIGH | No UI component to view detailed execution traces of a specific agent run. |
| **System Prompts** | `/api/prompts` | 🟡 Partial | LOW | Prompt text can be fetched, but the UI lacks an "Editor" for fine-tuning system prompts. |
| **Manual Anchor** | `/jarvis/anchor` | 🟡 Partial | HIGH | UI supports promotion of existing nodes, but lacks a way to explicitly "Anchor" a raw brick before it becomes a graph node. |
| **Vector Management**| `maintenance/rebuild` | 🔴 Missing | LOW | Rebuilding the vector index requires CLI access; no UI button for index maintenance. |
| **Conversation Map**| `public/chat_mapping.json` | 🧪 Mocked | MED | Currently uses a static JSON file; needs dynamic API to map conversation IDs to human-friendly names. |

## Technical Debt & Refactoring
- [ ] **Unified Visualization Logic**: Merge the data transformation logic between `App.tsx` (React Flow) and `CortexVisualizer.tsx` (Cytoscape) into a shared adapter.
- [ ] **WebSocket Integration**: Replace 5s polling in `AuditPanel.tsx` with WebSockets for true real-time observability.
- [ ] **Error Boundaries**: Implement React Error Boundaries around the graph visualizers to prevent crashes on malformed backend data.
- [ ] **Mobile Optimization**: The `ControlPanel` and `AuditPanel` are currently desktop-first; they overlap awkwardly on smaller screens.

## Missing Implementation Hooks (🧪/🔴)
- **`handleAnchor` (ControlStrip.tsx)**: Missing logic to dispatch `POST /jarvis/anchor`.
- **`runDetailsView` (New Component)**: Required to visualize data from `/api/runs/<run_id>`.
- **`nodeMergeLogic` (Graph Manager)**: Backend supports merging nodes, but UI lacks a multi-select "Merge" action.
