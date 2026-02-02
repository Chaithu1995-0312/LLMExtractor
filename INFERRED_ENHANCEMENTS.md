# Inferred Enhancements

## 1. Semantic Graph Construction
**Logic**: Instead of relying on manual/static `nodes.json`, use an LLM during the `Sync` phase to extract concepts from Walls.
**Implementation**:
-   New module `nexus.graph.builder`.
-   Input: `Wall` markdown content.
-   Prompt: "Extract key technical concepts and their relationships from this conversation."
-   Output: Update `nodes.json` and `edges.json`.

## 2. LLM-Based Reranking
**Logic**: Replace the placeholder `RerankOrchestrator` with a local or API-based LLM check.
**Implementation**:
-   Take Top-K FAISS results.
-   Prompt: "Given query Q and these 10 snippets, rate relevance 0-1."
-   Update `confidence` scores in `recall.py`.

## 3. Streaming Responses
**Logic**: Cortex API currently waits for full recall completion.
**Implementation**:
-   Use Python Generators / Server-Sent Events (SSE).
-   Stream results to Jarvis as they are found/reranked.

## 4. Multi-Modal Bricks
**Logic**: `extractor.py` currently focuses on text.
**Implementation**:
-   Detect code blocks, images (if present in export), and links.
-   Create specialized Brick types (e.g., `CodeBrick`, `ImageBrick`).
