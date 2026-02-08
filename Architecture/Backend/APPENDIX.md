# APPENDIX.md

## Consolidated Class → Method → Responsibility Reference Table

| Class | Method | Responsibility | Used By |
| :--- | :--- | :--- | :--- |
| `GraphManager` | `register_node` | Atomic persistence with conflict checks | `NexusCompiler`, `CortexAPI`, UI |
| `GraphManager` | `add_typed_edge` | Invariant-safe relationship creation | `Synthesizer`, UI |
| `GraphManager` | `promote_node_to_frozen` | Immutable state transition | `CortexAPI`, UI |
| `GraphManager` | `supersede_node` | Knowledge versioning and replacement | `CortexAPI`, UI |
| `GraphManager` | `sync_bricks_to_nodes` | Batch ingestion promotion | `tasks.py`, `CortexAPI` |
| `NexusCompiler` | `compile_run` | Main pipeline orchestration | `tasks.py`, CLI |
| `NexusCompiler` | `_materialize_brick` | Brick persistence and deduplication | Internal |
| `SyncDatabase` | `save_brick` | Low-level brick storage | `NexusCompiler` |
| `CortexAPI` | `route` | Strategic query routing | `server.py` (Flask) |
| `CortexAPI` | `generate` | Contextual response synthesis | `server.py` (Flask) |
| `RecallEngine` | `recall_bricks` | Hybrid vector/graph retrieval | `CortexAPI` |
| `RelationshipSynthesizer`| `forward` | DSPy-based edge inference | `Synthesizer` |
| `CognitiveExtractor` | `forward` | Recursive semantic extraction | `RelationshipSynthesizer` |
| `JarvisGateway` | `pulse` | Real-time event broadcasting | `GraphManager`, `CortexAPI` |

## Layer Definitions
- **Ingestion**: Raw data capture, fingerprinting, and atomic segmentation (Bricks).
- **Graph**: Persistent source of truth for validated knowledge units (Intents) and relations (Edges).
- **Cognition**: Analytical layer for relationship discovery, assembly, and synthesis.
- **Service**: Orchestration and API gateway for external consumers.
- **UI**: Visual representation and manual override interface.

## System Invariants Summary
- **DAG enforcement** on dependency/lineage edges.
- **Audit-trailed state transitions** (Draft → Frozen → Superseded/Killed).
- **Fingerprint-locked ingestion** (No duplicate bricks).
- **Actor-bound write authority**.

## Glossary
- **Brick**: Atomic semantic unit extracted from raw data.
- **Intent**: Promoted knowledge node in the graph.
- **Wall**: A spatial projection/view of a subset of the graph.
- **Synthesis**: The process of inferring latent relationships between nodes.
- **Pulsing**: Real-time event notifications via WebSockets.
