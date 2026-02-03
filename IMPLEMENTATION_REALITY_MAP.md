# IMPLEMENTATION_REALITY_MAP.md

## 1. Mapped Concepts to Code Paths

| Conceptual Component     | Real-world Implementation Path(s)             | Description                                                                                                                                                                                                                                                                                                                             |
| :----------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Core Nexus Library**   | `src/nexus/`                                  | Top-level package for the Nexus productivity backbone.                                                                                                                                                                                                    |
| Configuration            | `src/nexus/config.py`                         | Defines constants and filesystem paths for data, index, bricks, and output.                                                                                                                                                                                          |
| Vector Embeddings        | `src/nexus/vector/embedder.py`                | Singleton for loading and applying `SentenceTransformer` (`all-MiniLM-L6-v2`) to convert text into 384-dimensional dense vectors.                                                                                                                                      |
| Local Vector Index (FAISS)| `src/nexus/vector/local_index.py`             | Manages the in-memory FAISS `IndexFlatL2` for vector similarity search, along with a mapping of vector indices to `brick_id`s. Handles persistence of the index and metadata to `data/index/index.faiss` and `data/brick_ids.json`.                                |
| Brick Storage            | `src/nexus/bricks/brick_store.py`             | Provides an interface to retrieve brick metadata and raw content from JSON files located in `output/nexus/bricks/`.                                                                                                                                                  |
| Semantic Recall          | `src/nexus/ask/recall.py`                     | Orchestrates the semantic search process: embeds query, searches FAISS index, retrieves brick content, and applies reranking. Exposes `recall_bricks` and `recall_bricks_readonly`.                                                                            |
| Reranking Orchestration  | `src/nexus/rerank/orchestrator.py`            | Implements the hierarchical reranking strategy (LLM -> CrossEncoder -> Heuristic) with graceful fallbacks.                                                                                                                                                           |
| LLM Reranker             | `src/nexus/rerank/llm_reranker.py`            | Reranks candidates using a local quantized LLM (e.g., Llama-3 via `llama-cpp-python`). Prioritized as the most sophisticated reranker.                                                                                                                               |
| Cross-Encoder Reranker   | `src/nexus/rerank/cross_encoder.py`           | Fallback reranker using a `sentence-transformers` CrossEncoder (`cross-encoder/ms-marco-TinyBERT-L-2-v2`) for contextual scoring.                                                                                                                                    |
| Heuristic Reranker       | `src/nexus/rerank/heuristic.py`               | Safest fallback reranker, using simple token overlap and exact phrase matching. Always available.                                                                                                                                                                    |
| **Cortex Service**       | `services/cortex/`                            | Package for the Cortex microservice.                                                                                                                                                                                                                        |
| Cortex API Interface     | `services/cortex/api.py`                      | Defines the Flask-based API endpoints for `/route` (intent routing), `/generate` (LLM-based generation with memory and audit), and `/ask_preview` (read-only recall). Integrates `BrickStore` and `nexus.ask.recall`.                                          |
| Cortex Server Application| `services/cortex/server.py`                   | (🟡 UNCONFIRMED - Assumed to be the main Flask application script that initializes `CortexAPI` and runs the web server.)                                                                                                                                         |

## 2. Abstractions vs. Concrete Implementations

- **Vector Embedder:** The abstract concept of an embedder is concretely implemented by `VectorEmbedder` in `src/nexus/vector/embedder.py` using `SentenceTransformer`.
- **Vector Index:** The abstract concept of a vector index is concretely implemented by `LocalVectorIndex` in `src/nexus/vector/local_index.py` using FAISS.
- **Brick Storage:** The abstract concept of a brick store is implemented by `BrickStore` in `src/nexus/bricks/brick_store.py`, which reads from local JSON files.
- **Reranker:** The abstract concept of a reranker has multiple concrete implementations: `LlmReranker`, `CrossEncoderReranker`, and `HeuristicReranker`, orchestrated by `RerankOrchestrator`.
- **LLM Backend:** The `CortexAPI.generate` method abstracts the LLM call, with concrete implementations supporting OpenAI API, local Ollama, and a mock fallback.

## 3. Discrepancies & Ambiguities

- **Brick `extractor.py`:** The contents of `src/nexus/bricks/extractor.py` were not reviewed. Its precise role in creating bricks from raw input is inferred, not confirmed. The integration point into the overall content ingestion workflow is also unclear.
- **Sync Module (`nexus.sync`):** The `__main__.py` and `runner.py` files within `src/nexus/sync` were not reviewed. The exact mechanism and triggers for index building and content synchronization are inferred, but the implementation details are missing.
- **Walls Module (`nexus.walls`):** The `builder.py` file within `src/nexus/walls` was not reviewed. Its purpose is inferred (aggregating bricks into larger "walls" of content for various purposes, e.g., generating consolidated documentation.)
- **Other Modules:** `src/nexus/extract`, `src/nexus/graph` were not reviewed but exist in the project structure, implying further functionalities like content extraction and knowledge graph management.

## 4. Dependencies and Environment Variables

- **`faiss-cpu`, `numpy`, `flask`, `sentence-transformers`, `tiktoken`:** Declared in `pyproject.toml` as core dependencies for the `nexus` package.
- **`openai`:** Required for `CortexAPI.generate` when `OPENAI_API_KEY` is present. Implicitly imported within `api.py`.
- **`requests`:** Used in `CortexAPI.generate` for communicating with a local Ollama instance.
- **`llama-cpp-python`:** Required for `LlmReranker`. The `LlmReranker` explicitly raises `ImportError` if not found.
- **`torch`:** Implicit dependency for `sentence-transformers` and `CrossEncoder`. Not directly imported in reviewed code but essential for these libraries.
- **`OPENAI_API_KEY` (Environment Variable):** Used by `CortexAPI.generate` to authenticate with the OpenAI API. If not set, it falls back to Ollama or a mock.
- **Local LLM Model Files:** The `LlmReranker` expects a quantized LLM model (e.g., `llama-3-8b-quantized.gguf`) at a specific path (`models/llama-3-8b-quantized.gguf`). Its absence leads to `FileNotFoundError`.

## 5. Deployment and Execution

- **Nexus CLI:** Executable via `nexus` command, as defined by `[project.scripts]` in `pyproject.toml` (`nexus = "nexus.cli.main:main"`).
- **Cortex Service:** Assumed to be run as a Flask application via `services/cortex/server.py`. (🟡 UNCONFIRMED - `server.py` was not reviewed, but its existence strongly suggests this.)
- **Ollama:** The Cortex service can integrate with a locally running Ollama instance (at `http://localhost:11434/api/generate`) for LLM inference.

## 6. Audit Trail

- All calls to `CortexAPI.generate` are logged to `phase3_audit_trace.jsonl` in a line-delimited JSON format. This log includes `user_id`, `agent_id`, `brick_ids_used`, `model`, `token_cost`, and `timestamp`. This is a critical invariant for security and traceability.

## 7. Inferred System Boundaries

- **Nexus Core:** Acts as a library providing low-level knowledge management capabilities (vector search, brick storage, reranking). It is designed to be embeddable.
- **Cortex Service:** Acts as an API layer on top of Nexus, adding high-level functionalities like intent routing, secure generation, and audit logging. It consumes Nexus core functionalities.
- **UI/Clients:** Not explicitly reviewed, but implied consumers of the Cortex API (e.g., a web UI like Jarvis or other automated agents) would interact with the system at this boundary.