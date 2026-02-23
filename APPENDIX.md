# APPENDIX

## Method Intelligence Matrix

| Class | Method | Responsibility | Risk | Used By |
| :--- | :--- | :--- | :--- | :--- |
| **SyncDatabase** | `register_run_safe` | Enforces Zero-Trust Append-Only logic for source ingestion. | MED | `Runner.run_sync` |
| **SyncDatabase** | `save_brick` | Persists extracted Brick and syncs to Unified Graph. | MED | `Runner.run_sync` |
| **GraphManager** | `promote_node_to_frozen` | Locks a node state, making it an anchor. | HIGH | `CortexAPI.jarvis_node_promote` |
| **GraphManager** | `kill_node` | Rejects a node, removing it from active consideration. | HIGH | `CortexAPI.jarvis_node_kill` |
| **GraphManager** | `supersede_node` | Versions a FROZEN node with a newer replacement. | HIGH | `CortexAPI.jarvis_node_supersede` |
| **GraphManager** | `_log_audit_event` | Writes immutable record of state changes. | LOW | `GraphManager` (internal) |
| **Assembler** | `assemble_topic` | End-to-end DSPy pipeline for topic artifact creation. | HIGH | `CortexAPI.cognition_assemble` |
| **Synthesizer** | `run_relationship_synthesis` | Automated discovery of edges between intents. | HIGH | `CortexAPI.cognition_synthesize` |
| **CortexAPI** | `metrics_overview` | Read-only aggregation of DB stats. | LOW | `ui/jarvis` (Dashboard) |

## Edge Type Reference

| Type | Description | Invariant |
| :--- | :--- | :--- |
| `DERIVED_FROM` | Provenance link: Intent -> Brick. | Every Intent MUST have >= 1 source. |
| `ASSEMBLED_IN` | Grouping link: Brick/Intent -> Topic/Artifact. | Used for retrieval scoping. |
| `OVERRIDES` | Conflict resolution: New -> Old. | Source must be valid, Target usually Frozen. |
| `SUPERSEDED_BY` | Versioning: Old -> New. | Both nodes must be FROZEN. |
| `APPLIES_TO` | Scope link: Intent -> ScopeNode. | Required for freezing some intents. |

## Lifecycle Reference

| State | Mutable? | Description |
| :--- | :--- | :--- |
| `LOOSE` | Yes | Volatile, untrusted. Default state. |
| `FORMING` | Yes | Validated by Agent, waiting for human/final approval. |
| `FROZEN` | **NO** | Trusted Anchor. Can only be superseded. |
| `SUPERSEDED` | **NO** | Historical record. Replaced by newer truth. |
| `KILLED` | **NO** | Rejected/Dead. Retained for anti-pattern matching. |
