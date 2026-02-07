# GAPS_AND_TODOS

## 1. High Priority (Critical)

- [ ] **Security:** `services/cortex/server.py` has no authentication. Add API Key or OAuth middleware.
- [ ] **Data Integrity:** `GraphManager.kill_node` does not explicitly check for incoming edges that might break traversal (orphaned nodes).
- [ ] **Error Handling:** `CognitiveExtractor` in `assembler.py` swallows DSPy errors. Add robust retry logic and error reporting.

## 2. Medium Priority (Important)

- [ ] **Audit Logs:** `GraphManager._log_audit_event` only prints to stdout. Implement structured file logging (`phase3_audit_trace.jsonl`).
- [ ] **Scalability:** `GraphManager` uses SQLite directly. For production, migrate to PostgreSQL or Neo4j.
- [ ] **Search:** `recall_bricks_readonly` uses `k=15` hardcoded. Make configurable based on query complexity.
- [ ] **UI Feedback:** `ControlStrip` actions are optimistic. Add loading states and error toasts.

## 3. Low Priority (Nice to Have)

- [ ] **Visuals:** `CortexVisualizer` "Radar" mode is experimental. Polish rendering.
- [ ] **Refinement:** Implement "Merge Nodes" feature for manual consolidation of similar intents.
- [ ] **Testing:** Add unit tests for `GraphManager` lifecycle transitions.
