# MODULE_DEEP_DIVES

## 1. Graph Manager (`src/nexus/graph/manager.py`)
The `GraphManager` is the system's **Transactional Source of Truth**. It encapsulates all SQLite operations, ensuring that the graph state remains consistent across cognitive operations.

### Method Intelligence Table: `GraphManager`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `register_node` | Core node persistence | type, id, attrs, merge | Writes to SQL; updates `nodes.json` | Node ID uniqueness |
| `promote_node_to_frozen` | Lifecycle advancement | node_id, promote_bricks, actor | Updates state to `FROZEN`; creates audit link | Only `FORMING` can become `FROZEN` |
| `kill_node` | Soft deletion | node_id, reason, actor | State -> `KILLED`; prevents further retrieval | Requires valid `reason` string |
| `supersede_node` | Versioning | old_id, new_id, reason, actor | Old -> `SUPERSEDED`; New -> active | Preserves edge history |
| `add_intent` | Intent registration | Intent object | Direct SQL insert | Enforces schema validation |

### Method Usage Graph
- `register_node` is called by `NexusIngestor` during discovery.
- `promote_node_to_frozen` is called by `CortexAPI` via `server.py` endpoints.
- `kill_node` is triggered by UI actions via `server.py`.

---

## 2. Cortex API (`services/cortex/api.py`)
`CortexAPI` serves as the **Operational Orchestrator**. It bridges the gap between semantic retrieval and cognitive synthesis.

### Method Intelligence Table: `CortexAPI`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `route` | Query dispatching | query | Specific handler response | None (Heuristic branch) |
| `generate` | Final answer synthesis | query, brick_ids | Structured LLM response | Requires at least 1 brick |
| `_audit_trace` | Governance logging | IDs, model, tokens | Appends to `phase3_audit_trace.jsonl` | Write-authoritative for audit |
| `_fetch_graph_context` | Context assembly | brick_ids | Formatted string for LLM | Must respect scope boundaries |

### Control Flow and Authority
`CortexAPI` holds the authority for **Cognitive Spend**. No LLM call is made without passing through `CortexAPI`, ensuring every token used is logged in the Audit Trace. It enforces the "Human-in-the-loop" requirement by prioritizing `FROZEN` nodes in context assembly.

---

## 3. Cognitive Extractor (`src/nexus/cognition/dspy_modules.py`)
This module represents the **Inference Authority**. It defines how raw text is distilled into structured knowledge.

### Method Intelligence Table: `CognitiveExtractor`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `forward` | Primary inference loop | context | Facts, Diagrams | DSPy-governed output |
| `extract_facts` (IMPLIED) | Atomic fact detection | context | List of Fact objects | No contradictory facts |
| `generate_diagram` (IMPLIED)| Architectural mapping | context | Mermaid/DSL code | Valid syntax |

### Layer Assignment: Cognition
This layer is **Stateful** in terms of prompt optimization (DSPy compiled states) but **Pure** in its execution—it does not write directly to the graph; it returns structured objects to the Service layer for registration.

---

## 4. Nexus Ingestor (`src/nexus/sync/ingest_history.py`)
The **Ingestion Boundary**. It is responsible for the "First Contact" with raw data.

### Method Intelligence Table: `NexusIngestor`
| Method Name | Responsibility | Inputs | Outputs / Side Effects | Invariants |
| :--- | :--- | :--- | :--- | :--- |
| `brickify` | Text atomization | content, source | List of Bricks | Semantic integrity of atoms |
| `ingest_history` | Batch processing | input_path | Mass registration in Graph & Vector | Idempotency via content hash |

### Usage Graph
`NexusIngestor` is a standalone CLI tool or scheduled task. It is the primary writer for `LOOSE` nodes and Source records in the `GraphManager`.
