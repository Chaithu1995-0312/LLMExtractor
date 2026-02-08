# Inferred Enhancements

## 1. Zero-Copy Ingestion (Performance)
*   **Inference:** `NexusCompiler` currently loads entire raw logs into memory.
*   **Proposal:** Implement streaming JSON parser (`ijson`) to handle multi-GB conversation logs without OOM errors.
*   **Impact:** Reduce memory footprint by 90% during ingestion.

## 2. Graph-Aware RAG (Quality)
*   **Inference:** `CortexAPI` retrieves bricks via vector search but doesn't fully traverse the graph edges during context window construction.
*   **Proposal:** Implement "Graph Walk" in `_fetch_graph_context`. If a Brick is retrieved, automatically pull its `APPLIES_TO` Scope and any `CONFLICTS_WITH` nodes.
*   **Impact:** Responses will be more contextually accurate and aware of contradictions.

## 3. Automated Staleness Detection (Maintenance)
*   **Inference:** The `SUPERSEDED` state exists but is manual.
*   **Proposal:** Create a `ChronologicalAuditor` agent that scans `FROZEN` nodes older than X months and flags them for review (moves to `FORMING` or adds `REVIEW_NEEDED` tag).
*   **Impact:** Prevents knowledge rot.

## 4. Federated Knowledge Sync (Scale)
*   **Inference:** `SyncDatabase` is local SQLite.
*   **Proposal:** Add a `ReplicationManager` to sync verified Bricks/Nodes between multiple Nexus instances (e.g., Laptop <-> Desktop).
*   **Impact:** Enables multi-device personal cloud.

## 5. Visual "War Room" (UX)
*   **Inference:** `WallView` exists but is generic.
*   **Proposal:** Create a dedicated "War Room" dashboard that visualizes:
    *   Real-time Pulse (L1) stream.
    *   Budget Burn Down chart (L2/L3 costs).
    *   Graph Health metrics (Orphans, Cycles).
*   **Impact:** Better operational awareness for the user.
