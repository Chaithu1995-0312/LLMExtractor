# APPENDIX

## 1. Consolidated Class-Method-Responsibility Reference

| Class | Method | Responsibility | Used By | Layer | Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GraphManager** | `register_node` | Persist nodes in SQL | `NexusIngestor` | Graph | Stateful |
| | `promote_node_to_frozen` | Advance lifecycle state | `CortexAPI` | Graph | Transactional |
| | `kill_node` | Logical deletion | UI / `CortexAPI` | Graph | Transactional |
| | `supersede_node` | Knowledge versioning | Admin / CLI | Graph | Transactional |
| **CortexAPI** | `route` | Query dispatching | `server.py` | Service | Read-only |
| | `generate` | LLM synthesis | `server.py` | Service | Stateful |
| | `_audit_trace` | Governance logging | Internal | Service | Write-only |
| **CognitiveExtractor**| `forward` | Fact extraction | `CortexAPI` | Cognition | Pure |
| | `extract_facts` (🧪) | Schema detection | Internal | Cognition | Pure |
| **NexusIngestor** | `brickify` | Text atomization | CLI / Sync | Ingestion | Pure |
| | `ingest_history` | Batch processing | CLI / Sync | Ingestion | Write-authoritative |
| **LocalVectorIndex** | `add_bricks` | Vector persistence | `NexusIngestor` | Vector | Stateful |
| | `search` | Semantic retrieval | `recall_bricks` | Vector | Read-only |
| **VectorEmbedder** | `embed_query` | Query vectorization | `CortexAPI` | Vector | Pure |
| **NexusNode** (UI) | `onSelect` | Node focus selection | `WallView` | UI | UI Event |
| **WallView** (UI) | `render` | Lane layout generation | `App.tsx` | UI | View |

## 2. Key Terminology Reference

- **Brick**: The atomic unit of text/knowledge ingested into the system.
- **Intent**: A high-level node representing a specific goal or piece of consolidated knowledge.
- **Lane**: A vertical grouping in the UI representing a lifecycle stage (Frozen, Forming, Loose).
- **Audit Trace**: A JSONL file recording every cognitive operation for transparency.
- **Scope**: A boundary (Global or Context-specific) within which an Intent is valid.

## 3. Interaction Boundary Notes

- **The Write Barrier**: No component except `GraphManager` and `LocalVectorIndex` may write to disk. `CortexAPI` must use these classes for all state changes.
- **The Security Barrier**: `CortexAPI` is the only component allowed to interact with the External LLM (e.g., GPT-4). No direct calls from UI or Ingestion layers are permitted.
- **The Lifecycle Gate**: Promotion to `FROZEN` is a "one-way" transition in terms of UI visibility; it moves the node into the high-confidence swimlane.
