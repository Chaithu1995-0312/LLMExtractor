# Module Deep Dives

## 1. Nexus Sync (ETL)
**Module**: `nexus.sync`
**Entry Point**: `runner.py`

### Process Flow
1.  **Load**: Reads `conversations.json` (ChatGPT export).
2.  **Split Trees**: `tree_splitter.py` traverses the conversation tree. For every leaf node, it traces back to the root to create a linear "path". This handles branched conversations by duplicating shared history into unique linear paths.
    -   *Output*: JSON files in `output/nexus/trees/<conv_id>/path_<hash>.json`.
3.  **Extract Bricks**: `extractor.py` processes these linear paths.
    -   *Logic*: Chunks text (likely by message or paragraph).
    -   *Output*: Brick JSONs in `output/nexus/bricks/`.
4.  **Build Walls**: `walls.builder.py` aggregates trees into "Walls".
    -   *Logic*: Concatenates conversation text until a token limit (e.g., 32k) is reached.
    -   *Output*: Markdown files in `output/nexus/walls/`.
5.  **Embed**: `LocalVectorIndex` iterates over new bricks and adds them to FAISS.
    -   *Current State*: Uses random embeddings.

## 2. Nexus Ask (Recall)
**Module**: `nexus.ask`
**Entry Point**: `recall.py`

### Logic
1.  **Query Processing**: Converts user query to vector (mocked via seeded random).
2.  **Vector Search**: Queries `LocalVectorIndex` (FAISS) for K nearest neighbors.
3.  **Hydration**: Retrieves text content for candidate bricks using `BrickStore`.
4.  **Reranking**: Passes candidates to `RerankOrchestrator` (placeholder) to refine order.
5.  **Output**: Returns list of bricks with confidence scores.

## 3. Cortex (API)
**Module**: `backend.cortex`
**Entry Point**: `server.py`

### Endpoints
-   `GET /jarvis/ask-preview`: Triggers `recall.recall_bricks_readonly`.
    -   *Params*: `query`.
    -   *Returns*: Top K bricks with confidence.
-   `GET /jarvis/brick-meta`: Retrieves metadata for a brick.
    -   *Params*: `brick_id`.
    -   *Returns*: Source file path, span, preview text.
-   `GET /jarvis/brick-full`: Retrieves full text of a brick/message.
-   `GET /jarvis/graph-index`: Returns content of `nodes.json` and `edges.json`.

### Design Patterns
-   **Read-Only Adapter**: Imports `recall_bricks_readonly` to avoid side effects or state mutation in the Nexus Core during API calls.
-   **Direct File Access**: Reads JSON files directly for metadata/content, rather than using a DB abstraction layer.

## 4. Jarvis (UI)
**Module**: `ui.jarvis`
**Entry Point**: `App.tsx`

### Key Components
-   **Preview Panel**: Input box + Results list. Shows confidence bars.
-   **Detail Panel**: Shows selected brick metadata. "Enhanced AI View" button.
-   **Graph Modal**: Custom graph visualizer.
    -   **Concept Cards**: Rendered based on `nodes.json`.
    -   **Anchors Drawer**: Shows Hard/Soft anchors.
    -   **Action Logging**: Consoles `PROMOTE` or `REJECT` actions (no backend persistence yet).
    -   **Highlighting**: Highlights concepts based on recalled bricks (Strong/Weak match).
