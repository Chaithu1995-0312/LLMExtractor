# MODULE_DEEP_DIVES.md

## 1. Graph Manager Core (`src/nexus/graph/manager.py`)

The `GraphManager` is the authoritative controller for the Nexus state. It handles all state transitions and enforces graph-level invariants.

### Method Intelligence Table: `GraphManager`

| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants Enforced |
| :--- | :--- | :--- | :--- | :--- |
| `register_node` | Atomic node creation/merge | node_type, node_id, attrs | Persistent record in SQLite | Prevents duplicate ID collisions |
| `add_typed_edge` | Schema-aware relationship creation | edge object | Typed edge record | Validates node existence; checks for cycles |
| `promote_node_to_frozen` | Finalize node state | node_id, promote_bricks, actor | State -> `frozen`; audit log entry | Transitions node to immutable status |
| `supersede_node` | Versioning replacement | old_id, new_id, reason | Links old to new; marks old as `superseded` | Maintains lineage; prevents circular supersession |
| `kill_node` | Logical removal | node_id, reason, actor | State -> `killed`; audit log entry | Preserves history (no physical delete) |
| `sync_bricks_to_nodes` | Ingestion bridge | limit | Promotes bricks to Intent nodes | Ensures bricks aren't double-processed |

### Method Usage Graph: `GraphManager`
- **Called By**: `CortexAPI` (via `server.py`), `NexusCompiler` (indirectly via brick promotion), `ui/jarvis` (via REST API).
- **Layer**: Graph Layer.
- **Authority**: Write-authoritative. All state changes MUST pass through this class.

---

## 2. Nexus Compiler (`src/nexus/sync/compiler.py`)

The `NexusCompiler` manages the transformation of raw data into atomic Bricks. It is the primary orchestrator of the Ingestion layer.

### Method Intelligence Table: `NexusCompiler`

| Method Name | Responsibility | Inputs | Outputs / Side Effects | Failure Modes |
| :--- | :--- | :--- | :--- | :--- |
| `compile_run` | Process a conversation run | run_id, topic_id | Count of bricks materialized | LLM timeout; malformed JSON input |
| `_llm_extract_pointers` | Semantic segmentation | content, topic | List of brick pointers | Hallucinated JSON paths; empty responses |
| `_materialize_brick` | Brick persistence | run_data, pointer | JSON Brick object in `BrickStore` | Integrity error on duplicate fingerprint |

### Method Usage Graph: `NexusCompiler`
- **Called By**: `sync_bricks_task` (Cortex Worker), `runner.py` (CLI).
- **Layer**: Ingestion Layer.
- **Authority**: Transactional (Run level). Read-write on `SyncDatabase` and `BrickStore`.

---

## 3. Cognitive Extractor (`src/nexus/cognition/dspy_modules.py`)

Uses DSPy to recursively extract structured knowledge from text context.

### Method Intelligence Table: `CognitiveExtractor`

| Method Name | Responsibility | Inputs | Outputs / Side Effects | Lifecycle Impact |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | Recursive extraction | context, depth | Facts, Entities, Relationships | High token cost; defines graph topology |

### Method Usage Graph: `CognitiveExtractor`
- **Called By**: `RelationshipSynthesizer`, `CortexAPI` (indirectly).
- **Layer**: Cognition Layer.
- **Authority**: Pure (Analytical). No direct side effects on main Graph.

---

## 4. Relationship Synthesizer (`src/nexus/cognition/dspy_modules.py`)

Infers typed edges between existing Intents by analyzing their semantic overlap.

### Method Intelligence Table: `RelationshipSynthesizer`

| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants Enforced |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | Edge inference | intents, existing_edges | List of inferred typed edges | Prevents redundant edge creation |

### Method Usage Graph: `RelationshipSynthesizer`
- **Called By**: `run_relationship_synthesis` (Synthesizer).
- **Layer**: Cognition Layer.
- **Authority**: Stateful Read / Pure Write (Generates proposals for the Graph Layer).
