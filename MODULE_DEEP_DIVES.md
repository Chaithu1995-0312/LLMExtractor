# Module Deep Dives

## 1. Ingestion Engine (`src/nexus/sync`)

### Purpose
Converts raw conversational history (JSON trees) into atomic "Bricks" suitable for vector embedding and retrieval.

### Mechanism
1.  **Parsing**: Reads `tree_file_path` JSONs.
2.  **Distillation**: Uses `src/nexus/bricks/extractor.py` to clean and split text.
    -   Library: `unstructured` (cleaning).
    -   Splitting: Paragraph-based splitting (fallback to simple split if unstructured fails).
3.  **Brick Creation**: Generates a stable SHA256 `brick_id` based on source path, content, and index.
4.  **Persistence**: Saves bricks to `data/bricks/`.
5.  **Indexing**: Passes bricks to `LocalVectorIndex` for embedding.

### Technical Constraints
-   **Granularity**: Currently splits by message/paragraph. May lose context if paragraphs are too short.
-   **Idempotency**: Relies on stable hashing. Rerunning sync on same data produces same IDs.

## 2. Recall System (`src/nexus/ask`)

### Purpose
Retrieves relevant context for a query while strictly enforcing "read-only" safety during preview/routing.

### Architecture
-   **Entry Point**: `recall_bricks` or `recall_bricks_readonly`.
-   **Vector Search**: Queries `LocalVectorIndex` (FAISS).
    -   Converts L2 distance to confidence score (0.0 - 1.0).
-   **Hydration**: Fetches full text and metadata from `BrickStore`.
-   **Reranking**: `RerankOrchestrator` uses Cross-Encoder to refine results.
-   **Scoping**: Applies priority boost for non-global scopes.

### Key Class: `LocalVectorIndex`
-   **Backend**: `faiss.IndexFlatL2`.
-   **Storage**: `data/index/nexus_bricks.index`.
-   **Mapping**: Maintains a parallel JSON list of `brick_ids` to map FAISS integer IDs back to string IDs.

## 3. Cognition Assembler (`src/nexus/cognition`)

### Purpose
Synthesizes scattered bricks into a coherent, structured Knowledge Artifact (Topic).

### Workflow ("Mode-1")
1.  **Recall**: Fetches top-k bricks for the topic.
2.  **Expansion**: Loads the *entire* source conversation tree for every recalled brick.
    -   *Why?* To provide full context to the extraction model.
3.  **Deduplication**: Merges overlapping source spans.
4.  **Extraction**: `CognitiveExtractor` (DSPy module) processes the aggregated text.
    -   Extracts: Facts, Mermaid diagrams, LaTeX formulas.
5.  **Persistence**: Writes artifact to `output/artifacts/{slug}_{hash}.json`.
6.  **Graph Sync**: Updates the Knowledge Graph with new Intents and Relationships.

### DSPy Integration
-   **Signature**: `Context -> Facts, Mermaid, Latex`.
-   **Model**: Configured globally (likely GPT-4o or similar via DSPy).

## 4. Graph Manager (`src/nexus/graph`)

### Purpose
Manages the lifecycle and relationships of knowledge units (Intents).

### Schema (SQLite)
-   **Nodes**: Generic table `(id, type, data_json)`.
    -   Types: `intent`, `topic`, `artifact`, `brick`, `source`, `scope`.
-   **Edges**: Generic table `(source, target, type, data_json)`.
    -   Types: `ASSEMBLED_IN`, `DERIVED_FROM`, `OVERRIDES`, `APPLIES_TO`.

### Lifecycle Logic
-   **Monotonicity**: State transitions are strictly controlled.
    -   `LOOSE` -> `FORMING` -> `FROZEN` -> `SUPERSEDED` -> `KILLED`.
-   **Conflict Resolution**:
    -   Newer `FORMING` intent can override older `FORMING` intent.
    -   `FROZEN` intent acts as an anchor; newer data must explicitly `OVERRIDE` it (and likely requires human/high-confidence approval, though currently automated based on similarity > 0.85).

## 5. Cortex API (`services/cortex`)

### Purpose
Exposes system capabilities via REST (or internal Python API).

### Endpoints
-   `/route`: Keyword-based agent routing.
-   `/generate`: RAG generation with mandatory source reload audit.
-   `/assemble`: Triggers topic assembly.
-   `/ask_preview`: Read-only recall for UI.

### Security / Audit
-   **Audit Log**: `phase3_audit_trace.jsonl`.
-   **Invariant**: Generation *must* reload source text from bricks. If reload fails, generation is blocked.
