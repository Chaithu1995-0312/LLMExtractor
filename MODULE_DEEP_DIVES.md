# Module Deep Dives

## 1. Sync & Ingestion Pipeline (`src/nexus/sync`)

### Purpose
To transform a monolithic `conversations.json` dump into a queryable, atomized vector store.

### Key Components
- **`TreeSplitter`**: Parses the source JSON. Splits it into individual JSON files per conversation tree. Uses a hash of content to detect duplicates.
- **`BrickExtractor`**:
  - Traverses the conversation tree.
  - Identifies "Bricks": Semantic units of text.
  - Splitting Logic: Message boundaries are hard stops. Within messages, splits on double newlines (`\n\n`).
  - Metadata: Captures `message_id`, `role`, `timestamp`, `block_index`.
- **`WallBuilder`**: Aggregates processed files into larger "Wall" files to reduce filesystem fragmentation, though this seems to be a storage optimization step that might be partially decoupled from the indexing itself in the current runner.
- **`Runner`**: The orchestrator.
  1. Load Conversations
  2. Extract Trees (Disk I/O intensive)
  3. Extract Bricks (CPU intensive)
  4. Build Walls
  5. Vector Embedding (GPU/CPU intensive)

### Data Flow
`conversations.json` ➔ `[Conversation Trees]` ➔ `[Bricks (in-memory)]` ➔ `[Walls]` ➔ `LocalVectorIndex`

---

## 2. Vector System (`src/nexus/vector`)

### Purpose
To provide semantic similarity search over the extracted Bricks.

### Architecture
- **Engine**: FAISS (Facebook AI Similarity Search).
- **Index Type**: `IndexFlatL2` (Exact search, no quantization).
- **Dimension**: 384 (matches `all-MiniLM-L6-v2`).
- **Storage**:
  - `index.faiss`: Binary FAISS index.
  - `brick_ids.json`: Parallel list mapping integer IDs (FAISS) to string Brick IDs (Nexus).
- **Embedder**: Singleton wrapper around `sentence_transformers`.

### Operations
- **`add_bricks(bricks)`**:
  - Filters for `PENDING` status.
  - Embeds text content.
  - Adds to FAISS index.
  - Appends IDs to `brick_ids` list.
  - Updates status to `EMBEDDED`.
- **`search(vector, k)`**: Returns distances and indices. Distances are L2; lower is better.

---

## 3. Cognition Engine (`src/nexus/cognition`)

### Purpose
To synthesize higher-order knowledge artifacts from retrieved memories.

### The Assembly Pipeline (`assembler.py`)
1. **Recall**: Queries the Vector Index for a `topic_query`.
2. **Expansion**:
   - Takes recalled Bricks.
   - Uses `brick_metadata` to find the original `source_file`.
   - Loads the *full* conversation tree for that file.
3. **Deduplication**:
   - Hashes the content of loaded trees.
   - If multiple bricks point to the same content (even if different files), they are merged into a single "Document".
4. **Assembly**:
   - Constructs a `TopicCognitionArtifact`.
   - Payload includes:
     - `topic`: The query.
     - `provenance`: List of Brick IDs and Source Files.
     - `raw_excerpts`: Structured conversation excerpts with highlighted spans.
5. **Persistence**: Saves to `artifacts/` with a content-hash-based filename.
6. **Graph Linkage**: Updates the Knowledge Graph with `ASSEMBLED_IN` and `DERIVED_FROM` edges.

---

## 4. Knowledge Graph (`src/nexus/graph`)

### Purpose
To track relationships between Topics, Artifacts, and Bricks, providing a structural overlay to the vector soup.

### Implementation
- **Storage**: Naive JSON files (`nodes.json`, `edges.json`).
- **Nodes**:
  - `Topic`: Represents a query/concept.
  - `Artifact`: Represents a specific assembled JSON file.
  - `Brick`: Represents a source fragment.
- **Edges**:
  - `ASSEMBLED_IN`: Topic ➔ Artifact.
  - `DERIVED_FROM`: Artifact ➔ Brick.
- **Anchors**: `anchors.override.json` allows manual intervention (promote/reject) to influence future recall (though integration into `recall.py` needs verification).

---

## 5. Cortex Service (`services/cortex`)

### Purpose
The HTTP interface for the Jarvis UI.

### Endpoints
- `GET /jarvis/graph-index`: Returns the full graph for visualization.
- `POST /jarvis/assemble-topic`: Triggers the Assembler.
- `GET /jarvis/brick-full`: Retrieves the full context of a specific brick.
- `POST /jarvis/anchor`: Updates anchor overrides.
