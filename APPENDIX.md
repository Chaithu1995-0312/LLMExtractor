# APPENDIX

## Consolidated Method Intelligence Table

| Class | Method | Responsibility | Risk | Used By |
| :--- | :--- | :--- | :--- | :--- |
| **NexusCompiler** | `compile_run` | Compiles a full ingestion run. | MED | `runner.py` (CLI) |
| **NexusCompiler** | `_materialize_brick` | Persists a single Brick. | MED | `compile_run` |
| **SyncDatabase** | `create_topic` | Creates topic record. | MED | `NexusCompiler` |
| **SyncDatabase** | `register_run` | Logs ingestion run. | MED | `NexusCompiler` |
| **SyncDatabase** | `save_brick` | Saves brick data. | MED | `NexusCompiler` |
| **GraphManager** | `register_node` | Upserts graph node. | MED | `NexusCompiler`, `CortexAPI` |
| **GraphManager** | `register_edge` | Creates edge. | MED | `RelationshipSynthesizer`, `CortexAPI` |
| **GraphManager** | `kill_node` | Deprecates a node. | HIGH | `CortexAPI` (Governance) |
| **GraphManager** | `_check_for_cycle` | Cycle detection. | LOW | `register_edge` |
| **CortexAPI** | `route` | Intent classification. | LOW | `JarvisGateway` |
| **CortexAPI** | `generate` | Agent response generation. | MED | `JarvisGateway` |
| **RelationshipSynthesizer** | `run_relationship_synthesis` | Batch edge discovery. | HIGH | `CortexAPI` (Async Task) |
| **CoverageSentinel** | `analyze_topic` | Scores topic completeness. | MED | `CortexAPI` (Async Task) |
| **PromptGenerator** | `generate_prompts` | Creates healing prompts. | LOW | `CortexAPI` |

## Terminology

- **Brick:** Atomic unit of unstructured data (e.g., a paragraph, a message).
- **Intent:** A structured node in the graph representing a goal or topic.
- **Edge:** A directed relationship between two nodes (e.g., `CAUSES`, `RELATED_TO`).
- **Run:** A single ingestion session.
- **Topic:** A high-level container for related Bricks.
- **Wall:** A visual projection of Intends/Topics in the UI.
- **Pulse:** A heartbeat or event signal in the system.
- **Sentinel:** An automated agent monitoring graph quality.
