# FILE_INDEX

## 1. Graph Layer (`src/nexus/graph`)

### `manager.py`
Contains the primary authority for graph persistence and state.
- **`GraphManager`**: Central SQLite-backed manager for knowledge nodes.
  - `register_node`: Persists or updates nodes with attribute merging.
  - `promote_node_to_frozen`: Lifecycle gate for knowledge validation.
  - `kill_node`: Logical deletion with audit reasoning.
  - `supersede_node`: Version control for replacing old knowledge.
  - `get_intents_by_topic`: Relational retrieval for cognitive assembly.

### `projection.py`
Transforms raw graph data into specific views.
- `project_intent`: Calculates layout/state for UI lanes.
- `has_conflict`: Logic to detect overlapping intent claims.

### `schema.py`
Defines the structural types for the system.
- `Intent`, `Source`, `ScopeNode`: Core node entities.
- `Edge`: Relationship entity with `EdgeType` classification.

### `validation.py`
Ensures graph integrity.
- `validate_no_cycles`: Invariant enforcement for hierarchical scopes.

---

## 2. Cognition Layer (`src/nexus/cognition`)

### `dspy_modules.py`
Defines the LLM interaction signatures.
- **`CognitiveExtractor`**: DSPy module for structured knowledge extraction.
  - `forward`: Orchestrates the context-to-fact flow.
- `FactSignature`: Schema for atomic fact extraction.
- `DiagramSignature`: Schema for visual architectural generation.

### `assembler.py`
Synthesizes high-level topics from low-level data.
- `assemble_topic`: Collates related bricks into a unified topic summary.

---

## 3. Service Layer (`services/cortex`)

### `api.py`
Main entry point for external interaction.
- **`CortexAPI`**: Orchestrates search, retrieval, and generation.
  - `route`: Logic to dispatch queries to specific handlers.
  - `generate`: Synthesizes final LLM responses using graph context.
  - `_audit_trace`: Logs operations for human audit.

### `server.py`
Flask-based REST interface.
- Maps internal methods to endpoints (e.g., `/jarvis/node/promote`).

---

## 4. Vector & Search Layer (`src/nexus/vector`, `src/nexus/ask`)

### `src/nexus/vector/embedder.py`
- **`VectorEmbedder`**: Manages embedding model lifecycle and query rewriting.

### `src/nexus/vector/local_index.py`
- **`LocalVectorIndex`**: FAISS wrapper for brick persistence.

### `src/nexus/ask/recall.py`
- `recall_bricks`: Orchestrates multi-stage retrieval (Semantic search + Scoping).

---

## 5. UI Layer (`ui/jarvis/src/components`)

### `NexusNode.tsx`
- **`NexusNode`**: React component for individual knowledge nodes.
  - Renders lifecycle state, confidence, and telemetry.

### `WallView.tsx`
- **`WallView`**: Layout engine for lifecycle lanes (Frozen/Forming/Loose).
  - Organizes nodes into vertical swimlanes.
