# INFERRED_ENHANCEMENTS

These enhancements are logically derived from the current architecture but are not yet present in the codebase.

## 1. Strategic Architectural Shifts

### A. Graph-Grounded Reranking
**Current**: Retrieval uses FAISS and semantic embeddings.
**Inferred**: Use the `GraphManager` to boost Brick scores if they belong to a `FROZEN` node or share many `Source` edges with already retrieved bricks.
- **Impact**: Higher precision for historical queries.

### B. Proactive Conflict Detection
**Current**: `has_conflict` is a helper in `projection.py`.
**Inferred**: Move conflict detection to a background process in `CortexAPI`. When two `FORMING` nodes appear to describe the same fact with different values, create a `CONFLICT` edge automatically and flag it in the UI.
- **Impact**: Pre-emptive data cleaning.

## 2. Technical Optimizations

### C. Vector Compression & Quantization
**Current**: `LocalVectorIndex` stores raw float32 vectors.
**Inferred**: Implement Product Quantization (PQ) within the FAISS wrapper as the knowledge base grows to 100k+ bricks.
- **Impact**: Reduced memory footprint.

### D. Multi-Agent Consensus
**Current**: Single LLM path in `generate`.
**Inferred**: Use the `Orchestration` layer to run three parallel `CognitiveExtractor` calls for high-risk promotion tasks. Only promote to `FROZEN` if 2/3 agents agree on the fact set.
- **Impact**: High-integrity automated knowledge curation.

## 3. UI/UX Enhancements

### E. Time-Travel Debugger
**Current**: `supersede_node` exists in the graph.
**Inferred**: A UI slider in `WallView` that uses the `lastUpdatedAt` and `reason` metadata to show the graph state at any point in history.
- **Impact**: Powerful human audit capability.

### F. Cognitive Hot-Loading
**Current**: DSPy modules are initialized at startup.
**Inferred**: An API endpoint to "re-compile" or swap DSPy prompts without restarting the `Cortex` server.
- **Impact**: Rapid iteration on knowledge extraction logic.
