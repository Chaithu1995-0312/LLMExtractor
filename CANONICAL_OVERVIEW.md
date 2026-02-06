# CANONICAL_OVERVIEW

## 1. System Purpose
**NEXUS** is a multi-layered cognitive architecture designed to transform unstructured conversational history and raw data into a high-integrity, structured knowledge graph. It facilitates "Intent-driven Knowledge Management," where information is not merely stored but evolved through a rigorous lifecycle (Loose → Forming → Frozen). The system provides a unified cognitive interface for both human auditing and LLM-driven knowledge retrieval.

## 2. Core Architectural Layers

### I. Ingestion Layer
- **Responsibility**: Raw data acquisition and structural normalization.
- **Key Modules**: `src/nexus/sync`, `src/nexus/extract`.
- **Workflow**: Ingests `conversations.json`, splits them into a hierarchy (`tree_splitter`), and extracts atomic "Bricks" of information.

### II. Graph Layer
- **Responsibility**: Persistence and relationship management.
- **Key Modules**: `src/nexus/graph`.
- **Mechanism**: A central `GraphManager` manages Nodes (Intents, Sources, Scopes) and Edges. It enforces the knowledge lifecycle and provides graph projections for visualization.

### III. Vector & Search Layer
- **Responsibility**: Semantic retrieval and ranking.
- **Key Modules**: `src/nexus/vector`, `src/nexus/rerank`, `src/nexus/ask`.
- **Mechanism**: Local vector indices (FAISS) store Brick embeddings. Retrieval is multi-stage: semantic recall → heuristic/cross-encoder reranking → graph-aware context injection.

### IV. Cognition Layer
- **Responsibility**: Synthesis, fact extraction, and diagram generation.
- **Key Modules**: `src/nexus/cognition`.
- **Mechanism**: Uses DSPy-based modules (`CognitiveExtractor`) to distill raw "Bricks" into validated "Facts" and architectural "Diagrams."

### V. Service Layer (Cortex)
- **Responsibility**: API orchestration and governance.
- **Key Modules**: `services/cortex`.
- **Mechanism**: Provides RESTful endpoints for the UI, manages the "Audit Trace" (JSONL) for all LLM calls, and enforces security/policy boundaries.

### VI. UI Layer (Jarvis)
- **Responsibility**: High-fidelity visualization and node management.
- **Key Modules**: `ui/jarvis`.
- **Mechanism**: A React-based "Wall View" that visualizes the state of knowledge across the lifecycle lanes (Frozen/Forming/Loose/Killed).

## 3. Knowledge Evolution Flow
1. **Discovery**: `NexusIngestor` creates `LOOSE` nodes from new bricks.
2. **Consolidation**: `CortexAPI` assembles loose bricks into `FORMING` intents using cognitive modules.
3. **Validation**: Human or automated agents promote forming nodes to `FROZEN` once confidence thresholds are met.
4. **Pruning**: Redundant or invalidated nodes are moved to the `KILLED` lane to maintain graph signal quality.
