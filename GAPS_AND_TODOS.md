# Gaps and TODOs

## 1. Critical Technical Debt
-   [ ] **Sync Performance**: `runner.py` processes conversations sequentially. Needs parallelization (`ProcessPoolExecutor`) for large datasets.
-   [ ] **Graph Scalability**: Currently using a single SQLite file (`graph.db`). Concurrent writes (Sync + Synthesis + API) will hit lock contention.
-   [ ] **Error Handling**: `synthesizer.py` uses broad `except Exception` blocks. Needs specific error handling and recovery strategies.
-   [ ] **Test Coverage**: Unit test coverage is sparse. `tests/` folder contains mostly integration tests.

## 2. Missing Features
-   [ ] **Authentication**: `server.py` has no authentication middleware. The API is effectively open to the network.
-   [ ] **Incremental Sync**: The `runner.py` has logic for `rebuild_index` but lacks true differential sync (processing only new messages in existing conversations).
-   [ ] **Multi-Tenancy**: The system assumes a single user/tenant. `src/nexus/config.py` hardcodes paths.
-   [ ] **Cognitive Feedback Loop**: There is no automated retraining. "Rejected" nodes do not currently improve future DSPy extraction prompts.

## 3. Recommended Immediate Actions
1.  **Migrate DB**: Switch `SyncDatabase` and `GraphManager` to PostgreSQL to allow concurrent API and Sync operations.
2.  **Secure API**: Add API Key middleware to `services/cortex/server.py`.
3.  **Parallelize**: Refactor `NexusCompiler` to support parallel execution.
4.  **Schema Migration**: Implement a formal migration tool (e.g., Alembic) instead of manual SQL scripts.
