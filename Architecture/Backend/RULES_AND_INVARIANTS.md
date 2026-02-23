# Rules & Invariants

## 1. Graph State Invariants
These rules are enforced by `GraphManager` and MUST NOT be bypassed.

### 🔴 Cycle Prevention (Strict)
*   **Rule**: The graph must be Acyclic for `OVERRIDES` and `SUPERSEDED_BY` edges.
*   **Enforcement**: `GraphManager._check_for_cycle()` runs DFS on every write attempt.
*   **Safety Rail**: Do not attempt to insert these edges via raw SQL; always use the Manager.

### 🟡 Lifecycle Monotonicity
*   **Rule**: Entities must move forward in lifecycle: `LOOSE` -> `FORMING` -> `FROZEN` -> `SUPERSEDED` | `KILLED`.
*   **Exception**: `LOOSE` -> `KILLED` (Immediate Rejection) is allowed.
*   **Enforcement**: `GraphManager.promote_intent` validates transitions.

### 🔵 Scope Completeness
*   **Rule**: A Node cannot be `FROZEN` without an `APPLIES_TO` edge linking it to a Scope.
*   **Reason**: Every frozen truth must be scoped (contextualized).

## 2. Economic Cognition Invariants
Rules governing the use of AI models (L3 Sage, Router).

### 💸 No Silent Spend
*   **Rule**: Any operation invoking a paid model (Tier > L1) **MUST** emit cost metadata in the Audit Log.
*   **Enforcement**: `GraphManager._log_audit_event` emits a warning if `model_tier > L1` and `cost_usd` is missing.

### ⚖️ Hybrid Escalation
*   **Rule**: High-cost models (Pro) should only be invoked if Flash confidence is low.
*   **Enforcement**: `L3Sage.audit_topic_health` implements the Router/Retry loop.

## 3. Worker Safety Rails

### 🔒 Transactional Atomicity
*   **Rule**: Task State (Pending/Running/Completed) and Business Logic (Graph Mutation) must occur in the **SAME** database transaction.
*   **Reason**: Prevents "Ghost Tasks" (Executed but failed to update status) or "Zombie State" (Status updated but execution failed).
*   **Enforcement**: `PGWorker.run_once` wraps the handler call in `with db.transaction()`.

### ⏱️ Visibility Timeout
*   **Rule**: Stalled tasks (locked > 5 mins) must be reset to `pending`.
*   **Enforcement**: `PGWorker._cleanup_stalled_tasks` (Janitor).

## 4. "Do Not Touch" Zones
Areas of the codebase that are critical infrastructure and should only be modified with extreme caution and full regression testing.

1.  **`src/nexus/graph/manager.py` > `_check_for_cycle`**: Modifications here risk infinite recursion loops in the graph.
2.  **`services/cortex/worker.py` > `run_once`**: The `FOR UPDATE SKIP LOCKED` logic is subtle and critical for preventing race conditions.
3.  **`src/nexus/sync/runner.py` > `run_sync`**: The deterministic seeding logic ensures idempotency; breaking this corrupts the knowledge base.
