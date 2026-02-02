# Canonical Overview: Nexus Personal Knowledge System

## 1. System Identity
**Nexus** is a local-first Personal Knowledge Retrieval System designed to ingest, index, and surface insights from large volumes of conversational data (specifically ChatGPT exports). It operates on the principle of "Bricks" (atomic units of information) and "Walls" (context-rich aggregations), utilizing a graph-based approach to connect related concepts.

## 2. Core Architecture
The system follows a classic 3-tier architecture, split into distinct responsibilities:

### **Tier 1: Nexus Core (ETL & Logic)**
The heart of the system, responsible for data ingestion, transformation, and storage.
- **Ingest**: Parses complex JSON conversation trees into linear paths.
- **Extract**: Breaks paths into "Bricks" (atomic data units).
- **Construct**: Aggregates contexts into "Walls" (token-bounded markdown files).
- **Index**: Embeds bricks into a local Vector Store (FAISS).
- **Graph**: Maintains a concept map (Nodes & Edges) for structured navigation.

### **Tier 2: Cortex (API Layer)**
A lightweight Flask-based backend acting as the gateway between the UI and Nexus Core.
- **Role**: Read-only adapter (mostly) that exposes Nexus data to the frontend.
- **Responsibility**: Handles search requests, metadata retrieval, and graph data serving.
- **Constraint**: Does not directly import heavy Nexus ETL modules at runtime; relies on adapters.

### **Tier 3: Jarvis (User Interface)**
A modern React (Vite) application for interaction and exploration.
- **Ask/Preview**: Real-time semantic search over the brick index.
- **Brick Viewer**: Detailed inspection of source context.
- **Enhanced AI View**: Interactive graph visualization of concepts and relationships.
- **Curator Mode**: Tools for promoting/demoting connections (anchors) between bricks and concepts.

## 3. Data Flow
1.  **Sync Phase**: `conversations.json` -> `TreeSplitter` -> `BrickExtractor` -> `WallBuilder` -> `VectorIndex`.
2.  **Recall Phase**: User Query -> `Cortex` -> `Nexus Recall` -> `Vector Search` -> `Reranker` -> `Ranked Bricks`.
3.  **Explore Phase**: User Click -> `Graph Index` -> `Nodes/Edges` -> `Related Anchors`.

## 4. Key Terminology
-   **Tree**: A linear path extracted from a branching conversation.
-   **Brick**: A specific message or block of text, the atomic unit of search.
-   **Wall**: A large, token-managed markdown file containing multiple conversations, used for context window management.
-   **Anchor**: A link between a Concept (Graph Node) and a Brick. Can be Hard (human-verified) or Soft (AI-suggested).
