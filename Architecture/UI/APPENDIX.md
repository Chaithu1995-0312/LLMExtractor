# UI Appendix: Component Intelligence

## Component → Logic Map

| Component | Responsibility | Risk | Inputs (Props) | State Interactions |
| :--- | :--- | :---: | :--- | :--- |
| **CortexVisualizer** | Graph Rendering | HIGH | `nodes: Node[]`, `edges: Edge[]` | Reads nothing; pure render. |
| **AuditStreamPanel** | Stream Visualization | MED | None | Subscribes to `useStreamStore`. |
| **ControlPanel** | Global Commands | LOW | None | Writes to `useSystemStore`. |
| **NexusNode** | Node Detail/Edit | MED | `nodeId: string` | Reads `useGraphStore`. Writes `NODE_PATCH`. |
| **AppLayout** | Structure/Shell | LOW | `children: ReactNode` | Reads `useNexusStore` (Panel Toggles). |

## State Store Map

| Store | Responsibility | Persistence | Events Handled |
| :--- | :--- | :---: | :--- |
| **GraphStore** | Nodes, Edges | Memory | `NODE_CREATE`, `NODE_PATCH`, `EDGE_CREATE` |
| **StreamStore** | Audit Logs | Memory | `AUDIT_EVENT` |
| **SystemStore** | Health, Config | Memory | `SYSTEM_HEALTH` |
| **NexusStore** | UI Selection | Memory | (Local UI Actions only) |

## Event Envelope Structure
```typescript
interface EventEnvelope<T> {
  event_id: string;   // UUID
  sequence: number;   // Monotonic Int
  timestamp: number;  // Unix MS
  type: string;       // Event Type Enum
  payload: T;         // Typed Data
}
```
