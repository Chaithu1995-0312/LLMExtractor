# CANONICAL_OVERVIEW.md

## 1. System Name

**Nexus**

## 2. System Purpose

The Nexus system serves as a productivity backbone designed to manage, store, index, and retrieve "bricks" of information, which are granular units of knowledge extracted from various sources. It provides capabilities for semantic search (recall), intelligent content generation, and intent-based routing through its exposed APIs. The primary goal is to enhance knowledge retrieval and content synthesis for both automated agents and human users.

## 3. Core Components & Their Roles

### 3.1. Nexus (Core Library)

- **CLI (`nexus.cli.main`):** The command-line interface for interacting with the Nexus system, likely for setup, synchronization, and testing.
- **Config (`nexus.config`):** Defines global constants and paths for data, index files, brick storage, and output directories.
- **Vector (`nexus.vector`):**
    - **`embedder.py`:** Manages the loading and use of a `SentenceTransformer` model (`all-MiniLM-L6-v2`) to convert text into fixed-size numerical vector embeddings (384 dimensions). Implements a singleton pattern.
    - **`local_index.py`:** Encapsulates the FAISS (Facebook AI Similarity Search) index for efficient similarity search over vector embeddings. Stores brick IDs alongside the index. Handles loading and saving the index and associated metadata.
- **Bricks (`nexus.bricks`):)
    - **`brick_store.py`:** Manages the storage and retrieval of "bricks" (small, discrete units of information). It handles loading brick metadata from JSON files and retrieving the raw text content of individual bricks.
    - **`extractor.py`:** (🟡 UNCONFIRMED - Based on file name, assumed to be responsible for extracting raw text from various sources into bricks. Details of implementation not reviewed.)
- **Ask (`nexus.ask`):**
    - **`recall.py`:** Implements the core semantic search (recall) functionality. It uses the `VectorEmbedder` to embed queries, `LocalVectorIndex` for initial vector search, and then passes candidates through the `RerankOrchestrator` for refinement. Provides a read-only variant for external services like Cortex.
- **Rerank (`nexus.rerank`):**
    - **`orchestrator.py`:** Coordinates a multi-stage reranking pipeline (LLM -> CrossEncoder -> Heuristic) to refine search results from the vector index. Implements a fallback mechanism if higher-fidelity rerankers fail.
    - **`llm_reranker.py`:** A primary reranker that uses a local quantized LLM (e.g., Llama-3) to score the relevance of candidates. Requires `llama-cpp-python`.
    - **`cross_encoder.py`:** A secondary reranker that uses a `sentence-transformers` CrossEncoder model (`cross-encoder/ms-marco-TinyBERT-L-2-v2`) to score candidate relevance. Requires `sentence-transformers` and `torch`.
    - **`heuristic.py`:** A tertiary (fallback) reranker that uses simple heuristics like token overlap and phrase matching to score candidates. Always available and has no external dependencies.
- **Sync (`nexus.sync`):**
    - **`__main__.py`:** (🟡 UNCONFIRMED - Likely the entry point for synchronization operations, e.g., building the index from new content.)
    - **`runner.py`:** (🟡 UNCONFIRMED - Likely orchestrates the synchronization process, involving extraction, embedding, and indexing.)
- **Walls (`nexus.walls`):**
    - **`builder.py`:** (🟡 UNCONFIRMED - Based on name, possibly aggregates bricks into larger "walls" of content for various purposes.)

### 3.2. Cortex (Service Layer)

- **`services.cortex.api.py`:** Defines the API for the Cortex service, providing endpoints for:
    - **`/route`:** Intent-based routing of user queries to specific agents/models based on deterministic rules.
    - **`/generate`:** Secure content generation, injecting memory (reloaded brick content) into a pluggable LLM backend (OpenAI GPT-4o, local Ollama, or a mock fallback). Includes mandatory audit logging.
    - **`/ask_preview`:** A read-only endpoint for previewing recalled bricks for a given query, utilizing `nexus.ask.recall` without generating responses or auditing.
- **`services.cortex.server.py`:** (🟡 UNCONFIRMED - Assumed to be the Flask application entry point that exposes the `CortexAPI` endpoints as a web service.)

## 4. Key Data Structures / Entities

- **Brick:** A fundamental unit of information, typically a JSON object containing `brick_id`, `content` (raw text), `source_file`, `source_span` (location within the source), and potentially `status` (e.g., PENDING, EMBEDDED).
- **Vector Embedding:** A 384-dimensional floating-point vector representation of a brick's content or a user query, used for semantic similarity search.
- **FAISS Index:** An optimized data structure for efficient nearest-neighbor search over high-dimensional vectors, storing embeddings and mapping back to `brick_id`s.
- **Audit Record:** A JSON line emitted for each `/generate` call, capturing `user_id`, `agent_id`, `brick_ids_used`, `model`, `token_cost`, and `timestamp`.
- **Candidates (for Reranking):** A list of dictionaries, each representing a potentially relevant brick, containing `brick_id`, `base_confidence` (from vector search), and `brick_text`.

## 5. Major Workflows

### 5.1. Content Ingestion / Index Building (Inferred)

1. Raw source content (e.g., Markdown files, code) is processed.
2. **Extraction:** Content is split into granular "bricks" (`nexus.bricks.extractor.py`).
3. **Embedding:** Each brick's text content is converted into a vector embedding (`nexus.vector.embedder.py`).
4. **Indexing:** Embeddings and their corresponding `brick_id`s are added to the FAISS `LocalVectorIndex` (`nexus.vector.local_index.py`).
5. The FAISS index and brick ID mapping are persisted to disk.

### 5.2. Semantic Recall (Query to Bricks)

1. A user query is received (e.g., via `CortexAPI.ask_preview` or internally).
2. **Embedding:** The query is embedded into a vector (`nexus.vector.embedder.py`).
3. **Initial Search:** The query vector is used to search the `LocalVectorIndex` to find the top-K most similar brick embeddings (`nexus.vector.local_index.py`), yielding candidate `brick_id`s and `base_confidence` scores.
4. **Hydration:** The raw text content for each candidate brick is retrieved from the `BrickStore` (`nexus.bricks.brick_store.py`).
5. **Reranking:** Candidates are passed through the `RerankOrchestrator`:
    a. Attempt `LlmReranker` (if available).
    b. If LLM reranker fails, attempt `CrossEncoderReranker` (if available).
    c. If CrossEncoder reranker fails, fallback to `HeuristicReranker`.
6. The reranker assigns a `final_score` to each brick, and the list is sorted by this score.
7. The top relevant bricks (IDs and scores) are returned.

### 5.3. LLM-based Content Generation (Cortex)

1. A user request for generation is received by `CortexAPI.generate` with `user_id`, `agent_id`, `user_query`, and a list of `brick_ids` (memory).
2. **MODE-1 Enforcement (Memory Reload):** For each provided `brick_id`, the raw source text is reloaded from the `BrickStore` (`nexus.bricks.brick_store.py`). If any brick fails to reload, the generation is blocked.
3. **LLM Call:** An LLM is invoked with the `user_query` and the reloaded `context_text` (concatenated brick content). This can be OpenAI's GPT-4o, a local Ollama instance (e.g., Llama3), or a mock fallback.
4. **Audit Logging:** A record of the generation event, including `user_id`, `agent_id`, `brick_ids_used`, `model`, `token_cost`, and `timestamp`, is appended to a `phase3_audit_trace.jsonl` file.
5. The generated LLM response is returned.

## 6. External Integrations / Dependencies

- **`faiss-cpu`:** For efficient vector similarity search.
- **`numpy`:** For numerical operations, especially with vector embeddings.
- **`flask`:** The web framework for the Cortex service.
- **`sentence-transformers`:** For creating embeddings (`all-MiniLM-L6-v2`) and for the `CrossEncoderReranker` (`cross-encoder/ms-marco-TinyBERT-L-2-v2`).
- **`tiktoken`:** (🟡 UNCONFIRMED - Likely used for token counting, possibly for cost estimation or context window management, though not explicitly seen in reviewed code).
- **`openai` (library):** Used for interacting with OpenAI's LLMs (e.g., GPT-4o) if `OPENAI_API_KEY` is set.
- **`requests` (library):** Used for making HTTP requests to local Ollama instances.
- **`llama-cpp-python`:** Required for the `LlmReranker` to interact with local quantized LLMs (e.g., GGUF models).
- **`torch`:** (🟡 UNCONFIRMED - Implicit dependency for `sentence-transformers` and `CrossEncoderReranker`).

## 7. Assumptions & Constraints

- **Deterministic Routing:** Cortex's `/route` endpoint uses hardcoded keyword matching for agent assignment.
- **MODE-1 Enforcement:** Generation requires successful reloading of all referenced brick source text to prevent hallucination or out-of-date context.
- **LLM Availability:** The `/generate` endpoint prioritizes OpenAI, then Ollama, then a mock fallback. At least one must be available for real generation.
- **Local Model Paths:** `LlmReranker` expects quantized LLM models to be present at specified local paths.
- **Embedding Model:** `all-MiniLM-L6-v2` is the fixed embedding model.
- **Cross-Encoder Model:** `cross-encoder/ms-marco-TinyBERT-L-2-v2` is the fixed cross-encoder model.
- **Data Persistence:** FAISS index and brick ID mappings are saved to and loaded from specific paths (`INDEX_PATH`, `BRICK_IDS_PATH`).
- **Audit Log:** All `/generate` calls are mandatorily logged to `phase3_audit_trace.jsonl`.
- **Read-Only Recall:** `CortexAPI.ask_preview` is explicitly designed not to trigger generation or audit logs.

## 8. Open Questions & Future Considerations

- **Scalability of LocalVectorIndex:** How will FAISS perform with a very large number of bricks? Are more advanced FAISS indices (e.g., IVF, HNSW) considered?
- **Brick Extraction Logic:** The detailed implementation of how raw content is transformed into bricks (`extractor.py`) is unclear.
- **Synchronization (`nexus.sync`):** The full workflow and triggers for updating the index are not fully detailed.
- **`tiktoken` Usage:** Confirm actual usage of `tiktoken`.
- **`torch` Direct Dependency:** Confirm if `torch` is a direct or transitive dependency and its specific role.
- **Error Handling Robustness:** Improve error handling and logging, especially for LLM and external API calls.
- **Configuration Management:** More flexible configuration (e.g., model names, paths) beyond `nexus.config`.
- **Agent Management:** How are agents (Jarvis, Architect, etc.) defined and their associated models managed beyond hardcoded routing?
- **Security:** Further secure API endpoints and data handling, particularly concerning audit logs and sensitive information.
- **Testing:** Comprehensive unit and integration tests for all components, especially reranking fallback logic and MODE-1 enforcement.