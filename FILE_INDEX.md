# File Index

## `src/nexus/graph/`
### `manager.py`
*   `GraphManager`
    *   `register_node`: Upsert a generic node into the graph.
    *   `register_edge`: Create a directed edge between two nodes.
    *   `kill_node`: Move a node to KILLED state (soft delete).
    *   `promote_node_to_frozen`: Lock a node into FROZEN state.
    *   `supersede_node`: Replace a FROZEN node with a new one.
    *   `sync_bricks_to_nodes`: Migrate bricks from ingestion table to graph table.

### `projection.py`
*   (Functions)
    *   `project_intent`: Resolve an intent's effective state based on edges.
    *   `has_conflict`: Check for CONFLICTS_WITH edges.

### `schema.py`
*   `IntentLifecycle` (Enum): LOOSE, FORMING, FROZEN, SUPERSEDED, KILLED.
*   `EdgeType` (Enum): APPLIES_TO, ASSEMBLED_IN, SUPERSEDED_BY, CONFLICTS_WITH.

## `src/nexus/sync/`
### `compiler.py`
*   `NexusCompiler`
    *   `compile_run`: Orchestrate the extraction pipeline for a run.
    *   `_llm_extract_pointers`: Call LLM to find text coordinates.
    *   `_materialize_brick`: Verify and create a Brick object.

### `db.py`
*   `SyncDatabase`
    *   `save_brick`: Persist a brick to SQLite.
    *   `register_run`: Log a new ingestion run.

### `ingest_history.py`
*   `NexusIngestor`
    *   `brickify`: Convert raw content into bricks.

## `src/nexus/vector/`
### `embedder.py`
*   `VectorEmbedder` (Singleton)
    *   `embed_query`: Generate vector for search query.
    *   `embed_texts`: Batch embed text strings.
    *   `_rewrite_with_llm`: Expand query terms using LLM.

### `local_index.py`
*   `LocalVectorIndex`
    *   `add_bricks`: Add brick content to FAISS index.
    *   `search`: Perform Nearest Neighbor search.

## `services/cortex/`
### `api.py`
*   `CortexAPI`
    *   `route`: Determine which agent handles a query.
    *   `generate`: Execute the L2 (Voice) cognitive pipeline.
    *   `ask_preview`: Read-only L2 preview.
    *   `assemble`: Trigger background assembly.

### `gateway.py`
*   `JarvisGateway`
    *   `pulse`: L1 local inference (fast/free).
    *   `explain`: L2 proxy inference (smart/paid).
    *   `synthesize`: L3 proxy inference (deep/expensive).

### `server.py`
*   (Functions)
    *   `jarvis_node_promote`: HTTP endpoint wrapper for GraphManager.
    *   `jarvis_ask_preview`: HTTP endpoint wrapper for CortexAPI.

## `src/nexus/cognition/`
### `dspy_modules.py`
*   `CognitiveExtractor` (DSPy Module)
    *   `forward`: Extract Facts and Diagrams from text.
*   `RelationshipSynthesizer` (DSPy Module)
    *   `forward`: Infer relationships between intents.
