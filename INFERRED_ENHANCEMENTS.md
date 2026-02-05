# Inferred Enhancements

## Architecture Refinements

### 1. Unified Graph Interface
-   **Current State**: `sqlite3` calls are scattered in `GraphManager`.
-   **Improvement**: Abstract `GraphStore` interface (Protocol) to allow seamless switching between SQLite and Neo4j. This would validate the existence of `Neo4jGraphManager` and allow scaling.

### 2. Hybrid Search (Keyword + Vector)
-   **Current State**: Pure dense retrieval (`FAISS` L2 distance).
-   **Improvement**: Add a sparse index (BM25) to catch exact keyword matches (e.g., project names, specific error codes) that embeddings might miss. Combine scores (Reciprocal Rank Fusion).

### 3. Event-Driven Ingestion
-   **Current State**: `python -m nexus.sync` is a batch process.
-   **Improvement**: Watch the `data/` directory for file changes (watchdog) and trigger incremental ingestion automatically.

## Cognition Upgrades

### 1. Iterative "Mode-2" Reasoning
-   **Current State**: "Mode-1" is single-pass extraction.
-   **Improvement**: Implement "Mode-2" (Iterative Refinement).
    -   Step 1: Extract facts.
    -   Step 2: Check for contradictions in Graph.
    -   Step 3: Re-query/Re-read if needed.
    -   Step 4: Update Intent Lifecycle.

### 2. Automatic Topic Discovery
-   **Current State**: User must ask for a topic (`/assemble?topic=X`).
-   **Improvement**: Cluster bricks in vector space to auto-discover latent topics ("You have 50 bricks discussing 'Login Auth', should I assemble them?").

## Developer Experience

### 1. Nexus CLI
-   **Improvement**: Expand `nexus-cli` to support standard admin tasks:
    -   `nexus purge <file_id>`
    -   `nexus graph stats`
    -   `nexus config set vector_provider pinecone`

### 2. Visualization Dashboard
-   **Improvement**: A dedicated admin UI (separate from Jarvis) to inspect the raw bricks, vector distribution, and graph topology for debugging.
