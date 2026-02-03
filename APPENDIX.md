# Appendix

## A. Configuration Reference

| Variable | Value/Path | Description |
| :--- | :--- | :--- |
| `REPO_ROOT` | `d:\chatgptdocs` | Root of the workspace. |
| `DATA_DIR` | `REPO_ROOT/data` | Storage for index and fixtures. |
| `INDEX_PATH` | `DATA_DIR/index/index.faiss` | Location of FAISS vector index. |
| `BRICK_IDS_PATH` | `DATA_DIR/brick_ids.json` | Metadata for vector-to-brick mapping. |
| `DEFAULT_OUTPUT_DIR` | `REPO_ROOT/output/nexus` | Target for extracted Bricks/Trees. |

## B. Dependency Graph

### Python (Backend)
Defined in `pyproject.toml`:
*   `faiss-cpu`: Vector similarity search.
*   `sentence-transformers`: (Intended) Embedding generation.
*   `flask`: API server.
*   `tiktoken`: Token counting for "Walls".
*   `numpy`: Numerical operations.

### Node.js (Frontend)
Defined in `ui/jarvis/package.json`:
*   `vite`: Build tool and dev server.
*   `react`: UI library.
*   `typescript`: Type safety.

## C. Data Schemas

### Brick Schema (JSON)
```json
{
  "brick_id": "unique_hash_string",
  "content": "Raw text content...",
  "source_file": "path/to/source_tree.json",
  "source_span": {
    "message_id": "uuid",
    "block_index": 0
  },
  "timestamp": "ISO8601",
  "status": "PENDING|EMBEDDED"
}
```

### Audit Trace Record (JSONL)
```json
{
  "user_id": "string",
  "agent_id": "string",
  "brick_ids_used": ["id1", "id2"],
  "model": "gpt-4o",
  "token_cost": 0.002,
  "timestamp": "ISO8601"
}
```

### Concept Node (Graph)
```json
{
  "id": "concept_id",
  "label": "Human Readable Label",
  "anchors": {
    "hard": ["brick_id_1"],
    "soft": ["brick_id_2"]
  }
}
```
