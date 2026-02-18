# Inferred Enhancements

## 1. High-Impact Architecture Changes

### A. Migration to PostgreSQL
*   **Current**: SQLite (`graph.db`) with file-level locking.
*   **Proposed**: PostgreSQL with `pgvector` extension.
*   **Benefit**:
    -   Handles concurrent writes from Sync and API.
    -   Native vector search (replacing FAISS/`local_index.py` for simpler stack).
    -   Row-level locking for better performance.

### B. Parallel Ingestion Pipeline
*   **Current**: Sequential processing in `runner.py`.
*   **Proposed**: Use `concurrent.futures.ProcessPoolExecutor` for the `process_conversation` and `compile_run` steps.
*   **Benefit**: 5-10x speedup for initial ingestion of large history dumps.

## 2. Cognitive Enhancements

### A. Semantic Caching
*   **Concept**: Cache LLM responses for `NexusCompiler` based on the semantic similarity of the source block.
*   **Benefit**: Drastically reduces cost and time for re-runs of the sync pipeline.

### B. Active Learning Loop
*   **Concept**: When a user "Rejects" a node via `jarvis_anchor`, automatically generate a negative example for the DSPy `CognitiveExtractor`.
*   **Benefit**: System gets smarter over time without code changes.

## 3. Operational Improvements

### A. Structured Logging & Tracing
*   **Current**: `utils_logging.py` prints to stdout/file.
*   **Proposed**: OpenTelemetry integration for distributed tracing across Flask and Celery.

### B. Containerization
*   **Current**: Local python scripts.
*   **Proposed**: Docker Compose setup with services:
    -   `nexus-api` (Flask)
    -   `nexus-worker` (Celery)
    -   `nexus-db` (Postgres)
    -   `nexus-redis` (Redis)
    -   `nexus-ui` (React/Nginx)
