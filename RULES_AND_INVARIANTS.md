# RULES_AND_INVARIANTS

## 1. Knowledge Lifecycle Invariants
The core value of NEXUS is the strict enforcement of knowledge state transitions.

| Rule ID | Name | Description | Enforcer |
| :--- | :--- | :--- | :--- |
| **LIF-01** | Unidirectional Promotion | Nodes move `LOOSE` -> `FORMING` -> `FROZEN`. They cannot move backward unless superseded. | `GraphManager.promote_node_to_frozen` |
| **LIF-02** | Tombstone Integrity | Once a node is `KILLED`, its ID cannot be reused for a new node. It must remain in the graph as a tombstone. | `GraphManager.kill_node` |
| **LIF-03** | Conflict Resolution | A `FROZEN` node cannot be promoted if an active `CONFLICT` edge exists with another `FROZEN` node of the same scope. | `GraphManager` (IMPLIED check) |

## 2. Graph Connectivity Rules
| Rule ID | Name | Description | Enforcer |
| :--- | :--- | :--- | :--- |
| **CON-01** | Source Requirement | Every `LOOSE` node must have at least one `SUPPORTED_BY` edge linking to a `Source` node. | `NexusIngestor.brickify` |
| **CON-02** | Cycle Prevention | Hierarchical `SCOPE` relationships must be a Directed Acyclic Graph (DAG). No scope can contain itself. | `src/nexus/graph/validation.py` |
| **CON-03** | Atomic Bricks | A "Brick" is the smallest unit of knowledge. It cannot be further subdivided without generating a new ID and superseding the parent. | `extractor.py` |

## 3. Cognitive & Governance Rules
| Rule ID | Name | Description | Enforcer |
| :--- | :--- | :--- | :--- |
| **GOV-01** | Mandatory Audit | No LLM-driven knowledge mutation can occur without a corresponding entry in `phase3_audit_trace.jsonl`. | `CortexAPI._audit_trace` |
| **GOV-02** | Context Provenance | Responses generated for users must include citations to the specific `brick_ids` used in the assembly. | `CortexAPI.generate` |
| **GOV-03** | Threshold Confidence | A node cannot be promoted to `FROZEN` if its `confidence` score is below 0.7. | `ui/jarvis/src/components/NexusNode.tsx` (Visual cue) |

## 4. Operational Invariants
- **Write-Authoritative Boundary**: Only the `GraphManager` can perform `COMMIT` operations on the SQLite database.
- **Read-Only Scopes**: Retrieval operations (`recall_bricks_readonly`) must never modify the vector index or graph state.
- **Idempotent Ingestion**: Re-running the same `conversations.json` through the `NexusIngestor` must not result in duplicate nodes (Content hashing).
