# NEXUS MODULE DEEP DIVES

## 1. Graph Manager (`src/nexus/graph/manager.py`)
The `GraphManager` is the authoritative state controller for the Nexus Knowledge Graph. It abstracts the underlying SQLite database into a transactional graph interface.

### Method Intelligence: `GraphManager`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `register_node` | Core node insertion. | `type`, `id`, `attrs` | DB write; emits pulse. | Unique `id` constraint. |
| `register_edge` | Directional link creation. | `src`, `dst`, `type` | DB write; cycle check. | No cycles (if enforced). |
| `kill_node` | Logical deletion. | `node_id`, `reason` | Sets status to `KILLED`. | Immutable once killed. |
| `supersede_node` | Versioning/replacement. | `old_id`, `new_id` | Re-links edges to `new_id`. | `old_id` becomes `SUPERSEDED`. |
| `promote_intent` | Lifecycle progression. | `id`, `lifecycle` | Updates node status. | State must be valid Enum. |

- **Usage:** Called by `Cognition` (for fact storage) and `UI` (for manual overrides).
- **Layer:** Graph (State Authoritative).

---

## 2. Nexus Compiler (`src/nexus/sync/compiler.py`)
The `NexusCompiler` transforms messy conversation logs and documents into structured "Bricks". It uses JSON path resolution and LLM pointers to find relevant content.

### Method Intelligence: `NexusCompiler`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `compile_run` | Main orchestrator. | `run_id`, `topic_id` | Full brickification process. | Atomic run completion. |
| `_extract_pointers` | AI-assisted search. | `content`, `topic` | List of content paths. | Paths must exist in source. |
| `_materialize_brick` | Brick creation. | `data`, `pointer` | DB record in `SyncDatabase`. | Unique brick hash. |

- **Usage:** Triggered by `runner.py` or `tasks.py` during sync cycles.
- **Layer:** Ingestion (Data Processing).

---

## 3. Cortex API (`services/cortex/api.py`)
The business logic hub. It coordinates between the Vector Index, the Graph, and the LLM generation modules.

### Method Intelligence: `CortexAPI`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `route` | Intent routing. | `user_query` | Metadata + predicted agent. | Read-only. |
| `generate` | Response synthesis. | `query`, `bricks` | LLM-generated string. | Context window limits. |
| `assemble` | Context gathering. | `topic_id` | Aggregated brick content. | Permission/Scope check. |
| `_audit_trace` | Observability. | `event_data` | Writes to `.jsonl` file. | Non-blocking write. |

- **Usage:** Primary endpoint for the Jarvis UI and external integrations.
- **Layer:** Service (Orchestration).

---

## 4. Vector Index (`src/nexus/vector/local_index.py`)
Provides the semantic backbone for retrieval. Uses FAISS for local vector search.

### Method Intelligence: `LocalVectorIndex`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `add_bricks` | Index update. | `List[Brick]` | Updates FAISS buffer. | Vectors must match dim. |
| `search` | Nearest neighbor. | `query_vector` | List of `(id, score)`. | Sorted by distance. |
| `save` | Persistence. | - | Writes `.index` to disk. | Index must be valid. |

- **Usage:** Heavily used by `Recall` module to find context for LLM prompts.
- **Layer:** Vector (Semantic Storage).

---

## 5. Cognitive Extraction (`src/nexus/cognition/dspy_modules.py`)
Uses DSPy to provide structured reasoning. It identifies facts and relationships from raw text.

### Method Intelligence: `CognitiveExtractor`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | Inference pass. | `context` | List of `Fact` objects. | Adherence to signature. |

### Method Intelligence: `RelationshipSynthesizer`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | Link discovery. | `List[Intent]` | Proposed `Edges`. | Logical consistency. |

- **Usage:** Called during `Topic Assembly` to populate the Graph with extracted knowledge.
- **Layer:** Cognition (Inference).
