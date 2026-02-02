# File Index

## Nexus CLI
`nexus-cli/`
- `__main__.py`
- `backend/`
  - `cortex/`
    - `api.py`: Cortex logic.
    - `server.py`: Flask application entry point.
- `nexus/`
  - `ask/`
    - `recall.py`: Recall logic logic (Search + Rerank).
  - `bricks/`
    - `brick_store.py`: Data access layer for bricks.
    - `extractor.py`: Extracts bricks from conversation trees.
  - `extract/`
    - `tree_splitter.py`: Parses JSON trees into linear paths.
  - `graph/`
    - `nodes.json`: Static graph nodes.
    - `edges.json`: Static graph edges.
    - `index.md`: Graph explanation.
  - `rerank/`
    - `orchestrator.py`: Reranking logic.
    - `llm_reranker.py`: LLM-based reranking (inferred).
  - `sync/`
    - `runner.py`: Main ETL pipeline runner.
  - `vector/`
    - `local_index.py`: FAISS wrapper.
  - `walls/`
    - `builder.py`: Constructs Markdown walls from trees.

## UI (Jarvis)
`ui/jarvis/`
- `src/`
  - `App.tsx`: Main application component.
  - `main.tsx`: Entry point.
  - `vite-env.d.ts`: Vite types.
- `index.html`: HTML entry.
- `package.json`: Dependencies.
- `vite.config.ts`: Build config.

## Output (Generated)
`output/nexus/`
- `bricks/`: Extracted brick JSONs.
- `walls/`: Generated Markdown walls.
- `index.faiss`: Vector index file.
- `brick_ids.json`: Index metadata.
