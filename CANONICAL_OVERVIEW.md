# NEXUS CANONICAL OVERVIEW

## 1. Executive Summary
NEXUS is a multi-layered cognitive architecture designed for high-fidelity information extraction, structured knowledge representation, and autonomous reasoning. It bridges the gap between raw unstructured data (conversations, documents) and an actionable Knowledge Graph by employing a "Brick" methodology. This system ensures that every piece of information is atomized, verified, and contextualized within a governed graph structure.

## 2. System Architecture & Layers

### I. Ingestion Layer (`src/nexus/sync`, `src/nexus/extract`)
- **Responsibility:** Raw data acquisition and structural decomposition.
- **Key Mechanism:** `NexusCompiler` and `TreeSplitter`.
- **Outcome:** Conversion of unstructured streams into hierarchical JSON trees and raw "Bricks".

### II. Vector & Recall Layer (`src/nexus/vector`, `src/nexus/ask`, `src/nexus/rerank`)
- **Responsibility:** Semantic indexing and high-precision retrieval.
- **Key Mechanism:** `LocalVectorIndex` for FAISS-based search and `RerankOrchestrator` for multi-stage refinement.
- **Outcome:** Ranked context candidates filtered by semantic relevance and metadata scope.

### III. Graph Layer (`src/nexus/graph`)
- **Responsibility:** Relationship persistence, lifecycle management, and structural integrity.
- **Key Mechanism:** `GraphManager` (SQLite-backed) and `Projection`.
- **Outcome:** A persistent directed graph of Intents, Sources, and Scopes with enforced non-cyclicality and audit trails.

### IV. Cognition Layer (`src/nexus/cognition`)
- **Responsibility:** High-order synthesis, relationship inference, and fact extraction.
- **Key Mechanism:** `DSPy` modules (`CognitiveExtractor`, `RelationshipSynthesizer`) and `Assembler`.
- **Outcome:** Inferred "Intents" and "Edges" that populate the Graph Layer from raw Ingestion data.

### V. Service & UI Layer (`services/cortex`, `ui/jarvis`)
- **Responsibility:** API orchestration, external gatewaying, and human-in-the-loop auditing.
- **Key Mechanism:** `CortexAPI` and the `Jarvis` React dashboard.
- **Outcome:** Operational control surface for system monitoring and manual graph refinement.

## 3. Core Entities
- **Brick:** The atomic unit of data. Contains raw text, source metadata, and a unique fingerprint.
- **Intent:** A distilled cognitive unit representing a specific fact, requirement, or observation.
- **Edge:** A typed relationship (e.g., `SUPPORTS`, `CONFLICTS_WITH`, `FOLLOWS`) between nodes.
- **Scope:** A boundary defining the visibility and applicability of information (e.g., `global`, `session`).

## 4. Operational Flow
1.  **Sync:** `NexusIngestor` pulls data -> `Compiler` extracts pointers -> `BrickStore` saves atoms.
2.  **Cognition:** `Assembler` gathers bricks -> `Synthesizer` generates Intents/Edges -> `GraphManager` persists nodes.
3.  **Recall:** User query -> `VectorEmbedder` -> `LocalIndex` search -> `Reranker` refinement -> `CortexAPI` response.
4.  **Audit:** Every modification is logged in `phase3_audit_trace.jsonl` and visible in `AuditPanel`.
