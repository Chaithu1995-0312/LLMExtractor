# Gaps and TODOs

## Critical Path

### 🔴 Infrastructure & CI/CD
- [ ] **GitHub Actions Workflow**: No automated testing or linting on push.
- [ ] **Dockerization**: Service runs on bare metal; needs a `Dockerfile` and `docker-compose.yml` for Cortex + UI + DB.
- [ ] **Environment Config**: Hardcoded paths (e.g., `d:/chatgptdocs`) in environment details need to be fully configurable via `.env`.

### 🟡 Cognitive Pipeline Maturity
- [ ] **DSPy Optimization**: `FactSignature` is too generic. Needs specialized signatures for Code, Architecture, and Definitions.
- [ ] **Reranking Integration**: `cross_encoder.py` exists but isn't wired into the `recall_bricks` hot path in `nexus.ask`.
- [ ] **Hallucination Check**: No self-correction loop to verify if extracted facts are actually supported by the source Bricks.

### 🟡 User Interface Experience
- [ ] **Real-time Updates**: UI likely polls or refreshes manually. Needs WebSocket or SSE for graph updates.
- [ ] **Complex Editing**: Can only "Promote/Reject". Cannot edit Intent statements or merge nodes via UI.
- [ ] **Scope Management**: No UI to create or assign Scopes to Intents.

## Technical Debt

### 🧪 Vector Storage Scalability
- **Current**: `IndexFlatL2` (Brute force).
- **Risk**: Performance degradation > 100k vectors.
- **Fix**: Switch to `IndexIVFFlat` or migrate to Qdrant/Chroma.

### 🧪 Graph Projections
- **Current**: `projection.py` has logic but isn't exposed via API.
- **Risk**: API returns raw graph; frontend has to do heavy lifting to filter views.
- **Fix**: Expose projection endpoints (e.g., `/graph/view?scope=python`).

## Missing Features

- **Auth**: No authentication on Cortex API.
- **Multi-user**: No user isolation in Graph or History.
- **Backup**: No automated backup for `graph.db`.
