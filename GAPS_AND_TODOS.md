# Gaps and Todos

## Critical Gaps (🔴)

### 1. Inactive Infrastructure Code
-   **Gap**: `Neo4jGraphManager` and `PineconeVectorIndex` are fully implemented but not wired into the active system.
-   **Risk**: Code rot. Future developers might be confused about which storage engine is authoritative.
-   **Action**: Decide to either migrate *to* them or delete them. Given "implementation reality", deleting or moving to `archive/` is recommended if SQLite/FAISS is sufficient.

### 2. Lack of Access Control (ACLs)
-   **Gap**: `recall_bricks` has a `scope` boost, but no hard enforcement prevents a user from accessing private bricks if the vector match is strong enough.
-   **Risk**: Data leakage between "Private" and "Global" scopes.
-   **Action**: Implement strict filtering in `LocalVectorIndex.search` or post-filtering in `recall_bricks`.

### 3. Missing Garbage Collection
-   **Gap**: If source files are modified or deleted, old bricks remain in `data/bricks/` and the FAISS index forever.
-   **Risk**: Index bloat and phantom recalls of deleted content.
-   **Action**: Implement a `purge` or `reindex` command.

## Technical Debt (🟡)

### 1. Frontend Integration
-   **Gap**: `ui/jarvis` exists but its connection to `CortexAPI` is verified only by `ask_preview`. The full "Assembly" or "Graph Visualization" features might be mocks.
-   **Action**: Audit `ui/jarvis/src/store.ts` to confirm API calls.

### 2. Hardcoded Routing Rules
-   **Gap**: `CortexAPI.route` uses hardcoded keywords (`"trade"`, `"architect"`).
-   **Risk**: Brittle and unscalable.
-   **Action**: Move to a configuration file or a small classifier model.

### 3. Dependency Management
-   **Gap**: `nexus.ask.recall` has global state (`_local_index`, `_brick_store`) initialized at module level.
-   **Risk**: Hard to test; circular import potential.
-   **Action**: Use a dependency injection container or factory pattern.

## Feature Requests (From Inferred Context)

### 1. Continuous Assembly
-   **Idea**: Instead of triggering `/assemble` manually, the system should auto-assemble topics when sufficient new bricks accumulate.

### 2. Multi-User Support
-   **Idea**: The current `conversations.json` ingestion implies a single-user or single-team perspective. Multi-tenancy is not supported.

### 3. Graph Visualization
-   **Idea**: Expose the SQLite graph via an interactive endpoint (e.g., Cytoscape or generic JSON) for the UI, replacing the likely-mocked `NexusNode.tsx`.
