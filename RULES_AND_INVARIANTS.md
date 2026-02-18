# Rules and Invariants

## 1. Intent Lifecycle
All `Intent` nodes must adhere to the following state transition logic (`IntentLifecycle` enum):

| From State | To State | Trigger | Condition |
| :--- | :--- | :--- | :--- |
| **LOOSE** | **FORMING** | Initial Extraction | Created by `NexusCompiler` or `CognitiveExtractor`. |
| **FORMING** | **FROZEN** | `promote_node` | Human approval via API (`jarvis_anchor`). |
| **FORMING** | **KILLED** | `kill_node` | Human rejection or Hallucination check. |
| **FROZEN** | **SUPERSEDED** | `supersede_node` | New node replaces old one (Versioning). |
| **SUPERSEDED** | **KILLED** | - | *Illegal Transition* (Superseded nodes are immutable history). |

## 2. Graph Integrity Rules

### Edge Constraints
1.  **Type Safety**: All edges must have a valid `EdgeType` from `src/nexus/graph/schema.py`.
2.  **Directionality**:
    -   `DERIVED_FROM`: Must point from `Intent` -> `Source`.
    -   `APPLIES_TO`: Must point from `Intent` -> `ScopeNode`.
3.  **No Loops**: The graph should generally be a DAG for `DERIVED_FROM` edges, though circular dependencies (e.g., `CONFLICTS_WITH`) are allowed between Intents.

### Node Invariants
1.  **Immutability**: Once a node is `FROZEN`, its `statement` and `content` fields MUST NOT be modified. Updates require creating a new node and linking via `SUPERSEDED_BY`.
2.  **Source Tracking**: Every `Intent` node must be traceable back to a `Source` node via a chain of `DERIVED_FROM` edges.

## 3. Governance Invariants

### Prompt Safety
1.  **Approved List**: `PromptManager` must only serve prompts with slugs present in the `approved_slugs` list (currently hardcoded in `prompt_manager.py`).
2.  **Violation Behavior**: If a request is made for a non-existent or unapproved prompt, a `GovernanceViolation` exception must be raised (unless a fallback is explicitly allowed and logged).

### Audit Trail
1.  **Event Logging**: All state changes (Create, Update, Delete) and Prompt Fallbacks MUST emit an event to `phase3_audit_trace.jsonl` via `_log_audit_event`.
2.  **Actor Attribution**: All API mutations must include an `actor` field (User ID or System Agent Name).

## 4. Agent Safety Rails

### 🚫 Do Not Touch Zones
-   **`src/nexus/graph/schema.py`**: Changing Enum values here breaks the database and UI compatibility. Consult architecture team before modifying.
-   **`src/nexus/sync/db.py`**: The raw SQL/KV schema is rigid. Do not alter table structures without a migration script.

### ✅ Mandatory Verification Hooks
-   **Pre-Commit**: Run `scripts/test_full_loop.py` before pushing changes to Core Logic.
-   **Schema Changes**: Must be accompanied by an update to `src/nexus/graph/schema_sync.sql`.
