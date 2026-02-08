# FILE_INDEX.md

## src/nexus/graph

### `manager.py`
Primary interface for graph persistence and lifecycle management.
- `GraphManager`
  - `register_node`: Creates or updates graph nodes with conflict checks.
  - `register_edge`: Persists typed relationships between nodes.
  - `promote_node_to_frozen`: Transitions nodes to immutable state.
  - `supersede_node`: Deprecates old nodes in favor of new versions.
  - `kill_node`: Logical deletion of nodes with audit trail.
  - `sync_bricks_to_nodes`: Batch processes ingestion buffer into the graph.

### `projection.py`
Logic for transforming raw graph data into specific views (Walls).
- `project_intent`: Calculates spatial coordinates and metadata for UI display.

### `schema.py`
Data models and Enums for the Nexus graph.
- `Intent`, `Edge`, `Source`, `ScopeNode`: Core domain objects.
- `IntentLifecycle`, `EdgeType`: State and relationship definitions.

### `validation.py`
Integrity enforcement suite.
- `run_full_validation`: Executes cycle detection and orphan checks.

## src/nexus/sync

### `compiler.py`
Orchestration engine for the ingestion pipeline.
- `NexusCompiler`
  - `compile_run`: Main entry point for processing raw conversation files.
  - `_llm_extract_pointers`: Uses LLM to identify semantic units.
  - `_materialize_brick`: Persists extracted units to `BrickStore`.

### `db.py`
Persistence for the ingestion buffer and topic definitions.
- `SyncDatabase`: Handles SQLite storage for raw runs and bricks.

## src/nexus/cognition

### `assembler.py`
Retrieval and assembly logic for context construction.
- `assemble_topic`: Merges bricks and intents into a unified context string.

### `dspy_modules.py`
DSPy-based cognitive processing modules.
- `CognitiveExtractor`: Recursive fact and relationship extraction.
- `RelationshipSynthesizer`: Cross-intent relationship inference.

### `synthesizer.py`
Batch processing for the cognition layer.
- `run_relationship_synthesis`: High-level runner for graph-wide synthesis.

## services/cortex

### `api.py`
Core logic for the Cortex Service.
- `CortexAPI`
  - `route`: Directs user queries to appropriate agents or graph queries.
  - `generate`: Synthesizes final responses using retrieved context.
  - `get_audit_events`: Interfaces with the audit log for observability.

### `server.py`
Flask-based HTTP entry points.
- Maps URL routes to `CortexAPI` and `GraphManager` methods.

### `gateway.py`
External interaction and reasoning proxy.
- `JarvisGateway`: Proxies calls to reasoning models and handles pulsing.

## ui/jarvis

### `src/store.ts`
Central state management (Zustand).
- Manages graph state, UI selection, and server synchronization.
