# RULES_AND_INVARIANTS

## 1. Safety Rails & "Do Not Touch" Zones

### 🔴 Critical Infrastructure
The following components are core to the system's integrity. **Do not modify without running the full test suite.**

- **`src/nexus/graph/schema.py`**: Changing the schema of `GraphNode` or `Edge` will break all persistence and graph traversal logic. Migration scripts are required for any change.
- **`src/nexus/sync/db.py`**: The SQLite schema is the source of truth for ingestion. Altering table structures without migration will cause data loss.
- **`src/nexus/utils_logging.py`**: The logging infrastructure is used by all services. Breaking this blinds the entire system.

### 🟡 Managed Zones
Can be modified with caution, but require adherence to strict patterns.

- **`src/nexus/cognition/dspy_modules.py`**: Prompt signatures can be tuned, but input/output types must remain consistent to avoid breaking the `Synthesizer`.
- **`services/cortex/api.py`**: Adding new endpoints is safe; changing existing method signatures breaks the frontend.

## 2. Graph Invariants
The `GraphManager` enforces these strict rules:

1. **Acyclicity:** The graph must remain a DAG (Directed Acyclic Graph) for certain edge types (e.g., `DEPENDS_ON`).
   - *Enforced by:* `_check_for_cycle` in `manager.py`.
2. **Referential Integrity:** An edge cannot exist without valid source and destination nodes.
   - *Enforced by:* `register_edge` validation.
3. **Lifecycle Progression:** Nodes can only move forward in the lifecycle (Forming -> Frozen -> Superseded). They cannot revert.
   - *Enforced by:* `promote_node`, `supersede_node`.

## 3. Data Integrity & Persistence
1. **Append-Only Bricks:** Once a Brick is materialized and saved, its content should be treated as immutable. Updates should create new Bricks or new versions.
2. **Audit Trails:** All significant graph mutations (Create, Update, Delete) must be logged to the `audit_logs` table.
   - *Enforced by:* `GraphManager._log_audit_event`.

## 4. Operational Constraints
1. **Environment Variables:** API keys (OpenAI, etc.) must NEVER be hardcoded. They must be loaded from `.env` via `src/nexus/config.py`.
2. **Database Locking:** SQLite is single-writer. High-concurrency write operations should be serialized or handled via a queue (e.g., `GraphTransaction`).
