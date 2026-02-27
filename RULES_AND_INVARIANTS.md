# RULES AND INVARIANTS

## 1. Agent Safety Rails

### 1.1 "Do Not Touch" Zones
*   **Database Schema Migrations (`src/nexus/graph/*.sql`):** Agents must NEVER modify SQL schema files directly without running the associated migration script and verifying rollback capability.
*   **Vector Index Configuration:** The dimensions of the `pgvector` column (1536 for OpenAI) are hardcoded in the DB schema. Changing the embedding model requires a full re-index.

### 1.2 Mandatory Verification Hooks
*   **Before Merge:** Run `scripts/test_drift_engine.py` to ensure new code doesn't destabilize concept evolution.
*   **Before Deployment:** Run `tests/invariants/test_graph_integrity.py` to verify no orphaned nodes or broken edges exist.

## 2. Invariants

### 2.1 Data Integrity
*   **Immutable Bricks:** Once a Brick is `Status: EMBEDDED`, its content hash and vector must NEVER change. Updates require a new Brick and a `REPLACES` edge.
*   **Single Source of Truth:** The Postgres Graph is authoritative. The Vector Store is a derived index. If they disagree, rebuild the Vector Index from the Graph.

### 2.2 Cognitive Consistency
*   **Topic Determinism:** The same input text should route to the same `TopicID` with > 95% consistency.
*   **Resolution Convergence:** Repeated runs of `EntityResolver` on the same dataset must result in the same set of unique Nodes (idempotent clustering).

## 3. Operational Rules
*   **Rate Limiting:** All calls to external LLM APIs must be wrapped in `budget_controller` to prevent cost runaways.
*   **Async Processing:** Any operation taking > 2 seconds (e.g., summarization) must be offloaded to the Task Queue, never blocking the API thread.
