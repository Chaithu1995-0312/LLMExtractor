# NEXUS GAPS AND TODOS

## 1. High Priority (Architectural Gaps) 🔴
- **JSON Path Robustness:** `NexusCompiler._resolve_json_path` currently fails on nested arrays and wildcards. Needs a proper JSONPath library integration.
- **Transactional DB Wrappers:** `GraphManager` operations use raw `sqlite3` commits. Need a context manager for multi-statement transactions to prevent partial writes.
- **Sync State Migration:** Transition from `runner_old.py` (file-based state) to `runner.py` (DB-based state) is incomplete. Old state files are still present.
- **Reranker Latency:** `LlmReranker` is too slow for real-time API use. Needs a quantization or caching strategy.

## 2. Medium Priority (Feature Completeness) 🟡
- **Audit Filtering:** `CortexAPI.get_audit_events` needs advanced filtering (e.g., filter by specific `node_id` or `actor`).
- **Relationship Synthesis Batching:** `synthesizer.py` relationship discovery is currently all-or-nothing. Needs incremental batching to handle large graphs.
- **UI Real-time Sync:** `Jarvis` UI requires manual refresh to see new nodes created via `Cognition` background tasks.

## 3. Low Priority (Maintenance & DX) 🧪
- **Mock Cleanup:** `LLMClient._mock_response` should be moved to a dedicated testing provider.
- **Documentation Drift:** Inline docstrings in `src/nexus/graph/schema.py` are outdated compared to the actual database implementation.
- **Test Coverage:** Low coverage for edge cases in `supersede_node` logic (e.g., superseding a node that has already been killed).

## 4. Technical Debt 🔴
- **Global Singletons:** `VectorEmbedder` uses a singleton pattern that makes unit testing difficult.
- **Hardcoded Paths:** Multiple files contain hardcoded paths to `.db` and `.index` files. These should be moved to `src/nexus/config.py`.
- **Error Handling:** Many internal methods (e.g., `_load_tree_file`) do not have robust exception handling for missing files.

## 5. Implementation Roadmap (TODOs)
- [ ] Integrate `jsonpath-ng` into `NexusCompiler`.
- [ ] Implement `GraphTransaction` context manager.
- [ ] Deprecate `runner_old.py` and migrate all state to `SyncDatabase`.
- [ ] Add WebSocket support to `CortexAPI` for real-time audit streaming.
- [ ] Implement `heuristic` fallbacks for `LlmReranker` timeouts.
- [ ] Standardize config management via `dotenv` or `yaml`.
