# IMPLEMENTATION_REALITY_MAP.md

## Layer status: Ingestion & Sync

### `NexusCompiler` (src/nexus/sync/compiler.py)
- `compile_run` ✅ Implemented (Orchestrates brick extraction from raw runs)
- `_pre_filter_nodes` ✅ Implemented (Initial content scanning)
- `_llm_extract_pointers` ✅ Implemented (Generates brick pointers via LLM)
- `_materialize_brick` ✅ Implemented (Transforms pointers into persisted bricks)

### `BrickStore` (src/nexus/bricks/brick_store.py)
- `save_brick` ✅ Implemented (Physical persistence)
- `get_brick` ✅ Implemented (Retrieval)

## Layer status: Graph Management

### `GraphManager` (src/nexus/graph/manager.py)
- `register_node` ✅ Implemented (Core node creation with conflict resolution)
- `register_edge` ✅ Implemented (Basic edge creation)
- `add_typed_edge` ✅ Implemented (Schema-aware edge creation)
- `promote_node_to_frozen` ✅ Implemented (Lifecycle state transition)
- `supersede_node` ✅ Implemented (Versioning/Replacement logic)
- `kill_node` ✅ Implemented (Logical deletion)
- `_check_for_cycle` ✅ Implemented (Graph integrity check)
- `sync_bricks_to_nodes` ✅ Implemented (Bridge between Ingestion and Graph)

## Layer status: Cognition

### `RelationshipSynthesizer` (src/nexus/cognition/dspy_modules.py)
- `forward` ✅ Implemented (Relationship inference via DSPy)
- `analyze_sentiment` 🟡 Partial (Initial logic present, not integrated in main flow)

### `CognitiveExtractor` (src/nexus/cognition/dspy_modules.py)
- `forward` ✅ Implemented (Recursive entity/fact extraction)

### `Synthesizer` (src/nexus/cognition/synthesizer.py)
- `run_relationship_synthesis` ✅ Implemented (Batch synthesis runner)

## Layer status: Service & API

### `CortexAPI` (services/cortex/api.py)
- `route` ✅ Implemented (Central query routing)
- `generate` ✅ Implemented (Final context-aware response generation)
- `ask_preview` ✅ Implemented (Fast retrieval preview)
- `get_audit_events` ✅ Implemented (Observability endpoint)
- `trigger_self_healing` 🔴 Missing (Planned for automated graph correction)

### `JarvisGateway` (services/cortex/gateway.py)
- `pulse` ✅ Implemented (Event broadcasting)
- `explain` ✅ Implemented (LLM-backed reasoning)

## Layer status: UI (Jarvis)

### `Store` (ui/jarvis/src/store.ts)
- `fetchGraph` ✅ Implemented
- `promoteNode` ✅ Implemented
- `killNode` ✅ Implemented

### `Components`
- `WallView` ✅ Implemented (Spatial layout)
- `NodeEditor` ✅ Implemented (Node metadata modification)
- `AuditPanel` ✅ Implemented (Live trace monitoring)
- `CortexVisualizer` 🧪 Mocked (Simulated cognitive state visualization)
