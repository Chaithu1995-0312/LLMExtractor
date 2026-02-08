# CANONICAL_OVERVIEW

## System Definition
The **Jarvis Workbench** is the primary visual interface for the Nexus Knowledge Engine. It is an agent-centric UI designed to facilitate human-in-the-loop oversight of autonomous knowledge extraction, graph synthesis, and cognitive assembly processes.

## Technology Stack
- **Framework**: React 18.2 (TypeScript)
- **Build Tool**: Vite 4.4
- **State Management**: 
    - **Global**: Zustand (Client-side UI state)
    - **Server**: TanStack Query (Data fetching, caching, and mutation synchronization)
- **Visualization**:
    - **React Flow**: Hierarchical "Knowledge Wall" and logical node connections.
    - **Cytoscape.js**: N-dimensional "Cortex" graph visualization with Dagre layout engine.
    - **Mermaid.js**: Inline logic diagrams for message content.
- **Styling**: Tailwind CSS + Framer Motion (Adaptive UI transitions)
- **Icons**: Lucide React

## External Surface Map
The UI interacts primarily with the `Cortex API` (Flask-based) as its gateway to the backend services.

| Dependency | Purpose | Failure Mode | Impact |
|------------|---------|--------------|--------|
| **Cortex API** | Primary Data Gateway | Timeout / 500 Error | UI displays "Loading Data Stream" indefinitely or shows empty state. |
| **Vector Index** | Semantic Search (Recall) | Index out of sync | `Ask & Recall` returns stale or irrelevant bricks. |
| **Graph DB** | Relationship Storage | Connection Refused | Visualizers fail to render edges; promotions fail. |
| **KaTeX** | Math Rendering | JS Error | LaTeX strings remain in raw format in chat/panels. |

## Primary Data Schemas
### Brick / Node Lifecycle
- **LOOSE**: Initial state of extracted knowledge unit.
- **FROZEN**: Promoted by user or agent; considered "Truth" in the graph.
- **KILLED**: Explicitly rejected or invalidated data.
- **SUPERSEDED**: Replaced by a more current or accurate node.

### State Transition Logic
1. `LOOSE` -> `FROZEN` via `jarvis/node/promote`
2. `LOOSE`/`FROZEN` -> `KILLED` via `jarvis/node/kill`
3. `FROZEN` -> `SUPERSEDED` via `jarvis/node/supersede` (requires reference to New Node ID)
