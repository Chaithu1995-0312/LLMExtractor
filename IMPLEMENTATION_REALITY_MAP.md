# Implementation Reality Map

## Overview
This document maps the theoretical architecture to the actual codebase state, highlighting discrepancies, inactive code paths, and confirmed implementations.

## Component Status Matrix

| Module | Intended Role | Actual Implementation | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Parse & Split | `src/nexus/sync/ingest_history.py` | ✅ | Uses `unstructured` for cleaning. |
| **Vector Store** | Semantic Search | `src/nexus/vector/local_index.py` (FAISS) | ✅ | **Divergence**: `PineconeVectorIndex` exists but is unused. |
| **Graph Store** | Relationship Mgmt | `src/nexus/graph/manager.py` (SQLite) | ✅ | **Divergence**: `Neo4jGraphManager` exists but is unused. |
| **Recall** | Retrieval | `src/nexus/ask/recall.py` | ✅ | Strictly uses `LocalVectorIndex`. |
| **Cognition** | Logic/Reasoning | `src/nexus/cognition/assembler.py` | ✅ | Uses DSPy (`CognitiveExtractor`) for extraction. |
| **Orchestration** | API/Routing | `services/cortex/api.py` | ✅ | Simple routing table + LLM injection. |
| **Frontend** | UI | `ui/jarvis` (React) | 🟡 | Code exists but integration with Cortex is partial. |

## Code Path Analysis

### Active Paths
1.  **Ingestion**: `python -m nexus.sync` -> `runner.py` -> `ingest_history.py` -> `extractor.py` -> `LocalVectorIndex`.
2.  **Recall**: `CortexAPI.ask_preview` -> `recall_bricks_readonly` -> `LocalVectorIndex.search`.
3.  **Assembly**: `CortexAPI.assemble` -> `assemble_topic` -> `recall_bricks_readonly` -> `CognitiveExtractor` -> `GraphManager` (SQLite).

### Inactive / Dead Paths
-   `src/nexus/vector/pinecone_index.py`: Full implementation of Pinecone client, but not imported/used by `recall.py`.
-   `src/nexus/graph/neo4j_manager.py`: Full Neo4j driver implementation, but `assembler.py` imports `GraphManager` (SQLite).
-   `services/cortex/server.py`: Referenced in file lists but `runcortexapi.py` seems to be the entry point or `api.py` is the library. *Correction: `server.py` likely runs FastAPI.*

## Key Discrepancies

### Graph Storage
-   **Plan**: Likely originally intended for Neo4j (scalability).
-   **Reality**: Uses `sqlite3` in `src/nexus/graph/manager.py`. The schema is relational (Nodes table, Edges table) simulating a graph.
-   **Implication**: Lower operational overhead, but potential performance bottleneck at massive scale. Complex path queries (Cypher) are manually implemented or limited.

### Vector Storage
-   **Plan**: Cloud-native (Pinecone).
-   **Reality**: Local-native (FAISS).
-   **Implication**: Zero cost, privacy-preserving, but requires local disk management and lacks serverless scaling.

### Cognition
-   **Plan**: Complex multi-step reasoning?
-   **Reality**: DSPy `CognitiveExtractor` does a single pass to extract Facts, Mermaid, and Latex. It is effective but linear.

## Confirmed Invariants
-   **Mode-1 Enforcement**: `CortexAPI` checks `_reload_source_text` from `BrickStore`. If bricks cannot be reloaded, generation fails. This invariant is **LOCKED** in code.
-   **Immutable Artifacts**: `assembler.py` writes JSON files with content hashes to `artifacts/`.

## Uncertainty Markers
-   🧪 **UI Integration**: The `ui/jarvis` folder contains a React app, but it is unclear if it fully consumes the `CortexAPI` or just mocks data.
-   🧪 **Migration Scripts**: `scripts/migrate_to_intents.py` suggests a transition is in progress or recently completed.
