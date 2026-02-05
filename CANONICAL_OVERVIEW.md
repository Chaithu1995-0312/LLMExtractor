# Canonical Overview

## System Identity
**Nexus** is a Cognitive Knowledge Graph system designed to ingest unstructured conversation logs, extract atomic units of information ("Bricks"), and synthesize them into a structured, queryable knowledge graph ("Intents"). It serves as a bridge between raw LLM interactions and persistent, evolving knowledge.

## Core Architecture
The system follows a strict layered architecture:

1.  **Ingestion Layer (`nexus.bricks`, `nexus.sync`)**
    -   Parses raw `conversations.json`.
    -   Fragments messages into atomic "Bricks".
    -   Embeds Bricks using local vector models.

2.  **Storage Layer (`nexus.vector`, `nexus.graph`)**
    -   **Vector Store**: FAISS-based `LocalVectorIndex` for semantic retrieval.
    -   **Graph Store**: SQLite-backed `GraphManager` storing Nodes (Sources, Scopes, Intents) and Edges.

3.  **Cognition Layer (`nexus.cognition`)**
    -   **DSPy Modules**: Extracts Facts, Formulas, and Diagrams from text.
    -   **Assembler**: Synthesizes loose information into structured Topics and Intents.

4.  **Service Layer (`services.cortex`)**
    -   **Cortex API**: Flask-based REST API exposing the graph and cognition capabilities.
    -   **Orchestration**: Manages long-running tasks like history ingestion.

5.  **Interface Layer (`ui.jarvis`)**
    -   **Jarvis**: React-based frontend for visualizing the graph, managing intent lifecycles, and inspecting bricks.

## Data Flow
1.  **Raw Data** $\rightarrow$ `IngestHistory` $\rightarrow$ `Bricks`
2.  `Bricks` $\rightarrow$ `Embedder` $\rightarrow$ `Vector Index`
3.  `User Query` $\rightarrow$ `Recall` $\rightarrow$ `Cognitive Extraction` $\rightarrow$ `Topic Assembly`
4.  `Topic` $\rightarrow$ `Graph Projection` $\rightarrow$ `Intents` (Loose)
5.  `Human Review` $\rightarrow$ `Promote/Freeze` $\rightarrow$ `Canonical Knowledge`

## Key Concepts

### Bricks
The fundamental atomic unit of raw information. A Brick corresponds to a coherent block of text within a conversation message.

### Intents
Structured assertions derived from Bricks. An Intent represents a piece of knowledge with a defined lifecycle:
-   `LOOSE`: Newly proposed, unverified.
-   `FORMING`: Being actively structured.
-   `FROZEN`: Accepted as canonical truth.
-   `SUPERSEDED`: Replaced by newer knowledge.
-   `KILLED`: Rejected.

### Scopes
Namespaces or contexts that Intents apply to (e.g., "Python Coding", "Project Architecture"). Frozen Intents must be bound to a Scope.
