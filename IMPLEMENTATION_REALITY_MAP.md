# IMPLEMENTATION_REALITY_MAP

**Status Legend:**
✅ **Confirmed:** Logic present and operational.
🟡 **Partial:** Stubs, TODOs, or fragile implementation.
🔴 **Missing:** Referenced but not found.
🧪 **Mocked/Simulated:** Hardcoded or test-only logic.
🗑️ **Scrap/Diverted:** Deprecated or unused code.

## 1. Core Modules (`src/nexus`)

### `sync` (Ingestion Engine)
*   ✅ **Compiler (`compiler.py`):** Robust logic for parsing source runs into Bricks.
*   ✅ **Database (`db.py`):** Handles `topics`, `source_runs`, and `bricks` with append-only guarantees.
*   ✅ **Runner (`runner.py`):** Orchestrates the ingestion pipeline.
*   ✅ **CLI (`__main__.py`):** Entry point for sync operations.

### `graph` (Knowledge Graph)
*   ✅ **Manager (`manager.py`):** Central authority for node/edge lifecycle (LOOSE → FROZEN).
*   ✅ **Schema (`schema.py`):** Defines `Intent`, `Source`, `EdgeType`, `Lifecycle`.
*   ✅ **Projection (`projection.py`):** Logic for flattening graph views.
*   🟡 **Validation (`validation.py`):** Basic cycle detection exists in `manager.py`, but standalone validator is partial.

### `cognition` (AI Logic)
*   ✅ **Assembler (`assembler.py`):**  `assemble_topic` pipeline with DSPy integration and artifact persistence.
*   🟡 **Synthesizer (`synthesizer.py`):** `run_relationship_synthesis` exists but has fragile try/except blocks around DSPy calls.
*   ✅ **DSPy Modules (`dspy_modules.py`):**  (Inferred) Wrappers for LLM calls.
*   ✅ **Coverage Scorer (`coverage_scorer.py`):** Logic to score topic coverage.

### `vector` & `rerank` (Search)
*   ✅ **Embedder (`vector/embedder.py`):** Handles embedding generation.
*   ✅ **Index (`vector/index.py`):** FAISS/Vector store interface.
*   ✅ **Cross Encoder (`rerank/cross_encoder.py`):** Reranking logic for search results.

### `ask` (Query)
*   ✅ **Recall (`ask/recall.py`):** `recall_bricks_readonly` implements the retrieval logic.

## 2. Services (`services`)

### `cortex` (API Gateway)
*   ✅ **Server (`server.py`):** Flask app with Socket.IO, serving API and UI.
*   ✅ **API (`api.py`):** Application logic layer bridging Server and Core.
*   🟡 **Orchestration (`orchestration.py`):** Partial logic for complex workflows.
*   🟡 **Worker (`worker.py`):** Celery integration logic, fallback to sync is implemented.
*   🧪 **Audit Log (`phase3_audit_trace.jsonl`):** File-based audit log (should be DB in prod).

### `mcp` (Model Context Protocol)
*   ✅ **Nexus Server (`nexus_server.py`):** Implementation of MCP server.

## 3. User Interface (`ui/jarvis`)

### Frontend
*   ✅ **App Structure (`App.tsx`):** Main React application layout.
*   ✅ **State Management (`store.ts`, `reducers/`):** Redux-like state handling.
*   ✅ **Protocol (`protocol/event-types.ts`):** Typed event definitions for WebSocket.
*   ✅ **Components:** Rich set of components (`CortexVisualizer`, `AuditPanel`, etc.).

## 4. Infrastructure & Scripts

### Database
*   ✅ **Postgres (`src/nexus/db/postgres.py`):** Production DB adapter.
*   ✅ **SQLite (`src/nexus/db/adapter.py`):** Local/Dev DB adapter.
*   ✅ **Schema SQL (`src/nexus/graph/*.sql`):** SQL definitions for schema.

### Scripts
*   ✅ **Migration (`scripts/migrate_*.py`):** Utilities for DB migration.
*   ✅ **Maintenance (`scripts/maintenance/`):** Pruning and rebuilding scripts.
*   ✅ **Testing (`scripts/test_*.py`):** Various integration test scripts.

## 5. Diverted / Scrap Code
*   🗑️ **Archive (`archive/`):** Old `neo4j_manager.py` and `pinecone_index.py` - replaced by Postgres/FAISS.
*   🗑️ **Legacy Docs (`impldocs/`):** Text files describing previous implementation plans.
