# Inferred Enhancements

## Strategic Upgrades

### 1. SQLite Migration (Persistence Layer)
**Current State**: `json.load`/`dump` for Graph and Brick Metadata.
**Proposal**: Move `brick_ids.json`, `nodes.json`, and `edges.json` into a single SQLite database (`nexus.db`).
**Benefit**: ACID compliance, Atomic updates, SQL querying capability, much better performance for large datasets.

### 2. Asynchronous API (Service Layer)
**Current State**: Flask (Sync blocking).
**Proposal**: Migrate `services/cortex` to FastAPI or Quart.
**Benefit**: `assemble_topic` is I/O and CPU bound. An async architecture would allow the UI to poll for status or use WebSockets/SSE rather than hanging until completion.

### 3. Hierarchical Topic Modeling (Cognition)
**Current State**: Flat list of bricks recalled by similarity.
**Proposal**: Implement clustering (HDBSCAN) on the recalled vectors to identify sub-themes before assembly.
**Benefit**: Better structured "Cognition Artifacts" that break down complex queries into sub-sections.

## Tactical Improvements

### 4. Portable Indexing
**Current State**: Absolute paths stored in index.
**Proposal**: Store paths relative to `$NEXUS_DATA_ROOT`.
**Benefit**: Allows the entire `data/` folder to be synced between machines or developers without breaking retrieval.

### 5. Embedder Optimization
**Current State**: CPU-based inference (assumed from lack of CUDA checks in code snippets).
**Proposal**: Add ONNX Runtime support or quantization.
**Benefit**: Faster ingestion and lower latency on recall.

### 6. Graph Visualization
**Current State**: Raw JSON dump to UI.
**Proposal**: Server-side layout calculation or filtering (e.g., returning only the "ego graph" of a topic).
**Benefit**: The frontend won't crash when trying to render 10,000 nodes.
