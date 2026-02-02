# Gaps and TODOs

## Critical / Blocking
- [ ] 🔴 **Real Embeddings**: `LocalVectorIndex` and `BrickStore` currently use `np.random` for embeddings. This renders search results completely random/useless. MUST integrate a real model (e.g., `all-MiniLM-L6-v2` or OpenAI API).
- [ ] 🔴 **Production Server**: Cortex runs via `app.run(debug=True)`. Needs a proper WSGI/ASGI container (Gunicorn/Uvicorn).
- [ ] 🔴 **Missing Graph Builder**: `nodes.json` and `edges.json` exist but there is no code in the repo to generate them. They appear to be static assets. A builder logic is needed.

## Important / High Priority
- [ ] 🟡 **Reranker Implementation**: `RerankOrchestrator` logic is currently a shell. Needs actual implementation (Cross-Encoder).
- [ ] 🟡 **Graph Persistence**: The UI logs anchor promotion/rejection to console. This needs to be sent to a backend endpoint and persisted to `anchors.override.json`.
- [ ] 🟡 **Frontend State**: `App.tsx` is becoming monolithic. Refactor into `contexts` and smaller components.

## Technical Debt / Low Priority
- [ ] 🧪 **Mocking**: `query_to_vector` in `brick_store.py` uses a different random seed method than `LocalVectorIndex`. Even for mocks, this is inconsistent.
- [ ] 🧪 **Error Handling**: `server.py` has basic try/except blocks. Needs structured error responses and logging.
- [ ] 🧪 **Types**: Frontend types (`GraphNode`, `GraphEdge`) are defined in `App.tsx`. Move to a shared types file.
