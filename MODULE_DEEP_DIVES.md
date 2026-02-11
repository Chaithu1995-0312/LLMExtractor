# MODULE DEEP DIVES

This document provides deep dives into selected critical modules, detailing their class and method intelligence, control flow, and authority boundaries.

## `nexus.sync.compiler` Module

### Class: `NexusCompiler`

#### Responsibility
The `NexusCompiler` class orchestrates the core ingestion pipeline, transforming raw conversational data into structured "bricks." It enforces "Zero-Trust Validation" to prevent LLM hallucination and integrates with governance components for auditing and alerts.

#### Method Intelligence Table

| Method Name           | Responsibility                                                                   | Inputs                                     | Outputs / Side Effects                                                                      | Invariants Enforced                                                                                                                                                                                                                                                         | Failure Modes                                                                 | Lifecycle Impact     | Layer       | Attributes         |
|-----------------------|--------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|----------------------|-------------|--------------------|
| `__init__`            | Initializes the compiler.                                                        | `db_connection`, `llm_client`                               | Initializes instance variables.                                                             | None                                                                                                                                                                                                                  | Client initialization failures.                               | Instantiation        | Ingestion   | Stateful           |
| `compile_run`         | Orchestrates end-to-end compilation of a source run into bricks.                       | `run_id`, `topic_id`                                        | New bricks, DB updates, audit events, coverage alerts. | Ingestion authority, Zero-Trust Validation.                                                                                                                                       | Run/Topic not found, LLM/brick failures. | Creates `bricks` | Ingestion   | Stateful, Transactional, Write-authoritative |
| `_pre_filter_nodes`   | Filters raw messages based on boundaries and authority.                       | `raw_content`, `last_processed`                             | Filtered messages, max index seen.                                 | Incremental Boundary Guard, Ingestion Authority (user/system roles).                                                                                                                                    | None                                                              | Filtering            | Ingestion   | Pure               |
| `_build_batches`      | Groups filtered messages into token-bounded batches.                                          | `messages` (list of dicts)                          | List of message batches.                                                      | Max message/char count per batch.                                                                                                                            | None                                                              | Batching             | Ingestion   | Pure               |
| `_llm_extract_pointers` | Uses structured LLM for data pointer extraction.       | `content` (batch), `topic` (definition)       | Extracted pointers, audit event.                         | Grammar-constrained output.                                                                                                                                 | LLM call failure.                                             | Extraction           | Ingestion   | Stateful (LLM call) |
| `_materialize_brick`  | Zero-Trust Gate: Verifies LLM pointers and materializes a brick. | `run_data`, `run_id`, `pointer`, `topic_id`, `scanned_indices` | New brick, audit events. | Topic ID Mismatch, JSON Path Out of Bounds, Verbatim Quote Existence (anti-hallucination). | JSONPath/quote not found (hallucination). | Brick Creation       | Ingestion   | Stateful, Invariant Enforcer, Write-authoritative |

#### Method Usage Graph

##### `__init__`
- **Called by**: `nexus.sync.runner.run_sync`
- **Layer**: Ingestion
- **Type**: Stateful

##### `compile_run`
- **Called by**: `nexus.sync.runner.run_sync`
- **Layer**: Ingestion
- **Type**: Stateful, Transactional, Write-authoritative

##### `_pre_filter_nodes`
- **Called by**: `nexus.sync.compiler.compile_run`
- **Layer**: Ingestion
- **Type**: Pure

##### `_build_batches`
- **Called by**: `nexus.sync.compiler.compile_run`
- **Layer**: Ingestion
- **Type**: Pure

##### `_llm_extract_pointers`
- **Called by**: `nexus.sync.compiler.compile_run`
- **Layer**: Ingestion
- **Type**: Stateful

##### `_materialize_brick`
- **Called by**: `nexus.sync.compiler.compile_run`
- **Layer**: Ingestion
- **Type**: Stateful, Invariant Enforcer, Write-authoritative

--- 

## `nexus.graph.manager` Module

### Class: `GraphManager`

#### Responsibility
The `GraphManager` is the authoritative data access layer for the knowledge graph. It manages nodes and edges within an SQLite database, enforcing graph invariants and lifecycle of intents. It also centralizes audit logging and communication to the L1 Narrator.

#### Method Intelligence Table

| Method Name           | Responsibility                                                                                                     | Inputs (Logical)                                            | Outputs / Side Effects                                                                      | Invariants Enforced                                                                                                                                                                                                                                                         | Failure Modes                                                                 | Lifecycle Impact     | Layer       | Attributes         |
|-----------------------|--------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|----------------------|-------------|--------------------|
| `__init__`            | Initializes the GraphManager and database.                        | `db_path` (optional)                                        | Initializes DB, creates tables, calls `sync_bricks_to_nodes`.                               | Ensures `nodes` and `edges` tables exist and `schema_sync.sql` is applied.                  | SQLite connection failures.                                   | Instantiation        | Graph       | Stateful, Write-authoritative |
| `register_node`       | Idempotently adds a new node or merges data.                                    | `node_type`, `node_id`, `attrs` (dict), `merge` (bool)      | Inserts/updates `nodes` table.                                                              | Node ID uniqueness.                                                                                                                                                                                                   | Database insertion/update errors.                             | Node Management      | Graph       | Write-authoritative |
| `get_intents_by_topic` | Retrieves all intents linked to a topic.                                          | `topic_node_id`                                             | `List[Intent]` objects.                                                                     | None                                                                                                                                                                                                                  | None                                                              | Retrieval            | Graph       | Read-only          |
| `_check_for_cycle`    | Detects cycles for specific edge types.                | `start_node_id`, `target_node_id`, `edge_type_str`          | `Optional[List[str]]` cycle path.                                 | Prevents cyclic relationships for `OVERRIDES`, `SUPERSEDED_BY`.     | None                                                              | Graph Traversal      | Graph       | Pure, Invariant Enforcer |
| `register_edge`       | Idempotently adds an edge with real-time cycle prevention.       | `src` (tuple), `dst` (tuple), `edge_type` (Enum/str), `attrs` (dict) | Inserts into `edges` table. Raises `ValueError` on cycle.                       | Edge uniqueness, cycle prevention.                    | Database errors, `ValueError` on cycle.   | Edge Management      | Graph       | Write-authoritative, Invariant Enforcer |
| `_log_audit_event`    | Appends structured audit events to a file.                                         | `event_type`, `agent`, `component`, `decision_action`, `reason`, ... | Appends to audit log file.                                                                  | **Economic Cognition Invariant**: Non-free models must emit cost metadata. | File I/O errors.                                              | Audit                | Governance  | Write-authoritative, Invariant Enforcer |
| `promote_intent`      | Manages intent lifecycle state transitions.            | `intent_id`, `new_lifecycle`                                | Updates node lifecycle.                                                                     | Monotonic state transitions, `FROZEN` intents require `APPLIES_TO` edges. | Intent not found, invalid transition/invariant.    | Node Lifecycle       | Graph       | Stateful, Lifecycle Gatekeeper, Invariant Enforcer |
| `sync_bricks_to_nodes` | Migrates bricks to the unified `nodes` table.                            | `limit` (int)                                               | Inserts/updates `nodes` and `edges` tables, prints status.                             | Ensures data consistency.                 | Database errors. | Data Migration       | Graph       | Write-authoritative |

#### Cross-Class Interaction Notes
- `GraphManager` is a **lifecycle gatekeeper** for `Intent` objects, enforcing state transitions.
- It acts as a **write boundary** for all graph operations, encapsulating direct database interactions.
- `_check_for_cycle` and `register_edge` are **invariant enforcers** for graph integrity.
- `_log_audit_event` enforces the **Economic Cognition Invariant** for LLM cost transparency.

---