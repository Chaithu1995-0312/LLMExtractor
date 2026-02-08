# INFERRED_ENHANCEMENTS

Based on the architectural analysis of the Jarvis UI and Cortex backend, the following enhancements are proposed to improve agentic automation and user oversight.

## 1. Multi-Agent Orchestration UI
- **Concept**: A dedicated view to manage multiple concurrent agent runs.
- **Implementation**: Expand `ControlPanel.tsx` into a full-screen "Orchestration Deck" where users can spawn specialized agents (e.g., "Research Agent", "Critique Agent") and watch their progress in real-time via the `/api/audit/events` stream filtered by `run_id`.

## 2. Interactive Relationship Sculpting
- **Concept**: Allowing users to manually draw edges between nodes in the `CortexVisualizer`.
- **Implementation**: Enable Cytoscape's "Edgehandles" extension. When an edge is drawn, the UI should prompt for a relationship type (e.g., `supports`, `contradicts`) and dispatch a `register_edge` call to the `GraphManager`.

## 3. Semantic Drift Detection
- **Concept**: A visual alert system when a new brick significantly contradicts a `FROZEN` node.
- **Implementation**: 
    - **Backend**: Use the `LLM_Reranker` or a cross-encoder to calculate a "Conflict Score".
    - **UI**: Render a "Heat Map" or pulsing red edges in the `WallView` between conflicting units, forcing human audit before further synthesis.

## 4. Federated Knowledge Search
- **Concept**: Extending `Ask & Recall` to search external documentation (e.g., MDN, GitHub) alongside the local Nexus.
- **Implementation**: Add a "Search Scopes" toggle in `App.tsx`. If external scopes are selected, the `ask-preview` endpoint should trigger a search-capable agent to retrieve and ground external data.

## 5. Temporal Graph Playback
- **Concept**: A "Time Slider" to visualize how the knowledge graph evolved.
- **Implementation**: Leverage the `updated_at` / `created_at` timestamps in the graph index. Sliding the UI bar would filter nodes and edges, showing the incremental growth of the "Truth" over multiple extraction cycles.

## 6. Prompt Engineering Lab
- **Concept**: A live playground to test system prompts against specific bricks.
- **Implementation**: A "Lab" mode in the `AuditPanel`. Users could select a brick and a system prompt, trigger an on-the-fly `synthesize` task, and see the logical output without persisting it to the database.
