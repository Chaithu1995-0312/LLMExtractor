# File Index

## Services

### Cortex (API / Orchestration)
- `services/cortex/api.py`: ✅ Core API implementation (Routing, Generation, Assembly).
- `services/cortex/server.py`: ✅ Server entry point (FastAPI?).
- `services/cortex/orchestration.py`: 🟡 Orchestration logic (likely being merged into `api.py`).
- `services/cortex/runcortexapi.py`: ✅ CLI entry point for running the server.
- `services/cortex/phase3_audit_trace.jsonl`: 🧪 Audit log data.

### MCP
- `services/mcp/nexus_server.py`: ✅ Model Context Protocol implementation for Nexus tools.

## Source Code (`src/nexus`)

### Core
- `src/nexus/config.py`: ✅ System-wide configuration.
- `src/nexus/__init__.py`: Package init.

### Sync & Ingestion
- `src/nexus/sync/ingest_history.py`: ✅ History ingestion logic.
- `src/nexus/sync/runner.py`: ✅ Main ingestion runner.
- `src/nexus/sync/__main__.py`: CLI entry point for sync.

### Bricks (Memory Units)
- `src/nexus/bricks/extractor.py`: ✅ Semantic distillation (cleaning/splitting).
- `src/nexus/bricks/brick_store.py`: ✅ Content retrieval and metadata access.

### Vector Search
- `src/nexus/vector/local_index.py`: ✅ FAISS implementation (Active).
- `src/nexus/vector/pinecone_index.py`: 🟡 Pinecone implementation (Inactive).
- `src/nexus/vector/embedder.py`: ✅ Embedding generation (SentenceTransformers).
- `src/nexus/vector/index.py`: Abstract interface?

### Recall
- `src/nexus/ask/recall.py`: ✅ Retrieval orchestration (Recall -> Rerank).

### Cognition
- `src/nexus/cognition/assembler.py`: ✅ Topic assembly pipeline.
- `src/nexus/cognition/dspy_modules.py`: ✅ DSPy signatures and modules.
- `src/nexus/cognition/README.md`: Documentation.

### Graph
- `src/nexus/graph/manager.py`: ✅ SQLite graph implementation (Active).
- `src/nexus/graph/neo4j_manager.py`: 🟡 Neo4j graph implementation (Inactive).
- `src/nexus/graph/schema.py`: ✅ Data models (Intent, Edge, Lifecycle).
- `src/nexus/graph/validation.py`: ✅ Graph integrity checks.
- `src/nexus/graph/projection.py`: ✅ Graph projection logic.

### Rerank
- `src/nexus/rerank/cross_encoder.py`: ✅ Cross-encoder implementation.
- `src/nexus/rerank/orchestrator.py`: ✅ Reranking coordination.

### CLI
- `src/nexus/cli/main.py`: ✅ Command-line interface.

## User Interface (`ui/jarvis`)
- `ui/jarvis/src/App.tsx`: ✅ Main React component.
- `ui/jarvis/src/components/NexusNode.tsx`: ✅ Graph visualization component.
- `ui/jarvis/src/store.ts`: ✅ State management.
- `ui/jarvis/vite.config.ts`: Build config.

## Scripts & Utilities
- `scripts/migrate_to_intents.py`: 🧪 Migration utility.
- `scripts/test_assemble_topic.py`: 🧪 Test script for assembly.
- `scripts/visualize_walls.py`: Visualization tool.
- `scripts/utilities/`: Various helper scripts.
