# FILE_INDEX

## src/nexus/sync

### `db.py`
**Class: `SyncDatabase`**
*   `create_topic(id, name, definition)`: (MED) Writes topic metadata. Idempotent.
*   `register_run_safe(run_id, content)`: (MED) Appends source run with prefix validation. Enforces append-only.
*   `save_brick(brick)`: (MED) Upserts brick and unified node. Transactional.
*   `truncate_sync_data()`: (HIGH) **Destructive**. Clears all sync data.

### `compiler.py` (Inferred)
**Class: `Compiler`**
*   `compile(source_run)`: (LOW) Pure function. Transforms raw logs to Bricks.

### `runner.py` (Inferred)
**Class: `Runner`**
*   `run_sync()`: (MED) Orchestrates the sync process.

## src/nexus/graph

### `manager.py`
**Class: `GraphManager`**
*   `register_node(type, id, attrs)`: (MED) Upserts graph node. Idempotent.
*   `register_edge(src, dst, type)`: (MED) Creates edge with cycle detection for specific types.
*   `promote_node_to_frozen(id, anchors)`: (HIGH) Lifecycle transition FORMING -> FROZEN. Audited.
*   `kill_node(id, reason)`: (HIGH) Lifecycle transition -> KILLED. Audited.
*   `supersede_node(old, new)`: (HIGH) Lifecycle transition FROZEN -> SUPERSEDED. Versioning logic.
*   `sync_bricks_to_nodes()`: (MED) Batch migration of Bricks to Graph Nodes.

### `schema.py` (Inferred)
**Classes: `Intent`, `Edge`, `Lifecycle`**
*   (Data Classes): Define the domain model.

## src/nexus/cognition

### `assembler.py`
**Module Functions**
*   `assemble_topic(query)`: (HIGH) DSPy pipeline. Reads graph, queries LLM, writes Artifact.

### `synthesizer.py`
**Module Functions**
*   `run_relationship_synthesis(topic_id)`: (HIGH) DSPy pipeline. Infers relationships between Intents.

## services/cortex

### `server.py`
**Module Functions**
*   `api_metrics_overview()`: (LOW) Read-only DB stats.
*   `jarvis_node_promote()`: (HIGH) API endpoint for node promotion.
*   `jarvis_node_kill()`: (HIGH) API endpoint for node rejection.
*   `cognition_assemble()`: (HIGH) API endpoint to trigger topic assembly.

### `api.py` (Inferred)
**Class: `CortexAPI`**
*   `assemble(topic)`: (HIGH) Wrapper for `assemble_topic`.
*   `get_audit_events()`: (LOW) Read-only audit log query.

## ui/jarvis/src

### `protocol/event-types.ts`
**Types**
*   `GraphEventType`, `SystemEventType`, `StreamEventType`: Define WebSocket contract.

### `components` (Inferred)
*   `CortexVisualizer`: (UI) Renders the graph.
*   `AuditPanel`: (UI) Displays audit logs.
