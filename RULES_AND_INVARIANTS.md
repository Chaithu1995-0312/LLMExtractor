# Rules and Invariants

## Data Integrity

### 1. Brick Provenance
- **Invariant**: Every indexed Vector MUST map to a valid Entry in `brick_ids.json`.
- **Invariant**: Every Entry in `brick_ids.json` MUST contain valid `source_file` and `source_span` metadata.
- **Rule**: If a source file is deleted, the corresponding index entries become orphans (Nexus does not currently implement tombstoning or garbage collection).

### 2. Artifact Immutability
- **Invariant**: Cognition Artifacts are Content-Addressed.
- **Rule**: The filename format MUST be `{slug}_{hash}_{timestamp}.json`.
- **Rule**: Once written, an artifact file SHOULD NOT be modified. New insights require a new artifact (and thus a new node).

### 3. Graph Consistency
- **Rule**: Nodes and Edges are idempotent. Registering the same node/edge twice results in a no-op.
- **Invariant**: The Graph is a directed multigraph (technically allowed by JSON structure, though logical usage is usually simple directed).
- **Rule**: `brick_id` in the graph must match `brick_id` in the vector store.

## System Constraints

### 4. File System
- **Invariant**: All generated data resides in `output/nexus/`.
- **Rule**: The system assumes it has write access to the local filesystem.
- **Rule**: Paths in metadata (`source_file`) are absolute paths (based on observation of `os.path.abspath` usage). This makes the index non-portable across machines without path rewriting.

### 5. Vector Dimensions
- **Invariant**: All embeddings MUST be 384 dimensions.
- **Rule**: Changing the embedding model requires a full rebuild of the index (clearing `index.faiss` and `brick_ids.json`).

### 6. Sync Operations
- **Rule**: `run_sync` is a blocking operation.
- **Rule**: `rebuild_index=True` is destructive; it wipes the existing index before rebuilding.
