# Nexus: Inferred Enhancements

## Architectural Inferences
Based on the current trajectory of the Nexus codebase, the following enhancements are inferred as necessary for autonomous operational maturity.

### 1. Event-Driven Graph Pulse 🧪
Currently, graph synchronization and vector indexing are batch processes. The system implies a transition to an **Event-Driven Architecture**.
- **Inferred Method**: `GraphManager._emit_pulse(event_type, payload)`
- **Behavior**: Every successful mutation (e.g., node promotion) should emit a pulse that triggers downstream tasks (Vector refresh, Alert re-evaluation, UI notification).
- **Status**: 🧪 (Partially present in `GraphManager` as a skeleton).

### 2. Multi-Tier Model Routing 🧪
The `LLMRouter` implies a more sophisticated routing logic than currently implemented.
- **Inferred Logic**: Use `ModelTier.LOCAL` (Ollama) for extraction/filtering and `ModelTier.PREMIUM` (OpenAI) for complex relationship synthesis and prompt generation.
- **Inferred Method**: `LLMRouter.route_by_complexity(request_payload) -> LLMRoute`
- **Status**: 🧪 (Planned in `src/nexus/sync/llm.py`).

### 3. Graph-Native RAG (Recall v2) 🔴
Current recall (`src/nexus/ask/recall.py`) relies heavily on flat vector search. The existence of the Knowledge Graph suggests a **Graph-Native RAG** approach.
- **Inferred Behavior**: Perform vector search to find "Entry Bricks," then traverse `DEPENDS_ON` and `RELATES_TO` edges to pull context that vector similarity might miss.
- **Status**: 🔴 (MISSING_FROM_CONTEXT).

### 4. Self-Correcting Ingest Pipeline 🔴
Given the noise in conversation history, a self-correcting ingest layer is implied.
- **Inferred Method**: `NexusCompiler._validate_materialization(brick_data)`
- **Behavior**: Use a DSPy "Validator" to check if a materialized brick contradicts existing `FROZEN` intents before allowing it into the sync database.
- **Status**: 🔴 (MISSING_FROM_CONTEXT).

### 5. Intent Clustering (Unsupervised Cognition) 🧪
The `CognitiveExtractor` currently works on a topic-by-topic basis. A cross-topic clustering mechanism is inferred.
- **Inferred Logic**: Periodically run unsupervised clustering on all `PROPOSED` intents to identify emerging topics that haven't been manually defined.
- **Status**: 🧪 (Implied by `scripts/maintenance/rebuild_unified_graph.py`).
