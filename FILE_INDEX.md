# File Index & Intelligence Map

## src/nexus/sync/

### `runner.py`
Orchestrator for the deterministic ingestion pipeline.
-   `run_sync(input_json, output_dir, rebuild_index)`: **[HIGH]** Main entry point. Connects DB, Compiler, and processes all conversations.
    -   *Inputs*: JSON file path, output directory.
    -   *State Impact*: Mutates `SyncDatabase` (Source Runs, Bricks).

### `compiler.py`
Compiles linear conversation paths into atomic Bricks.
-   `NexusCompiler.compile_run(run_id, topic_id)`: **[MED]** Calls LLM to extract bricks from a source run.
    -   *Inputs*: `run_id`, `topic_id`.
    -   *State Impact*: Creates `Brick` records in DB.

### `db.py`
Database abstraction for the "Vault".
-   `SyncDatabase`: **[HIGH]** Manages SQLite/Key-Value storage for sync state.
-   `truncate_sync_data()`: **[HIGH]** Destructive. Wipes all sync data.
-   `register_run(run_id, content)`: **[MED]** Stores raw source content.

## src/nexus/extract/

### `tree_splitter.py`
Rich ingest parser for conversation trees.
-   `process_conversation(conv, output_dir)`: **[MED]** Converts JSON tree to linear paths with stable hashing.
    -   *Inputs*: Dict (conversation), output path.
    -   *State Impact*: Writes `path_{hash}.json` files to disk.
-   `extract_message(node_id, node)`: **[LOW]** Pure logic. Extracts text/code blocks from nodes.

## src/nexus/cognition/

### `dspy_modules.py`
DSPy Signatures and Modules for cognitive extraction.
-   `CognitiveExtractor`: **[LOW]** Pure logic. Extracts Facts, Diagrams, Entities.
-   `RelationshipSynthesizer`: **[LOW]** Pure logic. Infers edges between intents.

### `synthesizer.py`
Orchestrates the relationship discovery process.
-   `run_relationship_synthesis(topic_id)`: **[MED]** Batch process. Reads graph -> DSPy -> Writes Edges.
    -   *Inputs*: `topic_id` (optional).
    -   *State Impact*: Adds `Edge` records to Graph.

## src/nexus/graph/

### `manager.py`
Central API for Graph interactions.
-   `GraphManager`: **[HIGH]** Facade for all graph operations.
-   `add_typed_edge(edge)`: **[HIGH]** Persists a new edge.
-   `sync_bricks_to_nodes()`: **[HIGH]** Promotes Sync Bricks to Graph Nodes.

### `prompt_manager.py`
Governance for system prompts.
-   `get_prompt(slug, version)`: **[MED]** Retrieves approved prompts. Raises violation if missing.
-   `save_prompt(slug, content)`: **[HIGH]** Writes new prompt version to DB.

### `schema.py`
Data models and Enums.
-   `GraphNode`, `Source`, `ScopeNode`, `Intent`: Data classes.
-   `Edge`, `EdgeType`: Relationship definitions.
-   `IntentLifecycle`: Enum for state transitions.

## src/nexus/rerank/

### `llm_reranker.py`
Local LLM-based reranking.
-   `LlmReranker.rank(query, candidates)`: **[MED]** Calls local LLM. Has latency guard.
    -   *Inputs*: Query string, List[Dict] candidates.
    -   *Output*: Reordered List[Dict] with new scores.

## src/nexus/governance/

### `alert_manager.py`
Alerting and feedback loop.
-   `persist_alert(alert_data)`: **[HIGH]** Writes to `coverage_alerts` table.
-   `log_prompt_attempt(attempt_data)`: **[MED]** Logs feedback on auto-suggested prompts.

## services/cortex/

### `server.py`
Flask API Server entry point.
-   `jarvis_graph_index()`: **[LOW]** GET endpoint for graph dump.
-   `jarvis_anchor()`: **[HIGH]** POST endpoint for human validation.
-   `cognition_synthesize()`: **[MED]** POST endpoint to trigger synthesis.

### `tasks.py`
Celery task definitions (Async).
-   `sync_bricks_task`: **[MED]** Async wrapper for sync.
-   `synthesize_relationships_task`: **[MED]** Async wrapper for synthesis.
