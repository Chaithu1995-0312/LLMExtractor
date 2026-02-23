# GAPS_AND_TODOS

## 🔴 Critical Architectural Gaps

### 1. Security & Authentication
*   **Missing:** No auth middleware in `services/cortex/server.py`.
*   **Risk:** Unprotected API endpoints allow anyone to modify the graph.
*   **Remediation:** Implement JWT/OAuth2 middleware.

### 2. Transactional Integrity
*   **Weakness:** `GraphManager` writes to Postgres but `SyncDatabase` might write to SQLite/Postgres independently. Unified transaction manager missing.
*   **Risk:** Data inconsistency if one write fails.
*   **Remediation:** Implement a global `UnitOfWork` pattern or 2PC if multiple DBs.

### 3. Cognition Robustness
*   **Weakness:** `nexus.cognition.synthesizer` uses broad try/except blocks around DSPy calls.
*   **Risk:** Silent failures in relationship discovery.
*   **Remediation:** Implement circuit breakers and typed error handling for LLM calls.

## 🟡 High-Priority TODOs

### 1. Governance
- [ ] **Implement Proactive Alerts:** Currently `_log_audit_event` just logs. Needs to trigger alerts (PagerDuty/Slack).
- [ ] **Budget Enforcer:** Block LLM calls if daily spend > $X.

### 2. Frontend (UI)
- [ ] **Auth UI:** Login screen and token management.
- [ ] **Graph Editing:** Visual editor for fixing incorrect edges (drag-and-drop).

### 3. Testing
- [ ] **Integration Tests:** End-to-end test from `ingest` -> `graph` -> `api`.
- [ ] **Load Testing:** Verify graph performance with 100k+ nodes.

## 🧪 Future Experiments (Low Priority)
- [ ] **Multi-Model Support:** Allow swapping Ollama for OpenAI/Anthropic per task.
- [ ] **Vector Hybrid Search:** Combine keyword search (BM25) with vector search (FAISS).
