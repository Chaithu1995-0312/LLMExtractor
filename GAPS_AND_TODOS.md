# Gaps and Todos

## Critical Technical Debt (🔴)

### 1. Concurrency Control
- **Context**: `GraphManager` and `LocalVectorIndex` read/write files without file locking.
- **Risk**: Concurrent requests (e.g., Sync running while Cortex is serving) will corrupt `index.faiss`, `nodes.json`, or `edges.json`.
- **Todo**: Implement file locking (e.g., `portalocker`) or move to SQLite.

### 2. Scalability
- **Context**: `GraphManager` loads the entire graph into memory for every operation.
- **Risk**: O(N) performance degradation as graph grows.
- **Todo**: Migrate graph storage to NetworkX (persisted) or a dedicated GraphDB (Neo4j/FalkorDB) or even SQLite.

### 3. Absolute Paths
- **Context**: `brick_store` and `assembler` store absolute file paths (`d:/chatgptdocs/...`).
- **Risk**: Moving the repo or data directory breaks all references. Index is not portable.
- **Todo**: Normalize paths relative to `REPO_ROOT` or `DATA_DIR`.

## Missing Features (🟡)

### 4. Incremental Indexing
- **Context**: `add_bricks` exists, but `rebuild_index=True` is often used.
- **Gap**: Handling deletions (updates) of source files is not implemented.
- **Todo**: Implement a dirty-tracking mechanism to remove old bricks when files change.

### 5. Structured Logging
- **Context**: Current code uses `print()` debugging (`DEBUG: ...`).
- **Gap**: No log levels, no file output, difficult to parse.
- **Todo**: Replace `print` with Python `logging` module.

### 6. Testing Strategy
- **Context**: Only ad-hoc scripts exist.
- **Gap**: No CI/CD ready unit tests.
- **Todo**: Create `pytest` suite covering `assembler`, `recall`, and `extractor`.

## Minor Issues (🧪)

- **Hardcoded Dimension**: `384` is hardcoded in `LocalVectorIndex`. Should be in `config.py` derived from model name.
- **Redundant Code**: `services/cortex/api.py` seems to duplicate logic in `server.py`.
- **Error Swallowing**: Broad `except Exception:` blocks in `server.py` hide root causes.
