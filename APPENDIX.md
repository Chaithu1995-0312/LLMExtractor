# Appendix: Class Responsibility Matrix

| Class | Method | Responsibility | Layer | Used By |
| :--- | :--- | :--- | :--- | :--- |
| **GraphManager** | `register_node` | Upsert node (Idempotent) | Graph | `sync_bricks_to_nodes`, `NexusCompiler` |
| | `register_edge` | Create edge (Idempotent) | Graph | `RelationshipSynthesizer`, `supersede_node` |
| | `promote_node_to_frozen` | Enforce FROZEN state | Governance | `server.py` (API), Manual Scripts |
| | `kill_node` | Soft-delete node | Governance | `server.py` (API) |
| | `supersede_node` | Replace node with history | Governance | `server.py` (API) |
| **NexusCompiler** | `compile_run` | End-to-end ingestion | Ingest | `nexus-cli` (CLI), `server.py` (API) |
| | `_materialize_brick` | Zero-Trust Verification | Ingest | `compile_run` |
| **CortexAPI** | `route` | Agent selection | Service | `server.py` (API) |
| | `generate` | L2 Pipeline Execution | Service | `server.py` (API) |
| | `ask_preview` | Read-only Preview | Service | `server.py` (API), `Jarvis UI` |
| **JarvisGateway** | `pulse` | L1 (Local) Inference | Service | `GraphManager` (Events), `NexusIngestor` |
| | `explain` | L2 (Cloud) Inference | Service | `CortexAPI.generate` |
| | `synthesize` | L3 (Cloud) Inference | Service | `CortexAPI.synthesize` |
| **VectorEmbedder** | `embed_query` | Text-to-Vector | Vector | `LocalVectorIndex`, `CortexAPI` |
| **LocalVectorIndex** | `search` | K-NN Search | Vector | `recall.py`, `CortexAPI` |
| **SyncDatabase** | `save_brick` | Persist Brick | Ingest | `NexusCompiler` |

---

## Terminology
*   **Brick:** Atomic unit of extracted knowledge (verbatim quote).
*   **Intent:** Synthesized fact or goal derived from one or more Bricks.
*   **Scope:** The domain or context an Intent applies to (e.g., "Project A", "Global").
*   **Pointer:** A JSONPath + Quote pair identified by the LLM during scanning.
*   **Frozen:** A state where a node is immutable and considered "Truth".
*   **Superseded:** A state where a node is historically preserved but logically obsolete.
