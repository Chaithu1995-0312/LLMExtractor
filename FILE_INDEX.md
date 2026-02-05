# File Index

## Source Code (`src/nexus`)

### Core Graph (`src/nexus/graph`)
- `schema.py`: Core data models (Intent, Source, Scope, Edge) and Enums.
- `manager.py`: SQLite-backed GraphManager for CRUD and lifecycle operations.
- `projection.py`: Logic for projecting graph views.
- `validation.py`: Invariant validation logic.
- `graph.db`: SQLite database file (runtime artifact).

### Ingestion (`src/nexus/sync`, `src/nexus/bricks`)
- `sync/ingest_history.py`: Parses `conversations.json` into Bricks.
- `sync/runner.py`: CLI runner for sync operations.
- `bricks/extractor.py`: Logic for splitting messages into Bricks.
- `bricks/brick_store.py`: Storage interface for raw Bricks.

### Vector & Indexing (`src/nexus/vector`, `src/nexus/index`)
- `vector/local_index.py`: FAISS-based vector storage implementation.
- `vector/embedder.py`: Embedding model wrapper.
- `index/conversation_index.py`: Metadata indexing for conversations.

### Cognition (`src/nexus/cognition`)
- `assembler.py`: Orchestrates Topic assembly from Bricks.
- `dspy_modules.py`: DSPy signatures and modules for information extraction.
- `dspy_config.py` (Implied/Pending): Configuration for LLM backends.

### Retrieval (`src/nexus/ask`, `src/nexus/rerank`)
- `ask/recall.py`: Semantic search and recall logic.
- `rerank/cross_encoder.py`: Re-ranking logic using cross-encoders.

## Services (`services`)

### Cortex API (`services/cortex`)
- `server.py`: Flask application entry point.
- `api.py`: API route definitions and logic.
- `orchestration.py`: Background task management.

### MCP (`services/mcp`)
- `nexus_server.py`: Model Context Protocol server implementation.

## User Interface (`ui/jarvis`)
- `src/App.tsx`: Main application component.
- `src/components/NexusNode.tsx`: Graph node visualization component.
- `src/store.ts`: Local state management.
- `vite.config.ts`: Build configuration.

## Tests (`tests`)
- `unit/`: Unit tests for individual components.
- `invariants/`: System invariant tests (Lifecycle, Graph Integrity).
- `test_server_graph.py`: Integration tests for API.

## Scripts (`scripts`)
- `migrate_to_intents.py`: Database migration utilities.
- `maintenance/prune_bricks.py`: Cleanup utilities.
- `test_assemble_topic.py`: Testing script for cognitive assembly.

## Configuration & Root
- `pyproject.toml`: Python project dependencies and metadata.
- `conversations.json`: Input data source (conversation history).
