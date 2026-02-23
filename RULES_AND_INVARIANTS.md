# RULES_AND_INVARIANTS

## 1. Safety Rails (Do Not Touch)

### ⛔ Ingestion Integrity
*   **Source Runs are Append-Only:** `src/nexus/sync/db.py` -> `register_run_safe`.
    *   **Rule:** Never modify the `raw_content` of a registered run unless extending it (prefix match required).
    *   **Reason:** Breaks cryptographic provenance and invalidates downstream Bricks.

### ⛔ Graph Lifecycle
*   **FROZEN Nodes are Immutable:** `src/nexus/graph/manager.py`.
    *   **Rule:** Never `UPDATE` the `statement` of a node with `lifecycle='frozen'`.
    *   **Reason:** FROZEN nodes are anchors for other knowledge. Use `supersede_node` instead.
*   **Valid Transitions Only:**
    *   `LOOSE` -> `FORMING` | `KILLED`
    *   `FORMING` -> `FROZEN` | `KILLED`
    *   `FROZEN` -> `SUPERSEDED` | `KILLED`
    *   `SUPERSEDED` -> `KILLED`

### ⛔ Audit Trail
*   **No Silent Actions:** `src/nexus/graph/manager.py` -> `_log_audit_event`.
    *   **Rule:** Every write operation to the Graph (create, update, delete) MUST emit an Audit Event.
    *   **Reason:** Regulatory compliance and debugging.

## 2. Mandatory Verification Hooks

### 🛡️ Pre-Commit Hooks
1.  **Cycle Detection:** Before adding `OVERRIDES` or `SUPERSEDED_BY` edges, run `_check_for_cycle` (`GraphManager`).
2.  **Schema Validation:** Ensure `Intent` nodes have `statement` and `lifecycle` fields.

### 🛡️ Post-Commit Hooks
1.  **Unified Sync:** After adding Bricks to `sync.bricks`, MUST run `sync_bricks_to_nodes` to populate the Graph.
2.  **Audit Pulse:** Emit a WebSocket pulse for real-time UI updates.

## 3. Data Invariants

### 🔒 Content Addressing
*   **Brick IDs:** Must be derived from the hash of their content + source span.
*   **Artifact IDs:** Must be SHA256 of the JSON payload.

### 🔒 Provenance Chain
*   Every `Intent` MUST have a `DERIVED_FROM` edge pointing to at least one `Brick` (or another `Intent`).
*   Every `Brick` MUST have a valid `source_address` (Run ID + Index).

## 4. Economic Cognition (Cost Control)
*   **Token Tracking:** Any function invoking an LLM (`dspy_modules`) must return usage stats (`tokens_in`, `tokens_out`, `cost_usd`).
*   **Budget Guardrails:** (Future) Block requests if daily budget exceeded.
