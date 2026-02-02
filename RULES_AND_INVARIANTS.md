# Rules and Invariants

## 1. Data Integrity
-   **Path Stability**: `path_<hash>.json` filenames MUST be derived deterministically from the path content.
-   **Immutability**: Once a Brick is extracted and ID'd, its ID MUST NOT change unless content changes.
-   **Token Limits**: Walls MUST NOT exceed the configured token target (default 32k) to ensure fit within context windows.
-   **Atomic Bricks**: A brick generally corresponds to a single message or a logical block within a message. It MUST be retrievable independently.

## 2. Architectural Boundaries
-   **Cortex Constraint**: The Cortex API server (`server.py`) SHOULD NOT import heavy ETL modules (`runner.py`, `walls.builder`) at runtime. It MUST use read-only adapters (`recall.py`) to prevent accidental triggering of sync jobs or heavy memory usage.
-   **Separation of Concerns**: Nexus (Core) handles data logic; Cortex handles HTTP/Transport; Jarvis handles Presentation.

## 3. Graph Invariants
-   **Hard Anchors**: A "Hard Anchor" represents a verified, human-curated link between a Concept and a Brick. It implies ground truth.
-   **Soft Anchors**: A "Soft Anchor" is an inferred or suggested link. It MUST be visually distinct from Hard Anchors in the UI.
-   **Node Uniqueness**: Graph nodes (Concepts) MUST have unique IDs.

## 4. UI/UX Rules
-   **Preview vs Full**: The search results list shows a snippet/preview. Full context is ONLY loaded on demand via `/jarvis/brick-full`.
-   **Read-Only Default**: The primary interface is read-only exploration. "Curator Mode" (edit intent) is a distinct state (currently logged to console).

## 5. Development Invariants
-   **Local First**: All data is stored on the local filesystem (`output/nexus`). No external cloud database is required for core functionality.
-   **Dependencies**: `faiss` is the only heavy dependency for vector operations.
